import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import MenuPage from "./pages/MenuPage";
import LobbyPage from "./pages/LobbyPage";
import GamePage from "./pages/GamePage";
import ResultsPage from "./pages/ResultsPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import DeckEditorPage from "./pages/DeckEditorPage";
import StatsPage from "./pages/StatsPage";
import MatchHistoryPage from "./pages/MatchHistoryPage";
import ReplayPage from "./pages/ReplayPage";
import RLDemoLobbyPage from "./pages/RLDemoLobbyPage";
import RLDemoResultsPage from "./pages/RLDemoResultsPage";
import Loading from "./components/Loading";
import { useSocket } from "./socket/socketContext";

function ProtectedRoute({ element }) {
  const { socket, connected, authFailed } = useSocket();
  const hasToken = !!localStorage.getItem("token");

  // No token, or token was rejected by the server → send to login
  if (!hasToken || authFailed) {
    return <Navigate to="/login" replace />;
  }

  // Token exists but socket not yet connected → wait for connection
  if (!socket || !connected) {
    return <Loading />;
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

      <Route
        path="/stats"
        element={<ProtectedRoute element={<StatsPage />} />}
      />

      <Route
        path="/history"
        element={<ProtectedRoute element={<MatchHistoryPage />} />}
      />

      <Route
        path="/replay/:gameId"
        element={<ProtectedRoute element={<ReplayPage />} />}
      />

      {/* RL Demo — protected (needs socket), but no DB player record */}
      <Route
        path="/rl-demo"
        element={<ProtectedRoute element={<RLDemoLobbyPage />} />}
      />

      <Route
        path="/demo-results/:gameId"
        element={<ProtectedRoute element={<RLDemoResultsPage />} />}
      />

      <Route path="*" element={<Navigate to="/menu" replace />} />
    </Routes>
  );
}

