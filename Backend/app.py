import os
import requests
import polyline
import pandas as pd
import folium
from geopy.distance import geodesic
from flask import send_from_directory
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import timedelta
import jwt
import datetime
import pymysql
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from functools import wraps

pymysql.install_as_MySQLdb()
load_dotenv()
port = os.getenv("PORT", 5000)
# API_URL = "192.168.79.196"
API_URL = "10.4.54.93"
# Initialize Flask app
app = Flask(__name__)
# Update the CORS initialization
CORS(app, 
     resources={r"/api/*": {  
         "origins": ["http://localhost:3300",f'http://{API_URL}:3300'],  
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
         "supports_credentials": True,
         "expose_headers": ["Cross-Origin-Opener-Policy", "Cross-Origin-Resource-Policy"]
     }})


app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:070919@localhost/mapping_app'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

db = SQLAlchemy(app)
# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
bcrypt = Bcrypt(app)

# User Model
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=True)
    google_id = db.Column(db.String(120), unique=True, nullable=True) 
    
# Tambahkan model baru untuk menyimpan data titik gangguan
class Tiang(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cluster = db.Column(db.String(50), nullable=False)
    lokasi = db.Column(db.String(50), nullable=False)
    jarak = db.Column(db.Numeric(6, 3), nullable=False)
    latitude = db.Column(db.Numeric(12, 9), nullable=False)
    longitude = db.Column(db.Numeric(12, 9), nullable=False)

# Create tables
with app.app_context():
    db.create_all()

def generate_token(user_id):
    return jwt.encode(
        {
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        },
        app.config['SECRET_KEY'],
        algorithm='HS256'
    )
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'No token provided'}), 401
            
        try:
            token_parts = auth_header.split(' ')
            if len(token_parts) != 2 or token_parts[0].lower() != 'bearer':
                return jsonify({'error': 'Invalid token format'}), 401
                
            token = token_parts[1]
            
            data = jwt.decode(
                token, 
                app.config['SECRET_KEY'], 
                algorithms=['HS256'],
                options={"verify_signature": True}
            )
            
            current_time = datetime.datetime.utcnow().timestamp()
            if 'exp' in data and data['exp'] < current_time:
                return jsonify({'error': 'Token has expired'}), 401
                
            request.user_id = data['user_id']
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': f'Authentication error: {str(e)}'}), 401
            
        return f(*args, **kwargs)
    
    return decorated_function

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12),
        'iat': datetime.datetime.utcnow(),
        'nbf': datetime.datetime.utcnow()  # Not valid before current time
    }
    
    token = jwt.encode(
        payload,
        app.config['SECRET_KEY'],
        algorithm='HS256'  # Explicit algorithm specification
    )
    return token

class MapBackend:
    def __init__(self):
        self.start_lat, self.start_lon = -7.756111, 110.317792
        self.temp_map_path = os.path.join(os.getcwd(), './templates/temp_map.html')
        self.df = None
        self.clusters = set()
        self.cluster_distances = {}

        self.fetch_tiang_data()
        
    def find_nearby_poles(self, cluster, input_distance):
        if cluster not in self.cluster_distances:
            return None, None, None
        
        distances = sorted(self.cluster_distances[cluster])
        
        tolerance = 0.02
        
        matching_distances = [d for d in distances if abs(d - input_distance) <= tolerance]
        
        if matching_distances:
            closest = min(matching_distances, key=lambda x: abs(x - input_distance))
        else:
            closest = min(distances, key=lambda x: abs(x - input_distance))
        
        before = None
        for d in sorted(distances, reverse=True):
            if d < input_distance - tolerance:  
                before = d
                break
        
        after = None
        for d in sorted(distances):
            if d > input_distance + tolerance:  
                after = d
                break
        
        closest_rows = []
        for matching_distance in matching_distances:
            matching_rows = self.df[(self.df['cluster'] == cluster) & 
                            (self.df['numeric_distance'] == matching_distance)].to_dict('records')
            closest_rows.extend(matching_rows)
        
        if not closest_rows:
            closest_rows = self.df[(self.df['cluster'] == cluster) & 
                            (self.df['numeric_distance'] == closest)].to_dict('records')
        
        before_row = self.df[(self.df['cluster'] == cluster) & 
                        (self.df['numeric_distance'] == before)].iloc[0].to_dict() if before is not None and not self.df[(self.df['cluster'] == cluster) & 
                        (self.df['numeric_distance'] == before)].empty else None
        
        after_row = self.df[(self.df['cluster'] == cluster) & 
                        (self.df['numeric_distance'] == after)].iloc[0].to_dict() if after is not None and not self.df[(self.df['cluster'] == cluster) & 
                        (self.df['numeric_distance'] == after)].empty else None
        
        return closest_rows, before_row, after_row
        
    def fetch_tiang_data(self):
        try:
            tiang_data = Tiang.query.all()
            
            if not tiang_data:
                print("No data found in the Tiang table.")
                return

            data = {
                'cluster': [t.cluster for t in tiang_data],
                'lokasi': [t.lokasi for t in tiang_data],
                'jarak': [t.jarak for t in tiang_data],
                'latitude': [t.latitude for t in tiang_data],
                'longitude': [t.longitude for t in tiang_data]
            }
            
            self.df = pd.DataFrame(data)
            self.clusters = set(self.df['cluster'])

            self.df['numeric_distance'] = self.df['jarak'].apply(self.clean_distance).astype(float)

            self.cluster_distances = {
                cluster: self.df[self.df['cluster'] == cluster]['numeric_distance'].tolist()
                for cluster in self.clusters
            }
            
        except Exception as e:
            print(f"Error fetching data from database: {e}")
            self.df = None
            self.clusters = set()
            self.cluster_distances = {}

    def get_route(self, start_coords, end_coords):
        try:
            url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=polyline"
            response = requests.get(url)
            
            if response.status_code == 200:
                route_data = response.json()
                if route_data["code"] == "Ok":
                    distance = route_data["routes"][0]["distance"] / 1000  # Convert to km
                    geometry = route_data["routes"][0]["geometry"]
                    route_coords = polyline.decode(geometry)
                    return route_coords, distance
                    
            return None, None
            
        except Exception as e:
            print(f"Error getting route: {e}")
            return None, None

    def clean_distance(self, distance_str):
        """Convert distance string to float, removing 'KMS' and 'KM' and handling commas"""
        return float(str(distance_str).replace('KMS', '').replace('KM', '').strip().replace(',', '.'))

    def find_closest_distance(self, cluster, input_distance):
        if cluster not in self.cluster_distances:
            return None, None

        available_distances = self.cluster_distances[cluster]
        closest_numeric = min(available_distances, key=lambda x: abs(x - input_distance))
        
        threshold = 0.02
        
        similar_distances = [d for d in available_distances 
                            if abs(d - closest_numeric) <= threshold]
        
        matched_rows = []
        for dist in similar_distances:
            rows = self.df[
                (self.df['cluster'] == cluster) & 
                (self.df['numeric_distance'] == dist)
            ].to_dict('records')
            matched_rows.extend(rows)
        
        return closest_numeric, matched_rows

    def validate_input(self, cluster, distance):
        if not cluster or not distance:
            return None, "Cluster dan jarak tidak boleh kosong!"
        
        if cluster not in self.clusters:
            return None, f"Cluster {cluster} tidak valid! Cluster yang tersedia: {', '.join(sorted(self.clusters))}"
        
        try:
            input_distance = float(self.clean_distance(distance))
            closest_distance, matched_rows = self.find_closest_distance(cluster, input_distance)
            
            if closest_distance is None or not matched_rows:
                return None, f"Cluster {cluster} tidak memiliki data jarak!"
            
            return matched_rows[0]['jarak'], None
            
        except ValueError:
            return None, "Format jarak tidak valid! Gunakan angka dengan format: 1.5 atau 1,5"
            
    def get_tiang_terlewati(self, cluster, input_distance):
        if self.df is None:
            return []
        self.df['jarak'] = pd.to_numeric(self.df['jarak'], errors='coerce')

        filtered_df = self.df[(self.df['cluster'] == cluster) & (self.df['jarak'] <= float(input_distance))]
        
        return filtered_df.to_dict(orient='records')
    
    def create_map(self, cluster, distance, before_pole=None, after_pole=None):
        if self.df is None:
            return None, "Database tidak tersedia"

        input_distance = float(distance)
        
        tolerance = 0.02
        
        matched_rows = self.df[
            (self.df['cluster'] == cluster) & 
            (abs(self.df['jarak'].astype(float) - input_distance) <= tolerance)
        ].to_dict('records')
        
        if not matched_rows:
            cluster_poles = self.df[self.df['cluster'] == cluster]
            if cluster_poles.empty:
                return None, "Cluster tidak ditemukan"
                
            cluster_poles['jarak_float'] = cluster_poles['jarak'].astype(float)
            closest_distance = (cluster_poles['jarak_float'] - input_distance).abs().min()
            
            matched_rows = cluster_poles[
                abs(cluster_poles['jarak_float'] - input_distance) == closest_distance
            ].to_dict('records')
        
        max_matched_distance = max([float(row['jarak']) for row in matched_rows])
        tiang_terlewati = self.get_tiang_terlewati(cluster, max_matched_distance)
        
        if not tiang_terlewati:
            return None, "Data tidak ditemukan"
        
        end_points = [(float(row['latitude']), float(row['longitude'])) for row in matched_rows]
        
        all_lats = [self.start_lat] + [point[0] for point in end_points]
        all_lons = [self.start_lon] + [point[1] for point in end_points]
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles='OpenStreetMap')

        # Add start marker (Gardu Induk)
        folium.Marker(
            [self.start_lat, self.start_lon],
            popup='Gardu Induk (68V9+G5V)',
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(m)

        # Add markers for all matched destinations - ensure each one is clearly visible
        for i, row in enumerate(matched_rows):
            end_lat, end_lon = float(row['latitude']), float(row['longitude'])
            lokasi = row['lokasi']
            jarak = row['jarak']
            
            # Prepare popup for the destination point
            image_path = f"../images/{lokasi}.png"
            popup_html = f"""
            <div>
                <h4>Titik Gangguan {lokasi}</h4>
                <p>Cluster: {cluster}</p>
                <p>Estimasi Jarak Gangguan : {jarak} KMS</p>
                <img src="{image_path}" alt="Gambar Gangguan" width="100">
                <p>Koordinat: {end_lat}, {end_lon}</p>
            </div>
            """
            
            # Add destination marker - use a distinctive icon/color for each point when there are multiple
            if len(matched_rows) > 1:
                # Use different colors for multiple points to make them distinct
                marker_colors = ['red', 'purple', 'darkblue', 'darkgreen', 'cadetblue', 'black']
                marker_color = marker_colors[i % len(marker_colors)]
                
                # Use different icon types to distinguish multiple points further
                icon_types = ['info-sign', 'star', 'flag', 'bookmark']
                icon_type = icon_types[i % len(icon_types)]
                
                folium.Marker(
                    [end_lat, end_lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{lokasi} - {jarak} KMS",  # Add tooltip for quick identification
                    icon=folium.Icon(color=marker_color, icon=icon_type)
                ).add_to(m)
                
                # Add circle to highlight each point
                folium.Circle(
                    radius=10,
                    location=[end_lat, end_lon],
                    color=marker_color,
                    fill=True,
                    fill_opacity=0.4,
                    tooltip=f"{lokasi} - {jarak} KMS"
                ).add_to(m)
            else:
                # Single point - use standard marker
                folium.Marker(
                    [end_lat, end_lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{lokasi} - {jarak} KMS",
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m)

        # Sort poles by distance for proper routing
        sorted_tiang = sorted(tiang_terlewati, key=lambda x: float(x['jarak']))
        
        # Create a list of all waypoints in order
        waypoints = [(self.start_lat, self.start_lon)]  # Start with the Gardu Induk
        
        # Add all poles as waypoints
        for tiang in sorted_tiang:
            tiang_lat = float(tiang['latitude'])
            tiang_lon = float(tiang['longitude'])
            waypoints.append((tiang_lat, tiang_lon))
        
        # Setup custom icon for poles
        tiang_icon_path = "static/icons/tiang.ico"
        
        # Add markers for all poles that have been passed
        for tiang in tiang_terlewati:
            # Check if this pole is one of our matched points
            is_matched = any(
                tiang['lokasi'] == row['lokasi'] for row in matched_rows
            )
            
            # Skip if this is one of our destination points (we've already marked them)
            if is_matched:
                continue
                
            # For regular poles along the way
            if os.path.exists(tiang_icon_path):
                icon = folium.CustomIcon(icon_image=tiang_icon_path, icon_size=(30, 30))
            else:
                icon = folium.Icon(color='orange', icon='bolt')
            
            image_path2 = f"../images/{tiang['lokasi']}.png"
            popup_html_tiang_terlewati = f"""
            <div>
                <h4>Titik Gangguan {tiang['lokasi']}</h4>
                <p>Cluster: {tiang['cluster']}</p>
                <p>Estimasi Jarak Gangguan : {tiang['jarak']} KMS</p>
                <img src="{image_path2}" alt="Gambar Gangguan" width="100">
                <p>Koordinat: {tiang['latitude']}, {tiang['longitude']}</p>
            </div>
            """
            folium.Marker(
                [float(tiang['latitude']), float(tiang['longitude'])],
                popup=folium.Popup(popup_html_tiang_terlewati, max_width=300),
                icon=icon
            ).add_to(m)
        
        route_coords, route_distance = self.get_route((self.start_lat, self.start_lon), (end_lat, end_lon))
        if route_coords:
            folium.PolyLine(
                locations=route_coords,
                weight=3,
                color='blue',
                opacity=0.8,
                popup=f'Jarak: {route_distance:.2f} km'
            ).add_to(m)

        folium.LayerControl().add_to(m)
        m.save(self.temp_map_path)
        
        actual_distance = route_distance if route_distance else geodesic(
            (self.start_lat, self.start_lon), 
            (end_lat, end_lon)
        ).kilometers
        
        # If we have multiple matched locations, add a special route connecting them
        if len(matched_rows) > 1:
            matching_points = [(float(row['latitude']), float(row['longitude'])) for row in matched_rows]
            folium.PolyLine(
                matching_points,
                color='red',
                weight=3,
                dash_array='5, 10',
                opacity=0.7,
                tooltip='Titik-titik dengan jarak yang sama'
            ).add_to(m)
        
        # Calculate distances for each destination
        distances = []
        for end_lat, end_lon in end_points:
            # Get the direct route from Gardu Induk to the destination for comparison
            route_coords, route_distance = self.get_route(
                (self.start_lat, self.start_lon), 
                (end_lat, end_lon)
            )
            
            actual_distance = geodesic((self.start_lat, self.start_lon), (end_lat, end_lon)).kilometers
            distances.append(actual_distance)
        
        # Calculate the total distance through all poles
        total_pole_distance = 0
        for i in range(len(waypoints) - 1):
            pole_segment = geodesic(waypoints[i], waypoints[i+1]).kilometers
            total_pole_distance += pole_segment
        
        # Add layer control and save the map
        folium.LayerControl().add_to(m)
        m.save(self.temp_map_path)

        # Prepare response with all matched locations
        return {
            'map_url': f'http://{API_URL}:{port}/map',
            'distance': sum(distances) / len(distances),  # Average distance
            'tiang_terlewati': tiang_terlewati,
            'pole_route_distance': total_pole_distance,
            'multiple_locations': len(matched_rows) > 1,
            'matched_locations': [
                {
                    'distance': float(row['jarak']),
                    'lokasi': row['lokasi'],
                    'lat': float(row['latitude']),
                    'lon': float(row['longitude'])
                } for row in matched_rows
            ]
        }, None

with app.app_context():
    backend = MapBackend()

@app.route("/")
def home():
    return "Backend is running!"
    
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', f'http://{API_URL}:3300')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Cross-Origin-Opener-Policy', 'same-origin-allow-popups')
    response.headers.add('Cross-Origin-Resource-Policy', 'cross-origin')
    return response

@app.after_request
def add_cookie_attributes(response):
    if 'Set-Cookie' in response.headers:
        response.headers.set('Set-Cookie', response.headers.get('Set-Cookie') + '; SameSite=Lax')
    return response

@app.route('/images/<path:filename>')
def serve_image(filename):
    return send_from_directory('Data/images', filename)

@app.route('/map')
def serve_map():
    return render_template('temp_map.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    print("Received data:", data)  # Tambahkan logging

    if Users.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400

    if Users.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 400

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_user = Users(
        username=data['username'],
        email=data['email'],
        password=hashed_password
    )

    db.session.add(new_user)
    db.session.commit()

    token = generate_token(new_user.id)

    return jsonify({
        'token': token,
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email
        }
    })

@app.route('/api/verify-token', methods=['GET'])
@login_required
def verify_token():
    return jsonify({'valid': True})
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = Users.query.filter_by(email=data['email']).first()
    
    if user and bcrypt.check_password_hash(user.password, data['password']):
        token = generate_token(user.id)
        
        # ✅ Perbaiki agar backend mengembalikan `token` dan `user`
        return jsonify({
            'token': token,
            'user': {
                'username': user.username,
            }
        })

    return jsonify({'error': 'Username atau Password Salah'}), 401



@app.route('/api/google-login', methods=['POST'])
def google_login():
    token = request.json.get('token')
    
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        email = idinfo['email']
        user = Users.query.filter_by(email=email).first()
        
        if not user:
            user = Users(
                username=idinfo['name'],
                email=email,
                google_id=idinfo['sub']
            )
            db.session.add(user)
            db.session.commit()
        
        token = generate_token(user.id)
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
    
    except ValueError:
        return jsonify({'error': 'Invalid token'}), 401
@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    response = jsonify({"message": "Logged out"})
    response.set_cookie('session', '', expires=0)  # Clear session cookies
    return response
# Protected API routes
@app.route('/api/clusters', methods=['GET'])
@login_required
def get_clusters():
    if not backend.clusters:
        return jsonify({'error': 'No clusters available'}), 500
    return jsonify({'clusters': list(backend.clusters)})

@app.route('/api/validate', methods=['POST'])
@login_required
def validate_distance():
    data = request.get_json()
    cluster = data.get('cluster')
    distance = data.get('distance')
    validated_distance, error = backend.validate_input(cluster, distance)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'valid': True, 'distance': validated_distance})

@app.route('/api/tiang', methods=['GET'])
@login_required
def get_tiang_data():
    if backend.df is None:
        return jsonify({'error': 'Database tidak tersedia'}), 500

    tiang_list = backend.df.to_dict(orient='records')
    return jsonify(tiang_list)

@app.route('/api/map', methods=['POST'])
@login_required
def generate_map_data():
    data = request.get_json()
    cluster = data.get('cluster')
    input_distance = data.get('distance')

    if not cluster or not input_distance:
        return jsonify({'error': 'Cluster atau jarak tidak boleh kosong!'}), 400

    try:
        input_distance = float(input_distance)
    except ValueError:
        return jsonify({'error': 'Format jarak tidak valid!'}), 400

    # Find nearby poles (with enhanced behavior for multiple points)
    closest_rows, before_row, after_row = backend.find_nearby_poles(cluster, input_distance)
    
    if not closest_rows:
        return jsonify({'error': 'Tidak ada jarak yang tersedia dalam cluster ini!'}), 400

    # Create the map using the actual input distance to find points within tolerance
    map_data, error = backend.create_map(cluster, input_distance)
    
    if error:
        return jsonify({'error': error}), 400
    
    # Add coordinate information for each found point
    point_details = []
    for row in closest_rows:
        point_details.append({
            'lokasi': row['lokasi'],
            'jarak': float(row['jarak']),
            'lat': float(row['latitude']),
            'lon': float(row['longitude']),
            'coordinates': f"{float(row['latitude'])}, {float(row['longitude'])}"
        })
    
    # Add nearby poles information to the response
    map_data['nearby_poles'] = {
        'input_distance': input_distance,
        'multiple_points_found': len(closest_rows) > 1,
        'point_details': point_details,
        'before_pole': {
            'distance': float(before_row['jarak']),
            'lokasi': before_row['lokasi'],
            'lat': float(before_row['latitude']),
            'lon': float(before_row['longitude'])
        } if before_row is not None else None,
        'after_pole': {
            'distance': float(after_row['jarak']),
            'lokasi': after_row['lokasi'],
            'lat': float(after_row['latitude']),
            'lon': float(after_row['longitude'])
        } if after_row is not None else None
    }
    
    return jsonify(map_data)

# Update open browser route to support selecting between multiple coordinates
@app.route('/api/open-browser', methods=['POST'])
@login_required
def open_map_in_browser():
    data = request.get_json()
    cluster = data.get('cluster')
    distance = data.get('distance')
    selected_lokasi = data.get('lokasi')  # Optional parameter to select one location
    
    try:
        input_distance = float(distance)
        
        # Use tolerance for finding similar distances
        tolerance = 0.02
        
        # Find all rows within tolerance of the input distance
        rows = backend.df[
            (backend.df['cluster'] == cluster) & 
            (abs(backend.df['jarak'].astype(float) - input_distance) <= tolerance)
        ]
        
        # If user specified a specific location, filter for it
        if selected_lokasi and not rows.empty:
            selected_rows = rows[rows['lokasi'] == selected_lokasi]
            if not selected_rows.empty:
                rows = selected_rows
        
        if rows.empty:
            # If no match within tolerance, find closest
            cluster_poles = backend.df[backend.df['cluster'] == cluster]
            if cluster_poles.empty:
                return jsonify({'error': 'Cluster tidak ditemukan'}), 404
                
            # Find the closest distance
            cluster_poles['jarak_float'] = cluster_poles['jarak'].astype(float)
            closest_distance = (cluster_poles['jarak_float'] - input_distance).abs().min()
            
            # Get all poles at this closest distance
            rows = cluster_poles[
                abs(cluster_poles['jarak_float'] - input_distance) == closest_distance
            ]
        
        if rows.empty:
            return jsonify({'error': 'Lokasi tidak ditemukan untuk cluster dan jarak yang diberikan'}), 404
        
        # Return all matching locations
        locations = []
        for _, row in rows.iterrows():
            end_lat, end_lon = float(row['latitude']), float(row['longitude'])
            locations.append({
                'lokasi': row['lokasi'],
                'jarak': float(row['jarak']),
                'lat': end_lat,
                'lon': end_lon,
                'coordinates': f"{end_lat}, {end_lon}",
                'url': f"https://www.google.com/maps/search/?api=1&query={end_lat},{end_lon}"
            })

        return jsonify({
            'success': True, 
            'multiple_locations': len(locations) > 1,
            'locations': locations
        })

    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(port), debug=True)
