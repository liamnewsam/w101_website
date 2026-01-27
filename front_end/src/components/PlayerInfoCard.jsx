export default function PlayerInfoCard({
  name,
  currHealth,
  maxHealth,
  targetIcon
}) {
  const displayName =
    name.length > 8 ? name.slice(0, 8) + "…" : name;

  const healthPct = Math.max(
    0,
    Math.min(1, currHealth / maxHealth)
  );

  return (
    <div style={styles.card}>
      <div style={styles.topRow}>
        <span style={styles.name}>{displayName}</span>
        <span style={styles.healthText}>
          {currHealth} / {maxHealth}
        </span>
      </div>

      <div style={styles.healthBarOuter}>
        <div
          style={{
            ...styles.healthBarInner,
            width: `${healthPct * 100}%`,
          }}
        />
      </div>
    </div>
  );
}


const styles = {
  card: {
    width: "100%",
    height: "100%",
    padding: "6px 8px",
    borderRadius: 8,
    background: "#1e1e1e",
    color: "white",
    fontFamily: "sans-serif",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    boxSizing: "border-box",
  },

  topRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "0.75em",
  },

  name: {
    fontWeight: 600,
    whiteSpace: "nowrap",
  },

  healthText: {
    fontSize: "0.7em",
    opacity: 0.8,
  },

  healthBarOuter: {
    height: "25%",
    minHeight: 6,
    borderRadius: 4,
    background: "#333",
    overflow: "hidden",
  },

  healthBarInner: {
    height: "100%",
    background: "#4caf50",
    transition: "width 0.2s ease",
  },
};
