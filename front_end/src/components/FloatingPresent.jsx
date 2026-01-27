import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * props:
 * - items: [{ type: "text", value, color? } | { type: "image", src }]
 * - duration: ms (default 3000)
 * - color: default text color
 */
export default function FloatingPresent({
  items,
  duration = 3000,
  color = "#ffffff",
  pos = {x: 0, y: 0}
}) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), duration);
    return () => clearTimeout(timer);
  }, [duration]);

  return (
        <motion.div
          initial={{ x: pos.x, y: pos.y, opacity: 1 }}
          animate={{ x: pos.x, y: pos.y-60, opacity: 0 }}
          exit={{ opacity: 0 }}
          transition={{
            duration: duration / 1000,
            ease: "easeOut",
          }}
          style={{
            position: "absolute",
            pointerEvents: "none",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "18px",
            fontWeight: "bold",
            textShadow: "0 0 6px rgba(0,0,0,0.6)",
          }}
        >
          {items.map((item, i) => {
            if (item.type === "text") {
              return (
                <span
                  key={i}
                  style={{ color: item.color || color }}
                >
                  {item.value}
                </span>
              );
            }

            if (item.type === "image") {
              return (
                <img
                  key={i}
                  src={item.src}
                  alt=""
                  style={{ width: 24, height: 24 }}
                />
              );
            }

            return null;
          })}
        </motion.div>
  );
}
