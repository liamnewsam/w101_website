import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { SocketProvider } from "./socket/SocketProvider";
import { PlayerProvider } from "./PlayerContext"
import "./styles.css";

createRoot(document.getElementById("root")).render(
  //<React.StrictMode>
    <SocketProvider>
      <BrowserRouter>
        <PlayerProvider>
          <App />
        </PlayerProvider>
      </BrowserRouter>
    </SocketProvider>
  //</React.StrictMode>
);
