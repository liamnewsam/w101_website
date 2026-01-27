import { useState } from "react";
import { BACKEND_URL, BATTLE_PATH} from "../config";
import "./StatusGrid.css";


export default function StatusGrid({ activeIcons, statusIconSize }) {
  const [popupPos, setPopupPos] = useState({ x: 0, y: 0, visible: false, items: [] });

  const handleMouseMove = (e, items) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setPopupPos({
      x: e.clientX - rect.left + 10, // offset from cursor
      y: e.clientY - rect.top + 10,
      visible: true,
      items,
    });
  };

  const handleMouseLeave = () => {
    setPopupPos(prev => ({ ...prev, visible: false }));
  };

  return (
    <div className="status-grid">
      {activeIcons.map(({ key, icon, popupItems }) => (
        <div
          key={key}
          className="status-icon-wrapper"
          onMouseMove={(e) => handleMouseMove(e, popupItems)}
          onMouseLeave={handleMouseLeave}
          style={{ position: "relative", display: "inline-block" }}
        >
          <img
            src={BACKEND_URL + BATTLE_PATH + icon}
            alt={key}
            className="status-icon"
            style={{ height: statusIconSize, width: statusIconSize }}
          />

            {popupPos.visible && popupPos.items === popupItems && (
                <div
                    className="status-popup"
                    style={{ position: "absolute", left: popupPos.x, top: popupPos.y }}
                >
                    {popupItems.map((line, i) => (
                    <div key={i} className="popup-line">
                        {line.map((item, j) => {
                        if (item.type === "text") {
                            return (
                            <span key={j} style={{ color: item.color || "black", marginRight: 4 }}>
                                {item.value}
                            </span>
                            );
                        } else if (item.type === "image") {
                            return (
                            <img
                                key={j}
                                src={item.src}
                                alt=""
                                style={{ width: 16, height: 16, marginRight: 4 }}
                            />
                            );
                        }
                        })}
                    </div>
                    ))}
                </div>
            )}
        </div>
      ))}
    </div>
  );
}
