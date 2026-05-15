import { useReducer, useEffect, useMemo } from "react";
import { BACKEND_URL, BATTLE_PATH } from "../config";

export const ORBITAL_DIAMETER = 400;
// Orbit radius for self-targeting circular arrow. Larger = more visible arc.
// Start/end point is at playerPos + CIRCULAR_ARROW_RADIUS * (cos(playerAngle), sin(playerAngle)),
// i.e. the outer surface of the player icon in the direction away from the field center.
const CIRCULAR_ARROW_RADIUS = 80;
const CAST_ANIMATION_MS = 600;
const EFFECT_ARROW_MS = 600;
const EVENT_DELAY_MS = 300;
const FLOATING_PRESENT_OFFSET_X = 20;
const FLOATING_PRESENT_OFFSET_Y = -20;

const wait = ms => new Promise(r => setTimeout(r, ms));

function shallowMatch(obj, pattern) {
  return Object.keys(pattern).every(key => obj[key] === pattern[key]);
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

export function computePlayerAngle(playerState, gameState, user_id) {
  let user_team = -1;
  let user_index = -1;
  for (let i = 0; i < gameState.teams[0].length; i++) {
    if (gameState.teams[0][i].user_id === user_id) {
      user_team = 0;
      user_index = i;
      break;
    }
  }
  if (user_team === -1) {
    for (let i = 0; i < gameState.teams[1].length; i++) {
      if (gameState.teams[1][i].user_id === user_id) {
        user_team = 1;
        user_index = i;
        break;
      }
    }
  }
  let angle = (Math.PI * (user_index + 1)) / (gameState.teams[user_team].length + 1);
  if (playerState.team !== user_team) angle *= -1;
  return angle;
}

function computePlayerPos(playerState, gameState, user_id) {
  const angle = computePlayerAngle(playerState, gameState, user_id);
  return {
    x: (ORBITAL_DIAMETER / 2.0) * Math.cos(angle),
    y: (ORBITAL_DIAMETER / 2.0) * Math.sin(angle),
  };
}

function getPlayer(gs, user_id) {
  for (let j = 0; j < 2; j++) {
    for (let i = 0; i < gs.teams[j].length; i++) {
      if (gs.teams[j][i].user_id === user_id) return gs.teams[j][i];
    }
  }
  return null;
}

export const ACTIONS = {
  SNAPSHOT: "SNAPSHOT",
  TURN_RESOLVED: "TURN_RESOLVED",
  START_REPLAY: "START_REPLAY",
  ADVANCE_EVENT: "ADVANCE_EVENT",
  FINISH_REPLAY: "FINISH_REPLAY",
  OPTIMISTIC_DISCARD: "OPTIMISTIC_DISCARD",
  ACTION_RESULT: "ACTION_RESULT",
};

const initialReplayState = {
  authoritative: { game: null, player: null },
  visual: { game: null, player: null },
  turnQueue: [],
  eventQueue: [],
  replaying: false,
  confirmedDiscardIds: [],
};

function replayReducer(state, action) {
  switch (action.type) {
    case ACTIONS.SNAPSHOT: {
      const { game, player } = action.payload;
      const nextAuthoritative = {
        game: game ?? state.authoritative.game,
        player: player ?? state.authoritative.player,
      };
      if (state.replaying) return { ...state, authoritative: nextAuthoritative };
      return { ...state, authoritative: nextAuthoritative, visual: nextAuthoritative };
    }
    case ACTIONS.TURN_RESOLVED:
      return { ...state, turnQueue: [...state.turnQueue, action.payload] };
    case ACTIONS.START_REPLAY: {
      const [next, ...rest] = state.turnQueue;
      return {
        ...state,
        replaying: true,
        turnQueue: rest,
        eventQueue: next.log,
        authoritative: { game: next.finalGameState, player: next.finalPlayerState },
      };
    }
    case ACTIONS.ADVANCE_EVENT:
      return { ...state, eventQueue: state.eventQueue.slice(1) };
    case ACTIONS.FINISH_REPLAY: {
      const confirmedIds = new Set(state.confirmedDiscardIds);
      const hand = (state.authoritative.player?.hand ?? []).filter(
        c => !confirmedIds.has(c.instanceId)
      );
      return {
        ...state,
        replaying: false,
        eventQueue: [],
        confirmedDiscardIds: [],
        visual: {
          game: state.authoritative.game,
          player: { ...state.authoritative.player, hand },
        },
      };
    }
    case ACTIONS.ACTION_RESULT: {
      const { ok, cardId } = action.payload;
      if (!ok) {
        // Revert: rebuild visual from authoritative, re-applying any already-confirmed discards
        const confirmedIds = new Set(state.confirmedDiscardIds);
        const hand = (state.authoritative.player?.hand ?? []).filter(
          c => !confirmedIds.has(c.instanceId)
        );
        return {
          ...state,
          visual: {
            game: state.authoritative.game,
            player: { ...state.authoritative.player, hand },
          },
        };
      }
      if (!cardId) return state;
      // Server confirmed the discard. Track the ID so FINISH_REPLAY can filter it from
      // finalPlayerState (which may still have the card if the turn resolved first on
      // the backend). Also filter visual immediately in case FINISH_REPLAY already ran.
      const confirmedDiscardIds = [...state.confirmedDiscardIds, cardId];
      const visualHand = (state.visual.player?.hand ?? []).filter(
        c => c.instanceId !== cardId
      );
      return {
        ...state,
        confirmedDiscardIds,
        visual: {
          ...state.visual,
          player: { ...state.visual.player, hand: visualHand },
        },
      };
    }
    default:
      return state;
  }
}

async function processEvent(
  event, gs, ps, playerAngles, playerPositions, setVisualEffects, setActivatedPlayerID
) {
  switch (event.type) {
    case "turn_end": {
      setActivatedPlayerID(event.resting_player);
      break;
    }

    case "action": {
      switch (event.action) {
        case "activate":
          setActivatedPlayerID(event.player);
          // falls through — activate also shows the cast animation
          break;
        case "attempt_cast":
          console.log(event)
          setVisualEffects(effects => [...effects, {
            type: "IMAGE",
            srcImg: BACKEND_URL + BATTLE_PATH + "cast_symbols/" + event.school + ".png",
            id: crypto.randomUUID(),
          }]);
          await wait(CAST_ANIMATION_MS);
          break;
      }
      break;
    }

    case "effect_resolve": {
      if (event.target) {
        let effect;
        if (event.player === event.target) {
          effect = {
            type: "SIMPLE_ARROW",
            startPos: playerPositions[event.player],
            endPos: { x: 0, y: 0 },
            duration: EFFECT_ARROW_MS / 1000.0,
            id: crypto.randomUUID(),
          };
          setVisualEffects(effects => [...effects, effect]);
          await wait(EFFECT_ARROW_MS);
          effect = {
            type: "SIMPLE_ARROW",
            startPos: { x: 0, y: 0 },
            endPos: playerPositions[event.player],
            duration: EFFECT_ARROW_MS / 1000.0,
            id: crypto.randomUUID(),
          };
          setVisualEffects(effects => [...effects, effect]);
          await wait(EFFECT_ARROW_MS);
          
          
        } else {
          effect = {
            type: "SIMPLE_ARROW",
            startPos: playerPositions[event.player],
            endPos: playerPositions[event.target],
            duration: 0.6,
            id: crypto.randomUUID(),
          };
          setVisualEffects(effects => [...effects, effect]);
          await wait(EFFECT_ARROW_MS);
        }
        
      }

      switch (event.aspect) {
        case "damage": {
          setVisualEffects(effects => [...effects, {
            type: "FLOATING_PRESENT",
            items: [{ type: "text", value: `-${event.amount.toFixed(1)}` }],
            id: crypto.randomUUID(),
            pos: {
              x: playerPositions[event.target].x + FLOATING_PRESENT_OFFSET_X,
              y: playerPositions[event.target].y + FLOATING_PRESENT_OFFSET_Y
            },
          }]);
          const target = getPlayer(gs, event.target);
          if (target) target.health -= event.amount;
          break;
        }
        case "pip_lose": {
          const player = getPlayer(gs, event.player);
          for (const pip_type in event.amount) {
            if (pip_type === "converted") continue;
            player.pips[pip_type] -= event.amount[pip_type];
          }
          break;
        }
        case "pip_gain": {
          const player = getPlayer(gs, event.player);
          for (const pip_type in event.amount) {
            player.pips[pip_type] += event.amount[pip_type];
          }
          break;
        }
        case "charm":
        case "curse":
        case "ward":
        case "jinx": {
          const fieldMap = { charm: "charms", curse: "curses", ward: "wards", jinx: "jinxes" };
          setVisualEffects(effects => [...effects, {
            type: "FLOATING_PRESENT",
            items: [{ type: "text", value: `${event.aspect} gained` }],
            id: crypto.randomUUID(),
            pos: {
              x: playerPositions[event.target].x + FLOATING_PRESENT_OFFSET_X,
              y: playerPositions[event.target].y + FLOATING_PRESENT_OFFSET_Y
            },
          }]);
          const target = getPlayer(gs, event.target);
          target[fieldMap[event.aspect]] = [...target[fieldMap[event.aspect]], event.value];
          break;
        }
        case "heal": {
          setVisualEffects(effects => [...effects, {
            type: "FLOATING_PRESENT",
            items: [{ type: "text", value: `+${event.amount.toFixed(1)} health` }],
            id: crypto.randomUUID(),
            pos: {
              x: playerPositions[event.target].x + FLOATING_PRESENT_OFFSET_X,
              y: playerPositions[event.target].y + FLOATING_PRESENT_OFFSET_Y
            },
          }]);
          const target = getPlayer(gs, event.target);
          target.health += event.amount;
          break;
        }
      }
      break;
    }

    case "effect_trigger": {
      const fieldMap = { charm: "charms", curse: "curses", ward: "wards", jinx: "jinxes" };
      const field = fieldMap[event.aspect];
      if (field) {
        setVisualEffects(effects => [...effects, {
          type: "FLOATING_PRESENT",
          items: [{ type: "text", value: `${event.aspect} consumed` }],
          id: crypto.randomUUID(),
          pos: {
              x: playerPositions[event.player].x + FLOATING_PRESENT_OFFSET_X,
              y: playerPositions[event.player].y + FLOATING_PRESENT_OFFSET_Y
          }
        }]);
        const player = getPlayer(gs, event.player);
        player[field] = removeFirstMatching(player[field], event.value);
      }
      break;
    }

    case "result": {
      if (event.result === "success") {
        setVisualEffects(effects => [...effects, {
          type: "REVEAL",
          imgSrc: BACKEND_URL + "/" + event.card,
          id: crypto.randomUUID(),
          startPos: playerPositions[event.player],
        }]);
        await wait(2500);
      } else if (event.result === "fizzle") {
        setVisualEffects(effects => [...effects, {
          type: "FLOATING_PRESENT",
          items: [{ type: "text", value: "FIZZLE!" }],
          id: crypto.randomUUID(),
          pos: {
              x: playerPositions[event.player].x + FLOATING_PRESENT_OFFSET_X,
              y: playerPositions[event.player].y + FLOATING_PRESENT_OFFSET_Y
          },
        }]);
        await wait(1000);
      }
      break;
    }
  }

  await wait(EVENT_DELAY_MS);
  return { gs, ps };
}

export function useGameReplay({ socket, gameId, navigate, setVisualEffects, setActivatedPlayerID }) {
  const [replayState, dispatch] = useReducer(replayReducer, initialReplayState);
  const { visual, replaying, eventQueue, turnQueue } = replayState;

  const allUserIds = useMemo(() => {
    if (!visual.game) return [];
    return visual.game.teams.flatMap(team => team.map(p => p.user_id));
  }, [visual.game]);

  const playerPositions = useMemo(() => {
    if (!visual.game || !visual.player) return {};
    return Object.fromEntries(
      allUserIds.map(userId => [userId, computePlayerPos(visual.player, visual.game, userId)])
    );
  }, [allUserIds, visual.game, visual.player]);

  const playerAngles = useMemo(() => {
    if (!visual.game || !visual.player) return {};
    return Object.fromEntries(
      allUserIds.map(userId => [userId, computePlayerAngle(visual.player, visual.game, userId)])
    );
  }, [allUserIds, visual.game, visual.player]);

  // Subscribe to socket events and fetch initial state
  useEffect(() => {
    socket.emit("watch_team", { gameId });

    socket.on("turn_resolved", payload => {
      dispatch({ type: ACTIONS.TURN_RESOLVED, payload });
    });

    socket.on("match_finished", result => {
      navigate(`/results/${gameId}`, { state: { result } });
    });

    socket.emit("get_game_state", { gameId }, gs => {
      if (gs) {
        dispatch({ type: ACTIONS.SNAPSHOT, payload: { game: gs, player: null } });
        setActivatedPlayerID(gs.teams[gs.playing_team][0].user_id);
      }
    });

    socket.emit("get_player_state", { gameId }, ps => {
      if (ps) {
        dispatch({ type: ACTIONS.SNAPSHOT, payload: { game: null, player: ps } });
      }
    });

    return () => {
      socket.off("turn_resolved");
      socket.off("match_finished");
      socket.emit("unwatch_game", { gameId });
    };
  }, [socket, gameId, navigate]);

  // Start replaying the next queued turn when idle
  useEffect(() => {
    if (!replaying && turnQueue.length > 0) {
      dispatch({ type: ACTIONS.START_REPLAY });
    }
  }, [replaying, turnQueue.length]);

  // Process one event at a time from the queue
  useEffect(() => {
    if (!replaying || eventQueue.length === 0) return;

    let cancelled = false;

    const run = async () => {
      const event = eventQueue[0];
      if (!event) return;
      await processEvent(
        event, visual.game, visual.player,
        playerAngles, playerPositions,
        setVisualEffects, setActivatedPlayerID
      );
      if (!cancelled) dispatch({ type: ACTIONS.ADVANCE_EVENT });
    };

    run();
    return () => { cancelled = true; };
  }, [eventQueue, replaying]);

  // Finish replay once the event queue drains
  useEffect(() => {
    if (replaying && eventQueue.length === 0) {
      dispatch({ type: ACTIONS.FINISH_REPLAY });
    }
  }, [eventQueue.length, replaying]);

  return {
    visual,
    replaying,
    dispatch,
    playerAngles,
    authoritative: replayState.authoritative,
  };
}
