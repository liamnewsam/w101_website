import { motion, AnimatePresence, useAnimation } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * props:
 * - imgSrc: card image
 * - startX, startY: initial position (px)
 * - onComplete?: callback when animation ends
 */
const CARD_W = 200;
const CARD_H = 280;

export default function CardReveal({
  imgSrc,
  startPos,
  onComplete,
}) {
  const controls = useAnimation();
  const [visible, setVisible] = useState(true);

  const startX = startPos.x;
  const startY = startPos.y;

  useEffect(() => {
    async function runAnimation() {
      // 1. Spawn → move to center + grow
      await controls.start({
        x: -CARD_W / 2,
        y: -CARD_H / 2,
        scale: 1,
        opacity: 1,
        transition: {
          duration: 0.9,
          ease: "easeOut",
        },
      });

      // 2. Sit in center
      await controls.start({
        scale: 1,
        transition: { delay: 1 },
      });

      // 3. Exit placeholder (customize later)
      await controls.start({
        scale: 0.8,
        opacity: 0,
        transition: {
          duration: 0.5,
          ease: "easeIn",
        },
      });

      setVisible(false);
      onComplete?.();
    }

    runAnimation();
  }, [controls, onComplete]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.img
          src={imgSrc}
          alt="Card"
          initial={{
            x: startX - CARD_W / 2,
            y: startY - CARD_H / 2,
            scale: 0.1,
            opacity: 0.5,
          }}
          animate={controls}
          exit={{ opacity: 0 }}
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: CARD_W,
            height: CARD_H,
            objectFit: "contain",
            pointerEvents: "none",
            zIndex: 1000,
          }}
        />
      )}
    </AnimatePresence>
  );
}
