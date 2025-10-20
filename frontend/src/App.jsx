import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Auditoria from "./pages/Auditoria.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import Resultado from "./pages/Resultado.jsx";
import Votacao from "./pages/Votacao.jsx";

const TOKEN_KEY = "athenas-token";

const ProtectedRoute = ({ isAuthenticated, children }) => {
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY));
  const [wallet, setWallet] = useState(localStorage.getItem("athenas-wallet"));

  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }, [token]);

  const handleAuthSuccess = ({ accessToken, walletAddress }) => {
    setToken(accessToken);
    setWallet(walletAddress);
    localStorage.setItem("athenas-wallet", walletAddress);
  };

  const handleLogout = () => {
    setToken(null);
    setWallet(null);
    localStorage.removeItem("athenas-wallet");
  };

  const isAuthenticated = Boolean(token);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      <Navbar isAuthenticated={isAuthenticated} onLogout={handleLogout} wallet={wallet} />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/login" element={<Login onSuccess={handleAuthSuccess} />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute isAuthenticated={isAuthenticated}>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/votacao/:id"
            element={
              <ProtectedRoute isAuthenticated={isAuthenticated}>
                <Votacao wallet={wallet} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/resultado/:id"
            element={
              <ProtectedRoute isAuthenticated={isAuthenticated}>
                <Resultado />
              </ProtectedRoute>
            }
          />
          <Route
            path="/auditoria"
            element={
              <ProtectedRoute isAuthenticated={isAuthenticated}>
                <Auditoria />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
