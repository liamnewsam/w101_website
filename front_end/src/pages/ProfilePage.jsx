import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { usePlayer } from "../PlayerContext";
import { BACKEND_URL } from "../config";
import AvatarPicker from "../components/AvatarPicker";
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
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);
  const [cardCatalogue, setCardCatalogue] = useState(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/cards`)
      .then((r) => r.json())
      .then(setCardCatalogue)
      .catch(() => {});
  }, []);

  // Flat map of card id → pvp_level for quick lookup
  const pvpLevelById = useMemo(() => {
    if (!cardCatalogue) return {};
    const map = {};
    for (const cards of Object.values(cardCatalogue))
      for (const c of cards) map[c.id] = c.pvp_level ?? 0;
    return map;
  }, [cardCatalogue]);

  if (!player) return <div className="page profile-page"><p>Loading…</p></div>;

  const activeSchool = player.school || "Balance";
  const decks = player.decks || [];
  const selectedDeckIndex = player.selected_deck_index ?? 0;
  const schoolLevels = player.school_levels ?? {};
  const activeLevel = player.level ?? 0;
  const wins = player.wins ?? 0;
  const losses = player.losses ?? 0;

  function isDeckAllowed(deck) {
    if (!cardCatalogue) return true; // optimistic while loading
    return (deck.card_ids || []).every(
      (id) => (pvpLevelById[id] ?? 0) <= activeLevel
    );
  }

  function startEditingName() {
    setNameInput(player.name || "");
    setEditingName(true);
  }

  function cancelEditingName() {
    setEditingName(false);
    setNameInput("");
  }

  function saveName() {
    const trimmed = nameInput.trim();
    if (!trimmed || trimmed === player.name) {
      cancelEditingName();
      return;
    }
    socket.emit("update_player_name", { name: trimmed }, (resp) => {
      if (resp?.ok) setFeedback("Name updated.");
      else setFeedback(resp?.error || "Failed to update name.");
      setTimeout(() => setFeedback(""), 2500);
    });
    setEditingName(false);
  }

  function handleNameKeyDown(e) {
    if (e.key === "Enter") saveName();
    if (e.key === "Escape") cancelEditingName();
  }

  function selectAvatar(image_path) {
    socket.emit("update_player_avatar", { image_path }, (resp) => {
      if (resp?.ok) setFeedback("Avatar updated.");
      else setFeedback(resp?.error || "Failed to update avatar.");
      setTimeout(() => setFeedback(""), 2500);
    });
  }

  function selectSchool(schoolName) {
    socket.emit("update_player_school", { school: schoolName }, (resp) => {
      if (resp?.ok) setFeedback(`School changed to ${schoolName}.`);
      else setFeedback(resp?.error || "Failed to update school.");
      setTimeout(() => setFeedback(""), 2500);
    });
  }

  function selectDeck(index) {
    if (!isDeckAllowed(decks[index])) {
      setFeedback(`Deck contains cards above your current level (Lv.${activeLevel}).`);
      setTimeout(() => setFeedback(""), 2500);
      return;
    }
    socket.emit("update_player_deck", { deckIndex: index }, (resp) => {
      if (resp?.ok) setFeedback("Active deck changed.");
      else setFeedback(resp?.error || "Failed to update deck.");
      setTimeout(() => setFeedback(""), 2500);
    });
  }

  function deleteDeck(index, e) {
    e.stopPropagation();
    if (!window.confirm("Delete this deck?")) return;
    socket.emit("delete_deck", { deckIndex: index }, (resp) => {
      if (!resp?.ok) setFeedback(resp?.error || "Failed to delete deck.");
      setTimeout(() => setFeedback(""), 2500);
    });
  }

  return (
    <div className="page profile-page">
      <div className="profile-topbar">
        <button className="back-btn" onClick={() => navigate("/menu")}>← Back</button>
        <div className="profile-tabs">
          <button className="profile-tab active">Profile</button>
          <button className="profile-tab" onClick={() => navigate("/stats")}>Stats</button>
        </div>
      </div>

      {showAvatarPicker && (
        <AvatarPicker
          currentPath={player.image_path}
          onSelect={selectAvatar}
          onClose={() => setShowAvatarPicker(false)}
        />
      )}

      {/* ── Stats ── */}
      <section className="profile-section">
        <div className="profile-avatar-row">
          <button
            className="profile-avatar-btn"
            onClick={() => setShowAvatarPicker(true)}
            title="Change avatar"
          >
            <img
              className="profile-avatar"
              src={`${BACKEND_URL}/${player.image_path}`}
              alt={player.name}
              onError={(e) => { e.target.style.display = "none"; }}
            />
            <span className="profile-avatar-overlay">Change</span>
          </button>
          <div>
            {editingName ? (
              <div className="profile-name-edit">
                <input
                  className="profile-name-input"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  onKeyDown={handleNameKeyDown}
                  maxLength={32}
                  autoFocus
                />
                <button className="profile-name-save" onClick={saveName}>Save</button>
                <button className="profile-name-cancel" onClick={cancelEditingName}>✕</button>
              </div>
            ) : (
              <div className="profile-name-row">
                <h1 className="profile-name">{player.name}</h1>
                <button className="profile-name-edit-btn" onClick={startEditingName} title="Edit name">✏️</button>
              </div>
            )}
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
                <img
                  className="school-icon"
                  src={`${BACKEND_URL}/static/w101/icons/schools/${s.name.toLowerCase()}.png`}
                  alt={s.name}
                />
                {s.name}
                <span className="school-tile-level">
                  Lv.{schoolLevels[s.name.toLowerCase()] ?? 1}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* ── Deck selector ── */}
      <section className="profile-section">
        <div className="section-title-row">
          <h2 className="section-title">Decks</h2>
          <button className="deck-new-btn" onClick={() => navigate("/deck-editor", { state: { deckIndex: null } })}>
            + New Deck
          </button>
        </div>
        {decks.length === 0 ? (
          <p className="no-decks">No decks yet — create one above.</p>
        ) : (
          <div className="deck-list">
            {decks.map((deck, i) => {
              const isActive = i === selectedDeckIndex;
              const allowed = isDeckAllowed(deck);
              return (
                <div
                  key={i}
                  className={`deck-row${isActive ? " active" : ""}${!allowed ? " restricted" : ""}`}
                  onClick={() => selectDeck(i)}
                  title={!allowed ? `Contains cards above Lv.${activeLevel}` : undefined}
                >
                  <div className="deck-info">
                    <div className="deck-name">{deck.name || `Deck ${i + 1}`}</div>
                    <div className="deck-count">{deck.card_ids?.length ?? 0} cards</div>
                    {!allowed && <div className="deck-restricted-label">Above level</div>}
                  </div>
                  <div className="deck-row-actions">
                    {isActive && <span className="deck-active-mark">✓ Active</span>}
                    <button
                      className="deck-edit-btn"
                      onClick={(e) => { e.stopPropagation(); navigate("/deck-editor", { state: { deckIndex: i } }); }}
                      title="Edit deck"
                    >✏️</button>
                    <button
                      className="deck-delete-btn"
                      onClick={(e) => deleteDeck(i, e)}
                      title="Delete deck"
                    >🗑</button>
                  </div>
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
