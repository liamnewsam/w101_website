import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { BACKEND_URL } from "../config";
import "./RLDemoLobbyPage.css";

const SCHOOLS = ["Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"];

const SCHOOL_COLORS = {
  Fire:    "#e05c2c",
  Ice:     "#73b6f0",
  Storm:   "#9b59d0",
  Life:    "#3fb55c",
  Death:   "#9b8fe5",
  Myth:    "#c8a824",
  Balance: "#c8a85c",
};

function SchoolPicker({ label, value, onChange }) {
  return (
    <div className="demo-school-picker">
      <div className="demo-picker-label">{label}</div>
      <div className="demo-school-grid">
        {SCHOOLS.map((s) => (
          <button
            key={s}
            className={`demo-school-btn ${value === s ? "active" : ""}`}
            style={{ "--school-color": SCHOOL_COLORS[s] }}
            onClick={() => onChange(s)}
          >
            <img
              src={`${BACKEND_URL}/static/w101/icons/schools/${s.toLowerCase()}.png`}
              alt={s}
              className="demo-school-icon"
            />
            <span>{s}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function DeckPreview({ cardIds, allCards }) {
  if (!allCards || !cardIds || cardIds.length === 0) {
    return <p className="demo-deck-empty">No deck loaded.</p>;
  }
  const byId = {};
  for (const cards of Object.values(allCards)) {
    for (const c of cards) byId[c.id] = c;
  }
  return (
    <div className="demo-deck-preview">
      {cardIds.map((id, i) => {
        const card = byId[id];
        if (!card) return null;
        return (
          <div key={i} className="demo-deck-card-thumb" title={card.name}>
            <img
              src={`${BACKEND_URL}/${card.img_path}`}
              alt={card.name}
              loading="lazy"
            />
          </div>
        );
      })}
    </div>
  );
}

export default function RLDemoLobbyPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { socket, disconnectSocket } = useSocket();

  // If returning from deck editor, seed state directly from location so there
  // is no race between "read custom deck" and "fetch default deck".
  const returnedDeck   = location.state?.customDeck?.card_ids ?? null;
  const returnedSchool = location.state?.playerSchool ?? null;

  const [playerSchool, setPlayerSchool] = useState(returnedSchool ?? "Fire");
  const [aiSchool, setAiSchool]         = useState("Balance");
  const [playerDeckIds, setPlayerDeckIds] = useState(returnedDeck ?? []);
  const [allCards, setAllCards]           = useState(null);
  const [starting, setStarting]           = useState(false);
  const [error, setError]                 = useState("");

  // True on the very first render — used to skip the default-deck fetch when
  // we already have a custom deck coming back from the deck editor.
  const isFirstRender = useRef(true);

  // Load card catalogue once for deck preview
  useEffect(() => {
    fetch(`${BACKEND_URL}/cards`)
      .then((r) => r.json())
      .then(setAllCards)
      .catch(() => {});

    // Clear location state so a refresh doesn't re-apply the old custom deck
    if (location.state?.customDeck) {
      navigate("/rl-demo", { replace: true, state: {} });
    }
  }, []);

  // Fetch the default deck whenever the school changes, but skip on the very
  // first render if we already have a custom (or pre-seeded) deck.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      if (returnedDeck) return;   // keep the custom deck, don't overwrite
    }
    fetch(`${BACKEND_URL}/api/demo-deck/${playerSchool}`)
      .then((r) => r.json())
      .then((data) => { if (data.card_ids) setPlayerDeckIds(data.card_ids); })
      .catch(() => {});
  }, [playerSchool]);

  function goEditDeck() {
    navigate("/deck-editor", {
      state: {
        localMode: true,
        returnTo: "/rl-demo",
        cardIds: playerDeckIds,
        overrideLevel: 100,
        playerSchool,
      },
    });
  }

  function startGame() {
    if (!socket || starting) return;
    setStarting(true);
    setError("");
    socket.emit(
      "create_rl_demo_game",
      {
        player_school:        playerSchool,
        player_deck_card_ids: playerDeckIds,
        ai_school:            aiSchool,
        player_name:          "Demo Player",
      },
      (resp) => {
        if (resp?.ok && resp?.gameId) {
          navigate(`/game/${resp.gameId}`, {
            state: { isDemo: true },
          });
        } else {
          setError(resp?.error || "Failed to start game.");
          setStarting(false);
        }
      }
    );
  }

  const schoolColor = SCHOOL_COLORS[playerSchool] || "#aaa";

  return (
    <div className="demo-lobby-page">
      <div className="demo-lobby-header">
        <h1 className="demo-lobby-title">RL Demo</h1>
        <p className="demo-lobby-subtitle">
          Play against a trained AI opponent — no account needed
        </p>
      </div>

      <div className="demo-lobby-body">
        {/* ── Player setup ── */}
        <section className="demo-section">
          <h2 className="demo-section-title">Your Setup</h2>
          <SchoolPicker
            label="Your School"
            value={playerSchool}
            onChange={setPlayerSchool}
          />

          <div className="demo-deck-section">
            <div className="demo-deck-header">
              <span className="demo-deck-label">
                Deck ({playerDeckIds.length} cards)
              </span>
              <button className="demo-edit-deck-btn" onClick={goEditDeck}>
                Edit Deck
              </button>
            </div>
            <DeckPreview cardIds={playerDeckIds} allCards={allCards} />
          </div>
        </section>

        {/* ── AI setup ── */}
        <section className="demo-section">
          <h2 className="demo-section-title">AI Opponent</h2>
          <SchoolPicker
            label="AI School"
            value={aiSchool}
            onChange={setAiSchool}
          />
          <p className="demo-ai-note">
            The AI will use the best trained model for that school. Its deck is
            randomly chosen from its top-performing loadouts.
          </p>
        </section>
      </div>

      {error && <p className="demo-error">{error}</p>}

      <div className="demo-lobby-footer">
        <button
          className="demo-start-btn"
          onClick={startGame}
          disabled={starting || playerDeckIds.length === 0}
        >
          {starting ? "Starting…" : "Start Game"}
        </button>
        <button
          className="demo-back-btn"
          onClick={() => { disconnectSocket(); navigate("/login"); }}
          disabled={starting}
        >
          Back to Login
        </button>
      </div>
    </div>
  );
}
