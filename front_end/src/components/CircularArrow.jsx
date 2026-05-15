import { motion, AnimatePresence, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useState } from "react";

const SLANT = Math.PI / 2.0;
const SEPARATION = 20;
const WIDTH = 40;
//const SLANT = Math.PI;

/**
 * props:
 * - center: { x, y }
 * - radius: number
 * - startAngle: radians
 * - duration: seconds
 * - onComplete?: callback
 */
export default function CircularArrow({
  playerCenter,
  radius = 80,
  playerAngle = 0,
  duration = 1,
  onComplete,
}) {

  // Progress from 0 → 1
  const progress = useMotionValue(0);

  // Angle = startAngle + progress * 2π
  // ANGLES ARE MESSED UP, WHEN INCREASED, THEY GO CLOCKWISE!!
  const angle = useTransform(
    progress,
    v => (playerAngle-Math.PI/2 - (SLANT/2.0) - v * (Math.PI * 2 - SLANT))
  );
  const arrowWidthOffsetX = -WIDTH/2 * Math.cos(playerAngle-Math.PI/2);
  const arrowWidthOffsetY = -WIDTH/2 * Math.sin(playerAngle-Math.PI/2);
  const arrowOrbitCenter = {
    x: playerCenter.x - (radius + SEPARATION) * Math.cos(playerAngle) - arrowWidthOffsetX,
    y: playerCenter.y - (radius + SEPARATION) * Math.sin(playerAngle) + arrowWidthOffsetY
  };
  // Polar → Cartesian
  const x = useTransform(angle, a => arrowOrbitCenter.x + radius * Math.cos(a+Math.PI/2));
  const y = useTransform(angle, a => arrowOrbitCenter.y + radius * Math.sin(a+Math.PI/2));
  // Tangent of a negated-y circle: dx/da = -r·sin(a), dy/da = -r·cos(a)
  // → heading = atan2(-cos(a), -sin(a)) = -a·(180/π) - 90
  const rotate = useTransform(angle, a => a * (180 / Math.PI));



  useEffect(() => {
    const t = setTimeout(() => {
      onComplete?.();
    }, duration * 1000);

    return () => clearTimeout(t);
  }, [duration, onComplete]);

  return (
        <motion.div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            progress,   // 👈 REQUIRED
            x,
            y,
            rotate,
            width: WIDTH,
            height: 6,
            background: "linear-gradient(to right, #fff, #ffcc66)",
            borderRadius: 3,
            transformOrigin: "center",
            pointerEvents: "none",
            zIndex: 1000,
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, progress: 1 }}
          transition={{
            progress: { duration, ease: "linear" },
            opacity: { duration: 0.1 },
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
  );
}
