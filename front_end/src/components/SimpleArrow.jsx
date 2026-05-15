import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * props:
 * - startX, startY: starting position (px)
 * - endX, endY: ending position (px)
 * - duration: seconds
 * - onComplete?: callback
 */
// Half-dimensions of the arrow bar (40×6). Subtracting these from x,y makes
// Framer Motion's rotation pivot land exactly at the passed-in position rather
// than 20px to the right of it (the default top-left anchor offset).
const HALF_W = 20;
const HALF_H = 3;
const ARROWHEAD_LEN = 12; // borderLeft length in the arrowhead div
const PLAYER_RADIUS = 32; // orbit_size / 2 — keeps the bar outside player circles

export default function SimpleArrow({
  startPos,
  endPos,
  duration = 0.6,
  endDuration = 0.1,
  onComplete,
}) {
  const [visible, setVisible] = useState(true);

  const startX = startPos.x;
  const startY = startPos.y;
  const endX = endPos.x;
  const endY = endPos.y;

  useEffect(() => {
    const t = setTimeout(() => {
      //setVisible(false);
      onComplete?.();
    }, duration * 1000);

    return () => clearTimeout(t);
  }, [duration]);

  const dx = endX - startX;
  const dy = endY - startY;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const nx = dx / dist;
  const ny = dy / dist;

  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;

  // Offset start forward by PLAYER_RADIUS so the bar begins at the source edge.
  // Offset end back by PLAYER_RADIUS + ARROWHEAD_LEN so the tip stops at target edge.
  // Subtract HALF_W/HALF_H so the rotation pivot is exactly at the computed position.
  const adjStartX = startX + nx * PLAYER_RADIUS - HALF_W;
  const adjStartY = startY + ny * PLAYER_RADIUS - HALF_H;
  const adjEndX   = endX - nx * (PLAYER_RADIUS + ARROWHEAD_LEN) - HALF_W;
  const adjEndY   = endY - ny * (PLAYER_RADIUS + ARROWHEAD_LEN) - HALF_H;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{
            x: adjStartX,
            y: adjStartY,
            opacity: 0,
            rotate: angle,
          }}
          animate={{
            x: adjEndX,
            y: adjEndY,
            opacity: 1,
          }}
      
          exit={{ 
            opacity: 0,
            transition: { duration: 0.1 }
          }}
          transition={{ duration, ease: "easeOut" }}
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            width: 40,
            height: 6,
            background: "linear-gradient(to right, #fff, #ffcc66)",
            borderRadius: 3,
            transformOrigin: "center",
            pointerEvents: "none",
            zIndex: 1000,
          }}
        >
          {/* Arrow head */}
          <div
            style={{
              position: "absolute",
              right: -8,
              top: -6,
              width: 0,
              height: 0,
              borderTop: "9px solid transparent",
              borderBottom: "9px solid transparent",
              borderLeft: "12px solid #ffcc66",
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
