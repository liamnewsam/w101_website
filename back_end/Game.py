from typing import *
import random
#--------------
from Player import *
from Card import *
from Deck import *
from utils import *

def createBotPlayer(name, bot_id, image_path, school="random", deck=None, difficulty="moderate", level=100):
    from stats import compute_stats, compute_school_chart
    if school == "random":
        school = random.choice(list(DECK_MASTER[difficulty].keys()))
    if deck is None:
        deck = DECK_MASTER[difficulty][school]()
    base_stats   = compute_stats(level, school)
    school_chart = compute_school_chart(level, school)
    return Player(name, bot_id, school, deck, isBot=True, img_path=image_path, base_stats=base_stats, school_chart=school_chart)
    
    #return Player(name, bot_id, school, contrived_enemy_deck(), isBot=True, img_path=image_path)



def _collect_effect_targets(effects):
    targets = set()
    types = set()
    for effect in effects:
        if "target" in effect:
            targets.add(effect["target"])
        types.add(effect["type"])
        for key in ["effects", "true", "false"]:
            if key in effect:
                sub_targets, sub_types = _collect_effect_targets(effect[key])
                targets |= sub_targets
                types |= sub_types
        if "options" in effect:
            for option in effect["options"]:
                if "effect" in option:
                    sub_targets, sub_types = _collect_effect_targets([option["effect"]])
                    targets |= sub_targets
                    types |= sub_types
    return targets, types

def neededTargetType(card_def):
    all_targets, all_effect_types = _collect_effect_targets(card_def.effects)

    if "enemy" in all_targets:
        return "enemy"
    if "ally" in all_targets or "ally_same" in all_targets:
        return "ally"
    if "enemy_selected" in all_targets:
        return "enemy_selected"
    if "ally_selected" in all_targets:
        return "ally_selected"
    if "enemy_same" in all_targets:
        return "enemy_same"
    if "ally_same" in all_targets:
        return "ally_same"

    if "self" in all_targets or "enemy_all" in all_targets or "ally_all" in all_targets:
        return None

    # Defaulting
    if {"damage", "jinx"} & all_effect_types:
        return "enemy"
    if card_def.type == "heal":
        return "ally"

def getEffectTargetType(effect):
    if "target" in effect.keys():
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
        self.global_effects = []
        self.turns = 0
        self.winner = None

        self.log = []

        # Maps user_id → (model, device) for bots driven by a trained RL model.
        # Set externally after construction (e.g. in start_game or simulate_game).
        self.model_agents: dict = {}

        # Bot user_ids listed here will always pass instead of acting randomly.
        # Used for curriculum phase 2 (pass-bot training).
        self.pass_bot_ids: set = set()
    
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


        for player in self.current_team(aliveOnly=True) + self.opposite_team(aliveOnly=True):
            player.deck.draw_cards()

        for player in self.current_team(aliveOnly=True):
            log.append(player.receive_pip())
        
        self.update_playability()

        self.player_actions = {player.user_id: None for player in self.getPlayers()}

        pre_log_len = len(self.log)
        for player in self.current_team(aliveOnly=True):
            if player.isBot:
                self.takeRandomAction(player)
        log.extend(self.log[pre_log_len:])

        return log
    
    def takeRandomAction(self, player):
        if player.user_id in self.pass_bot_ids:
            self.player_pass(player)
            return

        if player.user_id in self.model_agents:
            self.model_agents[player.user_id](player)
            return

        if len(player.deck.play_hand) == 0:
            self.player_pass(player)
            return

        playable_indices = [i for i, option in enumerate(self.playability[player.user_id]) if option["playable"]]
        if len(playable_indices) == 0:
            discard_card = player.deck.play_hand[random.randint(0, len(player.deck.play_hand)-1)]
            self.player_discard(player, discard_card.instance_id)
            self.player_pass(player)
            return

        cardIndex = random.choice(playable_indices)
        target = None
        if self.playability[player.user_id][cardIndex]["targets"]:
            #target = player.user_id
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
        #print(self.player_actions)
        for player in self.current_team(aliveOnly=True):
            if self.player_actions[player.user_id] == None:
                return False
        return True

    def player_discard(self, player, card_id):
        if player not in self.current_team(aliveOnly=True):
            print(f"[invalid discard] Player {player.user_id} attempted an illegal discard")
            return False
        for i, card in enumerate(player.deck.play_hand):
            if card.instance_id == card_id:
                player.deck.play_hand.pop(i)
                self.log.append({"type": "action", "player": player.user_id, "action": "discard", "card": card.card_def.id, "cardIndex": i})
                player.deck.play_discard.append(card)
                self.playability[player.user_id].pop(i)
                return True

        print("[error] Discard card not found in hand")
        print(f"card_id={card_id}, hand={[c.instance_id for c in player.deck.play_hand]}")
        return False
    
    def player_pass(self, player):
        if player not in self.current_team(aliveOnly=True):
            print(f"[invalid pass] Player {player.user_id} attempted an illegal pass")
        self.player_actions[player.user_id] = {"type": "pass"}
        
        return True

    def player_cast(self, player, i, target):
        if player not in self.current_team(aliveOnly=True):
            print(f"[invalid cast] Player {player.user_id} attempted an illegal cast")
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


    def _resolve_condition_target(self, condition, player, action):
        target_type = condition.get("target") if condition else None
        if target_type == "self":
            return player
        return action["target"]

    def _expand_effects(self, effects, player, action):
        for effect in effects:
            if effect["type"] == "repeat":
                condition = effect.get("condition")
                if condition:
                    condition_target = self._resolve_condition_target(condition, player, action)
                    # For amount conditions, cap iterations at the current count of the
                    # aspect so over-expansion doesn't queue more destroy/consume effects
                    # than actually exist (expansion runs before resolution).
                    max_iters = effect["up_to"]
                    if condition.get("type") == "amount":
                        _aspect_lists = {
                            "charm": condition_target.charms,
                            "curse": condition_target.curses,
                            "ward":  condition_target.wards,
                            "jinx":  condition_target.jinxes,
                            "DoT":   condition_target.dots,
                            "HoT":   condition_target.hots,
                        }
                        aspect_list = _aspect_lists.get(condition.get("aspect", ""))
                        if aspect_list is not None:
                            max_iters = min(max_iters, len(aspect_list))
                    for _ in range(max_iters):
                        if not self.conditionMet(player, condition, condition_target):
                            break
                        yield from self._expand_effects(effect["effects"], player, action)
                else:
                    for _ in range(effect["up_to"]):
                        yield from self._expand_effects(effect["effects"], player, action)

            elif effect["type"] == "gambit":
                condition = effect["condition"]
                condition_target = self._resolve_condition_target(condition, player, action)
                branch = effect["true"] if self.conditionMet(player, condition, condition_target) else effect["false"]
                yield from self._expand_effects(branch, player, action)

            elif effect["type"] == "chance":
                for _ in range(effect["times"]):
                    roll = random.randint(1, 100)
                    cumulative = 0
                    for option in effect["options"]:
                        cumulative += option["chance"]
                        if roll <= cumulative:
                            yield option["effect"]
                            break

            else:
                yield effect

    def resolve_actions(self):
        log = []
        for player in self.current_team(aliveOnly=True):

            

            log.append({"type": "action", "player": player.user_id, "action": "activate"})

            log.extend(self.process_ongoing_effects(player))
            if player.health == 0: #They died
                continue


            action = self.player_actions[player.user_id]
            if action["type"] == "pass":
                log.append({"type": "action", "player": player.user_id, "action": "pass"})
                continue
            
            #Otherwise, the player is casting a card
            card_index = action["index"]
            card = player.deck.play_hand[card_index]
            log.append({"type": "action", "player": player.user_id, "action": "attempt_cast", "school": card.card_def.school})

            consumed_dispel = player.consume_dispel(card)
            if consumed_dispel:
                log.append({"type": "effect_trigger", "player": player.user_id, "aspect": "charm", "value": consumed_dispel.to_json()})
                log.append({"type": "result", "player": player.user_id, "result": "dispel"})
                #print(log[-1])
                player.deduct_pips(card)
                player.deck.play_hand.pop(card_index)
                player.deck.play_discard.append(card)
                continue


            
            accuracy, consumed_accuracies = player.consume_accuracy(card)
            for hangingEffect in consumed_accuracies:
                value = hangingEffect.to_json()
                log.append({"type": "effect_trigger", "player": player.user_id, "aspect": value["type"], "value": value})

            if random.randint(1, 100) > accuracy:
                log.append({"type": "result", "player": player.user_id, "result": "fizzle"})
                player.deck.play_hand.pop(card_index)
                player.deck.play_cards.insert(random.randint(0, len(player.deck.play_cards)), card)
                continue

            deducted = player.deduct_pips(card)
            x_pips = deducted.pop("x_pips", 1)
            log.append({"type": "effect_resolve", "target": player.user_id, "aspect": "pip_lose", "amount": deducted})
            log.append({"type": "result", "player": player.user_id, "result": "success", "card": card.card_def.id})


            # Expand effects first so gambit conditions see charms/curses intact.
            # caster_accumulation is shared across the whole cast so blades apply
            # to every hit, but per-effect consumption lets destroy effects run
            # before the first damage effect triggers blade consumption.
            expanded_effects = list(self._expand_effects(card.card_def.effects, player, action))

            caster_accumulation = {
                "damage": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                "armor_piercing": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                "heal": 0
            }

            overwritten_global = False
            for effect in expanded_effects:

                for hangingEffect in player.consume_charms_curses_for_effect(effect, caster_accumulation):
                    value = hangingEffect.to_json()
                    log.append({"type": "effect_trigger", "player": player.user_id, "aspect": value["type"], "value": value})

                target_pool = None
                if "target" not in effect.keys():
                    target_pool = None
                elif effect["target"] in ["enemy_same", "enemy", "ally", "ally_same"]:
                    target_pool = [action["target"]]
                elif effect["target"] in ["self"]:
                    target_pool = [player]
                elif effect["target"] == "enemy_all":
                    target_pool = self.opposite_team(aliveOnly=True)
                elif effect["target"] == "ally_all":
                    target_pool = self.current_team(aliveOnly=True)

                target_accumulation = {
                    "damage": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "armor_piercing": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "heal": 0,
                    "prism_school": False
                }
                critical_multiplier = 1

                if target_pool:
                    for target in target_pool:
                        target_accumulation = {
                            "damage": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                            "armor_piercing": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                            "heal": 0,
                            "prism_school": False
                        }

                        for hangingEffect in target.consume_wards_jinxes(effect, target_accumulation):
                            value = hangingEffect.to_json()
                            log.append({"type": "effect_trigger", "player": target.user_id, "aspect": value["type"], "value": value})

                        critical_multiplier = 1

                        if effect["type"] in ["damage", "DoT", "heal", "HoT", "drain", "detonate"]:
                            if random.randint(0, 99) < player.critical[card.card_def.school]:
                                log.append({"type": "effect_resolve", "player": player.user_id, "aspect": "critical"})
                                critical_multiplier = 2

                        log.extend(self.resolve_action(card, player, target, effect, caster_accumulation, target_accumulation, critical_multiplier, x_pips))

                else:
                    if effect["type"] == "global" and not overwritten_global:
                        overwritten_global = True
                        self.global_effects = []
                        log.extend(self.resolve_action(card, player, None, effect, caster_accumulation, target_accumulation, critical_multiplier, x_pips))
                
                
                

            player.deck.play_hand.pop(card_index)
            if card.card_def.reshuffle:
                player.deck.play_discard.append(card)
        
        #for message in log:
        #    print(message)
        self.log.extend(log)

        if self.check_end():
            self.log.append(f"TEAM {self.winner} WINS")

        return log

    def resolve_action(self, card: Card, caster: Player, target: Player, effect: dict, caster_accumulation, target_accumulation, critical_multiplier, x_pips=1):

        effect = EFFECT_TYPE_TO_CLASS[effect["type"]](effect, caster, target, card, x_pips=x_pips)
        if type(effect) in [DamageEffect, HealEffect, DoTEffect, HoTEffect, DrainEffect, DetonateEffect]:
            result = effect.resolve(self, caster_accumulation, target_accumulation, critical_multiplier)
        else:
            result = effect.resolve(self)

        if type(result) is dict:
            result = [result]
        return result

    def struggle_punish(self, player):
        """Apply escalating damage when both hand and deck are empty."""
        if len(player.deck.play_cards) == 0 and len(player.deck.play_hand) == 0:
            damage = 10 * player.struggle_counter
            player.health = max(0, player.health - damage)
            player.struggle_counter += 1
            return [{"type": "effect_resolve", "target": player.user_id, "aspect": "struggle", "amount": damage}]
        return []

    def is_playable(self, player, card):
        
        test = player.pips.copy()
        player_school = player.school
        card_school = card.card_def.school
        required_pips = card.card_def.pips
        school_aligned = player_school == card_school
        if type(required_pips) == dict:
            for school in [x for x in required_pips.keys() if x != "regular"]:
                test[school] -= required_pips[school]
        elif required_pips == "X":
            # X-pip spells consume all pips; need at least 1 pip to cast
            return player.pip_count() >= 1
        elif type(required_pips) == str:
            return False
        else:
            required_pips = {"regular": card.card_def.pips}    
        total_regular = 0

        for key, value in test.items():
            if value < 0:
                return False

            if key == "regular":
                total_regular += value
            elif key == "powerpip":
                # Power pips worth 2 for primary school, 1 for off-school
                total_regular += value * (2 if school_aligned else 1)
            else:
                # School pips worth 2 if they match the card's school, 1 otherwise
                total_regular += value * (2 if key == card_school else 1)

        if total_regular < required_pips.get("regular", 0):
            return False

        if card.card_def.condition == None:
            return True
        
        # TODO: Deal with conditions

        condition = card.card_def.condition
        target_type = condition.get("target")
        if target_type == "enemy":
            for enemy in self.opposite_team(aliveOnly=True):
                if self.conditionMet(player, condition, enemy):
                    return True
        elif target_type == "ally":
            for ally in self.current_team(aliveOnly=True):
                if self.conditionMet(player, condition, ally):
                    return True
        elif target_type == "self":
            if self.conditionMet(player, condition, player):
                return True
        else:  # compound condition (AND/OR) — use enemy as outer iteration target
            for enemy in self.opposite_team(aliveOnly=True):
                if self.conditionMet(player, condition, enemy):
                    return True

        return False

    
    def interpretTarget(self, player, targetType):
        if targetType in ["enemy", "enemy_same"]:
            return self.opposite_team()
        if targetType in ["ally", "ally_same"]:
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

        if "AND" in condition:
            return all(self.conditionMet(player, c, target) for c in condition["AND"])
        if "OR" in condition:
            return any(self.conditionMet(player, c, target) for c in condition["OR"])

        if condition.get("target") == "self":
            target = player

        if condition["type"] == "amount":
            if condition["aspect"] == "charm" and len(target.charms) >= condition["amount"]:
                return True
            if condition["aspect"] == "curse" and len(target.curses) >= condition["amount"]:
                return True
            if condition["aspect"] == "ward" and len(target.wards) >= condition["amount"]:
                return True
            if condition["aspect"] == "jinx" and len(target.jinxes) >= condition["amount"]:
                return True
            if condition["aspect"] == "pips" and target.pip_count() >= condition["amount"]:
                return True
            if condition["aspect"] == "DoT" and len(target.dots) >= condition["amount"]:
                for dot in target.dots:
                    if dot.rounds > 1:
                        return True
            if condition["aspect"] == "HoT" and len(target.hots) >= condition["amount"]:
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
                        if target.health > 0 and self.conditionMet(player, card.card_def.condition, target):
                            valid_targets.append(target)
                    
                    if valid_targets:
                        player_playability.append({"card": card, "playable": True, "targets": valid_targets})
                    else:
                        player_playability.append({"card": card, "playable": False})
                else:
                    player_playability.append({"card": card, "playable": False})
            
            self.playability[player.user_id] = player_playability
        
        

    def process_ongoing_effects(self, player):
        log = []

        log.extend(self.struggle_punish(player))
        if player.health == 0:
            return log

        for dot in player.dots[:]:

            

            target_accumulation = {
                    "damage": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "armor_piercing": {"any": 0, "myth": 0, "life": 0, "fire": 0, "ice": 0, "storm": 0, "death": 0, "balance": 0},
                    "heal": 0,
                    "prism_school": False
            }

            if not dot.wait or dot.rounds == 1: # Damage will be done
                dummyEffect = {"type": "damage", "school": dot.school, "amount": 0} #Dummy effect
                for hangingEffect in dot.target.consume_wards_jinxes(dummyEffect, target_accumulation):
                    value = hangingEffect.to_json()
                    log.append({"type": "effect_trigger", "player": dot.target.user_id, "aspect": value["type"], "value": value})
        


            log.extend(dot.tick(target_accumulation))
            
            if player.health == 0:
                return log


        #Process HoTs

        for hot in player.hots[:]:
            log.extend(hot.tick())

        return log
    def check_end(self):
        for player in self.teams[0]:
            if player.health > 0:
                break
        else:
            self.winner = "B"
            return True
        
        for player in self.teams[1]:
            if player.health > 0:
                break
        else:
            self.winner = "A"
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
            "global_effects": [effect.to_json() for effect in self.global_effects],
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