import { createContext, useContext } from "react";

console.log("Are we creating a new context?");
export const SocketContext = createContext(null);

export function useSocket() {
  return useContext(SocketContext);
}