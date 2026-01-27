export default function SpellDeck({ onCast, state }) {

  const castSpell = (spell) => {
    onCast({
      type: "cast",
      card: spell,
      target: "enemy-1",
    });
  };

  return (
    <div className="spell-deck">
      {state.available_spells.map((spell) => (
        <button key={spell} className="spell-card" onClick={() => castSpell(spell)}>
          {spell}
        </button>
      ))}
    </div>
  );
}
