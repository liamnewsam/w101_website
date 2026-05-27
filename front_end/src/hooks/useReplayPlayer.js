import { useReducer, useEffect, useMemo, useState } from "react";
import {
  replayReducer,
  initialReplayState,
  ACTIONS,
  processEvent,
  computePlayerAngle,
  computePlayerPos,
} from "./useGameReplay";

export function useReplayPlayer({ replayData, setVisualEffects, setActivatedPlayerID }) {
  const [replayState, dispatch] = useReducer(replayReducer, initialReplayState);
  const { visual, replaying, eventQueue, turnQueue } = replayState;
  const [deadPlayerIds, setDeadPlayerIds] = useState(new Set());
  const [isAutoPlay, setIsAutoPlay] = useState(true);
  const [totalTurns, setTotalTurns] = useState(0);
  const [loaded, setLoaded] = useState(false);

  const addDeadPlayer = userId =>
    setDeadPlayerIds(ids => { const s = new Set(ids); s.add(userId); return s; });

  // Synthetic "viewer" perspective — always watch from team A's point of view
  const perspectivePlayer = useMemo(() => {
    const first = replayData?.initial_game_state?.teams?.[0]?.[0];
    if (!first) return null;
    return { team: 0, user_id: first.user_id };
  }, [replayData]);

  // Load initial state and queue all turns once data arrives
  useEffect(() => {
    if (!replayData || !perspectivePlayer || loaded) return;

    dispatch({ type: ACTIONS.SNAPSHOT, payload: { game: replayData.initial_game_state, player: perspectivePlayer } });

    const playingTeam = replayData.initial_game_state.playing_team ?? 0;
    const firstActivePlayer = replayData.initial_game_state.teams?.[playingTeam]?.[0];
    if (firstActivePlayer) setActivatedPlayerID(firstActivePlayer.user_id);

    for (const turn of replayData.turns) {
      dispatch({
        type: ACTIONS.TURN_RESOLVED,
        payload: { log: turn.log, finalGameState: turn.finalGameState, finalPlayerState: perspectivePlayer },
      });
    }
    setTotalTurns(replayData.turns.length);
    setLoaded(true);
  }, [replayData, perspectivePlayer, loaded]);

  const allUserIds = useMemo(() => {
    if (!visual.game) return [];
    return visual.game.teams.flatMap(t => t.map(p => p.user_id));
  }, [visual.game]);

  const playerPositions = useMemo(() => {
    if (!visual.game || !visual.player) return {};
    return Object.fromEntries(
      allUserIds.map(uid => [uid, computePlayerPos(visual.player, visual.game, uid)])
    );
  }, [allUserIds, visual.game, visual.player]);

  const playerAngles = useMemo(() => {
    if (!visual.game || !visual.player) return {};
    return Object.fromEntries(
      allUserIds.map(uid => [uid, computePlayerAngle(visual.player, visual.game, uid)])
    );
  }, [allUserIds, visual.game, visual.player]);

  // Auto-play: start next queued turn when idle
  useEffect(() => {
    if (!replaying && turnQueue.length > 0 && isAutoPlay) {
      dispatch({ type: ACTIONS.START_REPLAY });
    }
  }, [replaying, turnQueue.length, isAutoPlay]);

  // Process one event at a time
  useEffect(() => {
    if (!replaying || eventQueue.length === 0) return;
    let cancelled = false;
    const run = async () => {
      const event = eventQueue[0];
      if (!event) return;
      await processEvent(
        event, visual.game, visual.player,
        playerAngles, playerPositions,
        setVisualEffects, setActivatedPlayerID, addDeadPlayer
      );
      if (!cancelled) dispatch({ type: ACTIONS.ADVANCE_EVENT });
    };
    run();
    return () => { cancelled = true; };
  }, [eventQueue, replaying]);

  // Finish replay when event queue drains
  useEffect(() => {
    if (replaying && eventQueue.length === 0) {
      dispatch({ type: ACTIONS.FINISH_REPLAY });
      setDeadPlayerIds(new Set());
    }
  }, [eventQueue.length, replaying]);

  function nextTurn() {
    if (!replaying && turnQueue.length > 0) {
      dispatch({ type: ACTIONS.START_REPLAY });
    }
  }

  const turnsPlayed = totalTurns - turnQueue.length - (replaying ? 1 : 0);
  const isFinished = loaded && !replaying && turnQueue.length === 0;

  return {
    visual,
    replaying,
    playerAngles,
    playerPositions,
    deadPlayerIds,
    isAutoPlay,
    setIsAutoPlay,
    nextTurn,
    turnsPlayed,
    totalTurns,
    isFinished,
  };
}
