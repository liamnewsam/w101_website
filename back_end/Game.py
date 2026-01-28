from typing import *
import random
#--------------
from Player import *
from Card import *
from Deck import *
from utils import *

def createBotPlayer(name, bot_id, image_path, school="random", deck=None, difficulty="easy"):
    if school=="random":
        school = random.choice(["Life", "Storm"])
        deck = DECK_MASTER[difficulty][school]()
    
    return Player(name, bot_id, school, deck, isBot=True, img_path=image_path)


def neededTargetType(card_def):
    if card_def.condition:
        return card_def["target"]

    all_targets = set([effect["target"] for effect in card_def.effects if "target" in effect.keys()])

    if "enemy" in all_targets:
        return "enemy"
    if "ally" in all_targets:
        return "ally"
    if "enemy_selected" in all_targets:
        return "enemy_selected"
    if "ally_selected" in all_targets:
        return "ally_selected"
    
    if "self" in all_targets or "enemy_all" in all_targets or "ally_all" in all_targets:
        return None
    
    all_effect_types = set([effect["type"] for effect in card_def.effects])
    #Defaulting
    if {"damage", "jinx"} & all_effect_types:
        return "enemy"
    if card_def.type == "heal":
        return "ally"

def getEffectTargetType(effect):
    if "target" in effect.keys():
        print(effect["target"])
        return effect["target"]
    
    #Defaulting
    if effect["type"] in ["damage", "jinx"]:
        return "enemy"

class Game():
    def __init__(self, teamA: List[Player], teamB: List[Player]):
        self.teams = [teamA, teamB]
        self.playability = {player.user_id: [] for player in teamA + teamB}
        #self.new_players = [[], []]
        self.player_actions = {player.user_id: None for player in teamA + teamB}
        self.playing_team_i = 0
        self.playing_team_ready = False
        self.global_effect = None
        self.turns = 0
        self.winner = None

        self.log = []
    
    def getPlayers(self, includeBots=True):
        players = self.teams[0] + self.teams[1]
        if not includeBots:
            players = list(filter(lambda p: not p.isBot, players))

        return players
    
    def isAllBots(self, teamIndex):
        return all([player.isBot for player in self.teams[teamIndex]])

    def start_turn(self):
        log = []
        self.turns += 1

        self.playing_team_i = (self.playing_team_i + 1) % 2


        for player in self.teams[0] + self.teams[1]:
            player.deck.draw_cards()

        for player in self.current_team():
            log.append(player.receive_pip())
        
        self.update_playability()

        self.player_actions = {player.user_id: None for player in self.getPlayers()}

        for player in self.current_team():
            if player.isBot: #Immediately do a random action
                self.takeRandomAction(player)

        return log
    
    def takeRandomAction(self, player):
        playable_indices = [i for i, option in enumerate(self.playability[player.user_id]) if option["playable"]]
        cardIndex = random.choice(playable_indices)
        target = None
        if self.playability[player.user_id][cardIndex]["targets"]:
            target = random.choice(self.playability[player.user_id][cardIndex]["targets"]).user_id
        self.player_cast(player, cardIndex, target)

    def begin(self):
        for team in self.teams:
            for player in team:
                player.refresh()

        self.playing_team_i = 1

        self.start_turn()


        

    def get_player(self, user_id):
        for player in self.teams[0] + self.teams[1]:
            if player.user_id == user_id:
                return player
        
        return None
    
    def get_player_by_name(self, name):
        for player in self.teams[0] + self.teams[1]:
            if player.name == name:
                return player
        
        return None
    

    def allActionsReceived(self):
        print(self.player_actions)
        for player in self.current_team():
            if self.player_actions[player.user_id] == None:
                return False
        return True

    def player_discard(self, player, i):
        if i >= 0 and i < len(player.deck.play_hand):
            card = player.deck.play_hand.pop(i)
            self.log.append({"type": "action", "player": player.user_id, "action": "discard", "cardIndex": i})
            player.deck.play_discard.append(card)

            self.playability[player.user_id].pop(0)
            return True
        
        print("[error] Error in discarding")
        return False
    
    def player_pass(self, player):
        self.player_actions[player.user_id] = {"type": "pass"}
        
        return True

    def player_cast(self, player, i, target):
        if player not in self.current_team():
            print("[invalid] Player action not valid")
            return False
        
        if i<0 or i>= len(player.deck.play_hand):
            print("[invalid] Hand index out of range")
            return False
        
        if not self.is_playable(player, player.deck.play_hand[i]):
            print("[invalid] Cannot play card")
            return False
        
        '''
        If the target is not a valid target, then return false
        '''

        self.player_actions[player.user_id] = {"type": "cast", "index": i, "target": self.get_player(target)}

        

        return True


    def resolve_actions(self):
        log = []
        for player in self.current_team():
            log.append({"type": "action", "player": player.user_id, "action": "activate"})

            action = self.player_actions[player.user_id]
            if action["type"] == "pass":
                log.append({"type": "action", "player": player.user_id, "action": "pass"})
                continue
            
            #Otherwise, the player is casting a card
            card_index = action["index"]
            card = player.deck.play_hand[card_index]
            log.append({"type": "action", "player": player.user_id, "action": "attempt_cast", "school": card.card_def.school})

            if player.consume_dispel(card):
                log.append({"type": "result", "player": player.user_id, "result": "dispel"})
                player.deduct_pips(card)
                player.deck.play_hand.pop(card_index)
                player.deck.play_discard.append(card)
                continue


            
            extra_accuracy = player.consume_accuracy(card)

            if extra_accuracy:
                log.append({"type": "effect_resolve", "player": player.user_id, "aspect": "accuracy", "amount": extra_accuracy})
            
            if random.randint(1, 100) > card.card_def.accuracy + extra_accuracy:
                print(card.card_def.accuracy)
                print(extra_accuracy)
                log.append({"type": "result", "player": player.user_id, "result": "fizzle"})
                player.deck.play_hand.pop(card_index)
                player.deck.play_cards.insert(random.randint(0, len(player.deck.play_cards)), card)
                continue
            
            log.append({"type": "effect_resolve", "player": player.user_id, "aspect": "pip_lose", "amount": player.deduct_pips(card)})
            log.append({"type": "result", "player": player.user_id, "result": "success", "card": card.card_def.id})
            

            caster_accumulation = {
                    "damage": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "armor_piercing": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "health": {"in": 0, "out": 0}
            }
            
            
            for charm in player.consume("charm", card, caster_accumulation):
                log.append({"type": "effect_trigger", "player": player.user_id, "aspect": "charm", "value": charm.to_json()})
            for curse in player.consume("curse", card, caster_accumulation):
                log.append({"type": "effect_trigger", "player": player.user_id, "aspect": "curse", "value": curse.to_json()})
            
            '''
            if card.card_def.target == "enemy_all":
                pass
            '''

            target_accumulation = {
                    "damage": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "armor_piercing": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "health": {"in": 0, "out": 0}
            }
            
            for jinx in action["target"].consume("jinx", card, target_accumulation):
                log.append({"type": "effect_trigger", "player": action["target"].user_id, "aspect": "jinx", "value": jinx.to_json()})
            for ward in action["target"].consume("ward", card, target_accumulation):
                log.append({"type": "effect_trigger", "player": action["target"].user_id, "aspect": "ward", "value": ward.to_json()})

            for effect in card.card_def.effects:
                critical_multiplier = 1

                if effect["type"] in (["damage", "DoT", "heal", "HoT"]):
                    if random.randint(0, 99) < player.critical[card.card_def.school]: 
                        log.append({"type": "effect_resolve", "player": player.user_id, "aspect": "critical"})
                        critical_multiplier = 2
                
                log.append(self.resolve_action(card, player, action["target"], effect, caster_accumulation, target_accumulation, critical_multiplier))


            player.deck.play_hand.pop(card_index)
            player.deck.play_discard.append(card)
        
        for message in log:
            print(message)
            print('\n\n')
        self.log.extend(log)

        if self.check_end():
            self.log.append(f"TEAM {self.winner} WINS")

        return log

    def is_playable(self, player, card):
        test = player.pips.copy()
        player_school = player.school
        card_school = card.card_def.school
        required_pips = card.card_def.pips
        school_aligned = player_school == card_school
        if type(required_pips) == dict:
            for school in [x for x in required_pips.keys() if x != "regular"]:
                test[school] -= required_pips[school]
        else:
            required_pips = {"regular": card.card_def.pips}    
        total_regular = 0
        for key, value in test.items():
            if value < 0:
                return False
            
            total_regular += value*(2 if school_aligned and key != "regular" else 1)
        
        if total_regular < required_pips["regular"]:
            return False

        if card.card_def.condition == None:
            return True

    
    def interpretTarget(self, player, targetType):
        if targetType == "enemy":
            return self.opposite_team()
        if targetType == "ally":
            return self.current_team()
        if targetType == "self":
            return [player]
    
    def opposite_team(self, aliveOnly=False):
        if aliveOnly:
            return [player for player in self.teams[(self.playing_team_i+1) % len(self.teams)] if player.health > 0]
        return self.teams[(self.playing_team_i+1) % len(self.teams)]
    
    def current_team(self, aliveOnly=False):
        if aliveOnly:
            return [player for player in self.teams[self.playing_team_i] if player.health > 0]
        return self.teams[self.playing_team_i]
    
    def conditionMet(self, player, condition, target):
        if not condition:
            return True
        if condition["type"] == "amount":
            if target.hasAspectAmount(condition["aspect"], condition["amount"]):
                return True
        
        return False
    
    def update_playability(self):
        for player in self.opposite_team():
            self.playability[player.user_id] = [{"card": card, "playable": False} for card in player.deck.play_hand]
        
        for player in self.current_team():
            player_playability = []
            for card in player.deck.play_hand:
                if self.is_playable(player, card):
                    valid_targets = []
                    targetType = neededTargetType(card.card_def)
                    if targetType == None:
                        player_playability.append({"card": card, "playable": True, "targets": []})
                        continue
                    for target in self.interpretTarget(player, targetType):
                        if self.conditionMet(player, card.card_def.condition, target):
                            valid_targets.append(target)
                    
                    if valid_targets:
                        player_playability.append({"card": card, "playable": True, "targets": valid_targets})
                    else:
                        player_playability.append({"card": card, "playable": False})
                else:
                    player_playability.append({"card": card, "playable": False})
            
            self.playability[player.user_id] = player_playability
        
        

    def resolve_action(self, card: Card, caster: Player, target: Player, effect: dict, caster_accumulation, target_accumulation, critical_multiplier):

        effect = EFFECT_TYPE_TO_CLASS[effect["type"]](effect, caster, target, card)
        if type(effect) in [DamageEffect, HealEffect, DoTEffect, HoTEffect]:
            result = effect.resolve(self, caster_accumulation, target_accumulation, critical_multiplier)
        else:
            result = effect.resolve(self)
        return result

    def struggle_punish(self, player):
        if len(player.deck.play_cards) == 0 and len(self.playable_cards(player)) == 0:
            player.health -= 10 * player.struggle_counter
            player.struggle_counter += 1

    def process_ongoing_effects(self, player):

        #Process DoTs
        remaining = []
        for dot in player.dots:
            alive = dot.tick(self)
            if alive:
                remaining.append(dot)
            else:
                print(f"{dot.type} on {player.name} expired.")
        player.dots = remaining

        #Process HoTs
        remaining = []
        for hot in player.hots:
            alive = hot.tick(self)
            if alive:
                remaining.append(hot)
            else:
                print(f"{hot.type} on {player.name} expired.")
        player.hot = remaining

    def check_end(self):
        for player in self.teams[0]:
            if player.health > 0:
                break
        else:
            self.winner = "A"
            return True
        
        for player in self.teams[1]:
            if player.health > 0:
                break
        else:
            self.winner = "B"
            return True
        
        return False
    
    def print_log(self):
        for message in self.log:
            print(message)
            

    def to_json_public(self):
        return {
            "teams": [
                [player.to_json_public() for player in self.teams[0]], 
                [player.to_json_public() for player in self.teams[1]]
                ],
            "playing_team": self.playing_team_i,
            "global_effect": None,
            "turns": self.turns,
            "winner": self.winner,
        }

    def __str__(self):
        s = ''
        for team_name, team in zip(["Team A", "Team B"], self.teams):
            s += team_name + ":\n"
            for player in team:
                s += f"\t{player.name}:\n"
                s += f"\t\tHealth: {player.health}\n"
                s += f"\t\tMana: {player.mana}\n"
                s += f"\t\tSchool: {player.school}\n"
                s += f"\t\tPips: {player.pips}\n"
                s += f"\t\tShields: {player.shields}\n"
                s += f"\t\tCharms: {player.charms}\n"
                s += f"\t\tTraps: {player.traps}\n"
                s += f"\t\tDoTs: {player.dots}\n"
                s += f"\t\tHoTs: {player.hots}\n"
        
        return s