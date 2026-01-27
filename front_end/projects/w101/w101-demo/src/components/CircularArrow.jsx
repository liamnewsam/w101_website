import { motion, AnimatePresence, useMotionValue, useTransform } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * props:
 * - center: { x, y }
 * - radius: number
 * - startAngle: radians
 * - duration: seconds
 * - onComplete?: callback
 */
export default function CircularArrow({
  center,
  radius = 80,
  startAngle = 0,
  duration = 1,
  onComplete,
}) {

  // Progress from 0 → 1
  const progress = useMotionValue(0);

  // Angle = startAngle + progress * 2π
  const angle = useTransform(
    progress,
    v => startAngle + v * Math.PI * 2
  );

  // Polar → Cartesian
  const x = useTransform(angle, a =>
    center.x + radius * Math.cos(a)
  );
  const y = useTransform(angle, a =>
    center.y + radius * Math.sin(a)
  );

  // Tangent rotation
  const rotate = useTransform(angle, a =>
    (a * 180) / Math.PI + 90
  );

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
            width: 40,
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
