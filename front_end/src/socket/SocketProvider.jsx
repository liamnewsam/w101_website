import React, { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { BACKEND_URL } from "../config";
import { SocketContext } from "./socketContext";

export function SocketProvider({ children }) {
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [token, setToken] = useState(localStorage.getItem("token"));

  const updateToken = (t) => {
    localStorage.setItem("token", t);
    setToken(t);
  };

  useEffect(() => {
    if (!token) return;

    // 🔒 Prevent duplicate sockets (StrictMode-safe)
    if (socketRef.current) return;

    console.log("CREATING SOCKET");

    const s = io(BACKEND_URL, {
      transports: ["websocket"],
      auth: { token },
    });

    s.on("connect", () => {
      console.log("socket connected");
      setConnected(true);
    });

    s.on("disconnect", (reason) => {
      console.log("socket disconnected:", reason);
      setConnected(false);
    });

    s.on("connect_error", (error) => {
      console.log("connect_error:", error.message);
    });

    socketRef.current = s;

    return () => {
      // 🚫 DO NOT disconnect here in StrictMode
      // React will fake-unmount this component
    };
  }, [token]);

  function disconnectSocket() {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    localStorage.removeItem("token");
    setToken(null);
    setConnected(false);
  }

  return (
    <SocketContext.Provider
      value={{
        socket: socketRef.current,
        connected,
        disconnectSocket,
        updateToken,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}
