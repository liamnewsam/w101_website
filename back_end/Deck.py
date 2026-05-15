from typing import *
import random

from Card import *

HAND_SIZE = 5

class Deck():
    def __init__(self, name, cards):
        self.name = name
        self.cards = cards
        self.play_cards = None
        self.play_hand = None
        self.play_discard = []
    
    def refresh(self):
        self.play_cards = self.cards[:]
        self.play_hand = []
        random.shuffle(self.play_cards)
        #self.draw_cards()

    def draw_cards(self):
        while len(self.play_hand) < HAND_SIZE and len(self.play_cards) != 0:
            self.play_hand.append(self.play_cards.pop())

        if len(self.play_cards) == 0:
            print("No more cards available!")

    def __str__(self):
        cards = [f"{i+1}. {self.cards[i]}" for i in range(len(self.cards))]
        #hand = [f"{i+1}. {self.hand[i]}" for i in range(len(self.hand))]

        s = 'Deck:\n' + '\n'.join(cards) #+ '\nHand:\n' + '\n'.join(hand)
        return s
    
    def str_hand(self):
        hand = [f"{i+1}. {self.play_hand[i]}" for i in range(len(self.play_hand))]
        return '\nHand:\n' + '\n'.join(hand)

    def to_dict(self):
        return {
            "name": self.name,
            "card_ids": [card.card_def.id for card in self.cards]
        }


def simple_life():
    cards = []
    cards.extend([Card(CARD_BY_ID["imp"]) for _ in range(8)])
    cards.extend([Card(CARD_BY_ID["life_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["life_weakness"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["minor_blessing"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["lifeblade"]) for _ in range(8)])
    #cards.append()
    return Deck("SimpleLifeDeck", cards)

def circular_arrow():
    cards = []
    cards.extend([Card(CARD_BY_ID["lifeblade"]) for _ in range(10)])
    #cards.append()
    return Deck("CircularArrow", cards)


def simple_storm():
    cards = []
    cards.extend([Card(CARD_BY_ID["thunder_snake"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["stormblade"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["thermic_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["lightning_bats"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["storm_shark"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["storm_trap"]) for _ in range(3)])
    return Deck("SimpleStormDeck", cards)

def simple_fire():
    cards = []
    cards.extend([Card(CARD_BY_ID["fire_cat"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["fire_elf"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["glacial_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["sunbird"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["fire_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["fire_weakness"]) for _ in range(3)])
    return Deck("SimpleStormDeck", cards)

def simple_ice():
    cards = []
    cards.extend([Card(CARD_BY_ID["frost_beetle"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["snow_serpent"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["volcanic_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["evil_snowman"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["tower_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["ice_trap"]) for _ in range(2)])
    return Deck("SimpleStormDeck", cards)

def simple_death():
    cards = []
    cards.extend([Card(CARD_BY_ID["dark_sprite"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["ghoul"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["dream_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["banshee"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["vampire"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["infection"]) for _ in range(3)])
    return Deck("SimpleStormDeck", cards)

def simple_myth():
    cards = []
    cards.extend([Card(CARD_BY_ID["blood_bat"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["troll"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["myth_trap"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["cyclops"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["ether_shield"]) for _ in range(3)])
    return Deck("SimpleStormDeck", cards)

def simple_balance():
    cards = []
    cards.extend([Card(CARD_BY_ID["scarab"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["scorpion"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["weakness"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["locust_swarm"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["elemental_trap"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["elemental_shield"]) for _ in range(2)])
    return Deck("SimpleStormDeck", cards)


DECK_MASTER = {
    "easy": {
        "Life": simple_life,
        "Storm": simple_storm,
        "Myth": simple_myth,
        "Fire": simple_fire,
        "Ice": simple_ice,
        "Death": simple_death,
        "Balance": simple_balance
    }
}