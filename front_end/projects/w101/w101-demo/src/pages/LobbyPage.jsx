import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { usePlayer } from "../PlayerContext"

function Slot({ player, onSwitchTeam }) {
  return (
    <div className="slot">
      {player ? (
        <>
          <div>{player.name}</div>
          <div>{player.isReady ? "Ready" : "Not Ready"}</div>
        </>
      ) : (
        <div>Empty</div>
      )}
      <button onClick={onSwitchTeam}>Switch Team</button>
    </div>
  );
}

export default function LobbyPage() {
  const { gameId } = useParams();
  const { socket } = useSocket();
  const { player } = usePlayer();
  const navigate = useNavigate();

  const [state, setState] = useState({ players: [], host: null, yourId: null });

  
  useEffect(() => {
    socket.emit("watch_lobby", { gameId });

    const onUpdate = (payload) => {
      setState(payload);
    };

    const onStart = () => {
      navigate(`/game/${gameId}`);
    };

    socket.on("update_lobby_state", onUpdate);
    socket.on("game_start", onStart);

    // request initial state
    socket.emit("get_lobby_state", { gameId });

    return () => {
      socket.off("update_lobby_state", onUpdate);
      socket.off("game_start", onStart);
      //socket.emit("leave_lobby", { gameId });
    };
  }, [socket, gameId, navigate]);

  function toggleReady() {
    socket.emit("player_ready", { gameId });
  }

  function leaveLobby() {
    socket.emit("leave_lobby", { gameId });
    navigate("/menu");
  }

  return (
    <div className="page lobby">
      <h1>Lobby {gameId}</h1>
      <div className="teams">
        <div className="team">
          <h3>Team A</h3>
          {state.players
            .filter((p) => p.team === "A")
            .map((p) => (
              <Slot key={p.id} player={p} onSwitchTeam={() => socket.emit("switch_team", { gameId, team: "B", playerId: p.id })} />
            ))}
        </div>

        <div className="team">
          <h3>Team B</h3>
          {state.players
            .filter((p) => p.team === "B")
            .map((p) => (
              <Slot key={p.id} player={p} onSwitchTeam={() => socket.emit("switch_team", { gameId, team: "A", playerId: p.id })} />
            ))}
        </div>
      </div>

      <div className="lobby-controls">
        <button onClick={toggleReady}>Toggle Ready</button>
        <button onClick={leaveLobby}>Return Home</button>
      </div>
    </div>
  );
}
