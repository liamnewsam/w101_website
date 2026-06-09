from Deck import *
from utils import *
from Card import *
from config import MAX_PIP_COUNT

import random

ACTIONS= ["Choose Card", "Pass", "Print State"]


class Player:
    def __init__(self, name: str, user_id, school: str, deck: Deck, isBot=False, img_path=None, base_stats=None, school_chart=None):
        self.isBot = isBot

        self.name = name
        self.user_id = user_id
        self.school = school.lower()
        self.deck = deck

        if base_stats:
            self.maxHealth = base_stats["health"]
            self.mana      = base_stats["mana"]
        else:
            self.maxHealth = 3000
            self.mana      = 300
        self.health = self.maxHealth

        self.boost            = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.resistance       = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.flat_boost       = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.flat_resistance  = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.accuracy         = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.critical         = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.block            = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.armor_piercing   = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.pip_conversion   = {"myth": 100, "life": 100, "fire": 100, "ice": 100, "storm": 100, "death": 100, "balance": 100}
        self.power_pip_chance = 100
        self.school_pip_chance = 60
        self.stun_resistance  = 0
        self.healing_in       = 0
        self.healing_out      = 0

        if base_stats:
            s = self.school
            # Per-school boost and resistance — use chart when available so all
            # school slots are populated (triangle bonuses/penalties included)
            if school_chart:
                for entry in school_chart:
                    es = entry["school"]
                    if es in self.boost:
                        self.boost[es]      = entry["damage"]
                        self.resistance[es] = entry["resistance"]
            elif s in self.boost:
                self.boost[s]      = base_stats["damage"]
                self.resistance[s] = base_stats["resistance"]

            # Own-school only stats
            if s in self.critical:
                self.critical[s]       = base_stats["critical"]
                self.block[s]          = base_stats["block"]
                self.armor_piercing[s] = base_stats["pierce"]
            self.power_pip_chance = base_stats["power_pip"]
            self.healing_in       = base_stats["heal_in"]
            self.healing_out      = base_stats["heal_out"]
            self.stun_resistance  = base_stats["stun_res"]

        self.active = False
        self.pips = {"regular": 0, "powerpip": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.school_pip_select = self.school

        # There are my personal categorizations:
        self.wards = [] # Things on the player that protect against incoming threat
        self.jinxes = [] # Things on the player that worsen incoming threat
        self.charms = []  # Things on the player that improve outgoing actions
        self.curses = [] # Things on the player that worsen outgoing actions

        self.auras = []
        self.dots = []
        self.hots = []

        self.struggle_counter = 1

        self.img_path = img_path

    def act(self):
        self.active = True
        i = f"{self.name}, Choose action:"
        action = ACTIONS[int(inp(ACTIONS))-1]

        
        if action == "Choose Card": #Choosing Card
            hand_str = fancy_print_hand(self.deck.play_hand)
            #print(hand_str)
            #card_i = int(inp(self.deck.play_hand, custom=hand_str))-1
            #print(fancy_print_card(self.deck.play_hand[card_i]))
            return (action, None)
        
        if action == "Pass":
            return ("Pass", None)

        if action == "Print State":
            return("Print State", None)

    def pip_count(self):
        return sum(self.pips.values())    
    
    def receive_pip(self):
        if self.pip_count() >= MAX_PIP_COUNT:
            return {"type": "effect_resolve", "target": self.user_id, "aspect": "pip_choke"}

        if random.randint(0, 99) < self.power_pip_chance:
            if random.randint(0, 99) < self.school_pip_chance:
                self.pips[self.school_pip_select] += 1
                return {"type": "effect_resolve", "target": self.user_id, "aspect": "pip_gain", "amount": {self.school_pip_select: 1}}
            else:
                self.pips["powerpip"] += 1
                return {"type": "effect_resolve", "target": self.user_id, "aspect": "pip_gain", "amount": {"powerpip": 1}}
        else:
            self.pips["regular"] += 1
            return {"type": "effect_resolve", "target": self.user_id, "aspect": "pip_gain", "amount": {"regular": 1}}

    def deduct_pips(self, card):

        deducted_pips = {"regular": 0, "powerpip": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}

        pips = card.card_def.pips

        if pips == "X":
            # Consume all pips; each power pip and matching school pip counts as 2
            card_school = card.card_def.school
            school_aligned = card_school == self.school
            x_pips = 0
            for key in list(self.pips.keys()):
                count = self.pips[key]
                if count <= 0:
                    continue
                if key == "powerpip":
                    x_pips += count * (2 if school_aligned else 1)
                elif key == card_school:
                    x_pips += count * 2
                else:
                    x_pips += count
                deducted_pips[key] = count
                self.pips[key] = 0
            deducted_final = {k: v for k, v in deducted_pips.items() if v}
            deducted_final["converted"] = False
            deducted_final["x_pips"] = x_pips
            return deducted_final

        if type(pips) == int:
            pips = {"regular": pips}

        # Deduct special pip costs (shadow pips, etc.) directly
        for key, value in pips.items():
            if key != "regular":
                self.pips[key] -= value
                deducted_pips[key] += value

        card_school = card.card_def.school
        school_aligned = card_school == self.school
        needed = pips.get("regular", 0)
        converted = False

        if school_aligned:
            # Primary school spell:
            # Regular pips are spent first (1:1), then power pips (2:1), then school pips (2:1).
            # Spending regular pips before power pips preserves the more valuable double-pips
            # for higher-cost spells later in the game.

            while needed > 0 and self.pips["regular"] > 0:
                needed -= 1
                self.pips["regular"] -= 1
                deducted_pips["regular"] += 1

            while needed >= 2 and self.pips["powerpip"] > 0:
                needed -= 2
                self.pips["powerpip"] -= 1
                deducted_pips["powerpip"] += 1

            while needed >= 2 and self.pips[card_school] > 0:
                needed -= 2
                self.pips[card_school] -= 1
                deducted_pips[card_school] += 1

            # Odd pip leftover: spend a power pip or school pip (worth 2, only need 1)
            if needed == 1:
                if self.pips["powerpip"] > 0:
                    needed -= 1
                    self.pips["powerpip"] -= 1
                    deducted_pips["powerpip"] += 1
                    if random.randint(0, 99) < self.pip_conversion[card_school]:
                        self.pips["regular"] += 1
                        converted = True
                elif self.pips[card_school] > 0:
                    needed -= 1
                    self.pips[card_school] -= 1
                    deducted_pips[card_school] += 1
                    if random.randint(0, 99) < self.pip_conversion[card_school]:
                        self.pips["regular"] += 1
                        converted = True

            # Last resort: other school pips count as 1 each
            if needed > 0:
                for pip_key in [k for k in self.pips if k not in ["regular", "powerpip", card_school]]:
                    while needed > 0 and self.pips[pip_key] > 0:
                        needed -= 1
                        self.pips[pip_key] -= 1
                        deducted_pips[pip_key] += 1

        else:
            # Off-school spell:
            # Matching school pips count as 2 → regular pips count as 1 → power pips count as 1
            # Power pips are saved for last so they remain available for primary school spells.

            while needed >= 2 and self.pips[card_school] > 0:
                needed -= 2
                self.pips[card_school] -= 1
                deducted_pips[card_school] += 1

            while needed > 0 and self.pips["regular"] > 0:
                needed -= 1
                self.pips["regular"] -= 1
                deducted_pips["regular"] += 1

            while needed > 0 and self.pips["powerpip"] > 0:
                needed -= 1
                self.pips["powerpip"] -= 1
                deducted_pips["powerpip"] += 1

            # Odd pip leftover: spend a matching school pip (worth 2, only need 1)
            if needed == 1 and self.pips[card_school] > 0:
                needed -= 1
                self.pips[card_school] -= 1
                deducted_pips[card_school] += 1
                if random.randint(0, 99) < self.pip_conversion[card_school]:
                    self.pips["regular"] += 1
                    converted = True

            # Last resort: other school pips count as 1 each
            if needed > 0:
                for pip_key in [k for k in self.pips if k not in ["regular", "powerpip", card_school]]:
                    while needed > 0 and self.pips[pip_key] > 0:
                        needed -= 1
                        self.pips[pip_key] -= 1
                        deducted_pips[pip_key] += 1

        deducted_final = {key: item for key, item in deducted_pips.items() if item > 0}
        deducted_final["converted"] = converted

        return deducted_final

    def refresh(self):
        self.deck.refresh()
        self.pips = {"regular": 0, "powerpip": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.active = False

    def consume_dispel(self, card):
        for curse in self.curses:
            if curse.aspect == "dispel" and curse.school == card.card_def.school:
                temp = curse 
                self.curses.remove(curse)
                return temp
        
        return None

    
    def consume_accuracy(self, card):
        acc = card.card_def.accuracy
        used = []
        i = 0
        while i < len(self.curses):
            curse = self.curses[i]
            if curse.aspect == "accuracy" and not isRedundant(used, curse):
                acc += curse.amount
                self.curses.remove(curse)
                used.append(curse)
            else:
                i += 1
        
        if acc == 100: #Then we don't need to consume accuracy
            return acc, []

        i = 0
        while i < len(self.charms):
            charm = self.charms[i]
            if charm.aspect == "accuracy" and not isRedundant(used, charm):
                acc += charm.amount
                self.charms.remove(charm)
                used.append(charm)
            else:
                i += 1

        return acc, used
    
    def consume_charms_curses_for_card(self, expanded_effects, accumulation):
        # Collect schools from all damage effects and whether any heals exist.
        # A blade is consumed if its school matches at least one hit in the cast.
        damage_schools = set()
        has_heal = False
        for effect in expanded_effects:
            if effect["type"] in ["damage", "DoT", "drain"]:
                damage_schools.add(effect.get("school", "any"))
            elif effect["type"] in ["heal", "HoT"]:
                has_heal = True

        used = []
        for hangingEffectList in [self.charms, self.curses]:
            i = 0
            while i < len(hangingEffectList):
                hangingEffect = hangingEffectList[i]
                consumed = False
                if hangingEffect.aspect == "damage" and damage_schools:
                    if (not hangingEffect.school or hangingEffect.school == "any" or hangingEffect.school in damage_schools) and not isRedundant(used, hangingEffect):
                        if not hangingEffect.school:
                            for school in SCHOOLS:
                                accumulation["damage"][school] += hangingEffect.amount
                        else:
                            accumulation["damage"][hangingEffect.school] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                        consumed = True
                elif hangingEffect.aspect == "armor_piercing" and damage_schools:
                    if (not hangingEffect.school or hangingEffect.school == "any" or hangingEffect.school in damage_schools) and not isRedundant(used, hangingEffect):
                        if not hangingEffect.school:
                            for school in SCHOOLS:
                                accumulation["armor_piercing"][school] += hangingEffect.amount
                        else:
                            accumulation["armor_piercing"][hangingEffect.school] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                        consumed = True
                elif hangingEffect.aspect == "heal" and has_heal and not isRedundant(used, hangingEffect):
                    accumulation["heal"] += hangingEffect.amount
                    hangingEffectList.remove(hangingEffect)
                    used.append(hangingEffect)
                    consumed = True
                if not consumed:
                    i += 1
        return used

    def consume_charms_curses_for_effect(self, effect, accumulation):
        used = []
        for hangingEffectList in [self.charms, self.curses]:
            if effect["type"] in ["damage", "DoT", "drain"]:
                i = 0
                while i < len(hangingEffectList):
                    hangingEffect = hangingEffectList[i]
                    if hangingEffect.aspect == "damage" and (not hangingEffect.school or hangingEffect.school in ["any", effect["school"]]) and not isRedundant(used, hangingEffect):
                        if not hangingEffect.school:
                            for school in SCHOOLS:
                                accumulation["damage"][school] += hangingEffect.amount
                        else:
                            accumulation["damage"][hangingEffect.school] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                    elif hangingEffect.aspect == "armor_piercing" and (not hangingEffect.school or hangingEffect.school in ["any", effect["school"]]) and not isRedundant(used, hangingEffect):
                        accumulation["armor_piercing"][hangingEffect.school] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                    else:
                        i += 1
            elif effect["type"] in ["heal", "HoT"]:
                i = 0
                while i < len(hangingEffectList):
                    hangingEffect = hangingEffectList[i]
                    if hangingEffect.aspect == "heal" and not isRedundant(used, hangingEffect):
                        accumulation["heal"] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                    else:
                        i += 1
        return used

    def consume_wards_jinxes(self, effect, target_accumulation):
        used = []
        if effect["type"] in ["damage", "drain", "detonate"]:
            
            for hangingEffectList in [self.wards, self.jinxes]:
                i = 0
                while i < len(hangingEffectList):
                    hangingEffect = hangingEffectList[i]
                    if hangingEffect.aspect == "damage" and (not hangingEffect.school or hangingEffect.school in ["any", target_accumulation["prism_school"] or effect.get("school", "")]) and not isRedundant(used, hangingEffect):
                        if not hangingEffect.school:
                            for school in SCHOOLS:
                                target_accumulation["damage"][school] += hangingEffect.amount
                        else:
                            target_accumulation["damage"][hangingEffect.school] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                    elif hangingEffect.aspect == "prism" and hangingEffect.inputSchool == (target_accumulation["prism_school"] or effect.get("school", "")):
                        target_accumulation["damage"][hangingEffect.outputSchool] = target_accumulation["damage"][hangingEffect.inputSchool]
                        target_accumulation["armor_piercing"][hangingEffect.outputSchool] = target_accumulation["armor_piercing"][hangingEffect.inputSchool]
                        target_accumulation["prism_school"] = hangingEffect.outputSchool

                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                    else:
                        i += 1
        elif effect["type"] in ["heal", "HoT"]:
            for hangingEffectList in [self.wards, self.jinxes]:
                i = 0
                while i < len(hangingEffectList):
                    hangingEffect = hangingEffectList[i]
                    if hangingEffect.aspect == "heal" and not isRedundant(used, hangingEffect):
                        target_accumulation["heal"] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                    else:
                        i += 1

        return used

    def absorb_damage(self, dmg):
        """Apply absorb wards to incoming flat damage. Returns (remaining_dmg, log_events).
        Shields reduce damage first (already applied via consume_wards_jinxes percentage modifiers),
        then absorb wards subtract from the post-shield flat amount. If an absorb ward breaks
        mid-absorption the leftover damage still hits the player."""
        events = []
        if dmg <= 0:
            return dmg, events
        for ward in self.wards[:]:
            if ward.aspect != "absorb" or dmg <= 0:
                continue
            prev = ward.to_json()
            absorbed = min(dmg, ward.amount)
            ward.amount -= absorbed
            dmg -= absorbed
            if ward.amount <= 0:
                self.wards.remove(ward)
                events.append({"type": "effect_trigger", "player": self.user_id, "aspect": "ward", "value": ward.to_json()})
            else:
                events.append({"type": "effect_resolve", "player": self.user_id, "aspect": "update", "aspectType": "ward", "from": prev, "to": ward.to_json()})
        return dmg, events

    def to_json(self):
        return {
            "name": self.name
        }
    
    def to_json_public(self):
        return {
            "name": self.name,
            "user_id": self.user_id,
            "maxHealth": self.maxHealth,
            "health": self.health,
            "school": self.school,
            "pips": self.pips,
            "charms": [charm.to_json() for charm in self.charms],
            "curses": [curse.to_json() for curse in self.curses],
            "wards": [ward.to_json() for ward in self.wards],
            "jinxes": [jinx.to_json() for jinx in self.jinxes],
            
            "auras": [aura.to_json() for aura in self.auras],
            "dots": [dot.to_json() for dot in self.dots],
            "hots": [hot.to_json() for hot in self.hots],
            "img_path": self.img_path
        }
    
    def to_json_private(self):
        return {
            "name": self.name,
            "user_id": self.user_id,
            "maxHealth": self.maxHealth,
            "health": self.health,
            "mana": self.mana,
            "school_pip_select": self.school_pip_select,
            "school": self.school,
            "pips": self.pips,
            
            "charms": [charm.to_json() for charm in self.charms],
            "curses": [curse.to_json() for curse in self.curses],
            "wards": [ward.to_json() for ward in self.wards],
            "jinxes": [jinx.to_json() for jinx in self.jinxes],

            "auras": [aura.to_json() for aura in self.auras],
            "dots": [dot.to_json() for dot in self.dots],
            "hots": [hot.to_json() for hot in self.hots],
        }


    def __str__(self):
        return self.name
    

def loadPlayer(data):
    from stats import compute_stats, compute_school_chart
    player_name   = data["name"]
    player_school = data["school"]
    level         = data.get("level", 1)
    img_path      = data["image_path"]
    cards = []
    for card_id in data["deck"]["card_ids"]:
        card_def = CARD_BY_ID.get(card_id)
        if card_def is None:
            continue
        if card_def.pvp_level and card_def.pvp_level > level:
            continue
        cards.append(Card(card_def))
    player_deck  = Deck(data["deck"]["name"], cards)
    base_stats   = compute_stats(level, player_school)
    school_chart = compute_school_chart(level, player_school)
    return Player(player_name, data["user_id"], player_school, player_deck, img_path=img_path, base_stats=base_stats, school_chart=school_chart)


#-------------------------------- EFFECTS ------------------------------------------------
from abc import ABC, abstractmethod
import random


def isRedundant(effects, effect):
    for e in effects:
        if type(e) == type(effect) and e.school == effect.school and e.aspect == effect.aspect and e.amount == effect.amount:
            return True
    return False

class Effect(ABC):
    """
    Base effect class.
    Subclasses implement resolve().
    """
    def __init__(self, template, owner, target, card, x_pips=1):
        self.template = template
        self.owner = owner
        self.target = target
        self.card = card
        self.x_pips = x_pips
        self.school = template.get("school", "any")
        if isinstance(self.school, list):
            self.school = random.choice(self.school)
        if self.school == "player" and owner is not None:
            self.school = owner.school.lower()

    @abstractmethod
    def resolve(self, game):
        """Apply the effect once (may be immediate or may add to linger list)."""
        pass

    def tick(self, game):
        """Called each round if the effect lingers."""
        if self.duration is None:
            return

        self.duration -= 1
        if self.duration <= 0:
            self.expire(game)

    def expire(self, game):
        """Optional cleanup hook."""
        pass

    # -------- Utility for subclasses --------
    def get_amount(self):
        """Handles: amount = X  or min/max random amounts. Scales by x_pips for X-pip spells."""
        if "amountType" in self.template:
            if self.template["amountType"] == "player_max":
                return self.template["amount"] * 1.0 / 100 * self.owner.maxHealth * self.x_pips
        if "amount" in self.template:
            amt = self.template["amount"]
            base = random.choice(amt) if isinstance(amt, list) else amt
            return base * self.x_pips
        if "min" in self.template and "max" in self.template:
            return random.randint(self.template["min"], self.template["max"]) * self.x_pips

        return False
    
    def to_json(self):
        return {"type": type(self).__name__, "school": self.school}


class DamageEffect(Effect):
    def compute_dmg(self, game, caster_accumulation, target_accumulation, critical_multiplier):
        base = self.get_amount()  
        dmg = base + (self.owner.flat_boost[self.school] if self.owner else 0)
        dmg *= (1 + (self.owner.boost[self.school] / 100.0 if self.owner else 0))
        blade_mult = 1.0 + (caster_accumulation["damage"]["any"] / 100.0 if caster_accumulation else 0)
                    
        if self.school != "any":
            blade_mult += (caster_accumulation["damage"][self.school] / 100.0 if caster_accumulation else 0)

        trap_mult = 1.0 + (target_accumulation["damage"]["any"] / 100.0 if target_accumulation else 0)

        #Prism Effect:
        if target_accumulation["prism_school"]:
            self.school = target_accumulation["prism_school"]

        if self.school != "any":
            blade_mult += (target_accumulation["damage"][self.school] / 100.0 if target_accumulation else 0)
        
        dmg *= blade_mult * trap_mult

        dmg *= critical_multiplier

        dmg -= self.target.flat_resistance[self.school]

        resist = self.target.resistance[self.school]
        pierce = self.owner.armor_piercing[self.school] if self.owner else 0
        pierce += caster_accumulation["armor_piercing"][self.school] if caster_accumulation else 0

        effective_resist = max(resist - pierce, 0)
        dmg *= (1 - effective_resist / 100.0)

        if dmg < 0:
            dmg = 0

        return dmg

    def resolve(self, game, caster_accumulation, target_accumulation, critical_multiplier, skip_absorb=False):

        dmg = self.compute_dmg(game, caster_accumulation, target_accumulation, critical_multiplier)

        if dmg < 0:
            dmg = 0

        pre_events = []
        if not skip_absorb and self.target:
            dmg, pre_events = self.target.absorb_damage(dmg)

        dmg_message = {"type": "effect_resolve", "player": self.owner.user_id if self.owner else None, "aspect": "damage", "amount": dmg, "target": self.target.user_id, "school": self.school}

        if self.target.health - dmg <= 0:
            self.target.health = 0
            return pre_events + [dmg_message, {"type": "result", "result": "dead", "player": self.target.user_id}]

        self.target.health -= dmg

        if pre_events:
            return pre_events + [dmg_message]
        return dmg_message

    

class HealEffect(Effect):
    def compute_heal(self, caster_accumulation, target_accumulation, critical_multiplier):
        hp = self.get_amount()  

        hp *= (1 + (self.owner.healing_out / 100.0 if self.owner else 0))
        out_mult = 1.0 + (caster_accumulation["heal"] / 100.0 if caster_accumulation else 0)
                    

        in_mult = 1.0 + (target_accumulation["heal"] / 100.0 if caster_accumulation else 0)

        hp *= out_mult * in_mult

        hp *= critical_multiplier

        if hp < 0:
            hp = 0

        return hp
    def resolve(self, game, caster_accumulation, target_accumulation, critical_multiplier):
        
        hp = self.compute_heal(caster_accumulation, target_accumulation, critical_multiplier)
        

        if self.target.health + hp > self.target.maxHealth:
            hp = self.target.maxHealth - self.target.health
            self.target.health = self.target.maxHealth
        else:
            self.target.health += hp
            
        return {"type": "effect_resolve", "player": self.owner.user_id if self.owner else None, "aspect": "heal", "amount": hp, "target": self.target.user_id}
    
class WardEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.aspect = template["aspect"]
        self.amount = self.get_amount()

    def resolve(self, game):
        # Add the shield to target's shield list
        self.target.wards.append(self)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "ward", "value": self.to_json()}

    def to_json(self):
        return {"type": "ward", "aspect": self.aspect, "school": self.school, "amount": self.amount}

    '''
    def absorb(self, incoming_amount):
        """Return how much of incoming damage is absorbed."""
        absorbed = min(incoming_amount, self.amount)
        self.amount -= absorbed

        if self.amount <= 0:
            # shield breaks
            if self in self.target.shields:
                self.target.shields.remove(self)

        return absorbed'''
    
class JinxEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        if template["type"] == "trap":
            self.aspect = "damage"
        else:
            self.aspect = template["aspect"]
        self.amount = self.get_amount()
        self.school = template.get("school", None)

    def resolve(self, game):
        self.target.jinxes.append(self)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "jinx", "value": self.to_json()}

    '''
    def trigger(self, base_damage):
        """Triggered when target is next hit."""
        #boosted = int(base_damage * (1 + self.amount / 100))
        self.target.jinxes.remove(self)
        if self.aspect == "damage":
            return self.amount'''
    
    def to_json(self):
        return {"type": "jinx", "aspect": self.aspect, "school": self.school, "amount": self.amount}

class DoTEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        r = template["rounds"]
        self.rounds = random.randint(r["min"], r["max"]) if isinstance(r, dict) else r
        self.wait = template.get("wait", False)
    
    def resolve(self, game, caster_accumulation, target_accumulation, critical_multiplier):
        self.target.dots.append(self)
        self.amount = DamageEffect(self.template, self.owner, self.target, self.card).compute_dmg(game, caster_accumulation, target_accumulation, critical_multiplier)

        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "dot", "value": self.to_json()}

    def tick(self, target_accumulation):
        log = []
        prev = self.to_json()
        if not self.wait:
            dmg = self.amount * 1.0 / self.rounds
            template = {"type": "damage", "school": self.school, "amount": dmg}

            damage = DamageEffect(template, None, self.target, self.card).resolve(None, None, target_accumulation, 1)
            if type(damage) == list:
                log.extend(damage)
            else:
                log.append(damage)

            self.amount -= dmg
        
        self.rounds -= 1

        if self.rounds == 0:
            if self.wait:
                dmg = self.amount
                template = {"type": "damage", "school": self.school, "amount": dmg}

                damage = DamageEffect(template, None, self.target, self.card).resolve(None, None, target_accumulation, 1)
                if type(damage) == list:
                    log.extend(damage)
                else:
                    log.append(damage)

            self.target.dots.remove(self)
            log.append({"type": "effect_trigger", "player": self.target.user_id, "aspect": "dot", "value": self.to_json()})
        else:
            log.append({"type": "effect_resolve", "player": self.target.user_id, "aspect": "update", "aspectType": "dot", "from":  prev, "to": self.to_json()})

        return log
    
    def to_json(self):
        return {"type": "dot", "school": self.school, "amount": getattr(self, "amount", None), "rounds": self.rounds, "wait": self.wait}

class HoTEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        r = template["rounds"]
        self.rounds = random.randint(r["min"], r["max"]) if isinstance(r, dict) else r
    def resolve(self, game, caster_accumulation, target_accumulation, critical_multiplier):
        self.target.hots.append(self)
        self.amount = HealEffect(self.template, self.owner, self.target, self.card).compute_heal(caster_accumulation, target_accumulation, critical_multiplier)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "hot", "value": self.to_json()}
    def tick(self):
        log = []
        prev = self.to_json()
        hp = self.amount * 1.0 / self.rounds
        template = {"type": "heal", "amount": hp}

        hpEffect = HealEffect(template, None, self.target, self.card).resolve(None, None, None, 1)
        if type(hp) == list:
            log.extend(hpEffect)
        else:
            log.append(hpEffect)

        self.rounds -= 1
        self.amount -= hp
        if self.rounds == 0:
            self.target.hots.remove(self)
            log.append({"type": "effect_trigger", "player": self.target.user_id, "aspect": "hot", "value": self.to_json()})
        else:
            log.append({"type": "effect_resolve", "player": self.target.user_id, "aspect": "update", "aspectType": "hot", "from":  prev, "to": self.to_json()})

        return log
    def to_json(self):
        return {"type": "hot", "amount": self.amount, "rounds": self.rounds}

class AuraEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.amount = self.get_amount()


class CharmEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.amount = self.get_amount()
        self.aspect = template["aspect"]
    def resolve(self, game):
        self.target.charms.append(self)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "charm", "value": self.to_json()}
    
    def to_json(self):
        return {"type": "charm", "aspect": self.aspect, "school": self.school, "amount": self.amount}

class CurseEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.amount = self.get_amount()
        self.aspect = template["aspect"]
    def resolve(self, game):
        self.target.curses.append(self)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "curse", "value": self.to_json()}
    
    def to_json(self):
        return {"type": "curse", "aspect": self.aspect, "school": self.school, "amount": self.amount}

class DestroyEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.aspect = template["aspect"]
    
    def resolve(self, game):
        _lists = {
            "charm": (self.target.charms, "charm"),
            "curse": (self.target.curses, "curse"),
            "ward":  (self.target.wards,  "ward"),
            "jinx":  (self.target.jinxes, "jinx"),
            "DoT":   (self.target.dots,   "dot"),
            "HoT":   (self.target.hots,   "hot"),
        }
        entry = _lists.get(self.aspect)
        if entry is None:
            return []
        lst, log_key = entry
        if not lst:
            # The aspect list was emptied mid-cast (e.g. a damage-modifier curse was
            # consumed by a paired DoT effect before this destroy could fire).
            print(f"[DestroyEffect] Warning: {self.target.user_id} has no {self.aspect} to destroy (consumed mid-cast)")
            return []
        item = lst.pop(random.randint(0, len(lst) - 1))
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "destroy", "aspectType": log_key, "value": item.to_json()}
class DetonateEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.amount = self.get_amount()

    def resolve(self, game, caster_accumulation, target_accumulation, critical_multiplier):
        if not self.target.dots:
            return []
        dot = self.target.dots.pop(random.randint(0, len(self.target.dots) - 1))
        school = dot.school
        dmg = dot.amount * self.amount

        # Detonate damage is not re-bladed, but target wards and critical apply
        trap_mult = 1.0 + (target_accumulation["damage"]["any"] / 100.0 if target_accumulation else 0)
        if school != "any":
            trap_mult += (target_accumulation["damage"][school] / 100.0 if target_accumulation else 0)
        dmg *= trap_mult * critical_multiplier

        pierce = (self.owner.armor_piercing[school] if self.owner else 0)
        pierce += caster_accumulation["armor_piercing"][school] if caster_accumulation else 0
        effective_resist = max(self.target.resistance[school] - pierce, 0)
        dmg *= (1 - effective_resist / 100.0)

        if dmg < 0:
            dmg = 0

        dmg, absorb_events = self.target.absorb_damage(dmg)


        dot_log = {"type": "effect_resolve", "player": self.owner.user_id if self.owner else None, "aspect": "destroy", "aspectType": "dot", "value": dot.to_json(), "target": self.target.user_id}
        dmg_message = {"type": "effect_resolve", "player": self.owner.user_id if self.owner else None, "aspect": "damage", "amount": dmg, "target": self.target.user_id, "school": school}

        if self.target.health - dmg <= 0:
            self.target.health = 0
            return [dot_log] + absorb_events + [dmg_message, {"type": "result", "result": "dead", "player": self.target.user_id}]

        self.target.health -= dmg
        return [dot_log] + absorb_events + [dmg_message]

class ExtendEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.amount = self.get_amount()
        self.aspect = template["aspect"]
    
    def resolve(self, game):
        
        if self.aspect == "HoT":
            hot = self.target.hots[random.randint(0, len(self.target.hots)-1)]
            hot_before = hot.to_json()
            hot.amount *= 1.0 * (hot.rounds + self.amount) / (hot.rounds)
            hot.rounds += self.amount
            return {"type": "effect_resolve", "target": self.target.user_id, "aspect": "update", "aspectType": "hot", "from": hot_before, "to": hot.to_json()}

class GlobalEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.amount = self.get_amount()
        self.aspect = template["aspect"]
        
    def resolve(self, game):
        game.global_effects.append(self)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": None, "aspect": "global", "value": self.to_json()}

    def to_json(self):
        return {"type": "global", "aspect": self.aspect, "school": self.school, "amount": self.amount}


class PipEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)

    def resolve(self, game):
        gained = 1 if self.target.pip_count() < MAX_PIP_COUNT else 0
        
        
        self.target.pips["regular"] += gained
        effect = {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "pip_gain", "amount": {"regular": gained}}

        if gained == 0:
            return [effect, {"type": "effect_resolve", "target": self.target.user_id, "aspect": "pip_choke"}]
        
        return effect

class PrismEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.inputSchool = template["from"]
        self.outputSchool = template["to"]
        self.aspect = "prism"

    

    def resolve(self, game):
        self.target.jinxes.append(self)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "jinx", "value": self.to_json()}

    def to_json(self):
        return {"type": "jinx", "aspect": "prism", "from": self.inputSchool, "to": self.outputSchool}

class ReshuffleEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
    
    def resolve(self, game):
        self.owner.deck.play_cards.extend(self.owner.deck.play_discard)
        self.owner.deck.play_discard = []
        random.shuffle(self.owner.deck.play_cards)

        return {"type": "effect_resolve", "target": self.owner.user_id, "aspect": "reshuffle"}

class DrainEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.amount = self.get_amount()

        self.damageEffect = DamageEffect(template, owner, target, card, x_pips=x_pips)

    def resolve(self, game, caster_accumulation, target_accumulation, critical_multiplier):
        result = self.damageEffect.resolve(game, caster_accumulation, target_accumulation, critical_multiplier, skip_absorb=True)
        if type(result) is list:
            result[0]["aspect"] = "drain"
            hp = result[0]["amount"] / 2.0
        else:
            result["aspect"] = "drain"

            hp = result["amount"] / 2.0
        
        if self.owner.health + hp > self.owner.maxHealth:
            hp = self.owner.maxHealth - self.owner.health
            self.owner.health = self.owner.maxHealth
        else:
            self.owner.health += hp

        return result



class TakeEffect(Effect):
    def __init__(self, template, owner, target, card, x_pips=1):
        super().__init__(template, owner, target, card, x_pips=x_pips)
        self.aspect = template["aspect"]
    
    def resolve(self, game):
        if self.aspect == "charm":
            charm = self.target.charms.pop(random.randint(0, len(self.target.charms)-1))
            self.owner.charms.append(charm)
            return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "take", "aspectType": "charm", "value": charm.to_json()}
        if self.aspect == "ward":
            ward = self.target.wards.pop(random.randint(0, len(self.target.wards)-1))
            self.owner.wards.append(ward)
            return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "take", "aspectType": "ward", "value": ward.to_json()}
        if self.aspect == "pip":
            pip_type = random.choice([pip_type for pip_type in self.target.pips.keys() if self.target.pips[pip_type] > 0])
            self.target.pips[pip_type] -= 1
            if self.owner.pip_count() < MAX_PIP_COUNT:
                self.owner.pips["regular"] += 1
            return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "take", "aspectType": "pip", "value": pip_type}
        


EFFECT_TYPE_TO_CLASS = {
    "charm": CharmEffect,
    "curse": CurseEffect,
    "ward": WardEffect,
    "jinx": JinxEffect,
    "trap": JinxEffect,
    "shield": WardEffect,

    "damage": DamageEffect,
    "heal": HealEffect,

    "DoT": DoTEffect,
    "HoT": HoTEffect,
    "aura": AuraEffect,
    
    
    "destroy": DestroyEffect,
    "detonate": DetonateEffect,
    "extend": ExtendEffect,
    "global": GlobalEffect,
    
    "pip": PipEffect,
    "reshuffle": ReshuffleEffect,
    "drain": DrainEffect,
    "take": TakeEffect,
    "prism": PrismEffect
}

