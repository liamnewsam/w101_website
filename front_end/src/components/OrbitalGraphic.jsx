import "./OrbitalGraphic.css";
import {BACKEND_URL, TARGET_PATH} from "../config";
import PlayerInfoWithIcons from "./PlayerInfoWithIcons";
import FloatingPresent from "./FloatingPresent";


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
  onSelectTarget
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

  function get_image_path(user_id) {
    //console.log(user_id);
    for (let i = 0; i < lobbyState.players.length; i++) {
        let player = lobbyState.players[i]
        //console.log(player);
        if (player.id == user_id) {
            //console.log(player.image_path);
            return player.image_path;
        }
    }
    return "";
  }

  function userSelectingTarget() {
    if (selectedCardIndex != null && selectedCardIndex >= 0 && selectedCardIndex < playerState.hand.length && playerState.hand[selectedCardIndex].targets.length > 0) {
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
            />

            
            <div style={{ overflow: "hidden" }}>
                <img
                    src={BACKEND_URL + "/" + player.img_path}
                    alt=""
                    className={`
                        player-image
                        ${userSelectingTarget() ? (targetIsValid(player.user_id) ? "valid-target" : "invalid-target") : ""}
                    `}
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
            />

            
            <div style={{ overflow: "hidden" }}>
                <img
                    src={BACKEND_URL + "/" + player.img_path}
                    alt=""
                    className={`
                        player-image
                        ${userSelectingTarget() ? (targetIsValid(player.user_id) ? "valid-target" : "invalid-target") : ""}
                    `}
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
