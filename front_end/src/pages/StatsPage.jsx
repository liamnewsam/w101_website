import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSocket } from "../socket/socketContext";
import { usePlayer } from "../PlayerContext";
import { BACKEND_URL } from "../config";
import "./StatsPage.css";

const SCHOOL_COLORS = {
  fire:    "#e05c2c",
  ice:     "#73b6f0",
  storm:   "#9b59d0",
  life:    "#3fb55c",
  death:   "#9b8fe5",
  myth:    "#c8a824",
  balance: "#c8a85c",
};

// Theoretical ceilings used only for progress-bar scaling
const STAT_MAXES = {
  health:     7700,
  mana:        625,
  accuracy:    100,
  damage:       30,
  resistance:   20,
  critical:     30,
  block:        30,
  pierce:        8,
  power_pip:    40,
  heal_out:     25,
  heal_in:      15,
  stun_res:     20,
};

const STAT_ICONS = {
  damage:     "static/w101/icons/battle/Damage.png",
  accuracy:   "static/w101/icons/battle/Accuracy.png",
  critical:   "static/w101/icons/battle/Critical.png",
  pierce:     "static/w101/icons/battle/Armor_Piercing.png",
  power_pip:  "static/w101/icons/battle/pips/Power_Pip.png",
  resistance: "static/w101/icons/battle/Ward.png",
  block:      "static/w101/icons/battle/Ward.png",
  stun_res:   "static/w101/icons/battle/Ward.png",
  heal_out:   "static/w101/icons/battle/Outgoing.png",
  heal_in:    "static/w101/icons/battle/Incoming.png",
};

function StatRow({ statKey, label, value, suffix = "%" }) {
  const iconPath = STAT_ICONS[statKey];
  const max = STAT_MAXES[statKey] ?? 100;
  const fillPct = Math.min((value ?? 0) / max, 1) * 100;
  return (
    <div className="sp-stat-row">
      <div className="sp-stat-left">
        {iconPath
          ? <img className="sp-stat-icon" src={`${BACKEND_URL}/${iconPath}`} alt="" />
          : <div className="sp-stat-icon sp-stat-icon-placeholder" />}
        <span className="sp-stat-label">{label}</span>
      </div>
      <div className="sp-stat-right">
        <div className="sp-bar-track">
          <div className="sp-bar-fill" style={{ width: `${fillPct}%` }} />
        </div>
        <span className="sp-stat-value">{value}{suffix}</span>
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="sp-section">
      <div className="sp-section-title">{title}</div>
      <div className="sp-section-body">{children}</div>
    </div>
  );
}

export default function StatsPage() {
  const navigate = useNavigate();
  const { socket } = useSocket();
  const { player } = usePlayer();

  const [stats, setStats] = useState(null);
  const [schoolChart, setSchoolChart] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!socket) return;

    const onStats = (data) => {
      if (data?.error) {
        setError(data.error);
      } else {
        setStats(data.stats);
        setSchoolChart(data.school_chart ?? null);
      }
    };

    socket.on("player_stats", onStats);
    socket.emit("get_player_stats");

    return () => socket.off("player_stats", onStats);
  }, [socket]);

  if (!player) return <div className="sp-page"><p>Loading…</p></div>;

  const school = (player.school || "balance").toLowerCase();
  const level  = player.level ?? 1;
  const color  = SCHOOL_COLORS[school] ?? "#c8a85c";
  const schoolLabel = school.charAt(0).toUpperCase() + school.slice(1);

  return (
    <div className="sp-page" style={{ "--school-color": color }}>

      {/* ── Header ── */}
      <div className="sp-header">
        <button className="sp-back-btn" onClick={() => navigate("/profile")}>← Profile</button>
        <div className="sp-identity">
          <img
            className="sp-school-icon"
            src={`${BACKEND_URL}/static/w101/icons/schools/${school}.png`}
            alt={school}
          />
          <div className="sp-identity-text">
            <span className="sp-player-name">{player.name}</span>
            <span className="sp-school-name" style={{ color }}>{schoolLabel} Wizard</span>
          </div>
          <div className="sp-level-badge" style={{ borderColor: color, color }}>
            Lv.&nbsp;{level}
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      <div className="sp-content">
        {error && <p className="sp-error">{error}</p>}

        {!stats && !error && <p className="sp-loading">Loading stats…</p>}

        {stats && <>
          {/* Vitals */}
          <Section title="Vitals">
            <div className="sp-stat-row">
              <div className="sp-stat-left">
                <div className="sp-health-pip" />
                <span className="sp-stat-label">Health</span>
              </div>
              <div className="sp-stat-right">
                <div className="sp-bar-track">
                  <div className="sp-bar-fill sp-bar-health"
                    style={{ width: `${(stats.health / STAT_MAXES.health) * 100}%` }} />
                </div>
                <span className="sp-stat-value">{stats.health.toLocaleString()}</span>
              </div>
            </div>
            <div className="sp-stat-row">
              <div className="sp-stat-left">
                <div className="sp-mana-pip" />
                <span className="sp-stat-label">Mana</span>
              </div>
              <div className="sp-stat-right">
                <div className="sp-bar-track">
                  <div className="sp-bar-fill sp-bar-mana"
                    style={{ width: `${(stats.mana / STAT_MAXES.mana) * 100}%` }} />
                </div>
                <span className="sp-stat-value">{stats.mana}</span>
              </div>
            </div>
          </Section>

          {/* Offense */}
          <Section title="Offense">
            <StatRow statKey="damage"    label="Damage Bonus"   value={stats.damage} />
            <StatRow statKey="accuracy"  label="Accuracy"       value={stats.accuracy} />
            <StatRow statKey="critical"  label="Critical"       value={stats.critical} />
            <StatRow statKey="pierce"    label="Armor Piercing" value={stats.pierce} />
            <StatRow statKey="power_pip" label="Power Pip"      value={stats.power_pip} />
          </Section>

          {/* Defense */}
          <Section title="Defense">
            <StatRow statKey="resistance" label="Resistance"      value={stats.resistance} />
            <StatRow statKey="block"      label="Critical Block"  value={stats.block} />
            <StatRow statKey="stun_res"   label="Stun Resistance" value={stats.stun_res} />
          </Section>

          {/* Healing */}
          <Section title="Healing">
            <StatRow statKey="heal_out" label="Outgoing Healing" value={stats.heal_out} />
            <StatRow statKey="heal_in"  label="Incoming Healing" value={stats.heal_in} />
          </Section>

          {/* School Chart */}
          {schoolChart && (
            <Section title="School Affinities">
              <table className="sp-school-table">
                <thead>
                  <tr>
                    <th>School</th>
                    <th>Damage&nbsp;Bonus</th>
                    <th>Resistance</th>
                  </tr>
                </thead>
                <tbody>
                  {schoolChart.map(row => {
                    const c = SCHOOL_COLORS[row.school] ?? "#aaa";
                    return (
                      <tr key={row.school}>
                        <td className="sp-school-cell">
                          <img
                            className="sp-school-table-icon"
                            src={`${BACKEND_URL}/static/w101/icons/schools/${row.school}.png`}
                            alt={row.school}
                          />
                          <span style={{ color: c }}>
                            {row.school.charAt(0).toUpperCase() + row.school.slice(1)}
                          </span>
                        </td>
                        <td className={row.damage > 0 ? "sp-positive" : ""}>{row.damage}%</td>
                        <td className={row.resistance < 0 ? "sp-negative" : row.resistance > 0 ? "sp-positive" : ""}>{row.resistance}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Section>
          )}
        </>}
      </div>
    </div>
  );
}
