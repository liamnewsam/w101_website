import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import CardHand from "../components/CardHand";
import OrbitalGraphic from "../components/OrbitalGraphic";
import "./GamePage.css";
import FloatingPresent from "../components/FloatingPresent";
import { BACKEND_URL, BATTLE_PATH } from "../config";
import CardReveal from "../components/CardReveal";
import SlideFadeReveal from "../components/SlideFadeReveal";
import SimpleArrow from "../components/SimpleArrow";

function computePlayerPos(orbitalDiameter, playerState, gameState, user_id) {
  let user_team = -1;
  let user_index = -1;
  for (let i =0; i < gameState.teams[0].length; i++) {
    if (gameState.teams[0][i].user_id == user_id) {
      user_team = 0;
      user_index = i;
      break
    }
  }

  if (user_team == -1) {
    for (let i = 0; i < gameState.teams[1].length; i++) {
      if (gameState.teams[1][i].user_id == user_id) {
        user_team = 1;
        user_index = i;
        break
      }
    }
  }

  let angle = (Math.PI * (user_index+1)) / (gameState.teams[user_team].length+1);
  if (playerState.team != user_team) {
    angle *= -1
  }


  return {x: orbitalDiameter/2.0*Math.cos(angle), y: orbitalDiameter/2.0*Math.sin(angle)}

}

function getPlayer(gs, user_id) {
  for (let j = 0; j < 2; j++) {
    for (let i = 0; i < gs.teams[j].length; i++) {
      if (gs.teams[j][i].user_id == user_id) {
        return gs.teams[j][i];
      }
    }
  }
  return null;
}

const orbitalDiameter = 400;

const wait = (ms) => new Promise(r => setTimeout(r, ms));

export default function GamePage() {
  const { gameId } = useParams();
  const { socket } = useSocket();
  const navigate = useNavigate();

  /* ============================
     AUTHORITATIVE STATE
     ============================ */
  const [lobbyState, setLobbyState] = useState(null);
  const [gameState, setGameState] = useState(null);
  const [playerState, setPlayerState] = useState(null);

  /* ============================
     VISUAL / ANIMATED STATE
     ============================ */
  const [visualGameState, setVisualGameState] = useState(null);
  const [visualPlayerState, setVisualPlayerState] = useState(null);

  /* ============================
     REPLAY STATE
     ============================ */
  const [eventQueue, setEventQueue] = useState([]);
  const [isReplaying, setIsReplaying] = useState(false);

  /* ============================
     INPUT STATE
     ============================ */
  const [selectedCardIndex, setSelectedCardIndex] = useState(-1);
  const [selectedTargetID, setSelectedTargetID] = useState(null);

  /* Visual Effects */
  const [visualEffects, setVisualEffects] = useState([]);


  let allUserIds;
  let playerPositions;
  /* Player Positions */
  useEffect(() => {
    if (!gameState || !playerState) return;
    allUserIds = gameState.teams.flatMap(team =>
      team.map(player => player.user_id)
    );

    playerPositions = Object.fromEntries(
      allUserIds.map(userId => [
        userId,
        computePlayerPos(orbitalDiameter, playerState, gameState, userId),
      ]));
    console.log(playerPositions);
    }, [gameState, playerState]);
    

  /* ============================
     SOCKET SETUP
     ============================ */
  useEffect(() => {
    socket.emit("watch_team", { gameId });

    const onLobbyState = (ls) => setLobbyState(ls);

    const onGameState = (gs) => {
      if (!isReplaying) {
        setGameState(gs);
        console.log("1 CHANGING VISUAL GAME STATE");
        setVisualGameState(gs);
      }
    };

    const onPlayerState = (ps) => {
      if (!isReplaying) {
        setPlayerState(ps);
        setVisualPlayerState(ps);
      }
    };

    const onTurnResolved = ({ finalGameState, finalPlayerState, log }) => {
      
      setGameState(finalGameState);
      setPlayerState(finalPlayerState);


      setEventQueue(events => [...events, ...log]);
      setIsReplaying(true);
    };

    const onEnd = (result) => {
      navigate(`/results/${gameId}`, { state: { result } });
    };

    socket.on("lobby_state_update", onLobbyState);
    //socket.on("game_state_update", onGameState);
    //socket.on("player_state_update", onPlayerState);
    socket.on("turn_resolved", onTurnResolved);
    socket.on("match_finished", onEnd);

    /* ===== SNAPSHOTS ===== */
    socket.emit("get_lobby_state", { gameId }, snap => snap && setLobbyState(snap));
    socket.emit("get_game_state", { gameId }, snap => {
      if (snap) {
        setGameState(snap);
        console.log("2 CHANGING VISUAL GAME STATE");
        setVisualGameState(snap);
      }
    });
    socket.emit("get_player_state", { gameId }, snap => {
      if (snap) {
        setPlayerState(snap);
        setVisualPlayerState(snap);
      }
    });

    return () => {
      socket.off("lobby_state_update", onLobbyState);
      //socket.off("game_state_update", onGameState);
      //socket.off("player_state_update", onPlayerState);
      socket.off("turn_resolved", onTurnResolved);
      socket.off("match_finished", onEnd);
      socket.emit("unwatch_game", { gameId });
    };
  }, [socket, gameId, navigate]);

  /* ============================
     TURN REPLAY ENGINE
     ============================ */
  useEffect(() => {
    console.log("HIHIHI");
    if (!isReplaying || eventQueue.length === 0) return;

    let cancelled = false;

    const replay = async () => {
      let gs = visualGameState;
      let ps = visualPlayerState;

      for (const event of eventQueue) {
        if (cancelled) return;
        ({ gs, ps } = await processEvent(event, gs, ps));
        console.log("3 CHANGING VISUAL GAME STATE");
        setVisualGameState(gs);
        setVisualPlayerState(ps);
      }

      if (!cancelled) {
        setIsReplaying(false);
        setEventQueue([]);
        console.log("4 CHANGING VISUAL GAME STATE");
        setVisualGameState(gameState);
        setVisualPlayerState(playerState);
        
      }
    };

    replay();
    return () => { cancelled = true; };
  }, [isReplaying]);

  /* ============================
     EVENT PROCESSOR
     ============================ */
  async function processEvent(event, gs, ps) {
    console.log(event);

    switch (event.type) {
      case "action":
        //gs = applyDamage(gs, event.target, event.amount);
        if (event.action == "attempt_cast") {
          console.log("At leat we are here");
          console.log(event);
          let effect = {
            type: "IMAGE",
            srcImg: BACKEND_URL + BATTLE_PATH + "cast_symbols/" + event.school + ".png",
            id: crypto.randomUUID()
          };
          setVisualEffects(effects => [...effects, effect]);
        }
        await wait(600);
        break;

      case "HEAL":
        gs = applyHeal(gs, event.target, event.amount);
        await wait(500);
        break;
      
      case "effect_resolve":
        if (event.aspect == "damage") {
          let effect = {
            type: "SIMPLE_ARROW",
            startPos: playerPositions[event.player],
            endPos: playerPositions[event.target],
            duration: 0.6,
            id: crypto.randomUUID()
          }
          setVisualEffects(effects => [...effects, effect]);
          await wait(600);
          let effect2 = {
            type: "FLOATING_PRESENT",
            items: [{"type": "text", "value": `-${event.amount}`}],
            id: crypto.randomUUID(),
            pos: playerPositions[event.target]
          }
          setVisualEffects(effects => [...effects, effect2]);
          
          let target = getPlayer(gs, event.target);
          if (target) {
            target.health -= event.amount;
          }
          break;
        }
        if (event.aspect == "pip_lose") {
          console.log("HI");
          let player = getPlayer(gs, event.player);
          for (const pip_type in event.amount) {
            player.pips[pip_type] -= event.amount[pip_type];
          }
          break;
        }
        if (event.aspect == "pip_gain") {
          console.log("BYE");
          let player = getPlayer(gs, event.player);
          for (const pip_type in event.amount) {
            console.log(pip_type);
            console.log(player.pips[pip_type]);
            player.pips[pip_type] += event.amount[pip_type];
          }
          break;
        }


      case "result":
        if (event.result == "success") {
          console.log("Success");
          let effect = {
            type: "REVEAL",
            img_path: event.card,
            id: crypto.randomUUID(),
            startPos: playerPositions[event.player]
          }
          setVisualEffects(effects => [...effects, effect]);
          await wait(2500);
          break;
        }
        if (event.result == "fizzle") {
          console.log("Fizzle");
          let effect = {
            type: "FLOATING_PRESENT",
            items: [{"type": "text", "value": "FIZZLE!"}],
            id: crypto.randomUUID()
          }
          setVisualEffects(effects => [...effects, effect]);
          await wait(1000);
          break;
        }
        

      default:
        await wait(300);
    }

    return { gs, ps };
  }

  /* ============================
     PLAYER ACTIONS
     ============================ */
  function sendAction(action, onResult=null) {
    socket.emit("player_action", { gameId, action }, ack => {
      if (!ack.ok) {
        console.warn("action rejected", ack.error);
      }
      if (onResult) {
        onResult(ack.ok);
      }
    });
  }

  function playCard(idx, target) {
    sendAction({ type: "cast", cardIndex: idx, target });
    setSelectedCardIndex(-1);
    setSelectedTargetID(null);
  }

  function discardCard(idx) {
    function onResult(result) {
      if (result) {
        setSelectedCardIndex(-1);
        setPlayerState(prev => ({
          ...prev,
          hand: prev.hand.filter((_, i) => i !== idx),
        }));
        setVisualPlayerState(prev => ({
          ...prev,
          hand: prev.hand.filter((_, i) => i !== idx),
        }));
      }
    }
    sendAction({ type: "discard", cardIndex: idx }, onResult);
  }

  function handleLeave() {
    sendAction({ type: "leave" });
    navigate("/menu");
  }

  /* ============================
     TURN / INPUT GATING
     ============================ */
  function isOurTurn() {
    if (isReplaying) return false;
    if (!playerState || !gameState) return false;
    return gameState.playing_team === playerState.team;
  }

  useEffect(() => {
    console.log(selectedCardIndex, selectedTargetID);
    if (
      selectedCardIndex >= 0 &&
      playerState &&
      playerState.hand[selectedCardIndex]
    ) {
      const card = playerState.hand[selectedCardIndex];
      if (card.targets.length === 0) {
        playCard(selectedCardIndex, null);
      } else if (selectedTargetID) {
        playCard(selectedCardIndex, selectedTargetID);
      }
    }
  }, [selectedCardIndex, selectedTargetID]);

  if (!visualGameState) return <div>Loading game…</div>;

  const board_info = {
    lobbyState,
    gameState: visualGameState,
    playerState: visualPlayerState
  };

  /* ============================
     RENDER
     ============================ */
  return (
    <div className="page game">
      <h1>Game {gameId}</h1>

      <div className="hud">
        {!isReplaying && <div>Round: {visualGameState.turns}</div>}
        {isReplaying && <div className="replay-indicator">Resolving turn…</div>}
      </div>

      <div className="orbital-layout">
        {lobbyState && visualGameState && visualPlayerState && (
          <OrbitalGraphic
            size={orbitalDiameter}
            board_info={board_info}
            selectedCardIndex={selectedCardIndex}
            onSelectTarget={setSelectedTargetID}
          />
        )}

        <div className="effects-layer">
          {visualEffects.map(effect => {
            switch (effect.type) {
              case "FLOATING_PRESENT":
                return (
                  <div style={{
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    transform: "translate(-50%, -50%)",
                  }}>
                    <FloatingPresent
                      key={effect.id}
                      items={effect.items}
                      onComplete={() =>
                        setVisualEffects(effects =>
                          effects.filter(e => e.id !== effect.id)
                        )
                      }
                      pos={effect.pos}
                    />
                  </div>
                );
              case "IMAGE":
                return (
                  <SlideFadeReveal 
                    key={effect.id}
                    srcImg={effect.srcImg}
                    onComplete={() => setVisualEffects(effects =>
                          effects.filter(e => e.id !== effect.id)
                        )}
                  />
                )

              case "REVEAL":
                return (            
                    <CardReveal
                      key={effect.id}
                      imgSrc={BACKEND_URL+ effect.img_path}
                      startPos={effect.startPos}
                      
                      onComplete={() => setVisualEffects(effects =>
                          effects.filter(e => e.id !== effect.id)
                        )}
                    />  
                )

              case "SIMPLE_ARROW":
                console.log(effect);
                return (
                  <SimpleArrow 
                    key={effect.id}
                    startPos={effect.startPos}
                    endPos={effect.endPos}
                    duration={effect.duration}
                    onComplete={() => setVisualEffects(effects =>
                          effects.filter(e => e.id !== effect.id)
                        )}
                  />

                )

              default:
                return null;
            }
          })}
      </div>
      </div>

      <div className="controls">
        {visualPlayerState && (
          <CardHand
            cards={visualPlayerState.hand}
            selectedIndex={selectedCardIndex}
            onSelectCard={setSelectedCardIndex}
            onDiscardCard={discardCard}
          />
        )}

        <div className="pass_leave">
          {isOurTurn() && (
            <button onClick={() => sendAction({ type: "pass" })}>
              Pass
            </button>
          )}
          <button onClick={handleLeave}>Leave Game</button>
        </div>
      </div>
        
      <div className="board"> {/* Replace with your duel view and animation canvas */} 
        <pre style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(gameState, null, 2)}
        </pre> 
        <pre style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(playerState, null, 2)}
        </pre> 
      </div>
      
    </div>
  );
}
