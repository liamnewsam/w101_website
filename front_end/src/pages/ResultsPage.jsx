import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function ResultsPage() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const result = state?.result || { winner: "unknown" };

  console.log(state)

  return (
    <div className="page results">
      <h1>Match Results</h1>
      <div>Winner: {result.winner}</div>
      <button onClick={() => navigate("/menu")}>Back to Menu</button>
    </div>
  );
}
