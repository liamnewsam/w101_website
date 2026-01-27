import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { logout } from "../api/auth";
import { usePlayer } from "../PlayerContext";
import Loading from "../components/Loading";

export default function MenuPage() {
  const { socket, connected, disconnectSocket } = useSocket();
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  console.log(socket);

  const { player } = usePlayer();
  // Redirect if no socket (means logged out)
  useEffect(() => {
    if (!socket) {
      console.log("We don't have socket");
      navigate("/login");
      return;
    }
  }, [socket, navigate]);

  useEffect(() => {
    const onList = (list) => setGames(list);
    socket.on("game_list", onList);

    socket.emit("list_games");

    return () => {
      socket.off("game_list", onList);
    };
  }, [socket]);

  function handleCreate() {
    socket.emit("create_game", {}, (resp) => {
      if (resp?.gameId) navigate(`/lobby/${resp.gameId}`);
    });
  }

  function handleCreateBots() {
    socket.emit("create_bot_game", {}, (resp) => {
      if (resp?.gameId) navigate(`/lobby/${resp.gameId}`);
    });
  }

  function handleJoin(gameId) {
    socket.emit("join_game", { gameId }, (ack) => {
      if (ack?.ok) navigate(`/lobby/${gameId}`);
      else alert(ack?.error || "Failed to join");
    });
  }

  function handleLogout() {
    logout(disconnectSocket);
    navigate("/login");
  }

  return ( !player ? <Loading /> :
    <div className="page menu">
      <h1>Magic Duel — Menu</h1>

      <div>
        {player.name}
      </div>

      <div>
        School: {player.school}
      </div>

      <div>
        Main Deck: {player.deck.name}
      </div>


      <div className="menu-actions">
        <button onClick={handleCreate}>Create Multiplayer Game</button>
        <button onClick={handleCreateBots}>Create vs Bots</button>
      </div>

      <h2>Open Games</h2>
      <div className="game-list">
        {games.length === 0 && <p>No open games</p>}
        {games.map((g) => (
          <div key={g.gameId} className="game-list-item">
            <span>{g.name || g.gameId}</span>
            <span>{g.players?.length || 0}/8</span>
            <button onClick={() => handleJoin(g.gameId)}>Join</button>
          </div>
        ))}
      </div>

      <p>Socket connected: {connected ? "yes" : "no"}</p>

      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}
