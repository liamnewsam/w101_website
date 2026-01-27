import random
#------------
from Game import *

def build_deck(card_ids):
    return [Card(ALL_CARD_DEFS[cid]) for cid in card_ids]
def random_deck(size):
    return Deck([Card(random.choice(list(ALL_CARD_DEFS))) for _ in range(size)])

def simple_life():
    cards = []
    cards.extend([Card(CARD_BY_ID["imp"]) for _ in range(8)])
    cards.extend([Card(CARD_BY_ID["life_trap"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["life_weakness"]) for _ in range(2)])
    cards.extend([Card(CARD_BY_ID["minor_blessing"]) for _ in range(3)])
    cards.extend([Card(CARD_BY_ID["lifeblade"]) for _ in range(3)])
    #cards.append()
    return Deck(cards)


def main():
    deck_r = random_deck(30)
    
    player1 = Player("ShadowSerpent", "life", simple_life())
    player2 = Player("Firegirl", "fire", simple_life())
    game = Game([player1], [player2])

    #print(deck_r)

    game.begin()
    while not game.ended:
        game.play_round()







if __name__ == "__main__":
    main()