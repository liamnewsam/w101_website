// src/pages/LoginPage.jsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import LoginForm from "../components/LoginForm";
import GuestButton from "../components/GuestButton";
import "./LoginPage.css";

export default function LoginPage() {
  const navigate = useNavigate();
  const { connected } = useSocket();

  useEffect(() => {
    if (connected) {
      navigate("/menu");
    }
  }, [connected]);

  return (
    <div className="login-page">
      <h1 className="login-page-title">Wizard101</h1>
      <p className="login-page-subtitle">Sign in to continue your adventure</p>
      <LoginForm />
      <div className="guest-divider" style={{ width: "100%", maxWidth: 360 }}>or</div>
      <GuestButton />
    </div>
  );
}
