import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import MenuPage from "./pages/MenuPage";
import LobbyPage from "./pages/LobbyPage";
import GamePage from "./pages/GamePage";
import ResultsPage from "./pages/ResultsPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import DeckEditorPage from "./pages/DeckEditorPage";
import {useSocket} from "./socket/socketContext"

function ProtectedRoute({ element }) {
  const { socket, connected, disconnectSocket } = useSocket();

  // No token → send to login page
  if (!socket || !connected) {
    console.log("UH OH!!");
    localStorage.removeItem("token");

    return <Navigate to="/login" replace />;
  }

  return element;
}


export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/menu" replace />} />

      {/* public */}
      <Route path="/login" element={<LoginPage />} />

      {/* protected */}
      <Route
        path="/menu"
        element={<ProtectedRoute element={<MenuPage />} />}
      />

      <Route
        path="/lobby/:gameId"
        element={<ProtectedRoute element={<LobbyPage />} />}
      />

      <Route
        path="/game/:gameId"
        element={<ProtectedRoute element={<GamePage />} />}
      />

      <Route
        path="/results/:gameId"
        element={<ProtectedRoute element={<ResultsPage />} />}
      />

      <Route
        path="/profile"
        element={<ProtectedRoute element={<ProfilePage />} />}
      />

      <Route
        path="/deck-editor"
        element={<ProtectedRoute element={<DeckEditorPage />} />}
      />

      <Route path="*" element={<Navigate to="/menu" replace />} />
    </Routes>
  );
}

