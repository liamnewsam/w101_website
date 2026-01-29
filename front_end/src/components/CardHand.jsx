import { useEffect, useRef } from "react";
import { BACKEND_URL } from "../config";

import "./CardHand.css";

export default function CardHand({
  cards,
  selectedIndex,
  onSelectCard,
  //onClearSelection,
  onDiscardCard
}) {
  const handRef = useRef(null);

  /*
  // Click outside → clear selection
  useEffect(() => {
    function handleClickOutside(e) {
      if (handRef.current && !handRef.current.contains(e.target)) {
        onClearSelection();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClearSelection]);*/

  function handleCardMouseDown(e, idx) {
    // Middle click → discard
    if (e.button === 1) {
      e.preventDefault();
      onDiscardCard(idx);
    }
  }

  function handleCardClick(e, idx, playable) {
    e.stopPropagation();
    if (!playable) return;
    onSelectCard(idx);
  }

  return (
    <div className="card-hand" ref={handRef}>
      {cards.map((card, idx) => {
        const isSelected = idx === selectedIndex;
        const isPlayable = card.playable;

        return (
          <div
            key={idx}
            className={[
              "card-wrapper",
              isSelected && "selected",
              !isPlayable && "disabled",
            ]
              .filter(Boolean)
              .join(" ")}
            onMouseDown={(e) => handleCardMouseDown(e, idx)}
            onClick={(e) => handleCardClick(e, idx, isPlayable)}
          >
            <img
              className="card"
              src={BACKEND_URL + "/" + card.img_path}
              alt={card.card}
              draggable={false}
            />
          </div>
        );
      })}
    </div>
  );
}
