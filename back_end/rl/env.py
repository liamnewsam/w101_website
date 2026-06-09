import datetime
import os
import sys
import traceback
import numpy as np
import gymnasium as gym

# Allow importing from back_end root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random as _random

from Game import Game                              # noqa: E402
from Player import Player                          # noqa: E402
from Deck import DECK_MASTER                       # noqa: E402
from stats import compute_stats, compute_school_chart  # noqa: E402

from config import HAND_SIZE  # noqa: E402

# ──────────────────────────────────────────────
# Encoding vocabulary
# ──────────────────────────────────────────────
SCHOOLS = ["myth", "life", "fire", "ice", "storm", "death", "balance"]
SCHOOL_TO_IDX = {s: i for i, s in enumerate(SCHOOLS)}

CARD_TYPES = [
    "damage", "heal", "DoT", "HoT", "charm", "ward",
    "jinx", "drain", "detonate", "pip", "reshuffle", "other",
]
CARD_TYPE_TO_IDX = {t: i for i, t in enumerate(CARD_TYPES)}

# DECK_MASTER keys are title-cased; player.school is lowercase
VALID_SCHOOLS = ["Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"]

# ──────────────────────────────────────────────
# Shape constants
# ──────────────────────────────────────────────
MAX_TEAM_SIZE  = 4
MAX_PLAYERS    = MAX_TEAM_SIZE * 2   # 8 global player slots

# Action encoding:
#   0                              → pass
#   1 + card_i * N_TARGET_SLOTS + j → cast card_i at target slot j
#     j = 0 .. MAX_TEAM_SIZE-1        Team-A (agent's team)
#     j = MAX_TEAM_SIZE .. MAX_PLAYERS-1  Team-B (opponents)
#     j = MAX_PLAYERS                 null target (AoE / self-cast)
N_TARGET_SLOTS       = MAX_PLAYERS + 1                                            # 9

N_CAST_ACTIONS       = HAND_SIZE * N_TARGET_SLOTS                                 # 45
N_DISCARD_ACTIONS    = HAND_SIZE                                                  # 5
N_PIP_SCHOOL_ACTIONS = len(SCHOOLS)                                               # 7

# Action base offsets
CAST_BASE       = 1
DISCARD_BASE    = CAST_BASE    + N_CAST_ACTIONS       # 46
PIP_SCHOOL_BASE = DISCARD_BASE + N_DISCARD_ACTIONS    # 51

N_ACTIONS = 1 + N_CAST_ACTIONS + N_DISCARD_ACTIONS + N_PIP_SCHOOL_ACTIONS        # 58

# card: school(7) + pip_cost(1) + is_x_pip(1) + type(12) + is_playable(1)
#       + location(3): is_hand(1) + is_deck(1) + is_discard(1)
#       + effect features(10): dmg(1) heal(1) dot(1) charm(1) trap(1) shield(1) curse(1)
#                               is_aoe(1) targets_ally(1) n_effects(1)
# CARD_DIM is computed after CONDITION_SIZE and MAXIMUM_CARD_EFFECTS are defined below

# Assumed maximum pips for scaling X-pip spell effect features
MAX_X_PIPS = 7
MAX_TOTAL_CARDS = 30   # unified card sequence: HAND_SIZE hand slots + remaining deck + discard
# per-player token: hp(1) + pips(9) + school_pip_select(7) = 17
# per-player token: hp(1) + pips(9) + school_pip_select(7)
#                   + outgoing_mult_norm(1) + shield_mit_norm(1) + trap_mult_norm(1)
PLAYER_DIM  = 2 + 9 + len(SCHOOLS)   # 18: max_health(1) + hp_ratio(1) + pips(9) + school(7)
GAME_DIM    = 2 + len(SCHOOLS)        # turn ratio + hand-size ratio + school_pip_select(7)

# per-effect token:
#   player_slot_one_hot(8) + effect_type_one_hot(6)
#   + aspect_one_hot(4)    — CHARM_TYPES for charm, CURSE_TYPES for curse, WARD_TYPES for ward
#   + amount(1)
#   + school_one_hot(7)    — school, or from-school for prism jinx
#   + to_school_one_hot(7) — to-school for prism jinx only
#   + rounds(1) + wait(1)
HANGING_EFFECT_TYPES = ["charm", "curse", "ward", "jinx", "DoT", "HoT"]
HANGING_EFFECT_TYPE_TO_IDX = {t: i for i, t in enumerate(HANGING_EFFECT_TYPES)}
EFFECT_TOKEN_DIM   = MAX_PLAYERS + len(HANGING_EFFECT_TYPES) + 4 + 1 + len(SCHOOLS) + len(SCHOOLS) + 1 + 1  # 35
MAX_EFFECT_TOKENS  = 32

TARGET_TYPES = ["enemy", "enemy_same", "enemy_all", "ally", "ally_same", "ally_all", "self"]
TARGET_TYPE_TO_IDX = {t: i for i, t in enumerate(TARGET_TYPES)}

CONDITION_TYPES = ["amount"]
AMOUNT_CONDITION_SIZE = len(CONDITION_TYPES) + 1 + len(HANGING_EFFECT_TYPES) + len(TARGET_TYPES)

PIP_KEYS = ["regular", "powerpip"] + SCHOOLS             # 9 keys


CARD_EFFECT_TYPES = ["damage", "drain", "heal", "DoT", "HoT", "charm", "curse", "ward",
                      "jinx", "destroy", "detonate", "extend", "global", "pip", "reshuffle", "take", "prism", "gambit_condition",
                      "gambit_true", "gambit_false", "repeat_condition", "repeat_result"]

CARD_EFFECT_TYPE_TO_IDX = {t : i for i, t in enumerate(CARD_EFFECT_TYPES)}
CARD_EFFECT_TYPE_TO_IDX["trap"] = CARD_EFFECT_TYPE_TO_IDX["jinx"]
CARD_EFFECT_TYPE_TO_IDX["shield"] = CARD_EFFECT_TYPE_TO_IDX["ward"]

CHARM_TYPES = ["damage", "heal", "accuracy", "armor_piercing"]
CHARM_TYPE_TO_IDX = {t : i for i, t in enumerate(CHARM_TYPES)}

CURSE_TYPES = ["damage", "heal", "accuracy", "dispel"]
CURSE_TYPE_TO_IDX = {t : i for i, t in enumerate(CURSE_TYPES)}

WARD_TYPES = ["damage", "absorb"]
WARD_TYPE_TO_IDX = {t : i for i, t in enumerate(WARD_TYPES)}

def _num(v, fallback=0.0):
    """Coerce a card/effect field to float — handles plain numbers, {min/max} dicts, and lists."""
    if isinstance(v, dict):
        return float(v.get("max", v.get("min", fallback)))
    if isinstance(v, list):
        return float(max(v)) if v else fallback
    return float(v) if v is not None else fallback


def _encode_hanging_effect_tokens(teams) -> np.ndarray:
    """Encode all active hanging effects across both teams as MAX_EFFECT_TOKENS tokens.

    Token layout (EFFECT_TOKEN_DIM = 35):
      [0:8]   player slot one-hot      — team 0 → slots 0-3, team 1 → slots 4-7
      [8:14]  effect type one-hot      — HANGING_EFFECT_TYPES order
      [14:18] aspect one-hot           — CHARM_TYPES for charm, CURSE_TYPES for curse,
                                         WARD_TYPES for ward (first 2 of 4 slots used)
      [18]    amount
      [19:26] school one-hot           — or from-school for prism jinx
      [26:33] to-school one-hot        — prism jinx only
      [33]    rounds remaining
      [34]    wait flag (DoT only)
    """
    arr = np.zeros((MAX_EFFECT_TOKENS, EFFECT_TOKEN_DIM), dtype=np.float32)
    idx = 0

    _P   = 0
    _ET  = MAX_PLAYERS
    _ASP = _ET  + len(HANGING_EFFECT_TYPES)
    _AMT = _ASP + 4
    _SCH = _AMT + 1
    _TSC = _SCH + len(SCHOOLS)
    _RND = _TSC + len(SCHOOLS)
    _WT  = _RND + 1

    def emit(player_slot, type_idx, aspect_idx, amount, school, to_school, rounds, wait):
        nonlocal idx
        if idx >= MAX_EFFECT_TOKENS:
            return
        tok = arr[idx]
        tok[_P + player_slot] = 1.0
        tok[_ET + type_idx]   = 1.0
        if aspect_idx is not None:
            tok[_ASP + aspect_idx] = 1.0
        tok[_AMT] = amount
        if school and school in SCHOOL_TO_IDX:
            tok[_SCH + SCHOOL_TO_IDX[school]] = 1.0
        if to_school and to_school in SCHOOL_TO_IDX:
            tok[_TSC + SCHOOL_TO_IDX[to_school]] = 1.0
        tok[_RND] = rounds
        tok[_WT]  = float(wait)
        idx += 1

    for team_idx, team in enumerate(teams):
        for p_idx, p in enumerate(team[:MAX_TEAM_SIZE]):
            pslot = team_idx * MAX_TEAM_SIZE + p_idx

            for e in p.charms:
                school = e.school if e.school and e.school != "any" else None
                emit(pslot, HANGING_EFFECT_TYPE_TO_IDX["charm"],
                     CHARM_TYPE_TO_IDX.get(e.aspect),
                     e.amount, school, None, 0.0, False)

            for e in p.curses:
                school = e.school if e.school and e.school != "any" else None
                emit(pslot, HANGING_EFFECT_TYPE_TO_IDX["curse"],
                     CURSE_TYPE_TO_IDX.get(e.aspect),
                     e.amount, school, None, 0.0, False)

            for e in p.wards:
                school = e.school if e.school and e.school != "any" else None
                emit(pslot, HANGING_EFFECT_TYPE_TO_IDX["ward"],
                     WARD_TYPE_TO_IDX.get(e.aspect),
                     e.amount, school, None, 0.0, False)

            for e in p.jinxes:
                if e.aspect == "prism":
                    emit(pslot, HANGING_EFFECT_TYPE_TO_IDX["jinx"],
                         None, 0.0, e.inputSchool, e.outputSchool, 0.0, False)
                else:
                    school = e.school if e.school and e.school != "any" else None
                    emit(pslot, HANGING_EFFECT_TYPE_TO_IDX["jinx"],
                         None, e.amount, school, None, 0.0, False)

            for e in p.dots:
                school = e.school if e.school and e.school != "any" else None
                emit(pslot, HANGING_EFFECT_TYPE_TO_IDX["DoT"],
                     None, getattr(e, "amount", 0.0),
                     school, None, float(e.rounds), e.wait)

            for e in p.hots:
                emit(pslot, HANGING_EFFECT_TYPE_TO_IDX["HoT"],
                     None, getattr(e, "amount", 0.0),
                     None, None, float(e.rounds), False)

    return arr


CARD_EFFECT_SIZE = 46

def determine_amount(effect):
    if "amount" in effect:
        if type(effect["amount"]) is int:
            return effect["amount"]
        if type(effect["amount"]) is list:
            return np.mean(effect["amount"])
        if type(effect["amount"]) is dict:
            if "min" in effect["amount"]:
                return (effect["amount"]["min"] + effect["amount"]["max"]) / 2.0
    if "min" in effect:
        return (effect["min"] + effect["max"]) / 2.0

    raise ValueError(effect)

def _encode_card_effect(effect, gambit_repeat_true = False, gambit_false = False):
    #special cases:
    if effect["type"] == "gambit":
        cond_dict = effect["condition"]
        if "AND" in cond_dict:
            conditions = cond_dict["AND"]
        elif "OR" in cond_dict:
            conditions = cond_dict["OR"]
        else:
            conditions = [cond_dict]
        vec = np.zeros(CARD_EFFECT_SIZE * (len(conditions) + len(effect["true"]) + len(effect["false"])), dtype=np.float32)
        col = 0
        for condition in conditions:
            vec[col + CARD_EFFECT_TYPE_TO_IDX["gambit_condition"]] = 1.0

            vec[col + len(CARD_EFFECT_TYPES) : col + CARD_EFFECT_SIZE] = _encode_condition(condition)
            col += CARD_EFFECT_SIZE

        for trueEffect in effect["true"]:
            vec[col : col + CARD_EFFECT_SIZE] = _encode_card_effect(trueEffect, gambit_repeat_true = True)
            col += CARD_EFFECT_SIZE
        for falseEffect in effect["false"]:
            vec[col : col + CARD_EFFECT_SIZE] = _encode_card_effect(falseEffect, gambit_false = True)
            col += CARD_EFFECT_SIZE
        
        return vec
    if effect["type"] == "repeat":
        vec = np.zeros(CARD_EFFECT_SIZE * (1 + len(effect["effects"])), dtype=np.float32)
        col = 0
        vec[col + CARD_EFFECT_TYPE_TO_IDX["repeat_condition"]] = 1.0
        vec[len(CARD_EFFECT_TYPES) : CARD_EFFECT_SIZE] = _encode_condition(effect["condition"], up_to = effect["up_to"])
        col += CARD_EFFECT_SIZE

        for repeatEffect in effect["effects"]:
            vec[col : col + CARD_EFFECT_SIZE] = _encode_card_effect(repeatEffect, gambit_repeat_true = True)
            col += CARD_EFFECT_SIZE

        return vec

    vec = np.zeros(CARD_EFFECT_SIZE, dtype=np.float32)

    if effect["type"] == "global":
        return vec
    

    vec[CARD_EFFECT_SIZE - len(TARGET_TYPES) + TARGET_TYPE_TO_IDX[effect["target"]]] = 1.0
    vec[CARD_EFFECT_SIZE - len(TARGET_TYPES) - 3] = 1 if gambit_repeat_true else 0
    vec[CARD_EFFECT_SIZE - len(TARGET_TYPES) - 2] = 1 if gambit_false  else 0
    col = 0
    vec[col + CARD_EFFECT_TYPE_TO_IDX[effect["type"]]] = 1.0
    col += len(CARD_EFFECT_TYPES)

    if effect["type"] in ["damage", "drain"]:
        vec[col] = determine_amount(effect)
        col += 1
        if type(effect["school"]) is list:
            for school in effect["school"]:
                vec[col + SCHOOL_TO_IDX[school]] = 1.0 / len(effect["school"])
        elif effect["school"] in SCHOOL_TO_IDX:
            vec[col + SCHOOL_TO_IDX[effect["school"]]] = 1.0
        
        col += len(SCHOOLS)

        
        return vec

    if effect["type"] == "heal":
        vec[col] = determine_amount(effect)
        col += 1

        return vec
    
    if effect["type"] == "DoT":
        vec[col] = determine_amount(effect)
        col += 1
        if effect["school"] in SCHOOL_TO_IDX:
            vec[col + SCHOOL_TO_IDX[effect["school"]]] = 1.0
        
        col += len(SCHOOLS)

        if type(effect["rounds"]) is int:
            vec[col] = effect["rounds"]
        elif type(effect["rounds"]) is dict: # Assume min max
            vec[col] = (effect["rounds"]["min"] + effect["rounds"]["max"]) / 2.0
        col += 1
        vec[col] = 1 if "wait" in effect else 0
        col += 1

        return vec

    if effect["type"] == "HoT":
        vec[col] = determine_amount(effect)
        col += 1

        if type(effect["rounds"]) is int:
            vec[col] = effect["rounds"]
        elif type(effect["rounds"]) is dict: # Assume min max
            vec[col] = (effect["rounds"]["min"] + effect["rounds"]["max"]) / 2.0

        col += 1

        return vec
    
    if effect["type"] == "charm":
        vec[col + CHARM_TYPE_TO_IDX[effect["aspect"]]] = 1.0
        col += len(CHARM_TYPES)

        vec[col] = determine_amount(effect)
        col += 1

        if effect["aspect"] in ["damage", "armor_piercing"]:
            if  effect.get("school", None) in SCHOOL_TO_IDX:
                vec[col + SCHOOL_TO_IDX[effect["school"]]] = 1.0
            
        return vec
    
    if effect["type"] == "curse":
        vec[col + CURSE_TYPE_TO_IDX[effect["aspect"]]] = 1.0
        col += len(CURSE_TYPES)

        vec[col] = effect.get("amount", 0)
        col += 1

        if effect["aspect"] in ["damage", "dispel"]:
            if  effect.get("school", None) in SCHOOL_TO_IDX:
                vec[col + SCHOOL_TO_IDX[effect["school"]]] = 1.0
            
        return vec
    
    if effect["type"] in ["ward", "shield"]:
        vec[col + WARD_TYPE_TO_IDX[effect["aspect"]]] = 1.0
        col += len(WARD_TYPES)

        vec[col] = determine_amount(effect)
        col += 1

        if effect["aspect"] in ["damage"]:
            if effect.get("school", None) in SCHOOL_TO_IDX:
                vec[col + SCHOOL_TO_IDX[effect["school"]]] = 1.0
            
        return vec
    
    if effect["type"] in ["jinx", "trap"]: #Technically theres a DoT version but eh
        #vec[col + JINX_TYPE_TO_IDX[effect["aspect"]]] = 1.0
        #col += len(WARD_TYPES)

        vec[col] = determine_amount(effect)
        col += 1

        if  effect.get("school", None) in SCHOOL_TO_IDX:
            vec[col + SCHOOL_TO_IDX[effect["school"]]] = 1.0
            
        return vec
    
    if effect["type"] == "prism":
        vec[col + SCHOOL_TO_IDX[effect["from"]]] = 1.0
        col += len(SCHOOLS)

        vec[col + SCHOOL_TO_IDX[effect["to"]]] = 1.0
        col += len(SCHOOLS)

        return vec

    if effect["type"] == "destroy":
        vec[col + HANGING_EFFECT_TYPE_TO_IDX[effect["aspect"]]] = 1.0
        col += len(HANGING_EFFECT_TYPES)

        return vec

    if effect["type"] == "extend":
        if effect["aspect"] == "DoT":
            vec[col] = 1.0
        else: #HoT
            vec[col+1] = 1.0

        return vec
    
    
    
    if effect["type"] == "take":
        if effect["aspect"] == "charm":
            vec[col] = 1.0
        else: #Ward
            vec[col+1] = 1.0

        return vec

    if effect["type"] == "detonate":
        vec[col] = effect.get("amount", 1.0)

        return vec
    
    if effect["type"] == "pip":
        return vec

    if effect["type"] == "reshuffle":
        return vec


MAXIMUM_CARD_EFFECTS = 12 #Tribunal Oni

def _encode_card_effects(effects) -> np.ndarray:
    vec = np.zeros(MAXIMUM_CARD_EFFECTS*CARD_EFFECT_SIZE, dtype=np.float32)
    col = 0
    for effect in effects:
        effect_encoding = _encode_card_effect(effect)
        vec[col : col + len(effect_encoding)] = effect_encoding
        col += len(effect_encoding)

    return vec

CONDITION_SIZE = CARD_EFFECT_SIZE - len(CARD_EFFECT_TYPES)

# school(7) + pips(8) + playable(1) + location(3) + condition(CONDITION_SIZE) + effects(MAXIMUM_CARD_EFFECTS*CARD_EFFECT_SIZE)
CARD_DIM = len(SCHOOLS) + 8 + 1 + 3 + CONDITION_SIZE + MAXIMUM_CARD_EFFECTS * CARD_EFFECT_SIZE

def _encode_condition(c, up_to=0):
    # Layout within CONDITION_SIZE slots:
    #   [0 : len(CONDITION_TYPES)]                      condition type one-hot
    #   [+len(HANGING_EFFECT_TYPES)]                    aspect one-hot
    #   [+1]                                            amount
    #   [CONDITION_SIZE - len(TARGET_TYPES) - 1]        up_to
    #   [CONDITION_SIZE - len(TARGET_TYPES) : end]      target one-hot
    vec = np.zeros(CONDITION_SIZE, dtype=np.float32)
    if not c:
        return vec
    # Compound OR/AND: unwrap to first sub-condition for fixed-size encoding
    if "OR" in c or "AND" in c:
        key = "OR" if "OR" in c else "AND"
        c = c[key][0] if c[key] else {}
    col = 0
    if c.get("type") == "amount":
        vec[col] = 1.0
    col += len(CONDITION_TYPES)

    if c.get("aspect") in HANGING_EFFECT_TYPE_TO_IDX:
        vec[col + HANGING_EFFECT_TYPE_TO_IDX[c["aspect"]]] = 1.0
    col += len(HANGING_EFFECT_TYPES)

    vec[col] = c.get("amount", 0)

    vec[CONDITION_SIZE - len(TARGET_TYPES) - 1] = float(up_to)
    if c.get("target") in TARGET_TYPE_TO_IDX:
        vec[CONDITION_SIZE - len(TARGET_TYPES) + TARGET_TYPE_TO_IDX[c["target"]]] = 1.0

    return vec


def _encode_card(card_def, is_playable: bool, location: str) -> np.ndarray:

    """Encode a single card as a CARD_DIM-dimensional vector.

    location: 'hand' | 'deck' | 'discard'
    """
    vec = np.zeros(CARD_DIM, dtype=np.float32)
    col = 0

    #Card School
    vec[col + SCHOOL_TO_IDX.get(card_def.school, 0)] = 1.0
    col += len(SCHOOLS)

    #Card Pips
    if card_def.pips == "X":
        vec[col] = 0.0
        col += 8
    elif isinstance(card_def.pips, (int,float)):
        vec[col] = card_def.pips * 1.0
        col += 8
    else:
        vec[col] = card_def.pips["regular"] * 1.0
        col += 1
        for i in range(len(SCHOOLS)):
            vec[col] = card_def.pips.get(SCHOOLS[i], 0) * 1.0
            col += 1

    # Card Playability
    if is_playable:
        vec[col] = 1.0
    col += 1  # is_playable

    # Card Location
    if location == "hand":
        vec[col] = 1.0
    elif location == "deck":
        vec[col + 1] = 1.0
    else:  # discard
        vec[col + 2] = 1.0
    col += 3  # is_hand, is_deck, is_discard

    #Card Condition:
    vec[col : col+CONDITION_SIZE] = _encode_condition(card_def.condition)
    col += CONDITION_SIZE

    #Card Effects:
    #Total of 11 effects (Tribunal Oni has a gambit effect, with the true branch having 7 and the false branch having 3)

    vec[col : col+MAXIMUM_CARD_EFFECTS*CARD_EFFECT_SIZE] = _encode_card_effects(card_def.effects)

    return vec


def _encode_all_cards(player, playability_info=None) -> np.ndarray:
    """Encode all of player's cards into MAX_TOTAL_CARDS tokens.

    Slots 0..HAND_SIZE-1          : hand cards (with playability flags)
    Slots HAND_SIZE..MAX_TOTAL_CARDS-1 : remaining deck cards, then discard cards
    """
    arr  = np.zeros((MAX_TOTAL_CARDS, CARD_DIM), dtype=np.float32)
    play = playability_info or []

    hand = player.deck.play_hand if (player.deck and player.deck.play_hand) else []
    for i in range(min(HAND_SIZE, len(hand))):
        is_playable = i < len(play) and play[i].get("playable", False)
        arr[i] = _encode_card(hand[i].card_def, is_playable, "hand")

    deck_cards    = player.deck.play_cards    if (player.deck and player.deck.play_cards)    else []
    discard_cards = player.deck.play_discard  if (player.deck and player.deck.play_discard)  else []

    slot = HAND_SIZE
    for card in deck_cards:
        if slot >= MAX_TOTAL_CARDS:
            break
        arr[slot] = _encode_card(card.card_def, False, "deck")
        slot += 1
    for card in discard_cards:
        if slot >= MAX_TOTAL_CARDS:
            break
        arr[slot] = _encode_card(card.card_def, False, "discard")
        slot += 1

    return arr


class W101Env(gym.Env):
    """Wizard101 card game environment (multi-player teams supported).

    Action space  – Discrete(N_ACTIONS = 46):
        0                                        : pass
        1 + card_i * N_TARGET_SLOTS + j          : cast card_i, target slot j
            j ∈ [0, MAX_TEAM_SIZE)               → Team-A player j
            j ∈ [MAX_TEAM_SIZE, MAX_PLAYERS)     → Team-B player j - MAX_TEAM_SIZE
            j = MAX_PLAYERS                      → no target (AoE / self)

    Observation space – Dict:
        "cards"       : float32 (MAX_TOTAL_CARDS, CARD_DIM)
        "players"     : float32 (MAX_PLAYERS, PLAYER_DIM)
        "game"        : float32 (GAME_DIM,)
        "action_mask" : float32 (N_ACTIONS,)  – 1 where legal
    """

    HAND_SIZE            = HAND_SIZE
    CARD_DIM             = CARD_DIM
    PLAYER_DIM           = PLAYER_DIM
    GAME_DIM             = GAME_DIM
    MAX_PLAYERS          = MAX_PLAYERS
    N_TARGET_SLOTS       = N_TARGET_SLOTS
    N_PIP_SCHOOL_ACTIONS = N_PIP_SCHOOL_ACTIONS
    N_ACTIONS            = N_ACTIONS

    def __init__(
        self,
        agent_school: str = "Fire",
        agent_level: int = 1,
        agent_deck=None,
        allies: list = None,
        enemies: list = None,
        max_turns: int = 300,
        suppress_output: bool = True,
        opponent_policies: list = None,
    ):
        """
        allies  – list of dicts, each {"school": str, "level": int, "deck": Deck|None},
                  placed on the agent's team.  Defaults to [] (agent fights alone).
        enemies – same format for the opposing team.
                  Defaults to [{"school": "random", "level": 1, "deck": None}].
        opponent_policies – optional list (one entry per enemy) of TrainedOpponent or None.
                  None entries fall back to the normal random bot.
        """
        super().__init__()
        self.agent_school      = agent_school
        self.agent_level       = agent_level
        self.agent_deck        = agent_deck
        self.allies            = allies  if allies  is not None else []
        self.opponent_policies = opponent_policies or []
        self.enemies = enemies if enemies is not None else [{"school": "random", "level": 1, "deck": None}]
        self.max_turns = max_turns
        self.suppress_output = suppress_output

        self.action_space = gym.spaces.Discrete(N_ACTIONS)
        self.observation_space = gym.spaces.Dict(
            {
                "cards":       gym.spaces.Box(0.0, 1.0, shape=(MAX_TOTAL_CARDS,   CARD_DIM),         dtype=np.float32),
                "players":     gym.spaces.Box(0.0, 1.0, shape=(MAX_PLAYERS,       PLAYER_DIM),       dtype=np.float32),
                "effects":     gym.spaces.Box(0.0, 1.0, shape=(MAX_EFFECT_TOKENS, EFFECT_TOKEN_DIM), dtype=np.float32),
                "game":        gym.spaces.Box(0.0, 1.0, shape=(GAME_DIM,),                           dtype=np.float32),
                "action_mask": gym.spaces.Box(0.0, 1.0, shape=(N_ACTIONS,),                          dtype=np.float32),
            }
        )

        self.game: Game = None
        self.agent = None
        self._prev_enemy_hp   = 0.0
        self._pip_change_turn = -1  # turn number of last pip-school change; -1 = none this episode

    # ──────────────────────────────────────────
    # Gym interface
    # ──────────────────────────────────────────

    @staticmethod
    def _make_player(name: str, uid: str, school: str, level: int, deck, is_agent: bool = False) -> Player:
        if school == "random":
            school = _random.choice(list(DECK_MASTER["easy"].keys()))
        if deck is None:
            deck = DECK_MASTER["easy"][school]()
        base_stats   = compute_stats(level, school)
        school_chart = compute_school_chart(level, school)
        p = Player(name, uid, school, deck, isBot=not is_agent, img_path=None,
                   base_stats=base_stats, school_chart=school_chart)
        return p

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.agent = self._make_player(
            "agent", "agent", self.agent_school, self.agent_level, self.agent_deck, is_agent=True,
        )

        ally_team  = [self.agent] + [
            self._make_player(f"ally_{i}", f"ally_{i}", cfg["school"], cfg["level"], cfg.get("deck"))
            for i, cfg in enumerate(self.allies)
        ]
        enemy_team = [
            self._make_player(f"enemy_{i}", f"enemy_{i}", cfg["school"], cfg["level"], cfg.get("deck"))
            for i, cfg in enumerate(self.enemies)
        ]

        self.game = Game(ally_team, enemy_team)
        for i, cfg in enumerate(self.enemies):
            if cfg.get("strategy") == "pass":
                self.game.pass_bot_ids.add(f"enemy_{i}")
        for i, policy in enumerate(self.opponent_policies):
            if policy is not None:
                enemy_player = next(
                    (p for p in self.game.teams[1] if p.user_id == f"enemy_{i}"), None
                )
                if enemy_player is not None:
                    policy.attach(self.game, enemy_player, own_team_idx=1)
        self._silent(self.game.begin)

        self._prev_enemy_hp   = sum(float(p.health) for p in self.game.teams[1])
        self._pip_change_turn = -1

        return self._obs(), {}

    def step(self, action: int):
        self._apply(action)

        # Discard and pip-school change leave player_actions[agent] as None.
        # Only resolve once the agent commits a pass or cast.
        if self.game.player_actions.get(self.agent.user_id) is None:
            return self._obs(), 0.0, False, False, {}

        agent_act = self.game.player_actions.get(self.agent.user_id, {})
        reward = -0.0005 if agent_act.get("type") == "pass" else 0.0

        try:
            self._silent(self.game.resolve_actions)
            reward += self._enemy_damage_reward()

            done = self.game.winner is not None
            if not done:
                self._silent(self.game.start_turn)   # bot auto-acts inside start_turn
                self._silent(self.game.resolve_actions)
                reward += self._enemy_damage_reward()
                done = self.game.winner is not None
                if not done:
                    log_mark = len(self.game.log)
                    self._silent(self.game.start_turn)  # agent's next turn begins
                    reward += self._pip_choke_penalty(log_mark)
                    reward += self._reshuffle_reward(log_mark)
        except Exception:
            self._dump_crash(action)
            raise

        if self.game.winner == "A":
            reward += 1.0
        elif self.game.winner == "B":
            reward -= 1.0

        truncated = self.game.turns > self.max_turns
        return self._obs(), reward, done, truncated, {}

    # ──────────────────────────────────────────
    # Action helpers
    # ──────────────────────────────────────────

    def _apply(self, action: int):
        if action == 0:
            self.game.player_pass(self.agent)
            return

        if action >= PIP_SCHOOL_BASE:
            if self.game.turns == self._pip_change_turn:
                return  # already changed pip school this turn; ignore
            school = SCHOOLS[action - PIP_SCHOOL_BASE]
            self.agent.school_pip_select = school
            self._pip_change_turn = self.game.turns
            self.game.log.append({"type": "action", "player": self.agent.user_id, "action": "pip_school_change", "school": school})
            return  # player_actions stays None; turn continues

        if action >= DISCARD_BASE:
            card_idx = action - DISCARD_BASE
            hand = self.agent.deck.play_hand
            if card_idx < len(hand):
                self._silent(lambda: self.game.player_discard(self.agent, hand[card_idx].instance_id))
            return  # player_actions stays None; turn continues

        encoded     = action - 1
        card_idx    = encoded // N_TARGET_SLOTS
        target_slot = encoded %  N_TARGET_SLOTS

        # Resolve target player from slot index
        if target_slot == MAX_PLAYERS:
            target_id = None                       # AoE / self-cast
        else:
            team_idx   = target_slot // MAX_TEAM_SIZE
            player_idx = target_slot %  MAX_TEAM_SIZE
            team       = self.game.teams[team_idx]
            if player_idx >= len(team):
                self.game.player_pass(self.agent)
                return
            target_id = team[player_idx].user_id

        play = self.game.playability.get(self.agent.user_id, [])
        if card_idx < len(play) and play[card_idx]["playable"]:
            if self.game.player_cast(self.agent, card_idx, target_id):
                return

        self.game.player_pass(self.agent)

    # ──────────────────────────────────────────
    # Observation helpers
    # ──────────────────────────────────────────

    def _obs(self) -> dict:
        return {
            "cards":       self._encode_cards(),
            "players":     self._encode_players(),
            "effects":     _encode_hanging_effect_tokens(self.game.teams),
            "game":        self._encode_game(),
            "action_mask": self._action_mask(),
        }

    def _encode_cards(self) -> np.ndarray:
        play = self.game.playability.get(self.agent.user_id, [])
        return _encode_all_cards(self.agent, play)

    def _encode_players(self) -> np.ndarray:
        arr = np.zeros((MAX_PLAYERS, PLAYER_DIM), dtype=np.float32)
        for team_idx, team in enumerate(self.game.teams):
            for p_idx, p in enumerate(team[:MAX_TEAM_SIZE]):
                arr[team_idx * MAX_TEAM_SIZE + p_idx] = self._encode_one_player(p)
        return arr

    @staticmethod
    def _encode_one_player(p) -> np.ndarray:
        feats = [p.maxHealth, p.health / float(p.maxHealth)]
        for k in PIP_KEYS:
            feats.append(p.pips.get(k, 0) * 1.0)
        one_hot = [0.0] * len(SCHOOLS)
        one_hot[SCHOOL_TO_IDX[p.school]] = 1.0
        feats.extend(one_hot)

        return np.array(feats, dtype=np.float32)

    def _encode_game(self) -> np.ndarray:
        vec = np.zeros(GAME_DIM, dtype=np.float32)
        vec[0] = min(self.game.turns / float(self.max_turns), 1.0)
        vec[1] = len(self.agent.deck.play_hand) / float(HAND_SIZE)
        sel = self.agent.school_pip_select
        if sel in SCHOOL_TO_IDX:
            vec[2 + SCHOOL_TO_IDX[sel]] = 1.0
        return vec

    def _action_mask(self) -> np.ndarray:
        mask = np.zeros(N_ACTIONS, dtype=np.float32)
        mask[0] = 1.0  # pass always legal

        play = self.game.playability.get(self.agent.user_id, [])
        for card_i, info in enumerate(play[:HAND_SIZE]):
            if not info["playable"]:
                continue
            targets = info["targets"]
            base = 1 + card_i * N_TARGET_SLOTS
            if not targets:
                # AoE / self-cast: null target slot
                mask[base + MAX_PLAYERS] = 1.0
            else:
                for p in targets:
                    j = self._global_idx(p)
                    if j >= 0:
                        mask[base + j] = 1.0

        # Discard actions (DISCARD_BASE .. DISCARD_BASE+HAND_SIZE-1)
        for i in range(min(HAND_SIZE, len(self.agent.deck.play_hand))):
            mask[DISCARD_BASE + i] = 1.0

        # School pip-select actions — only allowed once per turn
        if self.game.turns != self._pip_change_turn:
            for j in range(N_PIP_SCHOOL_ACTIONS):
                mask[PIP_SCHOOL_BASE + j] = 1.0

        return mask

    # ──────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────

    def _global_idx(self, player) -> int:
        """Return the global player slot index (team_idx * MAX_TEAM_SIZE + player_idx)."""
        for team_idx, team in enumerate(self.game.teams):
            for p_idx, p in enumerate(team):
                if p.user_id == player.user_id:
                    return team_idx * MAX_TEAM_SIZE + p_idx
        return -1

    def _enemy_damage_reward(self) -> float:
        """Small positive reward proportional to enemy HP lost since last call."""
        enemy_hp = sum(float(p.health) for p in self.game.teams[1])
        delta = max(self._prev_enemy_hp - enemy_hp, 0.0)  # positive when enemy takes damage
        self._prev_enemy_hp = enemy_hp
        return delta / float(self.agent.maxHealth) * 0.05

    def _pip_choke_penalty(self, log_start: int) -> float:
        """Return -0.05 if the agent received a pip-choke this turn, else 0."""
        for entry in self.game.log[log_start:]:
            if (isinstance(entry, dict)
                    and entry.get("type") == "effect_resolve"
                    and entry.get("aspect") == "pip_choke"
                    and entry.get("target") == self.agent.user_id):
                return -0.05
        return 0.0

    def _reshuffle_reward(self, log_start: int) -> float:
        """Return +0.1 if the agent reshuffled this turn, else 0."""
        for entry in self.game.log[log_start:]:
            if (isinstance(entry, dict)
                    and entry.get("type") == "effect_resolve"
                    and entry.get("aspect") == "reshuffle"
                    and entry.get("target") == self.agent.user_id):
                return 0.1
        return 0.0

    def _dump_crash(self, action: int) -> None:
        os.makedirs("rl/crashes", exist_ok=True)
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = f"rl/crashes/crash_{ts}.txt"
        with open(path, "w") as f:
            f.write(f"=== CRASH DUMP {ts} ===\n\n")
            f.write(f"action : {action}\n")
            f.write(f"turn   : {self.game.turns}\n")
            f.write(f"winner : {self.game.winner}\n\n")

            f.write("--- Traceback ---\n")
            f.write(traceback.format_exc())
            f.write("\n")

            f.write("--- Game Log ---\n")
            for entry in self.game.log:
                f.write(f"  {entry}\n")
            f.write("\n")

            f.write("--- Player States ---\n")
            for team_i, team in enumerate(self.game.teams):
                f.write(f"Team {team_i}:\n")
                for p in team:
                    f.write(f"  {p.name}  school={p.school}  hp={p.health}/{p.maxHealth}\n")
                    f.write(f"    pips   : {p.pips}\n")
                    f.write(f"    hand   : {[c.card_def.name for c in p.deck.play_hand]}\n")
                    f.write(f"    charms : {[c.to_json() for c in p.charms]}\n")
                    f.write(f"    curses : {[c.to_json() for c in p.curses]}\n")
                    f.write(f"    wards  : {[c.to_json() for c in p.wards]}\n")
                    f.write(f"    jinxes : {[c.to_json() for c in p.jinxes]}\n")
                    f.write(f"    dots   : {[c.to_json() for c in p.dots]}\n")
                    f.write(f"    hots   : {[c.to_json() for c in p.hots]}\n")

        print(f"[W101Env] crash dump → {path}", file=sys.stderr)

    def _silent(self, fn):
        if not self.suppress_output:
            return fn()
        with open(os.devnull, "w") as null:
            old, sys.stdout = sys.stdout, null
            try:
                return fn()
            finally:
                sys.stdout = old
