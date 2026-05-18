import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { usePlayer } from "../PlayerContext";
import { BACKEND_URL } from "../config";
import "./ProfilePage.css";

const SCHOOLS = [
  { name: "Fire",    color: "#e05c2c" },
  { name: "Ice",     color: "#73b6f0" },
  { name: "Storm",   color: "#9b59d0" },
  { name: "Life",    color: "#3fb55c" },
  { name: "Death",   color: "#9b8fe5" },
  { name: "Myth",    color: "#c8a824" },
  { name: "Balance", color: "#c8a85c" },
];

export default function ProfilePage() {
  const navigate = useNavigate();
  const { socket } = useSocket();
  const { player } = usePlayer();

  const [feedback, setFeedback] = useState("");

  if (!player) return <div className="page profile-page"><p>Loading…</p></div>;

  const activeSchool = player.school || "Balance";
  const decks = player.decks || [];
  const selectedDeckIndex = player.selected_deck_index ?? 0;
  const level = player.level ?? 1;
  const wins = player.wins ?? 0;
  const losses = player.losses ?? 0;

  function selectSchool(schoolName) {
    socket.emit("update_player_school", { school: schoolName }, (resp) => {
      if (resp?.ok) setFeedback(`School changed to ${schoolName}.`);
      else setFeedback(resp?.error || "Failed to update school.");
      setTimeout(() => setFeedback(""), 2500);
    });
  }

  function selectDeck(index) {
    socket.emit("update_player_deck", { deckIndex: index }, (resp) => {
      if (resp?.ok) setFeedback(`Active deck changed.`);
      else setFeedback(resp?.error || "Failed to update deck.");
      setTimeout(() => setFeedback(""), 2500);
    });
  }

  return (
    <div className="page profile-page">
      <button className="back-btn" onClick={() => navigate("/menu")}>← Back</button>

      {/* ── Stats ── */}
      <section className="profile-section">
        <div className="profile-avatar-row">
          <img
            className="profile-avatar"
            src={`${BACKEND_URL}/${player.image_path}`}
            alt={player.name}
            onError={(e) => { e.target.style.display = "none"; }}
          />
          <div>
            <h1 className="profile-name">{player.name}</h1>
            <div className="profile-level">Level {level}</div>
            <div className="profile-stats">
              <span className="stat win">{wins}W</span>
              <span className="stat sep">/</span>
              <span className="stat loss">{losses}L</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── School selector ── */}
      <section className="profile-section">
        <h2 className="section-title">School</h2>
        <div className="school-grid">
          {SCHOOLS.map((s) => {
            const isActive = activeSchool.toLowerCase() === s.name.toLowerCase();
            return (
              <button
                key={s.name}
                className={`school-tile${isActive ? " active" : ""}`}
                style={{
                  "--school-color": s.color,
                  borderColor: isActive ? s.color : "transparent",
                }}
                onClick={() => selectSchool(s.name)}
              >
                <div className="school-dot" style={{ background: s.color }} />
                {s.name}
              </button>
            );
          })}
        </div>
      </section>

      {/* ── Deck selector ── */}
      <section className="profile-section">
        <h2 className="section-title">Decks</h2>
        {decks.length === 0 ? (
          <p className="no-decks">No decks found.</p>
        ) : (
          <div className="deck-list">
            {decks.map((deck, i) => {
              const isActive = i === selectedDeckIndex;
              return (
                <div
                  key={i}
                  className={`deck-row${isActive ? " active" : ""}`}
                  onClick={() => selectDeck(i)}
                >
                  <div className="deck-info">
                    <div className="deck-name">{deck.name || `Deck ${i + 1}`}</div>
                    <div className="deck-count">{deck.card_ids?.length ?? 0} cards</div>
                  </div>
                  {isActive && <span className="deck-active-mark">✓ Active</span>}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {feedback && <div className="profile-feedback">{feedback}</div>}
    </div>
  );
}
