import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useParams, useNavigate } from "react-router-dom";
import OrbitalGraphic from "../components/OrbitalGraphic";
import FloatingPresent from "../components/FloatingPresent";
import CardReveal from "../components/CardReveal";
import SlideFadeReveal from "../components/SlideFadeReveal";
import SimpleArrow from "../components/SimpleArrow";
import CircularArrow from "../components/CircularArrow";
import Loading from "../components/Loading";
import { BACKEND_URL } from "../config";
import { ORBITAL_DIAMETER } from "../hooks/useGameReplay";
import { useReplayPlayer } from "../hooks/useReplayPlayer";
import "./ReplayPage.css";

export default function ReplayPage() {
  const { gameId } = useParams();
  const navigate = useNavigate();

  const [replayData, setReplayData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);

  const [visualEffects, setVisualEffects] = useState([]);
  const [activatedPlayerID, setActivatedPlayerID] = useState(null);
  const triangleAccRef = useRef({ lastNorm: null, cumulative: 0 });

  useEffect(() => {
    const token = localStorage.getItem("token");
    fetch(`${BACKEND_URL}/replay/${gameId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) { setFetchError(data.error); setLoading(false); return; }
        setReplayData(data);
        setLoading(false);
      })
      .catch(e => { setFetchError(e.message); setLoading(false); });
  }, [gameId]);

  useEffect(() => { return () => setVisualEffects([]); }, []);

  const {
    visual,
    replaying,
    playerAngles,
    deadPlayerIds,
    isAutoPlay,
    setIsAutoPlay,
    nextTurn,
    turnsPlayed,
    totalTurns,
    isFinished,
  } = useReplayPlayer({ replayData, setVisualEffects, setActivatedPlayerID });

  // Accumulate clockwise-only rotation for the battle triangle
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

  if (loading) return <Loading />;

  if (fetchError) {
    return (
      <div className="replay-page">
        <div className="replay-error">
          Error loading replay: {fetchError}
          <button className="replay-back-btn" onClick={() => navigate("/history")}>
            ← Back to History
          </button>
        </div>
      </div>
    );
  }

  if (!visual.game || !visual.player) return <Loading />;

  const statusText = replaying
    ? `Replaying turn ${turnsPlayed + 1} of ${totalTurns}…`
    : isFinished
      ? "Replay complete"
      : `Turn ${turnsPlayed} / ${totalTurns}`;

  return (
    <div className="replay-page">
      <div className="replay-header">
        <button className="replay-back-btn" onClick={() => navigate("/history")}>
          ← History
        </button>
        <span className="replay-title">Match Replay</span>
        <span className="replay-turn-info">{statusText}</span>
      </div>

      <div className="orbital-layout">
        <OrbitalGraphic
          size={ORBITAL_DIAMETER}
          board_info={{ gameState: visual.game, playerState: visual.player }}
          selectedCardIndex={-1}
          onSelectTarget={() => {}}
          deadPlayerIds={deadPlayerIds}
          currentPlayerSchoolPip={null}
          onSchoolPipChange={() => {}}
        />

        <motion.img
          src={BACKEND_URL + "/static/w101/battle_triangle.png"}
          animate={activatedPlayerID != null ? { rotate: triangleRotateDeg } : false}
          transition={{ duration: 0.4, ease: "linear" }}
          transformTemplate={({ rotate }) => `translate(-50%, -50%) rotate(${rotate})`}
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
                      onComplete={() => setVisualEffects(e => e.filter(x => x.id !== effect.id))}
                    />
                  </div>
                );
              case "IMAGE":
                return (
                  <SlideFadeReveal
                    key={effect.id}
                    {...effect}
                    onComplete={() => setVisualEffects(e => e.filter(x => x.id !== effect.id))}
                  />
                );
              case "REVEAL":
                return (
                  <CardReveal
                    key={effect.id}
                    {...effect}
                    onComplete={() => setVisualEffects(e => e.filter(x => x.id !== effect.id))}
                  />
                );
              case "SIMPLE_ARROW":
                return (
                  <SimpleArrow
                    key={effect.id}
                    {...effect}
                    onComplete={() => setVisualEffects(e => e.filter(x => x.id !== effect.id))}
                  />
                );
              case "CIRCULAR_ARROW":
                return (
                  <CircularArrow
                    key={effect.id}
                    {...effect}
                    onComplete={() => setVisualEffects(e => e.filter(x => x.id !== effect.id))}
                  />
                );
              default:
                return null;
            }
          })}
        </div>
      </div>

      <div className="replay-controls">
        <button className="replay-control-btn" onClick={() => setIsAutoPlay(a => !a)}>
          {isAutoPlay ? "Pause" : "Play"}
        </button>

        {!isAutoPlay && !replaying && !isFinished && (
          <button className="replay-control-btn" onClick={nextTurn}>
            Next Turn
          </button>
        )}

        {isFinished && (
          <button className="replay-control-btn" onClick={() => navigate("/history")}>
            Back to History
          </button>
        )}
      </div>
    </div>
  );
}
