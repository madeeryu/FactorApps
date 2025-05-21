import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { GoogleOAuthProvider } from '@react-oauth/google';
import MappingInterface from "./components/MappingInterface";
import LoginPage from "./components/LoginPage";
import API_BASE_URL from "./components/config"; 
import RegisterPage from "./components/RegisterPage";
import "./styles/App.css";
function app() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize authentication state
  useEffect(() => {
    const token = localStorage.getItem("token");
    setIsAuthenticated(!!token);
    setIsLoading(false);
  }, []);

  // Monitor localStorage changes
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem("token");
      setIsAuthenticated(!!token);
    };

    window.addEventListener("storage", checkAuth);
    return () => window.removeEventListener("storage", checkAuth);
  }, []);

  // Verify token validity with backend
  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          const response = await fetch(`${API_BASE_URL}/api/verify-token`, {
            method: "GET",
            headers: {
              "Authorization": `Bearer ${token}`
            },
            credentials: "include"
          });

          if (!response.ok) {
            // Token is invalid or expired
            handleLogout();
          }
        } catch (error) {
          console.error("Token verification failed:", error);
          handleLogout();
        }
      }
      setIsLoading(false);
    };

    verifyToken();
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem("token");
      if (token) {
        await fetch(`${API_BASE_URL}/api/logout`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          },
          credentials: "include"
        });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      setIsAuthenticated(false);
    }
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId="490656607647-1hcvkgmm33k5dlppeebq8841v8ustv3o.apps.googleusercontent.com">
      <Routes>
        <Route 
          path="/login" 
          element={!isAuthenticated ? (
            <LoginPage onLogin={handleLogin} />
          ) : (
            <Navigate to="/mapping" replace />
          )}
        />
        <Route 
          path="/register" 
          element={!isAuthenticated ? (
            <RegisterPage onRegister={handleLogin} />
          ) : (
            <Navigate to="/mapping" replace />
          )}
        />
        <Route 
          path="/" 
          element={isAuthenticated ? (
            <Navigate to="/mapping" replace />
          ) : (
            <Navigate to="/login" replace />
          )}
        />
        <Route 
          path="/mapping" 
          element={isAuthenticated ? (
            <MappingInterface onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )}
        />
        <Route 
          path="*" 
          element={<Navigate to="/" replace />} 
        />
      </Routes>
    </GoogleOAuthProvider>
  );
}

export default app;