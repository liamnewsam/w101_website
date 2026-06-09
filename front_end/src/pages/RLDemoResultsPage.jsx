import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { BACKEND_URL } from "../config";
import "./RLDemoResultsPage.css";

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

function PlayerCard({ p, isWinner }) {
  const color = schoolColor(p.school);
  return (
    <div className={`dr-player-card ${isWinner ? "dr-winner" : "dr-loser"}`}>
      <img
        className="dr-avatar"
        src={`${BACKEND_URL}/${p.image_path}`}
        alt={p.name}
        onError={(e) => { e.target.style.display = "none"; }}
      />
      <div className="dr-player-info">
        <div className="dr-player-name">{p.name}</div>
        <div className="dr-school-badge" style={{ color }}>
          <span className="dr-school-dot" style={{ background: color }} />
          {p.school}
        </div>
        {p.isBot && <div className="dr-bot-tag">AI Agent</div>}
      </div>
    </div>
  );
}

export default function RLDemoResultsPage() {
  const { state } = useLocation();
  const navigate  = useNavigate();
  const { disconnectSocket } = useSocket();

  const result  = state?.result;
  const winner  = typeof result === "string" ? result : result?.winner;
  const players = Array.isArray(result?.players) ? result.players : [];

  const myEntry  = players.find((p) => !p.isBot);
  const isVictory = myEntry ? myEntry.team === winner : null;

  const teamA = players.filter((p) => p.team === "A");
  const teamB = players.filter((p) => p.team === "B");
  const teamAWins = winner === "A";
  const teamBWins = winner === "B";

  function returnToLogin() {
    disconnectSocket();
    navigate("/login", { replace: true });
  }

  return (
    <div className="demo-results-page">
      {isVictory !== null && (
        <div className={`dr-outcome ${isVictory ? "dr-victory" : "dr-defeat"}`}>
          {isVictory ? "Victory!" : "Defeated"}
        </div>
      )}

      <div className="dr-subtitle">
        {isVictory
          ? "You outsmarted the AI. Well played!"
          : "The AI won this time. Try a different school or deck!"}
      </div>

      <div className="dr-teams">
        <div className={`dr-team-panel ${teamAWins ? "dr-team-won" : "dr-team-lost"}`}>
          <h2 className="dr-team-heading">{teamAWins ? "⭐ " : ""}Team A</h2>
          {teamA.map((p) => (
            <PlayerCard key={p.id} p={p} isWinner={teamAWins} />
          ))}
        </div>

        <div className="dr-divider" />

        <div className={`dr-team-panel ${teamBWins ? "dr-team-won" : "dr-team-lost"}`}>
          <h2 className="dr-team-heading">{teamBWins ? "⭐ " : ""}Team B</h2>
          {teamB.map((p) => (
            <PlayerCard key={p.id} p={p} isWinner={teamBWins} />
          ))}
        </div>
      </div>

      <button className="dr-return-btn" onClick={returnToLogin}>
        Return to Login
      </button>
    </div>
  );
}
