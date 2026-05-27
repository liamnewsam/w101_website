import React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { usePlayer } from "../PlayerContext";
import { BACKEND_URL } from "../config";
import { computeLevel, computeLevelProgress, ELO_FLOOR } from "../utils/levelUtils";
import "./ResultsPage.css";

const SCHOOL_COLORS = {
  fire:    "#e05c2c",
  ice:     "#73b6f0",
  storm:   "#9b59d0",
  life:    "#3fb55c",
  death:   "#9b8fe5",
  myth:    "#c8a824",
  balance: "#c8a85c",
};

function schoolColor(school) {
  return SCHOOL_COLORS[school?.toLowerCase()] ?? "#aaa";
}

function EloChange({ elo, eloChange }) {
  const newElo = Math.max(ELO_FLOOR, elo + eloChange);
  const newLevel = computeLevel(newElo);
  const oldLevel = computeLevel(elo);
  const levelDelta = newLevel - oldLevel;
  const progress = computeLevelProgress(newElo);
  const sign = eloChange >= 0 ? "+" : "";

  return (
    <div className="level-progress-wrap">
      <div className="level-progress-header">
        <span className="level-badge">Lv. {newLevel}</span>
        {levelDelta !== 0 && (
          <span className={`level-delta ${levelDelta > 0 ? "level-up" : "level-down"}`}>
            {levelDelta > 0 ? `▲ +${levelDelta}` : `▼ ${levelDelta}`}
          </span>
        )}
        <span className={`elo-delta ${eloChange >= 0 ? "elo-gain" : "elo-loss"}`}>
          {sign}{eloChange}
        </span>
      </div>
      <div className="level-bar-track">
        <div className="level-bar-fill" style={{ width: `${progress * 100}%` }} />
      </div>
    </div>
  );
}

function PlayerCard({ p, isWinner }) {
  const color = schoolColor(p.school);
  return (
    <div className={`result-player-card${isWinner ? " winner-card" : " loser-card"}`}>
      <img
        className="result-avatar"
        src={`${BACKEND_URL}/${p.image_path}`}
        alt={p.name}
        onError={e => { e.target.style.display = "none"; }}
      />
      <div className="result-player-info">
        <div className="result-player-name">{p.name}</div>
        <div className="result-school-badge" style={{ color }}>
          <span className="result-school-dot" style={{ background: color }} />
          {p.school}
        </div>
        {!p.isBot && (
          <EloChange elo={p.elo} eloChange={p.elo_change} />
        )}
        {p.isBot && <div className="result-bot-label">Bot</div>}
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { gameId } = useParams();
  const { player: currentPlayer } = usePlayer();

  const result = state?.result;
  const winner = typeof result === "string" ? result : result?.winner;
  const players = Array.isArray(result?.players) ? result.players : [];

  const myId = currentPlayer?.user_id;
  const myEntry = players.find(p => p.id === myId);
  const isVictory = myEntry ? myEntry.team === winner : null;

  const teamA = players.filter(p => p.team === "A");
  const teamB = players.filter(p => p.team === "B");

  const teamAWins = winner === "A";
  const teamBWins = winner === "B";

  return (
    <div className="results-page">
      {isVictory !== null && (
        <div className={`outcome-banner ${isVictory ? "victory" : "defeat"}`}>
          {isVictory ? "VICTORY" : "DEFEATED"}
        </div>
      )}

      <div className="results-teams">
        <div className={`results-team-panel${teamAWins ? " team-winner" : " team-loser"}`}>
          <h2 className="team-heading">
            {teamAWins ? "⭐ Team A" : "Team A"}
          </h2>
          {teamA.map((p) => (
            <PlayerCard key={p.id} p={p} isWinner={teamAWins} />
          ))}
        </div>

        <div className="results-divider" />

        <div className={`results-team-panel${teamBWins ? " team-winner" : " team-loser"}`}>
          <h2 className="team-heading">
            {teamBWins ? "⭐ Team B" : "Team B"}
          </h2>
          {teamB.map((p) => (
            <PlayerCard key={p.id} p={p} isWinner={teamBWins} />
          ))}
        </div>
      </div>

      <div className="results-actions">
        <button className="home-btn" onClick={() => navigate(`/replay/${gameId}`)}>
          Watch Replay
        </button>
        <button className="home-btn" onClick={() => navigate("/menu")}>
          Return to Home
        </button>
      </div>
    </div>
  );
}
