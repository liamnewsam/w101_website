import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

import { useParams, useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import CardHand from "../components/CardHand";
import OrbitalGraphic from "../components/OrbitalGraphic";
import FloatingPresent from "../components/FloatingPresent";
import CardReveal from "../components/CardReveal";
import SlideFadeReveal from "../components/SlideFadeReveal";
import SimpleArrow from "../components/SimpleArrow";
import { BACKEND_URL } from "../config";
import "./GamePage.css";
import CircularArrow from "../components/CircularArrow";
import { useGameReplay, ACTIONS, ORBITAL_DIAMETER } from "../hooks/useGameReplay";

/* ============================
   MAIN COMPONENT
   ============================ */

export default function GamePage() {
  const { gameId } = useParams();
  const { socket } = useSocket();
  const navigate = useNavigate();

  const [visualEffects, setVisualEffects] = useState([]);
  const [activatedPlayerID, setActivatedPlayerID] = useState();

  // Clear all effects on unmount so no stale animations linger
  useEffect(() => {
    return () => setVisualEffects([]);
  }, []);

  const { visual, replaying, dispatch, playerAngles, authoritative } = useGameReplay({
    socket,
    gameId,
    navigate,
    setVisualEffects,
    setActivatedPlayerID,
  });

  /* ============================
     INPUT HELPERS
     ============================ */

  function isOurTurn() {
    if (replaying || !visual.game || !visual.player) return false;
    return visual.game.playing_team === visual.player.team;
  }

  function sendAction(action) {
    socket.emit("player_action", { gameId, action });
  }

  function playCard(idx, target) {
    sendAction({ type: "cast", cardIndex: idx, target });
    clearSelection();
  }

  const [selectedCardIndex, setSelectedCardIndex] = useState(-1);

  function onCardSelected(idx) {
    const card = visual.player.hand[idx];

    if (card.targets.length === 0) {
      playCard(idx, null);
    } else {
      setSelectedCardIndex(idx);
    }
  }

  function onTargetSelected(targetId) {
    if (selectedCardIndex < 0 || !visual.player) return;
    playCard(selectedCardIndex, targetId);
  }

  function clearSelection() {
    setSelectedCardIndex(-1);
  }

  function discardCard(cardId) {
    if (replaying) return;
    socket.emit(
      "player_action",
      { gameId, action: { type: "discard", cardId } },
      ack => {
        dispatch({ type: ACTIONS.ACTION_RESULT, payload: { ...ack, cardId } });
      }
    );
  }

  /* ============================
     RENDER
     ============================ */

  if (!visual.game || !visual.player) {
    return <div>Loading game…</div>;
  }

  return (
    <div className="page game">
      <h1>Game {gameId}</h1>

      <div className="hud">
        {!replaying && <div>Round: {visual.game.turns}</div>}
        {replaying && <div className="replay-indicator">Resolving turn…</div>}
      </div>

      <div className="orbital-layout">
        <OrbitalGraphic
          size={ORBITAL_DIAMETER}
          board_info={{
            gameState: visual.game,
            playerState: visual.player,
          }}
          selectedCardIndex={selectedCardIndex}
          onSelectTarget={onTargetSelected}
        />

        <motion.img
          src={BACKEND_URL + "/static/w101/battle_triangle.png"}
          animate={
            activatedPlayerID != null
              ? { rotate: 90 + (playerAngles[activatedPlayerID] * 180) / Math.PI }
              : false
          }
          transition={{ duration: 0.4, ease: "linear" }}
          transformTemplate={({ rotate }) =>
            `translate(-50%, -50%) rotate(${rotate})`
          }
          style={{
            position: "absolute",
            width: ORBITAL_DIAMETER,
            height: ORBITAL_DIAMETER,
            left: "50%",
            top: "50%",
            pointerEvents: "none",
            zIndex: 1,
          }}
          initial={false}
        />

        <div className="effects-layer">
        {visualEffects.map(effect => {
          switch (effect.type) {
            case "FLOATING_PRESENT":
              return (
                <div key={effect.id} className="effect-anchor">
                  <FloatingPresent
                    {...effect}
                    onComplete={() =>
                      setVisualEffects(effects => effects.filter(e => e.id !== effect.id))
                    }
                  />
                </div>
              );

            case "IMAGE":
              return (
                <SlideFadeReveal
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects => effects.filter(e => e.id !== effect.id))
                  }
                />
              );

            case "REVEAL":
              return (
                <CardReveal
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects => effects.filter(e => e.id !== effect.id))
                  }
                />
              );

            case "SIMPLE_ARROW":
              return (
                <SimpleArrow
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects => effects.filter(e => e.id !== effect.id))
                  }
                />
              );

            case "CIRCULAR_ARROW":
              return (
                <CircularArrow
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects => effects.filter(e => e.id !== effect.id))
                  }
                />
              );

            default:
              return null;
          }
        })}
        </div>
      </div>

      <div className="controls">
        <CardHand
          cards={visual.player.hand}
          selectedIndex={selectedCardIndex}
          onSelectCard={onCardSelected}
          onDiscardCard={discardCard}
        />

        <div className="pass_leave">
          {isOurTurn() && (
            <button onClick={() => sendAction({ type: "pass" })}>
              Pass
            </button>
          )}
          <button onClick={() => navigate("/menu")}>Leave Game</button>
        </div>
      </div>

      <div className="board"> {/* Replace with your duel view and animation canvas */}
        <pre style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(authoritative.game, null, 2)}
        </pre>
        <pre style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(authoritative.player, null, 2)}
        </pre>
      </div>
    </div>
  );
}
