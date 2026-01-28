// src/api/auth.js
import { BACKEND_URL } from "../config";
 


export async function login(username, password) {
  const res = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    throw new Error("Invalid username or password");
  }

  const data = await res.json();
  localStorage.setItem("token", data.token);
  return data;
}

export async function guestLogin() {
  console.log("guestLogin called")
  const res = await fetch(`${BACKEND_URL}/auth/guest`, {
    method: "POST",
  });

  if (!res.ok) {
    throw new Error("Guest login failed");
  }

  const data = await res.json();
  localStorage.setItem("token", data.token); // ← REQUIRED
  return data;
}

export function logout(disconnectSocket) {
  console.log("removing token");
  localStorage.removeItem("token");
  if (disconnectSocket) disconnectSocket();
}


export function getToken() {
  console.log("getting token");
  return localStorage.getItem("token");
}
