import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import API_BASE_URL from "./config"; 
import "../styles/RegisterPage.css";  // Import file CSS terpisah
import logoPLN from "./logo/icon.png";
const RegisterPage = ({ onRegister }) => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, email, password }),
      });

      const data = await response.json();
      console.log("Response from backend:", data); // Debugging

      if (response.ok) {
        localStorage.setItem("token", data.token);
        localStorage.setItem("user", JSON.stringify(data.user));

        setSuccess("Registrasi berhasil! Mengalihkan ke halaman utama...");

        onRegister(); // Update state isAuthenticated di App.jsx

        setTimeout(() => {
          navigate("/mapping");
        }, 1000);
      } else {
        setError(data.error || "Registrasi gagal.");
      }
    } catch (err) {
      setError("Gagal terhubung ke server. Coba lagi.");
    }
  };

  return (
    <div className="register-container">
      <div className="register-box">
  
        {/* <h1 className="register-title">Register PLN</h1> */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'left', gap: '4px', marginBottom: '-25px', fontFamily:'system-ui', fontSize:'18px',fontWeight:'bold' }}>
            Ayo Bergabung!
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'left', gap: '4px', marginBottom: '30px' }}>
            <h1 style={{ fontSize: '64px', fontFamily:'fantasy'}}>
              <span style={{ color: '#007bff' }}>Fac</span>
              <span style={{ color: '#ffd700' }}>Tor</span>
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', fontSize: '14px', color: '#666', position:'relative', top:'20px' }}>
              by
              <img 
                src={logoPLN}
                style={{ margin: '0 4px', height: '24px', width: '24px' }}
                />
              <span style={{ fontWeight: '600', color:'#00afef'}}>PLN</span>
            </div>
          </div>
        </div>
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)}
              required 
            />
          </div>

          <div className="form-group">
            <label>Email</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>

          <button type="submit" className="register-button">Register</button>
        </form>

        <div className="login-link">
          <p>Sudah punya akun? <button onClick={() => navigate("/login")}>Login</button></p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;