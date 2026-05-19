// src/components/LoginForm.jsx
import { useState } from "react";
import { login, register } from "../api/auth";
import { useSocket } from "../socket/socketContext";

export default function LoginForm() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { updateToken } = useSocket();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (mode === "register" && password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);
    try {
      let data;
      if (mode === "login") {
        data = await login(username, password);
      } else {
        data = await register(username, password);
      }
      updateToken(data.token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function switchMode(newMode) {
    setMode(newMode);
    setError("");
    setPassword("");
    setConfirmPassword("");
  }

  return (
    <div className="login-card">
      <div className="login-tabs">
        <button
          type="button"
          className={`login-tab ${mode === "login" ? "active" : ""}`}
          onClick={() => switchMode("login")}
        >
          Login
        </button>
        <button
          type="button"
          className={`login-tab ${mode === "register" ? "active" : ""}`}
          onClick={() => switchMode("register")}
        >
          Create Account
        </button>
      </div>

      <form className="login-form" onSubmit={handleSubmit}>
        <input
          className="login-input"
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
        />

        <input
          className="login-input"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
        />

        {mode === "register" && (
          <input
            className="login-input"
            type="password"
            placeholder="Confirm Password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
          />
        )}

        <button className="login-submit-btn" type="submit" disabled={loading}>
          {loading ? "..." : mode === "login" ? "Login" : "Create Account"}
        </button>

        {error && <p className="login-error">{error}</p>}
      </form>
    </div>
  );
}
