import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * props:
 * - srcImg: image URL
 * - width, height: px
 * - duration: fade-in duration (seconds)
 * - stay: milliseconds fully visible
 * - onComplete: callback
 */
export default function SlideFadeReveal({
  srcImg,
  width = 200,
  height = 200,
  duration = 1,
  stay = 500,
  onComplete,
}) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const totalDuration = duration * 2 * 1000 + stay;
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, totalDuration);

    return () => clearTimeout(timer);
  }, [duration, stay, onComplete]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ "--mask": "linear-gradient(to right, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 0%)" }}
          animate={{
            "--mask": [
              "linear-gradient(to right, rgba(0,0,0,0) 0%, rgba(0,0,0,0) 0%)", // fully transparent
              "linear-gradient(to right, rgba(0,0,0,1) 100%, rgba(0,0,0,1) 100%)", // fully visible
              "linear-gradient(to right, rgba(0,0,0,0) 100%, rgba(0,0,0,0) 100%)", // fade out
            ],
          }}
          transition={{
            times: [0, duration / (duration + stay / 1000), 1],
            duration: duration * 2 + stay / 1000,
            ease: "linear",
          }}
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width,
            height,
            transform: "translate(-50%, -50%)",
            WebkitMaskImage: "var(--mask)",
            maskImage: "var(--mask)",
            WebkitMaskRepeat: "no-repeat",
            maskRepeat: "no-repeat",
            WebkitMaskSize: "100% 100%",
            maskSize: "100% 100%",
            pointerEvents: "none",
            zIndex: 1000,
            backgroundImage: `url(${srcImg})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
      )}
    </AnimatePresence>
  );
}
