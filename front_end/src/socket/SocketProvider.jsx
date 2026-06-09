import React, { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import { BACKEND_URL } from "../config";
import { SocketContext } from "./socketContext";

export function SocketProvider({ children }) {
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [authFailed, setAuthFailed] = useState(false);
  const [token, setToken] = useState(localStorage.getItem("token"));

  const updateToken = (t) => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setConnected(false);
    }
    localStorage.setItem("token", t);
    setAuthFailed(false);
    setToken(t);
  };

  useEffect(() => {
    if (!token) return;

    if (socketRef.current) return;

    const s = io(BACKEND_URL, {
      transports: ["websocket"],
      auth: { token },
    });

    s.on("connect", () => { setConnected(true); setAuthFailed(false); });
    s.on("disconnect", () => setConnected(false));
    s.on("connect_error", (err) => {
      if (err.message === "authentication failed") {
        setAuthFailed(true);
        localStorage.removeItem("token");
        s.disconnect();
        socketRef.current = null;
      }
    });

    socketRef.current = s;

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
        authFailed,
        disconnectSocket,
        updateToken,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}
