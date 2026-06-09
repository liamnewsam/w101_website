"""Evolutionary deck builder — population-based alternative to PPO deck building.

Maintains a fixed-size population of decks.  After `gen_games` games have been
played across all decks the population evolves: the elite decks survive and the
rest are replaced with mutated offspring.

Interface is designed to slot into train.py alongside the PPO deck builder with
minimal changes.
"""
from __future__ import annotations

import random
import numpy as np

from rl.deck_builder import (
    _get_all_pool, _get_school_mask, build_deck,
    DECK_SIZE, MAX_POOL_SIZE, MAX_COPIES,
)


class EvoDecBuilder:
    """(μ + λ) evolutionary deck optimizer.

    Attributes
    ----------
    population  : list of DECK_SIZE-length index lists
    stats       : [[wins, games], ...] parallel to population
    """

    def __init__(
        self,
        school:        str,
        pop_size:      int        = 20,
        n_elite:       int        = 5,
        mutation_rate: float      = 0.15,
        school_bias:   float      = 2.0,
        gen_games:        int        = 40,
        forced_cards:     list       = None,
        seed_deck:        list[int]  = None,  # pool indices to seed population from
        elite_reset_gens: int        = 5,     # reset elite stats every N generations
    ):
        self.school           = school
        self.pop_size         = pop_size
        self.n_elite          = max(1, n_elite)
        self.mutation_rate    = mutation_rate
        self.school_bias      = school_bias
        self.gen_games        = gen_games
        self.forced_cards     = forced_cards or []
        self.elite_reset_gens = elite_reset_gens

        all_cards, _ = _get_all_pool()
        real_n = min(len(all_cards), MAX_POOL_SIZE)
        self._real_n = real_n

        # Sampling weights: in-school cards only
        school_mask = _get_school_mask(school)
        weights     = np.zeros(real_n, dtype=np.float64)
        for i in range(real_n):
            if school_mask[i] > 0:
                weights[i] = float(school_bias)
        weights      /= weights.sum()
        self._weights = weights

        # Resolve forced card pool indices
        id_to_idx = {cd.id: i for i, cd in enumerate(all_cards[:real_n])}
        self._forced_indices: list[int] = []
        for cid in self.forced_cards:
            idx = id_to_idx.get(cid)
            if idx is not None:
                self._forced_indices.append(idx)

        # Initialise population from seed deck (or random)
        if seed_deck:
            # First individual is the exact seed; rest are mutations of it
            self.population = [list(seed_deck)]
            for _ in range(pop_size - 1):
                self.population.append(self._mutate(seed_deck))
            print(f"  → evo population seeded from provided deck ({len(seed_deck)} cards)")
        else:
            self.population: list[list[int]] = [self._random_deck() for _ in range(pop_size)]
        self.stats: list[list[int]]      = [[0, 0] for _ in range(pop_size)]

        self._eval_idx       = 0   # round-robin cursor through population
        self._games_this_gen = 0
        self.generation      = 0

    # ── deck sampling ────────────────────────────────────────────────────────

    def _random_deck(self) -> list[int]:
        counts  = np.zeros(MAX_POOL_SIZE, dtype=np.int32)
        indices: list[int] = []

        for idx in self._forced_indices:
            if counts[idx] < MAX_COPIES and len(indices) < DECK_SIZE:
                counts[idx] += 1
                indices.append(idx)

        attempts = 0
        while len(indices) < DECK_SIZE and attempts < DECK_SIZE * 30:
            idx = int(np.random.choice(self._real_n, p=self._weights))
            if counts[idx] < MAX_COPIES:
                counts[idx] += 1
                indices.append(idx)
            attempts += 1

        # Hard fallback: fill any remaining slots sequentially
        for idx in range(self._real_n):
            if len(indices) >= DECK_SIZE:
                break
            while counts[idx] < MAX_COPIES and len(indices) < DECK_SIZE:
                counts[idx] += 1
                indices.append(idx)

        return indices

    def _mutate(self, deck: list[int]) -> list[int]:
        deck   = list(deck)
        counts = np.zeros(MAX_POOL_SIZE, dtype=np.int32)
        for idx in deck:
            counts[idx] += 1

        n_forced   = len(self._forced_indices)
        free_slots = list(range(n_forced, len(deck)))
        n_replace  = max(1, int(len(free_slots) * self.mutation_rate))
        to_replace = random.sample(free_slots, min(n_replace, len(free_slots)))

        for pos in to_replace:
            counts[deck[pos]] -= 1
            for _ in range(50):
                new_idx = int(np.random.choice(self._real_n, p=self._weights))
                if counts[new_idx] < MAX_COPIES:
                    deck[pos]        = new_idx
                    counts[new_idx] += 1
                    break
            else:
                counts[deck[pos]] += 1   # restore if no replacement found

        return deck

    # ── evaluation interface ─────────────────────────────────────────────────

    def get_eval_deck(self) -> tuple[object, int]:
        """Return (Deck, population_index) for the next deck to evaluate."""
        idx  = self._eval_idx % self.pop_size
        deck = build_deck(self.population[idx])
        return deck, idx

    def record_outcome(self, deck_idx: int, won: bool) -> None:
        """Record a single game result for the deck at population index deck_idx."""
        self.stats[deck_idx][0] += int(won)
        self.stats[deck_idx][1] += 1
        self._eval_idx       += 1
        self._games_this_gen += 1

    @property
    def ready_to_evolve(self) -> bool:
        return self._games_this_gen >= self.gen_games

    # ── evolution ────────────────────────────────────────────────────────────

    def evolve(self) -> dict:
        """Replace weakest decks with mutated offspring from elite survivors."""
        def win_rate(i):
            g = self.stats[i][1]
            return self.stats[i][0] / g if g > 0 else 0.0

        ranked      = sorted(range(self.pop_size), key=win_rate, reverse=True)
        elite_idx   = ranked[:self.n_elite]
        replace_idx = ranked[self.n_elite:]

        best_wr  = win_rate(ranked[0])
        worst_wr = win_rate(ranked[-1])

        for slot in replace_idx:
            parent                = self.population[random.choice(elite_idx)]
            self.population[slot] = self._mutate(parent)
            self.stats[slot]      = [0, 0]

        self.generation += 1

        # Periodically reset elite stats so win rates reflect recent performance
        # rather than being diluted by games played many generations ago.
        if self.elite_reset_gens > 0 and self.generation % self.elite_reset_gens == 0:
            for slot in elite_idx:
                self.stats[slot] = [0, 0]

        self._games_this_gen = 0

        # Diversity: unique card indices across whole population / real pool size
        unique = len({c for deck in self.population for c in deck})
        diversity = unique / self._real_n

        return {
            "evo_best_wr":  round(best_wr,  4),
            "evo_worst_wr": round(worst_wr, 4),
            "evo_diversity": round(diversity, 4),
            "evo_gen":      self.generation,
        }

    def best_deck(self) -> object:
        """Return the deck with the highest current win rate."""
        best_i = max(range(self.pop_size),
                     key=lambda i: self.stats[i][0] / max(self.stats[i][1], 1))
        return build_deck(self.population[best_i])

    def top_n_decks(self, n: int = 5) -> list[dict]:
        """Return the top-N decks by win rate as a list of dicts.

        Each dict has keys: deck, win_rate, wins, games.
        Only includes decks that have played at least one game.
        """
        played = [(i, self.stats[i][0], self.stats[i][1])
                  for i in range(self.pop_size) if self.stats[i][1] > 0]
        played.sort(key=lambda x: x[1] / x[2], reverse=True)
        results = []
        for i, wins, games in played[:n]:
            results.append({
                "deck":     build_deck(self.population[i]),
                "win_rate": wins / games,
                "wins":     wins,
                "games":    games,
            })
        return results

    # ── persistence ──────────────────────────────────────────────────────────

    def state_dict(self) -> dict:
        return {
            "population":  self.population,
            "stats":       self.stats,
            "generation":  self.generation,
            "_eval_idx":   self._eval_idx,
        }

    def load_state_dict(self, d: dict) -> None:
        self.population       = d["population"]
        self.stats            = d["stats"]
        self.generation       = d.get("generation", 0)
        self._eval_idx        = d.get("_eval_idx", 0)
        self._games_this_gen  = 0
