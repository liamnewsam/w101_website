// src/pages/LoginPage.jsx
import LoginForm from "../components/LoginForm";
import GuestButton from "../components/GuestButton";
import { getToken } from "../api/auth";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {useSocket} from "../socket/socketContext"

export default function LoginPage() {
  const navigate = useNavigate();
  const { socket, connected, disconnectSocket } = useSocket();

  // Auto redirect if already logged in
  useEffect(() => {
    if (connected) {
      console.log("YOYOYOYOYO");
      navigate("/menu");
    }
  }, [connected]);

  return (
    <div className="login-container">
      <LoginForm />
      <GuestButton />
    </div>
  );
}
