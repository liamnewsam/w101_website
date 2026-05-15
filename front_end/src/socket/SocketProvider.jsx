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

    if (socketRef.current) return;

    const s = io(BACKEND_URL, {
      transports: ["websocket"],
      auth: { token },
    });

    s.on("connect", () => setConnected(true));
    s.on("disconnect", () => setConnected(false));

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
        disconnectSocket,
        updateToken,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}
