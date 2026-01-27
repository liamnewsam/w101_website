import PlayerInfoCard from "./PlayerInfoCard";
import "./PlayerInfoWithIcons.css";
import {BACKEND_URL, BATTLE_PATH} from "../config";
import StatusGrid from "./StatusGrid";
import PipGrid from "./PipGrid";


const STATUS_CATEGORIES = [
  { key: "wards", icon: "Ward.png", popupItems: [{"type": "text", "value":"HI"}]},
  { key: "jinxes",   icon: "Jinx.png" },
  { key: "charms",  icon: "Charm.png", popupItems: [{"type": "text", "value":"HI"}]},
  { key: "curses", icon: "Curse.png"},
  { key: "auras",   icon: "/icons/aura.png" },
  { key: "dots",    icon: "/icons/dot.png" },
  { key: "hots",    icon: "/icons/hot.png" },
];

const goodColor = "green";
const badColor = "red";

function statusToPopup(status) {
  switch (status.type) {
    case "charm":
      if (status["aspect"] == "damage") {
        return [
          {"type": "text", "value": `+${status.amount}%`, "color": goodColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`}
        ];
      }
    case "curse":
      return [
        {"type": "text", "value": `+${status.amount}%`, "color": badColor},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`}
      ];
    case "ward":
      return [
        {"type": "text", "value": `+${status.amount}%`, "color": badColor},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`}
      ];
    case "jin":
      return [
        {"type": "text", "value": `+${status.amount}%`, "color": badColor},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`}
      ];
    
  }
}



export default function PlayerInfoWithIcons({
  player,
  leftIcon,
  style
}) {
  const activeIcons = STATUS_CATEGORIES
  .filter(category => player[category.key]?.length > 0)
  .map(category => ({
    key: category.key,        // name your property
    icon: category.icon,      // name your property
    popupItems: player[category.key].map(status => statusToPopup(status)),
  }));

  const schoolIconSize = parseInt(style.height, 10)+10;
  const statusIconSize = parseInt(style.height, 10) / 2;
  return (
    <div className="info-wrapper" style={style}>
      {/* Left single icon */}
      {leftIcon && (
        <img
          src={leftIcon}
          className="left-icon"
          alt=""
          style={{
            height: schoolIconSize,
            width: schoolIconSize
          }}
        />
      )}

      {/* Center card (UNCHANGED) */}
      <PlayerInfoCard
        name={player.name}
        currHealth={player.health}
        maxHealth={player.maxHealth}
      />

      {/* Right 2x2 grid */}
      <div className="status-grid-container">
        <StatusGrid activeIcons={activeIcons} statusIconSize={statusIconSize}/>
      </div>

      <div className="pip-grid-container">
        <PipGrid pips={player.pips} pipIconSize={statusIconSize}/>
      </div>
    </div>
  );
}



/*
const emptySlots = Math.max(0, MAX_COLS - items.length);

  return (
    <div className="grid">
      {items.map((item, i) => (
        <div key={i} className="cell">
          {item}
        </div>
      ))}

      {Array.from({ length: emptySlots }).map((_, i) => (
        <div key={`empty-${i}`} className="cell empty" />
      ))}
    </div>
  );
*/