import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { usePlayer } from "../PlayerContext";
import { BACKEND_URL } from "../config";
import "./LobbyPage.css";

const SCHOOL_COLORS = {
  fire:    "#e05c2c",
  ice:     "#73b6f0",
  storm:   "#9b59d0",
  life:    "#3fb55c",
  death:   "#9b8fe5",
  myth:    "#c8a824",
  balance: "#c8a85c",
};

function PlayerTab({ p, isMe, onReady, onRemoveBot }) {
  const [hovered, setHovered] = useState(false);
  const isClickable = isMe || p.isBot;
  const schoolColor = SCHOOL_COLORS[p.school?.toLowerCase()] || "#888";

  function handleClick(e) {
    e.stopPropagation();
    if (isMe) onReady();
    else if (p.isBot) onRemoveBot(p.id);
  }

  let hintLabel = null;
  if (hovered && isMe) hintLabel = p.isReady ? "Unready" : "Ready up";
  if (hovered && p.isBot) hintLabel = "Remove";

  const isModelBot = p.isBot && p.model_path;

  return (
    <div
      className={`player-tab${p.isReady ? " ready" : ""}${hovered && isClickable ? " tab-hovered" : ""}`}
      style={{ borderColor: p.isReady ? "#3fb55c" : "transparent", cursor: isClickable ? "pointer" : "default" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={handleClick}
    >
      <div className="tab-school-bar" style={{ background: schoolColor }} />

      <img
        className="tab-icon"
        src={`${BACKEND_URL}/${p.image_path}`}
        alt={p.name}
        onError={(e) => { e.target.style.display = "none"; }}
      />

      <div className="tab-info">
        <div className="tab-name">{p.name}{isMe ? " (You)" : ""}</div>
        <div className="tab-school" style={{ color: schoolColor }}>
          {p.school ? p.school.charAt(0).toUpperCase() + p.school.slice(1).toLowerCase() : ""}
          {isModelBot && <span className="model-badge">AI</span>}
        </div>
        <div className="tab-deck">Lv. {p.level ?? 1}</div>
      </div>

      <div className="tab-right">
        {p.isReady && <span className="ready-mark">✓</span>}
        {hintLabel && <span className="tab-hint">{hintLabel}</span>}
      </div>
    </div>
  );
}

function TeamBox({
  team, label, players, myId, myTeam,
  onJoin, onAddBot, onAddDuplicateBot, onReady, onRemoveBot,
  availableModels, selectedBotType, onBotTypeChange,
}) {
  const [hovered, setHovered] = useState(false);
  const isMyTeam = myTeam === team;
  const showJoinHint = hovered && !isMyTeam && myTeam !== undefined;

  function handleAddClick(e) {
    e.stopPropagation();
    onAddBot(selectedBotType);
  }

  return (
    <div
      className={`team-box${isMyTeam ? " my-team" : ""}${showJoinHint ? " joinable" : ""}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => { if (!isMyTeam) onJoin(); }}
    >
      <div className="team-header">
        <h3 className="team-label">{label}</h3>
        <div className="team-header-buttons">
          <button
            className="duplicate-bot-btn"
            onClick={(e) => { e.stopPropagation(); onAddDuplicateBot(); }}
          >
            ⊕ Duplicate Me
          </button>
        </div>
      </div>

      <div className="team-players">
        {players.map((p) => (
          <PlayerTab
            key={p.id}
            p={p}
            isMe={p.id === myId}
            onReady={onReady}
            onRemoveBot={onRemoveBot}
          />
        ))}
        {players.length === 0 && (
          <div className="empty-slot">Empty</div>
        )}
      </div>

      <div className="add-bot-row" onClick={(e) => e.stopPropagation()}>
        <select
          className="bot-selector"
          value={selectedBotType}
          onChange={(e) => onBotTypeChange(e.target.value)}
        >
          <option value="random">Random Bot</option>
          {availableModels.map((m) => (
            <option key={m.path} value={m.path}>
              AI: {m.agent_school} Lv{m.agent_level} (iter {m.iteration})
            </option>
          ))}
        </select>
        <button className="add-bot-btn" onClick={handleAddClick}>
          + Add
        </button>
      </div>

      {showJoinHint && (
        <div className="join-hint">Click to join {label}</div>
      )}
    </div>
  );
}

export default function LobbyPage() {
  const { gameId } = useParams();
  const { socket } = useSocket();
  const { player } = usePlayer();
  const navigate = useNavigate();

  const [lobbyState, setLobbyState] = useState({ players: [], host: null });
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedBotTypeA, setSelectedBotTypeA] = useState("random");
  const [selectedBotTypeB, setSelectedBotTypeB] = useState("random");

  const myId = player?.user_id;
  const myPlayer = lobbyState.players.find((p) => p.id === myId);
  const myTeam = myPlayer?.team;

  const teamA = lobbyState.players.filter((p) => p.team === "A");
  const teamB = lobbyState.players.filter((p) => p.team === "B");

  const allReady =
    lobbyState.players.length > 0 &&
    teamA.length > 0 &&
    teamB.length > 0 &&
    lobbyState.players.every((p) => p.isReady);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/models`)
      .then((r) => r.json())
      .then((data) => {
        if (data.models) setAvailableModels(data.models.filter((m) => !m.error));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!socket || !gameId) return;

    socket.emit("watch_lobby", { gameId });

    const onUpdate = (payload) => setLobbyState(payload);
    const onStart = () => navigate(`/game/${gameId}`);

    socket.on("update_lobby_state", onUpdate);
    socket.on("game_start", onStart);

    socket.emit("get_lobby_state", { gameId }, (data) => {
      if (data && data.players) setLobbyState(data);
    });

    return () => {
      socket.off("update_lobby_state", onUpdate);
      socket.off("game_start", onStart);
    };
  }, [socket, gameId, navigate]);

  function toggleReady() {
    socket.emit("player_ready", { gameId });
  }

  function switchTeam(team) {
    socket.emit("switch_team", { gameId, team });
  }

  function addBot(team, botType) {
    if (botType === "random") {
      socket.emit("add_bot", { gameId, team });
    } else {
      socket.emit("add_model_bot", { gameId, team, model_path: botType });
    }
  }

  function addDuplicateBot(team) {
    socket.emit("add_duplicate_bot", { gameId, team });
  }

  function removeBot(botId) {
    socket.emit("remove_bot", { gameId, botId });
  }

  function startMatch() {
    if (!allReady) return;
    socket.emit("start_game", { gameId });
  }

  function leaveLobby() {
    socket.emit("leave_lobby", { gameId });
    navigate("/menu");
  }

  return (
    <div className="page lobby-page">
      <h1 className="lobby-title">Lobby</h1>
      <p className="lobby-id">Room: {gameId}</p>

      <div className="teams-container">
        <TeamBox
          team="A"
          label="Team A"
          players={teamA}
          myId={myId}
          myTeam={myTeam}
          onJoin={() => switchTeam("A")}
          onAddBot={(botType) => addBot("A", botType)}
          onAddDuplicateBot={() => addDuplicateBot("A")}
          onReady={toggleReady}
          onRemoveBot={removeBot}
          availableModels={availableModels}
          selectedBotType={selectedBotTypeA}
          onBotTypeChange={setSelectedBotTypeA}
        />
        <TeamBox
          team="B"
          label="Team B"
          players={teamB}
          myId={myId}
          myTeam={myTeam}
          onJoin={() => switchTeam("B")}
          onAddBot={(botType) => addBot("B", botType)}
          onAddDuplicateBot={() => addDuplicateBot("B")}
          onReady={toggleReady}
          onRemoveBot={removeBot}
          availableModels={availableModels}
          selectedBotType={selectedBotTypeB}
          onBotTypeChange={setSelectedBotTypeB}
        />
      </div>

      <div className="lobby-controls">
        <button
          className={`start-btn${allReady ? " active" : ""}`}
          onClick={startMatch}
          disabled={!allReady}
        >
          Start Match
        </button>
        <button className="leave-btn" onClick={leaveLobby}>
          Return Home
        </button>
      </div>
    </div>
  );
}
