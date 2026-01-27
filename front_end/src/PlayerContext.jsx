import { createContext, useContext, useEffect, useState } from "react";
import { useSocket } from "./socket/socketContext"; // your socket setup

const PlayerContext = createContext();

export function PlayerProvider({ children }) {
  const [player, setPlayer] = useState(null);
  const { socket, connected, disconnectSocket } = useSocket();

  useEffect(() => {
    if (!socket) return;

    const onPlayerInfo = (info) => {
      setPlayer(info);
    };

    socket.on("player_info", onPlayerInfo);
    socket.emit("get_player_info");

    return () => {
      socket.off("player_info", onPlayerInfo);
    };
  }, [socket]);

  return (
    <PlayerContext.Provider value={{ player, setPlayer }}>
      {children}
    </PlayerContext.Provider>
  );
}

export function usePlayer() {
  return useContext(PlayerContext);
}
