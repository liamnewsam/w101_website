// src/pages/LoginPage.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import LoginForm from "../components/LoginForm";
import GuestButton from "../components/GuestButton";
import { BACKEND_URL } from "../config";
import "./LoginPage.css";

function jwtPayload(token) {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(b64));
  } catch {
    return {};
  }
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { connected, updateToken } = useSocket();
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState("");

  useEffect(() => {
    if (!connected) return;
    const token = localStorage.getItem("token");
    const payload = jwtPayload(token || "");
    navigate(payload.type === "demo" ? "/rl-demo" : "/menu");
  }, [connected]);

  async function handleRLDemo() {
    setDemoLoading(true);
    setDemoError("");
    try {
      const res = await fetch(`${BACKEND_URL}/auth/demo`, { method: "POST" });
      const data = await res.json();
      if (!data.token) throw new Error("No token returned");
      updateToken(data.token);
      // Navigate immediately — ProtectedRoute shows Loading until the socket
      // connects, then renders the demo lobby.
      navigate("/rl-demo");
    } catch (e) {
      setDemoError("Could not start demo. Is the server running?");
      setDemoLoading(false);
    }
  }

  return (
    <div className="login-page">
      <h1 className="login-page-title">Wizard101</h1>
      <p className="login-page-subtitle">Sign in to continue your adventure</p>
      <LoginForm />
      <div className="guest-divider" style={{ width: "100%", maxWidth: 360 }}>or</div>
      <GuestButton />
      <div className="guest-divider" style={{ width: "100%", maxWidth: 360 }}>or</div>
      <button
        className="rl-demo-btn"
        onClick={handleRLDemo}
        disabled={demoLoading}
      >
        {demoLoading ? "Starting Demo…" : "RL Demo"}
      </button>
      {demoError && <p className="login-error">{demoError}</p>}
    </div>
  );
}
