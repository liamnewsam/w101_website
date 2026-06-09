import PlayerInfoCard from "./PlayerInfoCard";
import "./PlayerInfoWithIcons.css";
import {BACKEND_URL, BATTLE_PATH, goodColor, badColor} from "../config";
import StatusGrid from "./StatusGrid";
import PipGrid from "./PipGrid";
import SchoolPipSelector from "./SchoolPipSelector";



const STATUS_CATEGORIES = [
  { key: "wards", icon: "Ward.png"},
  { key: "jinxes",   icon: "Jinx.png"},
  { key: "charms",  icon: "Charm.png"},
  { key: "curses", icon: "Curse.png"},
  { key: "auras",   icon: "Aura.png"},
  { key: "dots",    icon: "Damage_over_Time.png" },
  { key: "hots",    icon: "Heal_over_Time.png" },
];



function statusToPopup(status) {
  switch (status.type) {
    case "charm":
      if (status["aspect"] == "damage") {
        return [
          {"type": "text", "value": `+${status.amount}%`, "color": goodColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Outgoing.png`}
        ];
      }
      if (status["aspect"] == "heal") {
        return [
          {"type": "text", "value": `+${status.amount}%`, "color": goodColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Heal.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Outgoing.png`}
        ];
      }
      if (status["aspect"] == "armor_piercing") {
        return [
          {"type": "text", "value": `+${status.amount}%`, "color": goodColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + "Armor_Piercing.png"}
        ];
      }
      if (status["aspect"] == "accuracy") {
        return [
          {"type": "text", "value": `+${status.amount}%`, "color": goodColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + "Accuracy.png"}
        ];
      }
    case "curse":
      if (status["aspect"] == "damage") {
        return [
          {"type": "text", "value": `${status.amount}%`, "color": badColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Outgoing.png`}
        ];
      }
      if (status["aspect"] == "heal") {
        return [
          {"type": "text", "value": `${status.amount}%`, "color": badColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Heal.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Outgoing.png`}
        ];
      }
      if (status["aspect"] == "dispel") {
        return [
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "text", "value": "Dispel", "color": badColor}
        ]
      }
      if (status["aspect"] == "accuracy") {
        return [
          {"type": "text", "value": `${status.amount}%`, "color": badColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + "Accuracy.png"}
        ];
      }
    case "ward":
      if (status["aspect"] == "absorb") {
        return [
          {"type": "text", "value": `${Math.round(status.amount)}`, "color": goodColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Ward.png`}
        ];
      }
      if (status["aspect"] == "damage") {
        return [
          {"type": "text", "value": `${status.amount}%`, "color": goodColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Incoming.png`}
        ];
      }
    case "jinx":
      if (status["aspect"] == "damage"){
        return [
          {"type": "text", "value": `+${status.amount}%`, "color": badColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Incoming.png`},
        ];
      } else if (status["aspect"] == "prism") {
        return [
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['from']}.png`},
          {"type": "text", "value": "to", "color": badColor},
          {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['to']}.png`}
        ]
      }

    case "dot":
      return [
        {"type": "text", "value": `${status.amount}`, "color": badColor},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `school_type/${status['school']}.png`},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Damage.png`},
        {"type": "text", "value": `${status.wait ? "after" : "over"} ${status.rounds}`, "color": badColor},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Round.png`}
      ]
    case "hot":
      return [
        {"type": "text", "value": `+${status.amount}`, "color": goodColor},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Heal.png`},
        {"type": "text", "value": `over ${status.rounds}`, "color": goodColor},
        {"type": "image", "src": BACKEND_URL + BATTLE_PATH + `Round.png`}
      ]
    default:
      return [{"type": "text", "value": status.type ?? "unknown"}];
  }
}



export default function PlayerInfoWithIcons({
  player,
  leftIcon,
  style,
  schoolPipSelect,
  onSchoolPipChange,
}) {
  const activeIcons = STATUS_CATEGORIES
  .filter(category => player[category.key]?.length > 0)
  .map(category => ({
    key: category.key,
    icon: category.icon,
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

      {/* School pip selector — only shown for the current player */}
      {schoolPipSelect && onSchoolPipChange && (
        <div className="school-pip-selector-container">
          <SchoolPipSelector
            currentSchool={schoolPipSelect}
            size={statusIconSize}
            onChange={onSchoolPipChange}
          />
        </div>
      )}
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