import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * props:
 * - startX, startY: starting position (px)
 * - endX, endY: ending position (px)
 * - duration: seconds
 * - onComplete?: callback
 */
export default function SimpleArrow({
  startPos,
  endPos,
  duration = 0.6,
  onComplete,
}) {
  const [visible, setVisible] = useState(true);

  let startX = startPos.x;
  let startY = startPos.y;
  let endX = endPos.x;
  let endY = endPos.y;


  useEffect(() => {
    const t = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, duration * 1000);

    return () => clearTimeout(t);
  }, [duration, onComplete]);

  // Compute rotation so arrow points toward target
  const angle =
    (Math.atan2(endY - startY, endX - startX) * 180) / Math.PI;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{
            x: startX,
            y: startY,
            opacity: 0,
            rotate: angle,
          }}
          animate={{
            x: endX,
            y: endY,
            opacity: 1,
          }}
      
          exit={{ opacity: 0 }}
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
