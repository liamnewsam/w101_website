# Base stat profiles per school, reflecting authentic Wizard101 school identities:
#   Ice   = highest health + resist + block (tank)
#   Storm = highest damage + critical, lowest health + resist (glass cannon)
#   Life  = strong healer with good health
#   Death = life-steal archetype, balanced offense/defense
#   Fire  = high damage with some sustain
#   Myth  = solid damage dealer, decent sturdiness
#   Balance = jack-of-all-trades, universal support
_PROFILES = {
    "fire": {
        "health_base": 345, "health_rate": 44,
        "mana_base": 30,    "mana_rate": 3.5,
        "accuracy": 75,
        "dmg_rate": 0.160,  "res_rate": 0.050,
        "crit_rate": 0.180, "block_rate": 0.100,
        "pierce_rate": 0.040,
        "pp_rate": 0.305,
        "heal_out_rate": 0.000, "heal_in_rate": 0.030,
        "stun_res_rate": 0.020,
    },
    "ice": {
        "health_base": 430, "health_rate": 56,
        "mana_base": 30,    "mana_rate": 3.0,
        "accuracy": 80,
        "dmg_rate": 0.060,  "res_rate": 0.140,
        "crit_rate": 0.100, "block_rate": 0.220,
        "pierce_rate": 0.010,
        "pp_rate": 0.300,
        "heal_out_rate": 0.000, "heal_in_rate": 0.080,
        "stun_res_rate": 0.120,
    },
    "storm": {
        "health_base": 280, "health_rate": 36,
        "mana_base": 30,    "mana_rate": 4.5,
        "accuracy": 70,
        "dmg_rate": 0.220,  "res_rate": 0.020,
        "crit_rate": 0.220, "block_rate": 0.060,
        "pierce_rate": 0.050,
        "pp_rate": 0.295,
        "heal_out_rate": 0.000, "heal_in_rate": 0.020,
        "stun_res_rate": 0.010,
    },
    "life": {
        "health_base": 400, "health_rate": 50,
        "mana_base": 35,    "mana_rate": 4.0,
        "accuracy": 80,
        "dmg_rate": 0.100,  "res_rate": 0.080,
        "crit_rate": 0.120, "block_rate": 0.180,
        "pierce_rate": 0.020,
        "pp_rate": 0.315,
        "heal_out_rate": 0.200, "heal_in_rate": 0.100,
        "stun_res_rate": 0.050,
    },
    "death": {
        "health_base": 375, "health_rate": 47,
        "mana_base": 30,    "mana_rate": 3.5,
        "accuracy": 80,
        "dmg_rate": 0.150,  "res_rate": 0.080,
        "crit_rate": 0.160, "block_rate": 0.120,
        "pierce_rate": 0.040,
        "pp_rate": 0.305,
        "heal_out_rate": 0.100, "heal_in_rate": 0.050,
        "stun_res_rate": 0.030,
    },
    "myth": {
        "health_base": 360, "health_rate": 45,
        "mana_base": 30,    "mana_rate": 3.5,
        "accuracy": 80,
        "dmg_rate": 0.140,  "res_rate": 0.060,
        "crit_rate": 0.160, "block_rate": 0.120,
        "pierce_rate": 0.030,
        "pp_rate": 0.305,
        "heal_out_rate": 0.000, "heal_in_rate": 0.030,
        "stun_res_rate": 0.040,
    },
    "balance": {
        "health_base": 385, "health_rate": 48,
        "mana_base": 30,    "mana_rate": 3.5,
        "accuracy": 80,
        "dmg_rate": 0.120,  "res_rate": 0.100,
        "crit_rate": 0.140, "block_rate": 0.140,
        "pierce_rate": 0.030,
        "pp_rate": 0.315,
        "heal_out_rate": 0.050, "heal_in_rate": 0.060,
        "stun_res_rate": 0.050,
    },
}

# Hard caps for percentage stats (matching front-end STAT_MAXES)
_CAPS = {
    "damage": 30, "resistance": 20, "critical": 30, "block": 30,
    "pierce": 8,  "power_pip": 40,  "heal_out": 25, "heal_in": 15,
    "stun_res": 20,
}

SCHOOLS = ["fire", "ice", "storm", "life", "death", "myth", "balance"]

# W101 school triangles:
#   Elemental — Fire beats Ice, Ice beats Storm, Storm beats Fire
#   Spirit    — Life beats Death, Death beats Myth, Myth beats Life
#   Balance   — neutral (no specific strength or weakness)
#
# "strong": the school you have an advantage over
#            → you gain extra resistance to their spells
# "weak":   the school that has an advantage over you
#            → you have reduced resistance to their spells
SCHOOL_TRIANGLE = {
    "fire":    {"strong": "ice",   "weak": "storm"},
    "ice":     {"strong": "storm", "weak": "fire"},
    "storm":   {"strong": "fire",  "weak": "ice"},
    "life":    {"strong": "death", "weak": "myth"},
    "death":   {"strong": "myth",  "weak": "life"},
    "myth":    {"strong": "life",  "weak": "death"},
    "balance": {"strong": None,    "weak": None},
}


def compute_stats(level: int, school: str) -> dict:
    """Return base stats for a wizard of the given level and school (no gear/pet).

    Returns None for an unrecognised school.
    """
    p = _PROFILES.get(school.lower())
    if p is None:
        return None

    def cap(val, key):
        return min(val, _CAPS[key])

    return {
        "health":     round(p["health_base"] + (level - 1) * p["health_rate"]),
        "mana":       round(p["mana_base"]   + (level - 1) * p["mana_rate"]),
        "accuracy":   p["accuracy"],
        "damage":     cap(round(level * p["dmg_rate"]),      "damage"),
        "resistance": cap(round(level * p["res_rate"]),      "resistance"),
        "critical":   cap(round(level * p["crit_rate"]),     "critical"),
        "block":      cap(round(level * p["block_rate"]),    "block"),
        "pierce":     cap(round(level * p["pierce_rate"]),   "pierce"),
        "power_pip":  cap(round(level * p["pp_rate"]),       "power_pip"),
        "heal_out":   cap(round(level * p["heal_out_rate"]), "heal_out"),
        "heal_in":    cap(round(level * p["heal_in_rate"]),  "heal_in"),
        "stun_res":   cap(round(level * p["stun_res_rate"]), "stun_res"),
    }


def compute_school_chart(level: int, school: str) -> list:
    """Return per-school damage and resistance for all seven schools.

    Each entry: { "school": str, "damage": int, "resistance": int }

    damage     = bonus % when casting spells of that school
                 (high for own school, small off-school value for others)
    resistance = % reduction against incoming spells of that school
                 (boosted vs the school you're strong against,
                  reduced / negative vs the school you're weak to)

    Returns None for an unrecognised school.
    """
    p = _PROFILES.get(school.lower())
    if p is None:
        return None

    tri    = SCHOOL_TRIANGLE[school.lower()]
    strong = tri["strong"]
    weak   = tri["weak"]

    own_dmg = min(round(level * p["dmg_rate"]), _CAPS["damage"])
    own_res = min(round(level * p["res_rate"]), _CAPS["resistance"])

    # Triangle adjustments scale with level
    res_bonus   = min(round(level * 0.08), 10)   # extra resist vs strong school
    res_penalty = min(round(level * 0.12), 15)   # lost resist vs weak school
    off_dmg     = min(round(level * 0.020), 3)   # small off-school damage
    off_res     = min(round(level * 0.030), 4)   # small off-school resist

    rows = []
    for s in SCHOOLS:
        if s == school.lower():
            dmg = own_dmg
            res = own_res
        elif s == strong:
            dmg = off_dmg
            res = own_res + res_bonus          # better resist vs the school you beat
        elif weak and s == weak:
            dmg = off_dmg
            res = own_res - res_penalty        # vulnerable to the school that beats you
        else:
            dmg = off_dmg
            res = off_res

        rows.append({"school": s, "damage": dmg, "resistance": res})

    return rows
