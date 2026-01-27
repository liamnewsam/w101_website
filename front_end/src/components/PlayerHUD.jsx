export default function PlayerHUD({ state }) {
  return (
    <div className="hud">
      <h2>Duel Status</h2>
      <p>Round: {state.round}</p>
    </div>
  );
}
