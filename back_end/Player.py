from Deck import *
from utils import *
from Card import *

import random

ACTIONS= ["Choose Card", "Pass", "Print State"]


class Player:
    def __init__(self, name: str, user_id, school: str, deck: Deck, isBot=False, img_path=None):
        self.isBot = isBot
        
        self.name = name
        self.user_id = user_id
        self.maxHealth = 300 if isBot else 3000
        self.health = self.maxHealth
        self.mana = 300
        self.school = school
        self.deck = deck
        self.boost = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.resistance = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.flat_boost = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.flat_resistance = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.accuracy = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.critical = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.block = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.armor_piercing = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.pip_conversion = {"myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}
        self.power_pip_chance = 0
        self.school_pip_chance = 0
        self.stun_resistance = 0
        self.healing_in = 0
        self.healing_out = 0

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
    def receive_pip(self):
        if random.randint(0, 99) < self.power_pip_chance:
            print("Receiving powerpip!")
            if random.randint(0, 99) < self.school_pip_chance:
                print(f"Converting to {self.school_pip_select} pip!")
                self.pips[self.school_pip_select] += 1
                return {"type": "effect_resolve", "player": self.user_id, "aspect": "pip_gain", "amount": {self.school_pip_select: 1}}
            else:
                self.pips["powerpip"] += 1
                return {"type": "effect_resolve", "player": self.user_id, "aspect": "pip_gain", "amount": {"powerpip": 1}}
        else:
            self.pips["regular"] += 1
            return {"type": "effect_resolve", "player": self.user_id, "aspect": "pip_gain", "amount": {"regular": 1}}

    def deduct_pips(self, card):

        deducted_pips = {"regular": 0, "powerpip": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0}

        pips = card.card_def.pips
        if type(pips) == int:
            pips = {"regular": pips}
        
        for key, value in pips.items():
            if key != "regular":
                self.pips[key] -= value
                deducted_pips[key] += value
        
        school_aligned = card.card_def.school == self.school
        needed_regular = pips["regular"] 
        while needed_regular > 1:
            if self.pips["regular"] > 1:
                needed_regular -= 1
                self.pips["regular"] -= 1
                deducted_pips["regular"] += 1
            elif school_aligned:
                if self.pips["powerpip"] > 0:
                    needed_regular -= 2
                    self.pips["powerpip"] -= 1
                    deducted_pips["powerpip"] += 1
                else:
                    available = [key for key, value in self.pips.items() if key not in ["regular", "powerpip"] and value > 0]
                    random_school_pip = random.choice(available)
                    needed_regular -= 2
                    self.pips[random_school_pip] -= 1
                    deducted_pips[random_school_pip] += 1
            else:
                if self.pips["regular"] == 1:
                    needed_regular -= 1
                    self.pips["regular"] -= 1
                    deducted_pips["regular"] += 1
                elif self.pips["powerpip"] > 0:
                    needed_regular -= 1
                    self.pips["powerpip"] -= 1
                    deducted_pips["powerpip"] += 1

                else:
                    available = [key for key, value in self.pips.items() if key not in ["regular", "powerpip"] and value > 0]
                    random_school_pip = random.choice(available)
                    needed_regular -= 1
                    self.pips[random_school_pip] -= 1
                    deducted_pips[random_school_pip] += 1

        converted = False

        if needed_regular == 1:
            if self.pips["regular"] > 0:
                needed_regular -= 1
                self.pips["regular"] -= 1
                deducted_pips["regular"] += 1
            elif self.pips["powerpip"] > 0:
                needed_regular -= 1
                self.pips["powerpip"] -= 1
                deducted_pips["powerpip"] += 1
                if random.randint(0, 99) < self.pip_conversion[card.card_def.school]:
                    print("Converted pip!")
                    self.pips["regular"] += 1
                    converted = True
            else:
                needed_regular -= 1
                available = [key for key, value in self.pips.items() if value > 0]
                random_school_pip = random.choice(available)
                self.pips[random_school_pip] -= 1
                deducted_pips[random_school_pip] += 1
                if random.randint(0, 99) < self.pip_conversion[card.card_def.school]:
                    print("Converted pip!")
                    self.pips["regular"] += 1
                    converted = True

        deducted_final = {key: item for key, item in deducted_pips.items() if item > 0}
        deducted_final["converted"] = converted

        return deducted_final

    def refresh(self):
        self.deck.refresh()
        self.pips = {"regular": 0, "powerpip": 0}
        self.active = False

    def consume_dispel(self, card):
        return False
    
    def consume_accuracy(self, card):
        return 0

    def consume(self, type, card, accumulation): # type = charm, curse, ward, jinx
        hangingEffectList = {"charm": self.charms, "curse": self.curses, "ward": self.wards, "jinx": self.jinxes}[type]
        used = []
        for effect in card.card_def.effects:
            if effect["type"] in ["damage", "DoT", "heal", "HoT"]:
                i = 0
                while i < len(hangingEffectList):
                    hangingEffect = hangingEffectList[i]
                    if hangingEffect.aspect == "damage" and hangingEffect.school in ["any", effect["school"]] and not isRedundant(used, hangingEffect):
                        accumulation["damage"][hangingEffect.school] += hangingEffect.amount
                        hangingEffectList.remove(hangingEffect)
                        used.append(hangingEffect)
                        print(f"Adding {hangingEffect.amount}% damage")
                    else:
                        i += 1

        return used

    def consumeCharms(self, card, accumulation): # Automatically assumes we are the caster
        used_charms = []
        for effect in card.card_def.effects:
            if effect["type"] in ["damage", "DoT", "heal", "HoT"]:
                for charm in self.charms:
                    if charm.aspect == "damage" and charm.school in ["any", effect["school"]] and not isRedundant(used_charms, charm):
                        accumulation["damage"][charm.school] += charm.amount
                        self.charms.remove(charm)
                        used_charms.append(charm)
                        print(f"Adding {charm.amount}% damage")
        
        return used_charms


    def consumeCurses(self, card, accumulation): # Automatically assumes we are the caster
        used_curses = []
        for effect in card.card_def.effects:
            if effect["type"] in ["damage", "DoT", "heal", "HoT"]:
                for curse in self.curses:
                    if curse.aspect == "damage" and curse.school in ["any", effect["school"]] and not isRedundant(used_curses, curse):
                        accumulation["damage"][curse.school] += curse.amount
                        self.curses.remove(curse)
                        used_curses.append(curse)
                        #print(f"Adding {curse.amount}% damage")
        
        return used_curses

    def consumeWards(self, card, accumulation): # Automatically assumes we are the target
        used_wards = []
        for effect in card.card_def.effects:
            if effect["type"] in ["damage", "DoT", "heal", "HoT"]:
                for ward in self.wards:
                    if ward.type == "damage" and ward.school in ["any", effect["school"]] and not isRedundant(used_wards, ward):
                        accumulation["damage"][ward.school] -= ward.amount
                        self.charms.remove(ward)
                        used_wards.append(ward)
                        print(f"Removing {ward.amount}% damage")
        
        return used_wards
    
    def consumeWards(self, card, accumulation): # Automatically assumes we are the target
        used_wards = []
        for effect in card.card_def.effects:
            if effect["type"] in ["damage", "DoT", "heal", "HoT"]:
                for ward in self.wards:
                    if ward.type == "damage" and ward.school in ["any", effect["school"]] and not isRedundant(used_wards, ward):
                        accumulation["damage"][ward.school] -= ward.amount
                        self.charms.remove(ward)
                        used_wards.append(ward)
                        print(f"Removing {ward.amount}% damage")
        
        return used_wards

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
    player_name = data["name"]
    player_school = data["school"]
    img_path = data["image_path"]
    cards = []
    #for card_id in data["decks"][0]["cards"]:
    print(data["deck"])
    for card_id in data["deck"]["card_ids"]:
        cards.append(Card(CARD_BY_ID[card_id]))
    player_deck = Deck(data["deck"]["name"], cards)
    return Player(player_name, data["user_id"], player_school, player_deck, img_path=img_path)


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
    def __init__(self, template, owner, target, card):
        self.template = template
        self.owner = owner
        self.target = target
        self.card = card
        self.school = template.get("school", "any")

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
        """Handles: amount = X  or min/max random amounts."""
        if "amount" in self.template:
            return self.template["amount"]
        if "min" in self.template and "max" in self.template:
            return random.randint(self.template["min"], self.template["max"])
        raise ValueError("Effect template has no amount or min/max")
    
    def to_json(self):
        return {"type": type(self).__name__, "school": self.school}
    
class DamageEffect(Effect):
    def resolve(self, game, caster_accumulation, target_accumulation, critical_multiplier):

        base = self.get_amount()  
        dmg = base + self.owner.flat_boost[school]
        dmg *= (1 + self.owner.boost[school] / 100.0)
        blade_mult = 1.0 + caster_accumulation["damage"]["any"] / 100.0
                    
        if self.school != "any":
            blade_mult += caster_accumulation["damage"][self.school] / 100.0

        trap_mult = 1.0 + target_accumulation["damage"]["any"] / 100.0

        if self.school != "any":
            blade_mult += target_accumulation["damage"][self.school] / 100.0
        
        dmg *= blade_mult * trap_mult

        dmg *= critical_multiplier

        dmg -= self.target.flat_resistance[school]

        resist = self.target.resistance[school]
        pierce = self.owner.armor_piercing[school]

        effective_resist = max(resist - pierce, 0)
        dmg *= (1 - effective_resist / 100.0)

        if dmg < 0:
            dmg = 0

        #absorbed = self.target.absorb_shield(dmg) Should be replaced with looking at wards with absorption aspect
        #dmg -= absorbed

        if dmg < 0:
            dmg = 0

        self.target.health -= dmg

        print(f"{self.owner.name} deals {int(dmg)} {school} damage to {self.target.name}!")

        return {"type": "effect_resolve", "player": self.owner.user_id, "aspect": "damage", "amount": dmg, "target": self.target.user_id, "school": self.school}

    

class HealEffect(Effect):
    def resolve(self, game, caster_consumed_charms, target_consumed_charms, critical_multiplier):
        amount = self.get_amount()
        self.target.health += amount
        print(f"{self.owner.name} heals {self.target.name} for {amount}!")
        return {"type": "effect_resolve", "player": self.owner.user_id, "aspect": "heal", "amount": amount, "target": self.target.user_id}
    
class WardEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.aspect = template["aspect"]
        self.amount = self.get_amount()

        self.is_lingering = True  # shields always linger

    def resolve(self, game):
        # Add the shield to target's shield list
        self.target.wards.append(self)
        print(f"{self.target.name} gains a {self.amount} shield!")
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
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.aspect = template["aspect"]
        self.amount = self.get_amount()
        self.school = template.get("school", None)

    def resolve(self, game):
        self.target.jinxes.append(self)
        print(f"{self.target.name} is trapped with +{self.amount} incoming damage.")
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
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class HoTEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class AuraEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class ChanceEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class CharmEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()
        self.aspect = template["aspect"]
    def resolve(self, game):
        self.target.charms.append(self)
        print(f"{self.target.name} gains a {self.amount}% {self.aspect} blade!")
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "charm", "value": self.to_json()}
    
    def to_json(self):
        return {"type": "charm", "aspect": self.aspect, "school": self.school, "amount": self.amount}

class CurseEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()
        self.aspect = template["aspect"]
    def resolve(self, game):
        self.target.curses.append(self)
        return {"type": "effect_resolve", "player": self.owner.user_id, "target": self.target.user_id, "aspect": "curses", "value": self.to_json()}
    
    def to_json(self):
        return {"type": "curse", "aspect": self.aspect, "school": self.school, "amount": self.amount}

class DestroyEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class DetonateEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class DispelEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class EmpowerEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class ExtendEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class GambitEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class GlobalEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()
        self.aspect = template["aspect"]
        
    def resolve(self, game):
        if game.global_effect:
            print(f"Overriding global effect: {game.global_effect}")
        game.global_effect = self

class PipEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class PrismEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class RepeatEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class ReshuffleEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class StealEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()

class TakeEffect(Effect):
    def __init__(self, template, owner, target, card):
        super().__init__(template, owner, target, card)
        self.amount = self.get_amount()



EFFECT_TYPE_TO_CLASS = {
    "charm": CharmEffect,
    "curse": CurseEffect,
    "ward": WardEffect,
    "jinx": JinxEffect,

    "damage": DamageEffect,
    "heal": HealEffect,

    "DoT": DoTEffect,
    "HoT": HoTEffect,
    "aura": AuraEffect,
    "chance": ChanceEffect,
    
    
    "destroy": DestroyEffect,
    "detonate": DetonateEffect,
    "dispel": DispelEffect,
    "empower": EmpowerEffect,
    "extend": ExtendEffect,
    "gambit": GambitEffect,
    "global": GlobalEffect,
    
    "pip": PipEffect,
    "repeat": RepeatEffect,
    "reshuffle": ReshuffleEffect,
    "steal": StealEffect,
    "take": TakeEffect,
}

