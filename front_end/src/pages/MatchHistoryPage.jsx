import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Loading from "../components/Loading";
import { BACKEND_URL } from "../config";
import "./MatchHistoryPage.css";

const SCHOOL_COLORS = {
  fire:    "#e05c2c",
  ice:     "#73b6f0",
  storm:   "#9b59d0",
  life:    "#3fb55c",
  death:   "#9b8fe5",
  myth:    "#c8a824",
  balance: "#c8a85c",
};

function schoolColor(s) {
  return SCHOOL_COLORS[s?.toLowerCase()] ?? "#aaa";
}

function MatchCard({ match, onWatch }) {
  const teamA = (match.players ?? []).filter(p => p.team === "A");
  const teamB = (match.players ?? []).filter(p => p.team === "B");
  const dateStr = match.created_at
    ? new Date(match.created_at).toLocaleDateString(undefined, {
        month: "short", day: "numeric", year: "numeric",
      })
    : "";

  return (
    <div className="match-card">
      <div className="match-card-header">
        <span className={`match-winner-tag ${match.winner === "A" ? "team-a-wins" : "team-b-wins"}`}>
          Team {match.winner} wins
        </span>
        <span className="match-date">{dateStr}</span>
      </div>

      <div className="match-teams">
        <div className={`match-team ${match.winner === "A" ? "winning-team" : "losing-team"}`}>
          {teamA.map(p => (
            <div key={p.id} className="match-player">
              <img
                src={`${BACKEND_URL}/${p.image_path}`}
                alt={p.name}
                className="match-avatar"
                onError={e => { e.target.style.display = "none"; }}
              />
              <span className="match-player-name" style={{ color: schoolColor(p.school) }}>
                {p.name}
              </span>
            </div>
          ))}
        </div>

        <div className="match-vs">vs</div>

        <div className={`match-team ${match.winner === "B" ? "winning-team" : "losing-team"}`}>
          {teamB.map(p => (
            <div key={p.id} className="match-player">
              <img
                src={`${BACKEND_URL}/${p.image_path}`}
                alt={p.name}
                className="match-avatar"
                onError={e => { e.target.style.display = "none"; }}
              />
              <span className="match-player-name" style={{ color: schoolColor(p.school) }}>
                {p.name}
              </span>
            </div>
          ))}
        </div>
      </div>

      <button className="match-watch-btn" onClick={() => onWatch(match.game_id)}>
        Watch Replay
      </button>
    </div>
  );
}

export default function MatchHistoryPage() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    fetch(`${BACKEND_URL}/replays`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) { setError(data.error); setLoading(false); return; }
        setHistory(data.replays ?? []);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <Loading />;

  return (
    <div className="history-page">
      <div className="history-header">
        <button className="history-back-btn" onClick={() => navigate("/menu")}>
          ← Menu
        </button>
        <h1 className="history-title">Match History</h1>
      </div>

      {error && <p className="history-error">{error}</p>}

      {!error && history.length === 0 && (
        <p className="history-empty">
          No matches on record yet. Play a game to see your history here.
        </p>
      )}

      <div className="history-list">
        {history.map(match => (
          <MatchCard
            key={match.game_id}
            match={match}
            onWatch={id => navigate(`/replay/${id}`)}
          />
        ))}
      </div>
    </div>
  );
}
