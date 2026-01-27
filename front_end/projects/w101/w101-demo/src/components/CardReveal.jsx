import { motion, AnimatePresence, useAnimation } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * props:
 * - imgSrc: card image
 * - startX, startY: initial position (px)
 * - onComplete?: callback when animation ends
 */
export default function CardReveal({
  imgSrc,
  startPos,
  onComplete,
}) {
  const controls = useAnimation();
  const [visible, setVisible] = useState(true);

  let startX = startPos.x;
  let startY = startPos.y;

  useEffect(() => {
    async function runAnimation() {
      // 1. Spawn → move to center + grow
      await controls.start({
        x: "-50%",
        y: "-50%",
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
            x: `calc(-50% + ${startX}px)`,
            y: `calc(-50% + ${startY}px)`,
            scale: 0.1,
            opacity: 0.5,
          }}
          animate={controls}
          exit={{ opacity: 0 }}
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            
            width: 200,
            pointerEvents: "none",
            zIndex: 1000,
          }}
        />
      )}
    </AnimatePresence>
  );
}
