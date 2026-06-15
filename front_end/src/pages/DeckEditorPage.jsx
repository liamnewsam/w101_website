import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { usePlayer } from "../PlayerContext";
import { BACKEND_URL } from "../config";
import "./DeckEditorPage.css";

const SCHOOLS = ["fire", "ice", "storm", "life", "death", "myth", "balance"];
const SCHOOL_COLORS = {
  fire:    "#e05c2c",
  ice:     "#73b6f0",
  storm:   "#9b59d0",
  life:    "#3fb55c",
  death:   "#9b8fe5",
  myth:    "#c8a824",
  balance: "#c8a85c",
};
const MAX_CARDS = 30;
const MAX_COPIES = 4;

export default function DeckEditorPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { socket } = useSocket();
  const { player } = usePlayer();

  // localMode: no DB save — return deck to returnTo route
  const localMode  = location.state?.localMode === true;
  const returnTo   = location.state?.returnTo ?? "/profile";
  const playerSchool = location.state?.playerSchool ?? null;

  // deckIndex === null means "new deck"
  const deckIndex = location.state?.deckIndex ?? null;
  const isNew = deckIndex === null;

  // Draft key for localStorage auto-save (null in localMode — no persistence needed)
  const draftKey = localMode ? null : `w101_deck_draft_${isNew ? "new" : deckIndex}`;

  const [deckName, setDeckName] = useState(() => {
    if (draftKey) {
      try {
        const draft = JSON.parse(localStorage.getItem(draftKey));
        if (draft?.name) return draft.name;
      } catch {}
    }
    if (!isNew) return player?.decks?.[deckIndex]?.name ?? "New Deck";
    return "New Deck";
  });

  const [cardIds, setCardIds] = useState(() => {
    if (localMode) return location.state?.cardIds ?? [];
    if (draftKey) {
      try {
        const draft = JSON.parse(localStorage.getItem(draftKey));
        if (draft?.cardIds) return draft.cardIds;
      } catch {}
    }
    return (isNew ? null : player?.decks?.[deckIndex])?.card_ids ?? [];
  });
  const [allCards, setAllCards] = useState(null); // { school: [{id,name,pips,pvp_level,img_path}] }
  const [activeSchool, setActiveSchool] = useState(
    playerSchool?.toLowerCase() ?? SCHOOLS[0]
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const nameRef = useRef(null);

  // In local mode override level to 100 so all cards are accessible
  const activeSchoolLevel = localMode
    ? (location.state?.overrideLevel ?? 100)
    : (player?.level ?? 0);

  // Fetch card catalogue once
  useEffect(() => {
    fetch(`${BACKEND_URL}/cards`)
      .then((r) => r.json())
      .then(setAllCards)
      .catch(() => setError("Failed to load cards."));
  }, []);

  // Auto-save draft to localStorage on every change
  useEffect(() => {
    if (!draftKey) return;
    localStorage.setItem(draftKey, JSON.stringify({ name: deckName, cardIds }));
  }, [deckName, cardIds, draftKey]);

  // Count how many of each card id are in the deck
  const counts = useMemo(() => {
    const m = {};
    for (const id of cardIds) m[id] = (m[id] ?? 0) + 1;
    return m;
  }, [cardIds]);

  // Current deck as full card objects (for display), in order
  const deckCards = useMemo(() => {
    if (!allCards) return [];
    const byId = {};
    for (const cards of Object.values(allCards))
      for (const c of cards) byId[c.id] = c;
    return cardIds.map((id) => byId[id]).filter(Boolean);
  }, [cardIds, allCards]);

  function addCard(card) {
    if (cardIds.length >= MAX_CARDS) return;
    if ((counts[card.id] ?? 0) >= MAX_COPIES) return;
    if (card.pvp_level > activeSchoolLevel) return;
    setCardIds((prev) => {
      const lastIdx = prev.lastIndexOf(card.id);
      if (lastIdx === -1) return [...prev, card.id];
      const next = [...prev];
      next.splice(lastIdx + 1, 0, card.id);
      return next;
    });
  }

  function removeCard(index) {
    setCardIds((prev) => prev.filter((_, i) => i !== index));
  }

  function save() {
    if (localMode) {
      navigate(returnTo, {
        state: {
          customDeck: { name: deckName.trim() || "Demo Deck", card_ids: cardIds },
          playerSchool: playerSchool ?? activeSchool,
        },
      });
      return;
    }
    setSaving(true);
    setError("");
    socket.emit(
      "save_deck",
      { deckIndex: isNew ? null : deckIndex, name: deckName.trim() || "New Deck", card_ids: cardIds },
      (resp) => {
        setSaving(false);
        if (resp?.ok) {
          if (draftKey) localStorage.removeItem(draftKey);
          navigate("/profile");
        } else {
          setError(resp?.error ?? "Failed to save deck.");
        }
      }
    );
  }

  const schoolCards = allCards?.[activeSchool] ?? [];

  return (
    <div className="deck-editor-page">
      {/* ── Header ── */}
      <div className="de-header">
        <button className="de-back-btn" onClick={() => navigate(localMode ? returnTo : "/profile")}>← Back</button>
        <input
          ref={nameRef}
          className="de-name-input"
          value={deckName}
          onChange={(e) => setDeckName(e.target.value)}
          maxLength={32}
          placeholder="Deck name"
        />
        <button className="de-save-btn" onClick={save} disabled={saving}>
          {localMode ? "Use This Deck" : (saving ? "Saving…" : "Save")}
        </button>
      </div>
      {error && <p className="de-error">{error}</p>}

      {/* ── Current deck ── */}
      <section className="de-section">
        <div className="de-section-header">
          <span className="de-section-title">Current Deck</span>
          <span className={`de-count ${cardIds.length >= MAX_CARDS ? "at-limit" : ""}`}>
            {cardIds.length} / {MAX_CARDS}
          </span>
        </div>
        {deckCards.length === 0 ? (
          <p className="de-empty">No cards yet — add some below.</p>
        ) : (
          <div className="de-deck-grid">
            {deckCards.map((card, i) => (
              <button
                key={i}
                className="de-deck-card"
                onClick={() => removeCard(i)}
                title={`Remove ${card.name}`}
              >
                <img src={`${BACKEND_URL}/${card.img_path}`} alt={card.name} loading="lazy" />
                <span className="de-remove-overlay">✕</span>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* ── Card browser ── */}
      <section className="de-section">
        <div className="de-section-header">
          <span className="de-section-title">Add Cards</span>
          {cardIds.length >= MAX_CARDS && (
            <span className="de-limit-badge">Deck full</span>
          )}
        </div>

        {/* School tabs */}
        <div className="de-school-tabs">
          {SCHOOLS.map((s) => (
            <button
              key={s}
              className={`de-school-tab ${s === activeSchool ? "active" : ""}`}
              style={{ "--school-color": SCHOOL_COLORS[s] }}
              onClick={() => setActiveSchool(s)}
            >
              <img
                className="de-school-icon"
                src={`${BACKEND_URL}/static/w101/icons/schools/${s}.png`}
                alt={s}
              />
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        {/* Card grid */}
        {!allCards ? (
          <p className="de-empty">Loading cards…</p>
        ) : (
          <div className="de-browser-grid">
            {schoolCards.map((card) => {
              const locked = card.pvp_level > activeSchoolLevel;
              const count = counts[card.id] ?? 0;
              const maxed = count >= MAX_COPIES;
              const full  = cardIds.length >= MAX_CARDS;
              const disabled = locked || maxed || full;

              return (
                <button
                  key={card.id}
                  className={`de-browser-card ${locked ? "locked" : ""} ${maxed ? "maxed" : ""}`}
                  onClick={() => !disabled && addCard(card)}
                  disabled={disabled}
                  title={
                    locked ? `Requires level ${card.pvp_level}`
                    : maxed ? `Max ${MAX_COPIES} copies`
                    : card.name
                  }
                >
                  <img src={`${BACKEND_URL}/${card.img_path}`} alt={card.name} loading="lazy" />

                  {/* Pip cost badge */}
                  <span className="de-pip-badge">{card.pips}</span>

                  {/* Lock overlay */}
                  {locked && (
                    <div className="de-lock-overlay">
                      <span className="de-lock-icon">🔒</span>
                      <span className="de-lock-level">Lv.{card.pvp_level}</span>
                    </div>
                  )}

                  {/* Copy count badge (shown when ≥1 already in deck) */}
                  {count > 0 && !locked && (
                    <span className={`de-copy-badge ${maxed ? "maxed" : ""}`}>
                      {count}/{MAX_COPIES}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
