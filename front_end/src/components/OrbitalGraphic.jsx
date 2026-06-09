import { useState } from "react";
import "./OrbitalGraphic.css";
import {BACKEND_URL, TARGET_PATH, BATTLE_PATH, goodColor} from "../config";
import PlayerInfoWithIcons from "./PlayerInfoWithIcons";
import FloatingPresent from "./FloatingPresent";

const GLOBAL_ASPECT_ICON = {
  damage: "Damage.png",
  armor_piercing: "Accuracy.png",
  critical: "Critical.png",
  heal: "Heal.png",
};

function GlobalEffectIcon({ effects, size = 32 }) {
  const [popup, setPopup] = useState({ visible: false, x: 0, y: 0 });

  return (
    <div
      style={{ position: "relative", display: "inline-block" }}
      onMouseMove={e => {
        const rect = e.currentTarget.getBoundingClientRect();
        setPopup({ visible: true, x: e.clientX - rect.left + 10, y: e.clientY - rect.top + 10 });
      }}
      onMouseLeave={() => setPopup(p => ({ ...p, visible: false }))}
    >
      <img
        src={BACKEND_URL + BATTLE_PATH + "Global.png"}
        alt="global effects"
        style={{ width: size, height: size, display: "block" }}
      />
      {popup.visible && (
        <div className="status-popup" style={{ position: "absolute", left: popup.x, top: popup.y, zIndex: 10 }}>
          {effects.map((effect, i) => (
            <div key={i} className="popup-line">
              <span style={{ color: goodColor, marginRight: 4 }}>+{effect.amount}%</span>
              {effect.school && (
                <img
                  src={BACKEND_URL + BATTLE_PATH + `school_type/${effect.school}.png`}
                  alt={effect.school}
                  style={{ width: 16, height: 16, marginRight: 4 }}
                />
              )}
              <img
                src={BACKEND_URL + BATTLE_PATH + (GLOBAL_ASPECT_ICON[effect.aspect] || "Damage.png")}
                alt={effect.aspect}
                style={{ width: 16, height: 16 }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


const bottomTargetIcons = [
    "Dagger.png",
    "Eye.png",
    "Gem.png",
    "Key.png" 
];

const topTargetIcons = [
    "Moon.png",
    "Spiral.png",
    "Star.png",
    "Sun.png"
]



export default function OrbitalGraphic({
  size = 400,          // diameter of the main circle
  board_info = {},
  selectedCardIndex,
  onSelectTarget,
  deadPlayerIds = new Set(),
  currentPlayerSchoolPip,
  onSchoolPipChange,
}) {
  const center = size / 2;

  let gameState = board_info.gameState;
  let playerState = board_info.playerState;
  let teamBottom = gameState.teams[playerState.team];
  const countBottom = teamBottom.length;

  let teamUp = gameState.teams[(playerState.team + 1) % 2]
  const countUp = teamUp.length;

  let player_angle = {};
  for (let i = 0; i < countUp; i++) {
    const angle = -(Math.PI * (i+1)) / (countUp+1);
    player_angle[teamUp[i].user_id] = angle;
  }
  for (let i = 0; i < countBottom; i++) {
    const angle = (Math.PI * (i+1)) / (countBottom+1);
    player_angle[teamBottom[i].user_id] = angle;
  }

  function userSelectingTarget() {
    if (selectedCardIndex != null && selectedCardIndex >= 0 && playerState && playerState.hand && selectedCardIndex < playerState.hand.length && playerState.hand[selectedCardIndex]?.targets?.length > 0) {
        return true;
    }
    return false;
  }

  function targetIsValid(user_id) {
    //console.log(playerState.hand[selectedCardIndex].targets);
    if (playerState.hand[selectedCardIndex].targets.includes(user_id)) return true;
    return false;
  }

  let triangle_angle=90 + 180/Math.PI * player_angle[gameState.teams[gameState.playing_team][0].user_id];
  const orbit_size=64;
  const targetSize = 50;
  const targetDistance = orbit_size / 2;
  return (
    <div
      className="orbital-container"
      style={{
        width: size,
        height: size,
        position: "absolute",
        left: "50%",
        top: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 3
      }}
    >
      {/* Main circle */}

      <div
        className="main-circle"
        style={{
          width: size,
          height: size,
          left: center,
          top: center,
        }}
      />

      {/* Global effects icon */}
      {gameState.global_effects?.length > 0 && (
        <div
          style={{
            position: "absolute",
            left: center,
            top: center,
            transform: "translate(-50%, -50%)",
            zIndex: 5,
          }}
        >
          <GlobalEffectIcon effects={gameState.global_effects} size={32} />
        </div>
      )}

      {/*
      <img
        src={BACKEND_URL + "static/w101/battle_triangle.png"}
        style={{
            position: "absolute",
            width: size,
            height: size,
            left: center,
            top: center,
            transform: `translate(-50%, -50%) rotate(${triangle_angle}deg)`,
            pointerEvents: "none", // optional
        }}
      />*/}
        

      {/* Enemy Team (UP) */}
      {teamUp.map((player, index) => {
        const angle = player_angle[player.user_id]
        const x = center + size/2 * Math.cos(angle);
        const y = center + size/2 * Math.sin(angle);

        const infoDistance = 120
        const infoXRelative = infoDistance * Math.cos(angle);
        const infoYRelative = infoDistance / 2 * Math.sin(angle);
        const infoWidth = 140;
        const infoHeight = 30;

        const targetXRelative = targetDistance * Math.cos(angle+Math.PI/2);
        const targetYRelative = targetDistance * Math.sin(angle+Math.PI/2);
        const isCurrentPlayer = player.user_id === playerState.user_id;
        //
        return (
          <div
            key={player.user_id}
            className="orbit-item"
            style={{
            width: `${orbit_size}px`,
            height: `${orbit_size}px`,
            left: x,
            top: y,
            }}
          >
            <PlayerInfoWithIcons
                player={player}
                leftIcon={BACKEND_URL + `/static/w101/icons/schools/${player.school}.png`}
                style={{
                    left: `${orbit_size/2 + infoXRelative}px`,
                    top: `${orbit_size/2 + infoYRelative}px`,
                    transform: "translate(-50%, -50%)",
                    position: "absolute",
                    borderStyle: "solid",
                    width: `${infoWidth}px`,
                    height: `${infoHeight}px`
                }}
                schoolPipSelect={isCurrentPlayer ? currentPlayerSchoolPip : undefined}
                onSchoolPipChange={isCurrentPlayer ? onSchoolPipChange : undefined}
            />

            
            <div style={{ overflow: "hidden" }}>
                <img
                    src={BACKEND_URL + "/" + player.img_path}
                    alt=""
                    className={`
                        player-image
                        ${(player.health == 0 || deadPlayerIds.has(player.user_id)) ? "dead" : userSelectingTarget() ? (targetIsValid(player.user_id) ? "valid-target" : "invalid-target") : ""}

                    `}
                    onMouseDown={(userSelectingTarget() && targetIsValid(player.user_id)) ? (e) => e.stopPropagation() : undefined}
                    onClick={(userSelectingTarget() && targetIsValid(player.user_id)) ? () => onSelectTarget(player.user_id) : undefined}
                    style={{
                        cursor: (userSelectingTarget() && targetIsValid(player.user_id)) ? "pointer" : "default",
                    }}
                />
            </div>


            <div style={{
                left: `${orbit_size/2 + targetXRelative}px`,
                top: `${orbit_size/2 + targetYRelative}px`,
                transform: "translate(-50%, -50%)",
                position: "absolute",
                /*borderStyle: "solid",*/
                width: `${targetSize}px`,
                height: `${targetSize}px`,
                overflow: "hidden",
                /*borderRadius: "50%",*/
            }}>
                <img src={BACKEND_URL+TARGET_PATH+topTargetIcons[index]} alt=""/>
            </div>
          </div>

        );
      })}

      {teamBottom.map((player, index) => {
        const angle = player_angle[player.user_id]
        const x = center + size/2 * Math.cos(angle);
        const y = center + size/2 * Math.sin(angle);

        const infoDistance = 120
        const infoXRelative = infoDistance * Math.cos(angle);
        const infoYRelative = infoDistance / 2 * Math.sin(angle);
        const infoWidth = 140;
        const infoHeight = 30;

        const targetXRelative = targetDistance * Math.cos(angle+Math.PI/2);
        const targetYRelative = targetDistance * Math.sin(angle+Math.PI/2);
        const isCurrentPlayer = player.user_id === playerState.user_id;
        //
        return (
          <div
            key={player.user_id}
            className="orbit-item"
            style={{
            width: `${orbit_size}px`,
            height: `${orbit_size}px`,
            left: x,
            top: y,
            }}
          >
            <PlayerInfoWithIcons
                player={player}
                leftIcon={BACKEND_URL + `/static/w101/icons/schools/${player.school}.png`}
                style={{
                    left: `${orbit_size/2 + infoXRelative}px`,
                    top: `${orbit_size/2 + infoYRelative}px`,
                    transform: "translate(-50%, -50%)",
                    position: "absolute",
                    borderStyle: "solid",
                    width: `${infoWidth}px`,
                    height: `${infoHeight}px`
                }}
                schoolPipSelect={isCurrentPlayer ? currentPlayerSchoolPip : undefined}
                onSchoolPipChange={isCurrentPlayer ? onSchoolPipChange : undefined}
            />


            <div style={{ overflow: "hidden" }}>
                <img
                    src={BACKEND_URL + "/" + player.img_path}
                    alt=""
                    className={`
                        player-image
                        ${(player.health == 0 || deadPlayerIds.has(player.user_id)) ? "dead" : userSelectingTarget() ? (targetIsValid(player.user_id) ? "valid-target" : "invalid-target") : ""}
                    `}
                    onMouseDown={(userSelectingTarget() && targetIsValid(player.user_id)) ? (e) => e.stopPropagation() : undefined}
                    onClick={(userSelectingTarget() && targetIsValid(player.user_id)) ? () => onSelectTarget(player.user_id) : undefined}
                    style={{
                        cursor: (userSelectingTarget() && targetIsValid(player.user_id)) ? "pointer" : "default",
                    }}
                />
            </div>
                
            <div style={{
                left: `${orbit_size/2 + targetXRelative}px`,
                top: `${orbit_size/2 + targetYRelative}px`,
                transform: "translate(-50%, -50%)",
                position: "absolute",
                /*borderStyle: "solid",*/
                width: `${targetSize}px`,
                height: `${targetSize}px`,
                overflow: "hidden",
                /*borderRadius: "50%",*/
            }}>
                <img src={BACKEND_URL+TARGET_PATH+bottomTargetIcons[index]} alt=""/>
            </div>
          </div>

        );
      })}

    </div>
  );
}
