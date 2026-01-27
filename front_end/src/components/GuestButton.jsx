// src/components/GuestButton.jsx
import { guestLogin } from "../api/auth"; 
import {useSocket} from "../socket/socketContext"

export default function GuestButton() {
  const { updateToken } = useSocket();

  async function handleGuest() {
    const data = await guestLogin();
    updateToken(data.token);   // <-- localStorage + React state update
  } 

  return (
    <button className="guest-btn" onClick={handleGuest}>
      Continue as Guest
    </button>
  );
}
