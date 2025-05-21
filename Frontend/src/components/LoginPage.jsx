import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GoogleLogin } from "@react-oauth/google";
import API_BASE_URL from "./config"; 
import "../styles/LoginPage.css";
import logoPLN from "./logo/icon.png";




const LoginPage = ({ onLogin }) => {
  const [credentials, setCredentials] = useState({
    email: "",
    password: ""
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setCredentials({
      ...credentials,
      [e.target.name]: e.target.value
    });
  };

  // Regular email/password login
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (!credentials.email.includes('@') || credentials.password.length < 6) {
      setError("Email harus valid dan password minimal 6 karakter");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Login gagal, periksa kembali email dan password!");
      }

      const data = await response.json();

      if (data.token) {
        localStorage.setItem("token", data.token);
        localStorage.setItem("user", JSON.stringify(data.user));
        onLogin();
        navigate("/mapping");
      }
    } catch (error) {
      console.error("Error saat login:", error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  // Google login success handler with error retry
  const handleGoogleSuccess = async (credentialResponse) => {
    const maxRetries = 3;
    let retryCount = 0;

    const attemptGoogleLogin = async () => {

      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error("Request timeout")), 10000)
      );

      try {
        const response = await Promise.race([fetch(`${API_BASE_URL}/api/google-login`, {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest"
          },
          credentials: "include",
          body: JSON.stringify({
            token: credentialResponse.credential
          }),
        }),
        timeoutPromise
      ]);

        if (!response.ok) {
          throw new Error("Google login failed");
        }

        const data = await response.json();
        
        if (data.token) {
          localStorage.setItem("token", data.token);
          localStorage.setItem("user", JSON.stringify(data.user));
          onLogin();
          navigate("/mapping");
        }
      } catch (error) {
        console.error("Google login error:", error);
        if (retryCount < maxRetries) {
          retryCount++;
          console.log(`Retrying Google login attempt ${retryCount} of ${maxRetries}`);
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second before retry
          return attemptGoogleLogin();
        }
        setError("Google login failed. Please try again.");
      }
    };

    await attemptGoogleLogin();
  };

  // Google login error handler
  const handleGoogleError = () => {
    console.error("Google Sign-In Error");
    setError("Google login failed. Please try again.");
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div style={{position:'relative', top:'20px', }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'left', gap: '4px', marginBottom: '-25px', fontFamily:'system-ui', fontSize:'18px',fontWeight:'bold' }}>
            Welcome To
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
        {/* <h2 className="login-title">Login</h2> */}
        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="error-message">{error}</div>}
          <div className="e-txt">
            <p className="txt-e">Email</p>
          </div>
          <div className="input-group">
            <input
              name="email"
              type="email"
              required
              className="login-input"
              placeholder="Email address"
              value={credentials.email}
              onChange={handleChange}
            />
          </div>
          <div className="pas-txt">
            <p className="txt-p">Password</p>
          </div>
          <div className="input-group">
            <input
              name="password"
              type="password"
              required
              className="login-input"
              placeholder="Password"
              value={credentials.password}
              onChange={handleChange}
            />
          </div>

          <button type="submit" disabled={loading} className="login-button">
            {loading ? "login in..." : "Log in"}
          </button>

          <div className="divider">
            <span>OR</span>
          </div>

          <div className="google-login-container">
          <GoogleLogin
            clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}  // 🔥 Tambahkan clientId
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
            shape="rectangular"
            theme="filled_white"
            text="signin_with"
            useOneTap
          />
          </div>
        </form>

        <div className="register-link">
          <p>Belum punya akun? <button onClick={() => navigate("/register")}>Register</button></p>
        </div>

      </div>
    </div>
  );
};

export default LoginPage;