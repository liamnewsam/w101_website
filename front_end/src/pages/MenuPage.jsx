import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { logout } from "../api/auth";
import { usePlayer } from "../PlayerContext";
import Loading from "../components/Loading";
import { BACKEND_URL } from "../config";
import "./MenuPage.css";

export default function MenuPage() {
  const { socket, disconnectSocket } = useSocket();
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const { player } = usePlayer();

  useEffect(() => {
    if (!socket) {
      navigate("/login");
      return;
    }
  }, [socket, navigate]);

  useEffect(() => {
    if (!socket) return;
    socket.emit("get_player_info");
  }, [socket]);

  useEffect(() => {
    if (!socket) return;
    const onList = (list) => setGames(list);
    socket.on("game_list", onList);
    socket.emit("list_games");
    return () => socket.off("game_list", onList);
  }, [socket]);

  function handleCreate() {
    socket.emit("create_game", {}, (resp) => {
      if (resp?.gameId) navigate(`/lobby/${resp.gameId}`);
    });
  }

  function handleCreateBots() {
    socket.emit("create_bot_game", {}, (resp) => {
      if (resp?.gameId) navigate(`/lobby/${resp.gameId}`);
    });
  }

  function handleJoin(gameId) {
    socket.emit("join_game", { gameId }, (ack) => {
      if (ack?.ok) navigate(`/lobby/${gameId}`);
      else alert(ack?.error || "Failed to join");
    });
  }

  function handleLogout() {
    logout(disconnectSocket);
    navigate("/login");
  }

  if (!player) return <Loading />;

  return (
    <div className="menu-page">
      <h1 className="menu-title">Wizard101</h1>

      {/* Player banner */}
      <div className="menu-player-banner">
        {player.image_path && (
          <img
            className="menu-avatar"
            src={`${BACKEND_URL}/${player.image_path}`}
            alt={player.name}
          />
        )}
        <div className="menu-player-details">
          <p className="menu-player-name">{player.name}</p>
          <div className="menu-player-meta">
            <span className="menu-level">Lv. {player.level ?? 1}</span>
            <span className="menu-sep">·</span>
            <span className="menu-school">{player.school}</span>
          </div>
          <div className="menu-record">
            <span className="menu-rating">{player.elo ?? 100} Rating</span>
          </div>
        </div>
        <button className="menu-profile-btn" onClick={() => navigate("/profile")}>
          Profile
        </button>
      </div>

      {/* Play section */}
      <div className="menu-section">
        <p className="menu-section-title">Play</p>
        <div className="menu-play-buttons">
          <button className="menu-play-btn primary" onClick={handleCreateBots}>
            Play vs Bots
          </button>
          <button className="menu-play-btn secondary" onClick={handleCreate}>
            Create Multiplayer Game
          </button>
        </div>
      </div>

      {/* Open games */}
      <div className="menu-section">
        <p className="menu-section-title">Open Games</p>
        <div className="menu-game-list">
          {games.length === 0 ? (
            <p className="menu-empty">No open games right now</p>
          ) : (
            games.map((g) => (
              <div key={g.gameId} className="menu-game-row">
                <div>
                  <div className="menu-game-name">{g.name || g.gameId}</div>
                  <div className="menu-game-count">{g.players?.length ?? 0} player{g.players?.length !== 1 ? "s" : ""}</div>
                </div>
                <button className="menu-join-btn" onClick={() => handleJoin(g.gameId)}>
                  Join
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <button className="menu-logout-btn" onClick={handleLogout}>
        Log out
      </button>
    </div>
  );
}
