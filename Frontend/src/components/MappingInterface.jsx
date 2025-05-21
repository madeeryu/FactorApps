import React, { useState, useEffect } from 'react';
import { Search, LogOut, AlertCircle } from 'lucide-react';
import API_BASE_URL from "./config"; // Import API URL
import '../styles/MappingInterface.css'

const MappingInterface = ({ onLogout }) => {
  const [selectedCluster, setSelectedCluster] = useState("");
  const [searchValue, setSearchValue] = useState("");
  const [clusters, setClusters] = useState([]);
  const [filteredClusters, setFilteredClusters] = useState([]); // Tambahkan ini
  const [showSuggestions, setShowSuggestions] = useState(false); // Tambahkan ini
  const [searchCluster, setSearchCluster] = useState(""); 
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [mapData, setMapData] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [whatsappNumber, setWhatsappNumber] = useState('');
  const [mapLoading, setMapLoading] = useState(true);

  

  

  const getLocationCoordinates = () => {
    // Multiple ways to extract coordinates
    if (mapData?.matched_locations?.[0]) {
      return {
        lat: mapData.matched_locations[0].lat,
        lon: mapData.matched_locations[0].lon
      };
    }
    
    if (mapData?.nearby_poles?.point_details?.[0]) {
      return {
        lat: mapData.nearby_poles.point_details[0].lat,
        lon: mapData.nearby_poles.point_details[0].lon
      };
    }
    
    // Fallback
    return { lat: 'N/A', lon: 'N/A' };
  };
  // Hardcoded WhatsApp numbers from Excel data
  const whatsappNumbers = [
    { id: "1", name: "Pak Liga", number: "6281217163391" },
    { id: "2", name: "Pak Dwiko", number: "6281288009890" },
    { id: "3", name: "Pak Alfi", number: "628112651771" },
    { id: "4", name: "Ahmad", number: "6287743639004" },
  ];
  
  const authenticatedFetch = async (url, options = {}) => {
    const token = localStorage.getItem("token");
    if (!token) {
      throw new Error("No token found");
    }
  
    // Ensure we're using the full URL
    const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
    
    const defaultHeaders = {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    };
  
    const response = await fetch(fullUrl, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
      credentials: "include",
    });
  
    if (response.status === 401) {
      handleLogout();
      throw new Error("Unauthorized");
    }
  
    return response;
  };

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
    }

    const fetchClusters = async () => {
      try {
        const response = await authenticatedFetch(`${API_BASE_URL}/api/clusters`);
        const data = await response.json();
        setClusters(data.clusters || []); // Pastikan default-nya array kosong
      } catch (error) {
        console.error("Error fetching clusters:", error);
        setClusters([]); // Pastikan tidak undefined
        setError("Failed to load clusters. Please try again.");
      }
    };
    

    fetchClusters();
  }, []);

  useEffect(() => {
    if (searchCluster) {
      const results = clusters.filter(cluster =>
        cluster.toLowerCase().includes(searchCluster.toLowerCase())
      );
      setFilteredClusters(results);
      setShowSuggestions(true);
    } else {
      setShowSuggestions(false);
    }
  }, [searchCluster, clusters]);

  const handleSelectCluster = (cluster) => {
    setSelectedCluster(cluster);
    setSearchCluster(cluster);
    setShowSuggestions(false);
  };

  const handleLogout = async () => {
    try {
      await authenticatedFetch(`${API_BASE_URL}/api/logout`, {
        method: "POST",
      });
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      onLogout();
    }
  };

  const handleOpenInBrowser = async () => {
    if (!selectedCluster || !searchValue) {
      setError("Pilih cluster dan masukkan jarak terlebih dahulu");
      return;
    }
  
    try {
      const response = await authenticatedFetch(`${API_BASE_URL}/api/open-browser`, {
        method: "POST",
        body: JSON.stringify({
          cluster: selectedCluster,
          distance: searchValue
        })
      });
  
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "Gagal membuka peta di browser");
        return;
      }
  
      // Membuka Google Maps di perangkat pengguna
      window.open(data.url, "_blank");
  
    } catch (error) {
      console.error("Error opening map in browser:", error);
      setError("Gagal membuka peta di browser. Silakan coba lagi.");
    }
  };
  

  const handleSearch = async () => {
    try {
      setMapLoading(true);
      setLoading(true);
      setError("");
      setMapData(null);

      const validateResponse = await authenticatedFetch(`${API_BASE_URL}/api/validate`, {
        method: "POST",
        body: JSON.stringify({ cluster: selectedCluster, distance: searchValue }),
      });

      const validateData = await validateResponse.json();
      if (!validateResponse.ok) {
        setError(validateData.error);
        return;
      }

      const mapResponse = await authenticatedFetch(`${API_BASE_URL}/api/map`, {
        method: "POST",
        body: JSON.stringify({ cluster: selectedCluster, distance: searchValue }),
      });

      const mapData = await mapResponse.json();
      if (!mapResponse.ok) {
        setError(mapData.error);
        return;
      }

      setMapData(mapData);
      setIsModalOpen(true);
    } catch (err) {
      setError("Terjadi kesalahan. Silakan coba lagi.");
    } finally {
      setLoading(false);
    }
  };
  
  const sendToWhatsApp = () => {
    if (!whatsappNumber) {
      setError("Pilih nomor WhatsApp terlebih dahulu!");
      return;
    }
  
    const selectedNumber = whatsappNumbers.find(num => num.id === whatsappNumber)?.number;
    if (!selectedNumber) {
      setError("Nomor WhatsApp tidak valid!");
      return;
    }
  
    if (!mapData) {
      setError("Tidak ada data peta yang tersedia!");
      return;
    }
  
    const { lat, lon } = getLocationCoordinates();
    
    // Fallback to default values if coordinates are not found
    const lokasi = mapData?.nearby_poles?.point_details?.[0]?.lokasi || 
                   mapData?.matched_locations?.[0]?.lokasi || 
                   "Unknown";
    
    // Calculate route distance, with multiple fallback options
    const routeDistance = mapData.pole_route_distance || 
                          mapData.distance || 
                          (mapData.nearby_poles?.input_distance) || 
                          0;
    
    let message = `Lokasi Tiang: ${lokasi}\nCluster: ${selectedCluster}\nEstimasi Jarak Rute: ${routeDistance.toFixed(2)} KM\nKoordinat: ${lat}, ${lon}\nMaps: https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
    
    // Add nearby poles info if available
    if (mapData.nearby_poles) {
      message += `\n\nJarak yang dicari: ${mapData.nearby_poles.input_distance} KMS`;
      
      if (mapData.nearby_poles.before_pole) {
        message += `\nTiang sebelumnya: ${mapData.nearby_poles.before_pole.lokasi} (${mapData.nearby_poles.before_pole.distance} KMS)`;
      }
      
      if (mapData.nearby_poles.after_pole) {
        message += `\nTiang selanjutnya: ${mapData.nearby_poles.after_pole.lokasi} (${mapData.nearby_poles.after_pole.distance} KMS)`;
      }
    }
    
    const encodedMessage = encodeURIComponent(message);
    const whatsappUrl = `https://wa.me/${selectedNumber}?text=${encodedMessage}`;
  
    window.open(whatsappUrl, '_blank');
  };
  
  return (
    <div className="app-container">
      <header className="header">
        <div className="logo">
          <span className="logo-route">Fac</span>
          <span className="logo-guard">Tor</span>
        </div>
        <div className="user-section">
          
          {user && <span className="username">{user.username}</span>}
          <button onClick={handleLogout} className="logout-button">
            <LogOut size={20} />
          </button>
        </div>
      </header>

      <main className="main-content">


        <h1 className="title">
          Temukan titik <span className="highlight">lokasi gangguan</span> secara akurat !
        </h1>

        <div className="form-container">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

        <div className="select-wrapper">
          <input
            type="text"
            placeholder="Cari Cluster..."
            value={searchCluster}
            onChange={(e) => setSearchCluster(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)} // Auto-hide setelah input kehilangan fokus
            className="search-input"
          />
          
          {showSuggestions && filteredClusters.length > 0 && (
            <ul className="suggestions-list">
              {filteredClusters.map((cluster) => (
                <li 
                  key={cluster} 
                  onMouseDown={() => handleSelectCluster(cluster)} // Gunakan onMouseDown agar klik langsung diterapkan
                >
                  {cluster}
                </li>
              ))}
            </ul>
          )}
        </div>


          <input
            type="text"
            placeholder="Masukan Jarak cth. 1.5"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            className="distance-input"
          />


          <div className="button-grid">
            <button
              onClick={handleSearch}
              disabled={loading}
              className="search-button"
            >
              <Search size={20} />
              <span>Search</span>
            </button>

            <button
              onClick={handleOpenInBrowser}
              className="browser-button"
            >
              Open in Browser
            </button>
          </div>
        </div>
      </main>
      
      {loading && (
          <div className="loading-overlay">
            <div className="loading-spinner"></div>
            <p>Loading Peta...</p>
          </div>
      )}

      {isModalOpen && mapData && (
        <div className="modal-overlay">
          <div className="modal">
          <h2 className="nearby-poles-title">
                  <AlertCircle size={16} className="icon-alert" />
                  INFORMASI TIANG GANGGUAN: 
                </h2>
            {mapData.nearby_poles && (
              <div className="nearby-poles-info">
                <div className="nearby-poles-content">
                  <p>Jarak yang dicari: <span className="highlight">{mapData.nearby_poles.input_distance} KMS</span></p>
                  <p>Nama Tiang: <span className="highlight">
                      {mapData?.matched_locations?.[0]?.lokasi || 
                      mapData?.nearby_poles?.point_details?.[0]?.lokasi || 
                      "Tidak ditemukan"}
                    </span>
                  </p>

                  <p>Jarak Titik Tiang: <span className="highlight">{mapData.nearby_poles.matched_distance} KMS</span></p>
                  <p>Jumlah Tiang Dilewati: <span className="highlight">{mapData.tiang_terlewati ? mapData.tiang_terlewati.length : 0}</span></p>
                  
                  {mapData.nearby_poles.before_pole && (
                    <p>Tiang sebelumnya: <span className="highlight">{mapData.nearby_poles.before_pole.lokasi}</span> ({mapData.nearby_poles.before_pole.distance} KMS)</p>
                  )}
                  
                  {mapData.nearby_poles.after_pole && (
                    <p>Tiang selanjutnya: <span className="highlight">{mapData.nearby_poles.after_pole.lokasi}</span> ({mapData.nearby_poles.after_pole.distance} KMS)</p>
                  )}

                  {/* Update this line in your modal JSX */}
                  <p>Koordinat: <span className="highlight">
                    {getLocationCoordinates().lat}, {getLocationCoordinates().lon}
                  </span>
                  </p>
                </div>
              </div>
            )}
            
            {/* List of passed poles */}
            {mapData.tiang_terlewati && mapData.tiang_terlewati.length > 0 && (
              <div className="passed-poles-info">
                <h3 className="passed-poles-title">
                  <AlertCircle size={16} className="icon-alert" />
                  Tiang yang Dilewati (Rute)
                </h3>
                <div className="passed-poles-list">
                  {mapData.tiang_terlewati.map((tiang, index) => (
                    <div key={index} className="pole-item">
                      <span className="pole-number">{index + 1}.</span>
                      <span className="pole-location">{tiang.lokasi}</span>
                      <span className="pole-distance">({tiang.jarak} KMS)</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="map-container">
            {mapLoading && (
              <div className="loading-map-overlay">
                <div className="loading-spinner"></div>
                <p>Memuat Peta...</p>
              </div>
            )}

            <iframe 
              src={mapData.map_url} 
              className={`map-frame ${mapLoading ? 'hidden' : ''}`} // 🔹 Sembunyikan iframe saat loading
              title="Map Display"
              onLoad={() => setMapLoading(false)} // 🔹 Hapus loading setelah iframe selesai dimuat
            />
          </div>
            
            <select
              value={whatsappNumber}
              onChange={(e) => setWhatsappNumber(e.target.value)}
              className="whatsapp-input"
            >
              <option value="">Pilih Nomor WhatsApp</option>
              {whatsappNumbers.map((num) => (
                <option key={num.id} value={num.id}>
                  {num.number} ({num.name})
                </option>
              ))}
            </select>
            
            <button className="send-whatsapp-button" onClick={sendToWhatsApp}>
              Kirim ke WhatsApp
            </button>
            <div className="modal-buttons">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="close-button">Tutup</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MappingInterface;