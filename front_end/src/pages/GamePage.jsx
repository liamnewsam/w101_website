import React, { useEffect, useReducer, useState } from "react";
import { motion } from "framer-motion";

import { useParams, useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import CardHand from "../components/CardHand";
import OrbitalGraphic from "../components/OrbitalGraphic";
import FloatingPresent from "../components/FloatingPresent";
import CardReveal from "../components/CardReveal";
import SlideFadeReveal from "../components/SlideFadeReveal";
import SimpleArrow from "../components/SimpleArrow";
import { BACKEND_URL, BATTLE_PATH } from "../config";
import "./GamePage.css";
import CircularArrow from "../components/CircularArrow";

/* ============================
   UTILITIES
   ============================ */
function shallowMatch(obj, pattern) {
  return Object.keys(pattern).every(
    key => obj[key] === pattern[key]
  );
}

function removeFirstMatching(arr, target) {
  let removed = false;

  return arr.filter(obj => {
    if (!removed && shallowMatch(obj, target)) {
      removed = true;
      return false;
    }
    return true;
  });
}


function computePlayerAngle(playerState, gameState, user_id) {
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
  return angle;
}



function computePlayerPos(orbitalDiameter, playerState, gameState, user_id) {
  let angle = computePlayerAngle(playerState, gameState, user_id);
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

const wait = ms => new Promise(r => setTimeout(r, ms));
const orbitalDiameter = 400;

/* ============================
   REDUCER
   ============================ */

const ACTIONS = {
  SNAPSHOT: "SNAPSHOT",
  TURN_RESOLVED: "TURN_RESOLVED",
  START_REPLAY: "START_REPLAY",
  ADVANCE_EVENT: "ADVANCE_EVENT",
  FINISH_REPLAY: "FINISH_REPLAY",
  OPTIMISTIC_DISCARD: "OPTIMISTIC_DISCARD",
  ACTION_RESULT: "ACTION_RESULT"
};

const initialReplayState = {
  authoritative: { game: null, player: null },
  visual: { game: null, player: null },
  turnQueue: [],
  eventQueue: [],
  replaying: false,
};

function replayReducer(state, action) {
  switch (action.type) {
    case ACTIONS.SNAPSHOT: {
        const { game, player } = action.payload;

        const nextAuthoritative = {
            game: game ?? state.authoritative.game,
            player: player ?? state.authoritative.player,
        };

        if (state.replaying) {
            return {
            ...state,
            authoritative: nextAuthoritative,
            };
        }

        return {
            ...state,
            authoritative: nextAuthoritative,
            visual: nextAuthoritative,
        };
        }


    case ACTIONS.TURN_RESOLVED:
      return {
        ...state,
        turnQueue: [...state.turnQueue, action.payload],
      };

    case ACTIONS.START_REPLAY: {
      const [next, ...rest] = state.turnQueue;
      return {
        ...state,
        replaying: true,
        turnQueue: rest,
        eventQueue: next.log,
        authoritative: {
          game: next.finalGameState,
          player: next.finalPlayerState,
        },
      };
    }

    case ACTIONS.ADVANCE_EVENT:
      return {
        ...state,
        eventQueue: state.eventQueue.slice(1),
      };

    case ACTIONS.FINISH_REPLAY:
      return {
        ...state,
        replaying: false,
        eventQueue: [],
        visual: {
          game: state.authoritative.game,
          player: state.authoritative.player,
        },
      };

    case ACTIONS.OPTIMISTIC_DISCARD: {
        const { cardIndex } = action.payload;

        const nextVisualPlayer = {
            ...state.visual.player,
            hand: state.visual.player.hand.filter((_, i) => i !== cardIndex),
        };

        return {
            ...state,
            visual: {
            ...state.visual,
            player: nextVisualPlayer,
            },
        };
    }

    case ACTIONS.ACTION_RESULT: {
        if (action.payload.ok) return state;

        // rollback
        return {
            ...state,
            visual: state.authoritative,
        };
    }



    default:
      return state;
  }
}

/* ============================
   MAIN COMPONENT
   ============================ */

export default function GamePage() {
  const { gameId } = useParams();
  const { socket } = useSocket();
  const navigate = useNavigate();

  const [replayState, dispatch] = useReducer(
    replayReducer,
    initialReplayState
  );

  const { visual, replaying, eventQueue, turnQueue } = replayState;

  const allUserIds = React.useMemo(() => {
    if (!visual.game) return [];

    return visual.game.teams.flatMap(team =>
        team.map(player => player.user_id)
    );
  }, [visual.game]);

  const playerPositions = React.useMemo(() => {
    if (!visual.game || !visual.player) return {};

    return Object.fromEntries(
        allUserIds.map(userId => [
        userId,
        computePlayerPos(
            orbitalDiameter,
            visual.player,
            visual.game,
            userId
        ),
        ])
    );
  }, [allUserIds, visual.game, visual.player]);

  const playerAngles = React.useMemo(() => {
    if (!visual.game || !visual.player) return {};

    return Object.fromEntries(
        allUserIds.map(userId => [
        userId,
        computePlayerAngle(
            visual.player,
            visual.game,
            userId
        ),
        ])
    );
  }, [allUserIds, visual.game, visual.player]);



  /* ============================
     VISUAL EFFECTS
     ============================ */

  const [visualEffects, setVisualEffects] = useState([]);

  /* ============================
     SOCKET SETUP
     ============================ */

  useEffect(() => {
    socket.emit("watch_team", { gameId });

    socket.on("turn_resolved", payload => {
      dispatch({ 
        type: ACTIONS.TURN_RESOLVED, 
        payload });
    });

    socket.on("match_finished", result => {
      navigate(`/results/${gameId}`, { state: { result } });
    });

    socket.emit("get_game_state", { gameId }, gs => {
      if (gs) {
        dispatch({
          type: ACTIONS.SNAPSHOT,
          payload: { game: gs, player: replayState.authoritative.player },
        });
        setActivatedPlayerID(gs.teams[gs.playing_team][0].user_id);
      }
    });

    socket.emit("get_player_state", { gameId }, ps => {
      if (ps) {
        dispatch({
          type: ACTIONS.SNAPSHOT,
          payload: { game: replayState.authoritative.game, player: ps },
        });
      }
    });

    return () => {
      socket.off("turn_resolved");
      socket.off("match_finished");
      socket.emit("unwatch_game", { gameId });
    };
  }, [socket, gameId, navigate]);

  /* ============================
     AUTO START REPLAY
     ============================ */

  useEffect(() => {
    if (!replaying && turnQueue.length > 0) {
      dispatch({ type: ACTIONS.START_REPLAY });
    }
  }, [replaying, turnQueue.length]);

  /* ============================
     EVENT REPLAY ENGINE
     ============================ */

  useEffect(() => {
    if (!replaying || eventQueue.length === 0) return;

    let cancelled = false;

    const run = async () => {
      const event = eventQueue[0];
      if (!event) return;

      const { gs, ps } = await processEvent(
        event,
        visual.game,
        visual.player,
        playerAngles,
        playerPositions,
        setVisualEffects,
        setActivatedPlayerID
      );

      if (!cancelled) {
        dispatch({ type: ACTIONS.ADVANCE_EVENT });
        
        /*
        dispatch({
          type: ACTIONS.SNAPSHOT,
          payload: { game: gs, player: ps },
        });*/
      }
    };

    run();
    return () => { cancelled = true; };
  }, [eventQueue, replaying]);

  /* ============================
     FINISH REPLAY
     ============================ */

  useEffect(() => {
    if (replaying && eventQueue.length === 0) {
      dispatch({ type: ACTIONS.FINISH_REPLAY });
    }
  }, [eventQueue.length, replaying]);

  /* ============================
     INPUT HELPERS
     ============================ */

  function isOurTurn() {
    if (replaying || !visual.game || !visual.player) return false;
    return visual.game.playing_team === visual.player.team;
  }

  function sendAction(action) {
    socket.emit("player_action", { gameId, action });
  }

  function playCard(idx, target) {
    sendAction({ type: "cast", cardIndex: idx, target });
    clearSelection();
  }

  const [selectedCardIndex, setSelectedCardIndex] = useState(-1);
  //const [selectedTargetID, setSelectedTargetID] = useState(null);

  function onCardSelected(idx) {
    const card = visual.player.hand[idx]; // ← already known

    if (card.targets.length === 0) {
        playCard(idx, null);
    } else {
        setSelectedCardIndex(idx);
    }
  }

  function onTargetSelected(targetId) {
    if (selectedCardIndex < 0 || !visual.player) return;
    playCard(selectedCardIndex, targetId);
  }


  function clearSelection() {
    setSelectedCardIndex(-1);
  }

  function discardCard(idx) {
    dispatch({
        type: ACTIONS.OPTIMISTIC_DISCARD,
        payload: { cardIndex: idx },
    });

    socket.emit(
        "player_action",
        { gameId, action: { type: "discard", cardIndex: idx } },
        ack => {
        dispatch({
            type: ACTIONS.ACTION_RESULT,
            payload: ack,
        });
        }
    );
  }

  
  const [activatedPlayerID, setActivatedPlayerID] = useState();
  //Once on load:
  /*
  useEffect(() => {
    if (!activatedPlayerID && visual?.teams?.[visual.playing_team]?.[0]) {
      setActivatedPlayerID(visual.teams[visual.playing_team][0].user_id);
      console.log("HI");
    }
  }, [visual, activatedPlayerID]);*/


  /* ============================
     RENDER
     ============================ */

  if (!visual.game || !visual.player) {
    return <div>Loading game…</div>;
  }


  return (
    <div className="page game">
      <h1>Game {gameId}</h1>

      <div className="hud">
        {!replaying && <div>Round: {visual.game.turns}</div>}
        {replaying && <div className="replay-indicator">Resolving turn…</div>}
      </div>

      <div className="orbital-layout">
        <OrbitalGraphic
            size={orbitalDiameter}
            board_info={{
            gameState: visual.game,
            playerState: visual.player,
            }}
            selectedCardIndex={selectedCardIndex}
            onSelectTarget={onTargetSelected}
        />


        <motion.img
          src={BACKEND_URL + "static/w101/battle_triangle.png"}
          animate={
            activatedPlayerID != null
              ? { rotate: 90 + (playerAngles[activatedPlayerID] * 180) / Math.PI }
              : false
          }
          transition={{ duration: 0.4, ease: "linear" }}
          transformTemplate={({ rotate }) =>
            `translate(-50%, -50%) rotate(${rotate})`
          }
          style={{
            position: "absolute",
            width: orbitalDiameter,
            height: orbitalDiameter,
            left: "50%",
            top: "50%",
            pointerEvents: "none",
            zIndex: 1,
          }}
          initial={false}

        />


      </div>

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
                    {...effect}
                    onComplete={() =>
                        setVisualEffects(effects =>
                        effects.filter(e => e.id !== effect.id)
                        )
                    }
                    />
                </div>
              );

            case "IMAGE":
              return (
                <SlideFadeReveal
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects =>
                      effects.filter(e => e.id !== effect.id)
                    )
                  }
                />
              );

            case "REVEAL":
              return (
                <CardReveal
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects =>
                      effects.filter(e => e.id !== effect.id)
                    )
                  }
                />
              );

            case "SIMPLE_ARROW":
              return (
                <SimpleArrow
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects =>
                      effects.filter(e => e.id !== effect.id)
                    )
                  }
                />
              );
            
            case "CIRCULAR_ARROW":
              return (
                <CircularArrow 
                  key={effect.id}
                  {...effect}
                  onComplete={() =>
                    setVisualEffects(effects =>
                      effects.filter(e => e.id !== effect.id)
                    )
                  }
                />
              )

            default:
              return null;
          }
        })}
      </div>

      <div className="controls">
        <CardHand
          cards={visual.player.hand}
          selectedIndex={selectedCardIndex}
          onSelectCard={onCardSelected}
          onDiscardCard={discardCard}
        />

        <div className="pass_leave">
          {isOurTurn() && (
            <button onClick={() => sendAction({ type: "pass" })}>
              Pass
            </button>
          )}
          <button onClick={() => navigate("/menu")}>Leave Game</button>
        </div>
      </div>

      <div className="board"> {/* Replace with your duel view and animation canvas */} 
        <pre style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(replayState.authoritative.game, null, 2)}
        </pre> 
        <pre style={{ whiteSpace: "pre-wrap" }}>
          {JSON.stringify(replayState.authoritative.player, null, 2)}
        </pre> 
      </div>
    </div>
  );
}

/* ============================
   EVENT PROCESSOR (UNCHANGED)
   ============================ */
const circularArrowRadius = 150;
async function processEvent(event, gs, ps, playerAngles, playerPositions, setVisualEffects, setActivatedPlayerID) {
  // your existing logic goes here
    console.log(event);
  
    switch (event.type) {
        case "turn_end": {
          setActivatedPlayerID(event.resting_player);
          break;
        }

        case "action": {
          
          switch (event.action) {
            case "activate": {
              setActivatedPlayerID(event.player);
            }
            case "attempt_cast": {
              let effect = {
                type: "IMAGE",
                srcImg: BACKEND_URL + BATTLE_PATH + "cast_symbols/" + event.school + ".png",
                id: crypto.randomUUID()
              };
              setVisualEffects(effects => [...effects, effect]);
            }
              await wait(600);
              break;
          }
          break;
        }
            

        case "HEAL": {
            gs = applyHeal(gs, event.target, event.amount);
            await wait(500);
            break;
        }
        case "effect_resolve": {
            if (event.target) {
              let effect;
              if (event.player == event.target) {
                effect = {
                  type: "CIRCULAR_ARROW",
                  center: {
                    x: (orbitalDiameter/2.0-circularArrowRadius)*Math.cos(playerAngles[event.player]),
                    y: (orbitalDiameter/2.0-circularArrowRadius)*Math.sin(playerAngles[event.player])
                  },
                  radius: circularArrowRadius,
                  startAngle: playerAngles[event.player]
                };
              } else {
                effect = {
                          type: "SIMPLE_ARROW",
                          startPos: playerPositions[event.player],
                          endPos: playerPositions[event.target],
                          duration: 0.6,
                          id: crypto.randomUUID()
                }
              }
              setVisualEffects(effects => [...effects, effect]);
              
              await wait(600);
            }
            switch (event.aspect) {
                case "damage": {
                    
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

                case "pip_lose": {
                    let player = getPlayer(gs, event.player);
                    for (const pip_type in event.amount) {
                        if (pip_type == "converted") {
                            if (event.amount["converted"]) {
                                console.log("Converted!"); //Placeholder
                            }
                        } else {
                            player.pips[pip_type] -= event.amount[pip_type];
                        }
                    }
                    break;
                }
                case "pip_gain": {
                    let player = getPlayer(gs, event.player);
                    for (const pip_type in event.amount) {
                        console.log(pip_type);
                        console.log(player.pips[pip_type]);
                        player.pips[pip_type] += event.amount[pip_type];
                    }
                    break;
                }
                case "charm": {
                    let effect2 = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "charm gained"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.target]
                    }
                    setVisualEffects(effects => [...effects, effect2]);

                    let target = getPlayer(gs, event.target);
                    target.charms = [...target.charms, event.value];
                    break;
                }
                case "curse": {
                    let effect2 = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "curse gained"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.target]
                    }
                    setVisualEffects(effects => [...effects, effect2]);

                    let target = getPlayer(gs, event.target);
                    target.curses = [...target.curses, event.value];
                    break;
                }
                case "ward": {
                    let effect2 = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "ward gained"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.target]
                    }
                    setVisualEffects(effects => [...effects, effect2]);

                    let target = getPlayer(gs, event.target);
                    target.wards = [...target.wards, event.value];
                    break;
                }
                case "jinx": {
                    let effect2 = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "jinx gained"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.target]
                    }
                    setVisualEffects(effects => [...effects, effect2]);

                    let target = getPlayer(gs, event.target);
                    target.jinxes = [...target.jinxes, event.value];
                    break;
                }
                case "heal": {
                  let effect2 = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": `+${event.amount} health`}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.target]
                    }
                  setVisualEffects(effects => [...effects, effect2]);

                  let target = getPlayer(gs, event.target);
                  target.health += event.amount;
                  break;
                }
            }
            break;
        }

        case "effect_trigger": {
            switch (event.aspect) {
                case "charm": {
                    let effect = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "charm consumed"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.player]
                    }
                    setVisualEffects(effects => [...effects, effect]);

                    let player = getPlayer(gs, event.player);
                    player.charms = removeFirstMatching(player.charms, event.value);
                    break;
                }
                case "curse": {
                    let effect = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "curse consumed"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.player]
                    }
                    setVisualEffects(effects => [...effects, effect]);

                    let player = getPlayer(gs, event.player);
                    player.curses = removeFirstMatching(player.curses, event.value);
                    break;
                }
                case "ward": {
                    let effect = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "ward consumed"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.player]
                    }
                    setVisualEffects(effects => [...effects, effect]);

                    let player = getPlayer(gs, event.player);
                    player.wards = removeFirstMatching(player.wards, event.value);
                    break;
                }
                case "jinx": {
                    let effect = {
                        type: "FLOATING_PRESENT",
                        items: [{"type": "text", "value": "jinx consumed"}],
                        id: crypto.randomUUID(),
                        pos: playerPositions[event.player]
                    }
                    setVisualEffects(effects => [...effects, effect]);

                    let player = getPlayer(gs, event.player);
                    player.jinxes = removeFirstMatching(player.jinxes, event.value);
                    break;
                }
            }
        break;
        }

        case "result": {
            if (event.result == "success") {
            console.log("Success");
            let effect = {
                type: "REVEAL",
                imgSrc: BACKEND_URL + event.card,
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
        }
    }
  await wait(300);
  return { gs, ps };
}
