from typing import *
import random

from Card import *
from config import HAND_SIZE


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
    cards.extend([Card(CARD_BY_ID["lifeblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["life_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["minor_blessing"]) for _ in range(2)])   # 0 pip heal
    cards.extend([Card(CARD_BY_ID["imp"]) for _ in range(2)])              # 1 pip
    cards.extend([Card(CARD_BY_ID["leprechaun"]) for _ in range(2)])       # 2 pip
    cards.extend([Card(CARD_BY_ID["nature's_wrath"]) for _ in range(3)])   # 3 pip
    cards.extend([Card(CARD_BY_ID["seraph"]) for _ in range(2)])           # 4 pip
    cards.extend([Card(CARD_BY_ID["centaur"]) for _ in range(2)])          # 6 pip finisher
    return Deck("SimpleLifeDeck", cards)

def contrived_enemy_deck():
    cards = []
    cards.extend([Card(CARD_BY_ID["infection"]) for _ in range(8)])
    return Deck("ContrivedEnemyDeck", cards)



def contrived_player_deck():
    cards = []
    cards.extend([Card(CARD_BY_ID["judgement"]) for _ in range(8)])
    return Deck("ContrivedPlayerDeck", cards)



def simple_storm():
    cards = []
    cards.extend([Card(CARD_BY_ID["stormblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["storm_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["thermic_shield"]) for _ in range(2)])   # 0 pip defense
    cards.extend([Card(CARD_BY_ID["thunder_snake"]) for _ in range(2)])    # 1 pip
    cards.extend([Card(CARD_BY_ID["lightning_bats"]) for _ in range(2)])   # 2 pip
    cards.extend([Card(CARD_BY_ID["storm_shark"]) for _ in range(3)])      # 3 pip
    cards.extend([Card(CARD_BY_ID["kraken"]) for _ in range(2)])           # 4 pip
    cards.extend([Card(CARD_BY_ID["stormzilla"]) for _ in range(2)])       # 5 pip finisher
    return Deck("SimpleStormDeck", cards)

def simple_fire():
    cards = []
    cards.extend([Card(CARD_BY_ID["fireblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["fire_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["fire_cat"]) for _ in range(2)])         # 1 pip
    cards.extend([Card(CARD_BY_ID["fire_elf"]) for _ in range(2)])         # 2 pip DoT
    cards.extend([Card(CARD_BY_ID["sunbird"]) for _ in range(3)])          # 3 pip DoT
    cards.extend([Card(CARD_BY_ID["immolate"]) for _ in range(2)])         # 4 pip
    cards.extend([Card(CARD_BY_ID["phoenix"]) for _ in range(2)])          # 5 pip DoT
    cards.extend([Card(CARD_BY_ID["helephant"]) for _ in range(2)])        # 6 pip finisher
    return Deck("SimpleFireDeck", cards)

def simple_ice():
    cards = []
    cards.extend([Card(CARD_BY_ID["iceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["ice_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["tower_shield"]) for _ in range(2)])     # 0 pip defense
    cards.extend([Card(CARD_BY_ID["frost_beetle"]) for _ in range(2)])     # 1 pip
    cards.extend([Card(CARD_BY_ID["snow_serpent"]) for _ in range(2)])     # 2 pip
    cards.extend([Card(CARD_BY_ID["evil_snowman"]) for _ in range(3)])     # 3 pip
    cards.extend([Card(CARD_BY_ID["ice_wyvern"]) for _ in range(2)])       # 4 pip
    cards.extend([Card(CARD_BY_ID["colossus"]) for _ in range(2)])         # 6 pip finisher
    return Deck("SimpleIceDeck", cards)

def simple_death():
    cards = []
    cards.extend([Card(CARD_BY_ID["deathblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["death_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["infection"]) for _ in range(2)])        # 0 pip debuff healing
    cards.extend([Card(CARD_BY_ID["dark_sprite"]) for _ in range(2)])      # 1 pip
    cards.extend([Card(CARD_BY_ID["ghoul"]) for _ in range(2)])            # 2 pip drain
    cards.extend([Card(CARD_BY_ID["banshee"]) for _ in range(3)])          # 3 pip
    cards.extend([Card(CARD_BY_ID["vampire"]) for _ in range(3)])          # 4 pip drain
    cards.extend([Card(CARD_BY_ID["wraith"]) for _ in range(2)])           # 6 pip drain finisher
    return Deck("SimpleDeathDeck", cards)

def simple_myth():
    cards = []
    cards.extend([Card(CARD_BY_ID["mythblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["myth_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["ether_shield"]) for _ in range(2)])     # 0 pip defense
    cards.extend([Card(CARD_BY_ID["blood_bat"]) for _ in range(2)])        # 1 pip
    cards.extend([Card(CARD_BY_ID["troll"]) for _ in range(2)])            # 2 pip
    cards.extend([Card(CARD_BY_ID["cyclops"]) for _ in range(3)])          # 3 pip
    cards.extend([Card(CARD_BY_ID["minotaur"]) for _ in range(2)])         # 5 pip
    cards.extend([Card(CARD_BY_ID["stone_colossus"]) for _ in range(2)])   # 6 pip finisher
    return Deck("SimpleMythDeck", cards)

def simple_balance():
    cards = []
    cards.extend([Card(CARD_BY_ID["balanceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["hex"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["elemental_trap"]) for _ in range(2)])   # 1 pip secondary traps
    cards.extend([Card(CARD_BY_ID["scarab"]) for _ in range(2)])           # 1 pip
    cards.extend([Card(CARD_BY_ID["scorpion"]) for _ in range(2)])         # 2 pip
    cards.extend([Card(CARD_BY_ID["locust_swarm"]) for _ in range(3)])     # 3 pip
    cards.extend([Card(CARD_BY_ID["judgement"]) for _ in range(3)])        # X pip finisher
    return Deck("SimpleBalanceDeck", cards)


def moderate_life():
    cards = []
    cards.extend([Card(CARD_BY_ID["lifeblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["lifespear"]) for _ in range(4)])       # pvp=80
    cards.extend([Card(CARD_BY_ID["life_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["triage"]) for _ in range(2)])           # 1 pip DoT removal
    cards.extend([Card(CARD_BY_ID["spirit_armor"]) for _ in range(2)])     # 3 pip ward
    cards.extend([Card(CARD_BY_ID["leprechaun"]) for _ in range(2)])       # 2 pip
    cards.extend([Card(CARD_BY_ID["nature's_wrath"]) for _ in range(2)])   # 3 pip
    cards.extend([Card(CARD_BY_ID["seraph"]) for _ in range(2)])           # 4 pip
    cards.extend([Card(CARD_BY_ID["earth_walker"]) for _ in range(2)])     # 5 pip
    cards.extend([Card(CARD_BY_ID["centaur"]) for _ in range(2)])          # 6 pip
    cards.extend([Card(CARD_BY_ID["gnomes!"]) for _ in range(3)])          # 9 pip finisher
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    return Deck("ModerateLifeDeck", cards)

def moderate_storm():
    cards = []
    cards.extend([Card(CARD_BY_ID["stormblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["stormspear"]) for _ in range(4)])       # pvp=80
    cards.extend([Card(CARD_BY_ID["storm_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["windstorm"]) for _ in range(2)])        # 1 pip mass trap
    cards.extend([Card(CARD_BY_ID["thermic_shield"]) for _ in range(2)])   # fire defense
    cards.extend([Card(CARD_BY_ID["lightning_bats"]) for _ in range(2)])   # 2 pip
    cards.extend([Card(CARD_BY_ID["storm_shark"]) for _ in range(2)])      # 3 pip
    cards.extend([Card(CARD_BY_ID["kraken"]) for _ in range(2)])           # 4 pip
    cards.extend([Card(CARD_BY_ID["stormzilla"]) for _ in range(2)])       # 5 pip
    cards.extend([Card(CARD_BY_ID["triton"]) for _ in range(2)])           # 6 pip
    cards.extend([Card(CARD_BY_ID["thundering_jinn"]) for _ in range(2)])  # 7 pip
    cards.extend([Card(CARD_BY_ID["king_artorius_(storm)"]) for _ in range(1)])  # 8 pip
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    return Deck("ModerateStormDeck", cards)

def moderate_myth():
    cards = []
    cards.extend([Card(CARD_BY_ID["mythblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["mythspear"]) for _ in range(4)])        # pvp=80
    cards.extend([Card(CARD_BY_ID["myth_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["pierce"]) for _ in range(2)])           # 0 pip shield removal
    cards.extend([Card(CARD_BY_ID["vaporize"]) for _ in range(2)])         # 2 pip ward removal
    cards.extend([Card(CARD_BY_ID["troll"]) for _ in range(2)])            # 2 pip
    cards.extend([Card(CARD_BY_ID["cyclops"]) for _ in range(2)])          # 3 pip
    cards.extend([Card(CARD_BY_ID["minotaur"]) for _ in range(2)])         # 5 pip
    cards.extend([Card(CARD_BY_ID["stone_colossus"]) for _ in range(2)])   # 6 pip
    cards.extend([Card(CARD_BY_ID["saturn's_reaping"]) for _ in range(2)]) # 7 pip
    cards.extend([Card(CARD_BY_ID["king_artorius_(myth)"]) for _ in range(2)])  # 8 pip
    cards.extend([Card(CARD_BY_ID["phantastic_jinn"]) for _ in range(1)])  # 11 pip finisher
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    return Deck("ModerateMythDeck", cards)

def moderate_fire():
    cards = []
    cards.extend([Card(CARD_BY_ID["fireblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["firespear"]) for _ in range(4)])        # pvp=80
    cards.extend([Card(CARD_BY_ID["fire_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["fire_cat"]) for _ in range(2)])         # 1 pip
    cards.extend([Card(CARD_BY_ID["fire_elf"]) for _ in range(2)])         # 2 pip DoT
    cards.extend([Card(CARD_BY_ID["naphtha_scarab"]) for _ in range(2)])   # 2 pip
    cards.extend([Card(CARD_BY_ID["sunbird"]) for _ in range(2)])          # 3 pip DoT
    cards.extend([Card(CARD_BY_ID["immolate"]) for _ in range(2)])         # 4 pip
    cards.extend([Card(CARD_BY_ID["phoenix"]) for _ in range(2)])          # 5 pip DoT
    cards.extend([Card(CARD_BY_ID["helephant"]) for _ in range(2)])        # 6 pip
    cards.extend([Card(CARD_BY_ID["infernal_oni"]) for _ in range(2)])     # 7 pip
    cards.extend([Card(CARD_BY_ID["caldera_jinn"]) for _ in range(1)])     # 9 pip finisher
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    return Deck("ModerateFireDeck", cards)

def moderate_ice():
    cards = []
    cards.extend([Card(CARD_BY_ID["iceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["icespear"]) for _ in range(4)])         # pvp=80
    cards.extend([Card(CARD_BY_ID["ice_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["tower_shield"]) for _ in range(2)])     # general defense
    cards.extend([Card(CARD_BY_ID["volcanic_shield"]) for _ in range(2)])  # fire defense
    cards.extend([Card(CARD_BY_ID["snow_serpent"]) for _ in range(2)])     # 2 pip
    cards.extend([Card(CARD_BY_ID["evil_snowman"]) for _ in range(2)])     # 3 pip
    cards.extend([Card(CARD_BY_ID["ice_wyvern"]) for _ in range(2)])       # 4 pip
    cards.extend([Card(CARD_BY_ID["blight_hound"]) for _ in range(2)])     # 5 pip
    cards.extend([Card(CARD_BY_ID["colossus"]) for _ in range(2)])         # 6 pip
    cards.extend([Card(CARD_BY_ID["king_artorius_(ice)"]) for _ in range(2)])   # 8 pip
    cards.extend([Card(CARD_BY_ID["iceburn_jinn"]) for _ in range(1)])     # 9 pip finisher
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    return Deck("ModerateIceDeck", cards)

def moderate_death():
    cards = []
    cards.extend([Card(CARD_BY_ID["deathblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["deathspear"]) for _ in range(4)])       # pvp=80
    cards.extend([Card(CARD_BY_ID["death_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["infection"]) for _ in range(2)])        # healing debuff
    cards.extend([Card(CARD_BY_ID["empower"]) for _ in range(2)])          # 0 pip pip gain
    cards.extend([Card(CARD_BY_ID["dark_sprite"]) for _ in range(2)])      # 1 pip
    cards.extend([Card(CARD_BY_ID["ghoul"]) for _ in range(2)])            # 2 pip drain
    cards.extend([Card(CARD_BY_ID["banshee"]) for _ in range(2)])          # 3 pip
    cards.extend([Card(CARD_BY_ID["vampire"]) for _ in range(2)])          # 4 pip drain
    cards.extend([Card(CARD_BY_ID["skeletal_pirate"]) for _ in range(2)])  # 5 pip
    cards.extend([Card(CARD_BY_ID["wraith"]) for _ in range(2)])           # 6 pip drain
    cards.extend([Card(CARD_BY_ID["macabre_jinn"]) for _ in range(1)])     # 9 pip finisher
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    return Deck("ModerateDeathDeck", cards)

'''
def moderate_balance():
    cards = []
    cards.extend([Card(CARD_BY_ID["balanceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["hex"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["spirit_blade"]) for _ in range(2)])     # 1 pip multi-school blade
    cards.extend([Card(CARD_BY_ID["elemental_blade"]) for _ in range(2)])  # 1 pip multi-school blade
    cards.extend([Card(CARD_BY_ID["elemental_trap"]) for _ in range(2)])   # 1 pip secondary trap
    cards.extend([Card(CARD_BY_ID["scarab"]) for _ in range(2)])           # 1 pip
    cards.extend([Card(CARD_BY_ID["scorpion"]) for _ in range(2)])         # 2 pip
    cards.extend([Card(CARD_BY_ID["locust_swarm"]) for _ in range(2)])     # 3 pip
    cards.extend([Card(CARD_BY_ID["spinning_scythe"]) for _ in range(2)])  # 5 pip
    cards.extend([Card(CARD_BY_ID["obsidian_colossus"]) for _ in range(2)])# 6 pip
    cards.extend([Card(CARD_BY_ID["terminus'_strike"]) for _ in range(2)]) # 8 pip
    cards.extend([Card(CARD_BY_ID["chimera"]) for _ in range(2)])          # 9 pip
    cards.extend([Card(CARD_BY_ID["duststorm_jinn"]) for _ in range(1)])   # 9 pip finisher
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    return Deck("ModerateBalanceDeck", cards)
'''
def moderate_balance():
    cards = []
    cards.extend([Card(CARD_BY_ID["reshuffle"]) for _ in range(1)])
    cards.extend([Card(CARD_BY_ID["availing_hands"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["balance_of_power"]) for _ in range(1)])
    cards.extend([Card(CARD_BY_ID["balanceblade"]) for _ in range(3)])     # 1 pip multi-school blade
    cards.extend([Card(CARD_BY_ID["locust_swarm"]) for _ in range(2)])  # 1 pip multi-school blade
    cards.extend([Card(CARD_BY_ID["hex"]) for _ in range(2)])   # 1 pip secondary trap
    cards.extend([Card(CARD_BY_ID["spirit_shield"]) for _ in range(2)])           # 1 pip
    cards.extend([Card(CARD_BY_ID["elemental_shield"]) for _ in range(2)])         # 2 pip
    cards.extend([Card(CARD_BY_ID["dyvim's_resurgence"]) for _ in range(2)])     # 3 pip
    cards.extend([Card(CARD_BY_ID["chimera"]) for _ in range(3)])  # 5 pip
    cards.extend([Card(CARD_BY_ID["spirit_blade"]) for _ in range(2)])# 6 pip
    cards.extend([Card(CARD_BY_ID["spirit_trap"]) for _ in range(2)]) # 8 pip
    cards.extend([Card(CARD_BY_ID["samoorai"]) for _ in range(2)])          # 9 pip
    cards.extend([Card(CARD_BY_ID["savage_paw"]) for _ in range(2)])   # 9 pip finisher
    
    return Deck("ModerateBalanceDeck", cards)

def hard_life():
    cards = []
    cards.extend([Card(CARD_BY_ID["lifeblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["lifespear"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["life_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["minor_blessing"]) for _ in range(2)])   # 0 pip heal
    cards.extend([Card(CARD_BY_ID["imp"]) for _ in range(2)])              # 1 pip
    cards.extend([Card(CARD_BY_ID["leprechaun"]) for _ in range(2)])       # 2 pip
    cards.extend([Card(CARD_BY_ID["nature's_wrath"]) for _ in range(2)])   # 3 pip
    cards.extend([Card(CARD_BY_ID["seraph"]) for _ in range(2)])           # 4 pip
    cards.extend([Card(CARD_BY_ID["hunting_wyrm"]) for _ in range(2)])     # 5 pip
    cards.extend([Card(CARD_BY_ID["centaur"]) for _ in range(2)])          # 6 pip
    cards.extend([Card(CARD_BY_ID["phoebus'_will"]) for _ in range(2)])    # 8 pip
    cards.extend([Card(CARD_BY_ID["gnomes!"]) for _ in range(2)])          # 9 pip
    return Deck("HardLifeDeck", cards)

def hard_storm():
    cards = []
    cards.extend([Card(CARD_BY_ID["stormblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["stormspear"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["storm_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["windstorm"]) for _ in range(2)])        # 1 pip mass trap
    cards.extend([Card(CARD_BY_ID["thermic_shield"]) for _ in range(2)])   # fire defense
    cards.extend([Card(CARD_BY_ID["lightning_bats"]) for _ in range(2)])   # 2 pip
    cards.extend([Card(CARD_BY_ID["storm_shark"]) for _ in range(2)])      # 3 pip
    cards.extend([Card(CARD_BY_ID["kraken"]) for _ in range(2)])           # 4 pip
    cards.extend([Card(CARD_BY_ID["triton"]) for _ in range(2)])           # 6 pip
    cards.extend([Card(CARD_BY_ID["heqet"]) for _ in range(2)])            # 7 pip
    cards.extend([Card(CARD_BY_ID["turmoil_oni"]) for _ in range(2)])      # 9 pip
    cards.extend([Card(CARD_BY_ID["the_tower"]) for _ in range(2)])        # 10 pip
    return Deck("HardStormDeck", cards)

def hard_myth():
    cards = []
    cards.extend([Card(CARD_BY_ID["mythblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["mythspear"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["myth_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["pierce"]) for _ in range(2)])           # 0 pip shield removal
    cards.extend([Card(CARD_BY_ID["blood_bat"]) for _ in range(2)])        # 1 pip
    cards.extend([Card(CARD_BY_ID["troll"]) for _ in range(2)])            # 2 pip
    cards.extend([Card(CARD_BY_ID["cyclops"]) for _ in range(2)])          # 3 pip
    cards.extend([Card(CARD_BY_ID["minotaur"]) for _ in range(2)])         # 5 pip
    cards.extend([Card(CARD_BY_ID["stone_colossus"]) for _ in range(2)])   # 6 pip
    cards.extend([Card(CARD_BY_ID["thoth"]) for _ in range(2)])            # 7 pip
    cards.extend([Card(CARD_BY_ID["the_emperor"]) for _ in range(2)])      # 10 pip
    cards.extend([Card(CARD_BY_ID["phantastic_jinn"]) for _ in range(2)])  # 11 pip
    return Deck("HardMythDeck", cards)

def hard_fire():
    cards = []
    cards.extend([Card(CARD_BY_ID["fireblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["firespear"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["fire_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["fire_cat"]) for _ in range(2)])         # 1 pip
    cards.extend([Card(CARD_BY_ID["fire_elf"]) for _ in range(2)])         # 2 pip DoT
    cards.extend([Card(CARD_BY_ID["sunbird"]) for _ in range(2)])          # 3 pip DoT
    cards.extend([Card(CARD_BY_ID["immolate"]) for _ in range(2)])         # 4 pip
    cards.extend([Card(CARD_BY_ID["phoenix"]) for _ in range(2)])          # 5 pip DoT
    cards.extend([Card(CARD_BY_ID["helephant"]) for _ in range(2)])        # 6 pip
    cards.extend([Card(CARD_BY_ID["ammut"]) for _ in range(2)])            # 7 pip
    cards.extend([Card(CARD_BY_ID["fires_of_mars"]) for _ in range(2)])    # 8 pip
    cards.extend([Card(CARD_BY_ID["the_chariot"]) for _ in range(2)])      # 10 pip
    return Deck("HardFireDeck", cards)

def hard_ice():
    cards = []
    cards.extend([Card(CARD_BY_ID["iceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["icespear"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["ice_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["tower_shield"]) for _ in range(2)])     # general defense
    cards.extend([Card(CARD_BY_ID["volcanic_shield"]) for _ in range(2)])  # fire defense
    cards.extend([Card(CARD_BY_ID["evil_snowman"]) for _ in range(2)])     # 3 pip
    cards.extend([Card(CARD_BY_ID["ice_wyvern"]) for _ in range(2)])       # 4 pip
    cards.extend([Card(CARD_BY_ID["blight_hound"]) for _ in range(2)])     # 5 pip
    cards.extend([Card(CARD_BY_ID["colossus"]) for _ in range(2)])         # 6 pip
    cards.extend([Card(CARD_BY_ID["shu"]) for _ in range(2)])              # 7 pip
    cards.extend([Card(CARD_BY_ID["neptune's_fury"]) for _ in range(2)])   # 9 pip
    cards.extend([Card(CARD_BY_ID["the_hierophant"]) for _ in range(2)])   # 10 pip
    return Deck("HardIceDeck", cards)

def hard_death():
    cards = []
    cards.extend([Card(CARD_BY_ID["deathblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["deathspear"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["death_trap"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["infection"]) for _ in range(2)])        # 0 pip healing debuff
    cards.extend([Card(CARD_BY_ID["dark_sprite"]) for _ in range(2)])      # 1 pip
    cards.extend([Card(CARD_BY_ID["ghoul"]) for _ in range(2)])            # 2 pip drain
    cards.extend([Card(CARD_BY_ID["banshee"]) for _ in range(2)])          # 3 pip
    cards.extend([Card(CARD_BY_ID["vampire"]) for _ in range(2)])          # 4 pip drain
    cards.extend([Card(CARD_BY_ID["wraith"]) for _ in range(2)])           # 6 pip drain
    cards.extend([Card(CARD_BY_ID["anubis"]) for _ in range(2)])           # 7 pip
    cards.extend([Card(CARD_BY_ID["dr._von's_monster"]) for _ in range(2)])# 9 pip drain
    cards.extend([Card(CARD_BY_ID["doom_oni"]) for _ in range(2)])         # 11 pip
    return Deck("HardDeathDeck", cards)

def hard_balance():
    cards = []
    cards.extend([Card(CARD_BY_ID["balanceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["hex"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["bladestorm"]) for _ in range(2)])       # 1 pip secondary blade
    cards.extend([Card(CARD_BY_ID["elemental_trap"]) for _ in range(2)])   # 1 pip secondary trap
    cards.extend([Card(CARD_BY_ID["scarab"]) for _ in range(2)])           # 1 pip
    cards.extend([Card(CARD_BY_ID["scorpion"]) for _ in range(2)])         # 2 pip
    cards.extend([Card(CARD_BY_ID["locust_swarm"]) for _ in range(2)])     # 3 pip
    cards.extend([Card(CARD_BY_ID["obsidian_colossus"]) for _ in range(2)])# 6 pip
    cards.extend([Card(CARD_BY_ID["chameleon_clash"]) for _ in range(2)])  # 7 pip
    cards.extend([Card(CARD_BY_ID["terminus'_strike"]) for _ in range(2)])  # 8 pip
    cards.extend([Card(CARD_BY_ID["chimera"]) for _ in range(2)])          # 9 pip
    cards.extend([Card(CARD_BY_ID["wheel_of_fortune"]) for _ in range(4)]) # 10 pip
    return Deck("HardBalanceDeck", cards)


def starter_life():
    cards = []
    cards.extend([Card(CARD_BY_ID["lifeblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["life_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["minor_blessing"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["imp"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["leprechaun"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["nature's_wrath"]) for _ in range(4)])
    return Deck("StarterLifeDeck", cards)

def starter_storm():
    cards = []
    cards.extend([Card(CARD_BY_ID["stormblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["storm_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["thermic_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["thunder_snake"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["lightning_bats"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["storm_shark"]) for _ in range(4)])
    return Deck("StarterStormDeck", cards)

def starter_myth():
    cards = []
    cards.extend([Card(CARD_BY_ID["mythblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["myth_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["ether_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["blood_bat"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["troll"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["cyclops"]) for _ in range(4)])
    return Deck("StarterMythDeck", cards)

def starter_fire():
    cards = []
    cards.extend([Card(CARD_BY_ID["fireblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["fire_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["fire_cat"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["fire_elf"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["link"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["sunbird"]) for _ in range(4)])
    return Deck("StarterFireDeck", cards)

def starter_ice():
    cards = []
    cards.extend([Card(CARD_BY_ID["iceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["ice_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["tower_shield"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["frost_beetle"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["snow_serpent"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["evil_snowman"]) for _ in range(4)])
    return Deck("StarterIceDeck", cards)

def starter_death():
    cards = []
    cards.extend([Card(CARD_BY_ID["deathblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["death_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["infection"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["dark_sprite"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["ghoul"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["banshee"]) for _ in range(4)])
    return Deck("StarterDeathDeck", cards)

def starter_balance():
    cards = []
    cards.extend([Card(CARD_BY_ID["balanceblade"]) for _ in range(4)])
    cards.extend([Card(CARD_BY_ID["hex"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["elemental_trap"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["scarab"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["scorpion"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["locust_swarm"]) for _ in range(4)])
    return Deck("StarterBalanceDeck", cards)


SCHOOL_DECK_ORDER = ["Life", "Storm", "Myth", "Fire", "Ice", "Death", "Balance"]

DECK_MASTER = {
    "moderate": {
        "Life": moderate_life,
        "Storm": moderate_storm,
        "Myth": moderate_myth,
        "Fire": moderate_fire,
        "Ice": moderate_ice,
        "Death": moderate_death,
        "Balance": moderate_balance,
    },
    "hard": {
        "Life": hard_life,
        "Storm": hard_storm,
        "Myth": hard_myth,
        "Fire": hard_fire,
        "Ice": hard_ice,
        "Death": hard_death,
        "Balance": hard_balance,
    },
    "starter": {
        "Life": starter_life,
        "Storm": starter_storm,
        "Myth": starter_myth,
        "Fire": starter_fire,
        "Ice": starter_ice,
        "Death": starter_death,
        "Balance": starter_balance,
    },
    "easy": {
        "Life": simple_life,
        "Storm": simple_storm,
        "Myth": simple_myth,
        "Fire": simple_fire,
        "Ice": simple_ice,
        "Death": simple_death,
        "Balance": simple_balance,
    },
}


def new_player_state():
    """Return (decks, school, selected_deck_index) for a freshly created player.

    All 7 school decks are included. School and its matching deck are chosen randomly.
    """
    school_funcs = DECK_MASTER["starter"]
    decks = [school_funcs[s]().to_dict() for s in SCHOOL_DECK_ORDER]
    school = random.choice(SCHOOL_DECK_ORDER)
    selected_deck_index = SCHOOL_DECK_ORDER.index(school)
    return decks, school, selected_deck_index


