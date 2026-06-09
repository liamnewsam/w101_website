import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import CardHand from "../components/CardHand";
import OrbitalGraphic from "../components/OrbitalGraphic";
import FloatingPresent from "../components/FloatingPresent";
import CardReveal from "../components/CardReveal";
import SlideFadeReveal from "../components/SlideFadeReveal";
import SimpleArrow from "../components/SimpleArrow";
import Loading from "../components/Loading";
import { BACKEND_URL } from "../config";
import { logout } from "../api/auth";
import "./GamePage.css";
import CircularArrow from "../components/CircularArrow";
import { useGameReplay, ACTIONS, ORBITAL_DIAMETER } from "../hooks/useGameReplay";

/* ============================
   MAIN COMPONENT
   ============================ */

export default function GamePage() {
  const { gameId } = useParams();
  const { socket, disconnectSocket } = useSocket();
  const navigate = useNavigate();
  const { state: locationState } = useLocation();

  const [visualEffects, setVisualEffects] = useState([]);
  const [activatedPlayerID, setActivatedPlayerID] = useState();

  const triangleAccRef = useRef({ lastNorm: null, cumulative: 0 });

  // Clear all effects on unmount so no stale animations linger
  useEffect(() => {
    return () => setVisualEffects([]);
  }, []);

  const isDemo = locationState?.isDemo === true;
  const demoResultPath = isDemo ? `/demo-results/${gameId}` : undefined;

  // Detect demo token even when location.state is lost (e.g. tab restore)
  const tokenType = (() => {
    try {
      const t = localStorage.getItem("token");
      if (!t) return null;
      return JSON.parse(atob(t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).type;
    } catch { return null; }
  })();
  const missingGamePath = (isDemo || tokenType === "demo") ? "/" : "/menu";

  const { visual, replaying, dispatch, playerAngles, authoritative, deadPlayerIds } = useGameReplay({
    socket,
    gameId,
    navigate,
    setVisualEffects,
    setActivatedPlayerID,
    resultPath: demoResultPath,
    missingGamePath,
  });

  // Compute clockwise-only cumulative rotation during render.
  // Using a ref (not state) avoids double-render; reading current angle
  // every render handles mutable playerAngles objects correctly.
  let triangleRotateDeg = triangleAccRef.current.cumulative;
  if (activatedPlayerID != null && playerAngles[activatedPlayerID] != null) {
    const rawDeg = 90 + (playerAngles[activatedPlayerID] * 180) / Math.PI;
    const normTarget = ((rawDeg % 360) + 360) % 360;
    const { lastNorm, cumulative } = triangleAccRef.current;
    if (lastNorm === null) {
      triangleAccRef.current = { lastNorm: normTarget, cumulative: rawDeg };
      triangleRotateDeg = rawDeg;
    } else if (Math.abs(normTarget - lastNorm) > 0.001) {
      let diff = normTarget - lastNorm;
      if (diff > 0) diff -= 360;
      const next = cumulative + diff;
      triangleAccRef.current = { lastNorm: normTarget, cumulative: next };
      triangleRotateDeg = next;
    }
  }

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

  const [localSchoolPipSelect, setLocalSchoolPipSelect] = useState(null);
  const currentSchoolPip = localSchoolPipSelect ?? visual.player?.school_pip_select ?? visual.player?.school;

  function handleSchoolPipChange(school) {
    setLocalSchoolPipSelect(school);
    socket.emit("set_school_pip", { gameId, school });
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
    return <Loading />;
  }

  return (
    <div className="game-page">
      <div className="game-hud">
        <span className="game-hud-round">Round {visual.game.turns}</span>
        {replaying && <span className="game-hud-status">Resolving turn…</span>}
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
          deadPlayerIds={deadPlayerIds}
          currentPlayerSchoolPip={currentSchoolPip}
          onSchoolPipChange={handleSchoolPipChange}
        />

        <motion.img
          src={BACKEND_URL + "/static/w101/battle_triangle.png"}
          animate={
            activatedPlayerID != null
              ? { rotate: triangleRotateDeg }
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

      <div className="game-controls">
        <CardHand
          cards={visual.player.hand}
          selectedIndex={selectedCardIndex}
          onSelectCard={onCardSelected}
          onClearSelection={clearSelection}
          onDiscardCard={discardCard}
        />

        <div className="game-action-row">
          {isOurTurn() && (
            <button className="game-btn primary" onClick={() => sendAction({ type: "pass" })}>
              Pass
            </button>
          )}
          <button className="game-btn secondary" onClick={() => {
              sendAction({ type: "leave" });
              if (isDemo) {
                logout(disconnectSocket);
                navigate("/");
              } else {
                navigate("/menu");
              }
            }}>Leave Game</button>
        </div>
      </div>
    </div>
  );
}
