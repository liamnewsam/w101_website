
import textwrap
from typing import *
#------------

import json

class CardDef:
    def __init__(self, id, name, school, description, type, pips, effects, accuracy, pvp_level, reshuffle, condition, img_path):
        self.id = id              # unique internal ID
        self.name = name
        self.school = school      # enum or string
        self.description = description
        self.pips = pips
        self.type = type        # damage, manipulation, 
        self.accuracy = accuracy
        self.pvp_level = pvp_level
        self.effects = effects    # list of effect definitions
        self.reshuffle = reshuffle
        self.condition = condition
        self.img_path = img_path
    def __str__(self):
        return self.name

all_card_key_types = set()
def load_cards(path, conditions=[]):
    with open(path, "r") as f:
        data = json.load(f)   # <-- this becomes a Python list
    cards = []
    for card in data:
        for condition in conditions:
            if not condition(card):
                break
        else:
            all_card_key_types.update(card.keys())

            cards.append(CardDef(
                card["id"],
                card["name"],
                card["school"],
                card["description"],
                card["type"],
                card["pips"],
                card["effects"], 
                card["accuracy"],
                card.get("pvp_level", 0),
                card.get("reshuffle", True),
                card.get("condition", None),
                card["image"]
            ))
    return cards
    
no_minion = lambda card: "minion" not in card["description"].lower()

CARD_BY_ID = {}
SCHOOLS = ["life", "death", "myth", "balance", "storm", "ice", "fire"]
CARDS_BY_SCHOOL = {}
ALL_CARD_DEFS = []
CARD_PATH = "static/w101/spells/spell_data/"
for school in SCHOOLS:
    cards = load_cards(CARD_PATH + school + ".json", [no_minion])
    CARDS_BY_SCHOOL[school] = cards
    ALL_CARD_DEFS += cards

    for card in cards:
        CARD_BY_ID[card.id] = card


print(f"# of Cards: {len(ALL_CARD_DEFS)}")


#print(f"All card keys: {all_card_key_types}")

effect_types = set()
all_types = set()
cards_with_repeat = []
for card in ALL_CARD_DEFS:
    effect_types.update([effect["type"] for effect in card.effects])
    for effect in card.effects:
        all_types.update(effect.keys())
        if effect["type"] == "clear":
            print(f"[{card.school.upper()}] {card.name}: {card.description}\n")

print(f"Types of effects: {sorted(effect_types)}")
#print(f"All effect types: {all_types}")

#print(f"reshuffle: ", CARDS_BY_ID["reshuffle"])

for card in cards_with_repeat:
    print(f"[{card.school.upper()}] {card.name}")

for card in ALL_CARD_DEFS:
    if not card.effects:
        print(f"[{card.school.upper()}] {card.name}: {card.description}\n")


class Card():
    def __init__(self, card_def):
        self.card_def = card_def

    def __str__(self):
        return str(self.card_def)
    
    def targets(self):
        return set([effect["target"] for effect in self.card_def.effects])
    
    def hasEffect(self, effects):
        for effect in self.card_def.effects:
            for e in effects:
                if effect["type"] == e:
                    return True
        return False


#[card.card_def for card in cards]
def fancy_print_hand(cards, width=24):
    """
    Returns a string representing cards printed side-by-side.
    Handles large text (wraps) and correct alignment for numbered prefixes.
    """
    card_blocks = []
    prefix_width = 4  # enough space for "999."

    for idx, card in enumerate([card.card_def for card in cards], start=1):
        # Format prefix so numbers never shift alignment
        prefix = f"{idx}.".ljust(prefix_width)

        top = f"{prefix}+{'-' * width}+"

        def line(label, value):
            text = f"{label}{value}"
            return f"{' ' * prefix_width}| {text:<{width-2}} |"

        body = [
            f"{' ' * prefix_width}| {card.name:<{width-2}} |",
            line("School: ", str(card.school)),
            line("Cost: ", f"{card.pips} pips"),
            line("Type: ", str(card.type)),
            f"{' ' * prefix_width}|{'-' * width}|",
        ]

        # Wrap description
        import textwrap
        desc_lines = textwrap.wrap(card.description, width - 2)
        desc_block = [
            f"{' ' * prefix_width}| {line:<{width-2}} |"
            for line in desc_lines
        ]

        bottom = f"{' ' * prefix_width}+{'-' * width}+"

        block = [top] + body + desc_block + [bottom]
        card_blocks.append(block)

    # Normalize card height
    max_height = max(len(block) for block in card_blocks)
    for b in card_blocks:
        while len(b) < max_height:
            b.insert(-1, f"{' ' * prefix_width}| {' ' * (width-2)} |")

    # Combine side-by-side
    rows = []
    for r in range(max_height):
        rows.append("   ".join(block[r] for block in card_blocks))

    return "\n".join(rows)

def fancy_print_card(card, width=24):
    """
    Returns a string representing a single card in the same
    style as fancy_print(), without numbering.
    """
    card = card.card_def
    # Helper to format key/value fields to fixed width
    def line(label, value):
        text = f"{label}{value}"
        return f"| {text:<{width-2}} |"

    top = f"+{'-' * width}+"

    body = [
        f"| {card.name:<{width-2}} |",
        line("School: ", str(card.school)),
        line("Cost: ", f"{card.pips} pips"),
        line("Type: ", str(card.type)),
        f"|{'-' * width}|",
    ]

    # Wrap description to card width
    desc_lines = textwrap.wrap(card.description, width - 2)
    desc_block = [f"| {line:<{width-2}} |" for line in desc_lines]

    bottom = f"+{'-' * width}+"

    # Join everything
    return "\n".join([top] + body + desc_block + [bottom])
