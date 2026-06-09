import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical


class TransformerActorCritic(nn.Module):
    """Transformer actor-critic that scores every (card, target) pair.

    Token sequence fed to the transformer:
        [CLS]  +  [card_0 … card_{H-1}]  +  [player_0 … player_{P-1}]

    Actor logits (N_ACTIONS = 1 + H * T):
        index 0          : pass
        1 + i*T + j      : cast card i at target slot j
            j < P        → player j (bilinear card×player score)
            j = P        → null target / AoE   (card-only score)

    Critic: scalar value from the CLS token.
    """

    def __init__(
        self,
        card_dim: int,
        player_dim: int,
        game_dim: int,
        effect_token_dim: int,
        hand_size: int        = 5,
        max_players: int      = 8,
        max_total_cards: int  = 30,
        max_effect_tokens: int = 32,
        n_target_slots: int   = 9,    # max_players + 1
        n_pip_school_actions: int = 7,
        embed_dim: int        = 64,
        n_heads: int          = 4,
        n_layers: int         = 2,
    ):
        super().__init__()
        self.hand_size            = hand_size
        self.max_players          = max_players
        self.max_total_cards      = max_total_cards
        self.max_effect_tokens    = max_effect_tokens
        self.n_target_slots       = n_target_slots
        self.n_pip_school_actions = n_pip_school_actions

        # ── Encoders ────────────────────────────────────────────
        # Card dim is large (549) due to the full effect tree; use a hidden layer
        # to learn intermediate structure before projecting to embed_dim.
        card_hidden = max(embed_dim * 2, card_dim // 4)
        self.card_encoder = nn.Sequential(
            nn.Linear(card_dim, card_hidden),
            nn.LayerNorm(card_hidden),
            nn.GELU(),
            nn.Linear(card_hidden, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
        )
        self.player_encoder = nn.Sequential(
            nn.Linear(player_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
        )
        self.effect_encoder = nn.Sequential(
            nn.Linear(effect_token_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
        )
        self.game_proj  = nn.Linear(game_dim, embed_dim)
        self.cls_token  = nn.Parameter(torch.zeros(1, 1, embed_dim))
        nn.init.trunc_normal_(self.cls_token, std=0.02)

        # ── Transformer ─────────────────────────────────────────
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=n_heads,
            dim_feedforward=embed_dim * 4,
            dropout=0.0,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # ── Actor heads ──────────────────────────────────────────
        self.pass_head = nn.Linear(embed_dim, 1)

        # (card token ∥ player token) → scalar logit
        self.pair_head = nn.Linear(embed_dim * 2, 1)

        # card token → scalar logit for null-target (AoE / self-cast)
        self.null_head = nn.Linear(embed_dim, 1)

        # card token → scalar logit for discarding that card
        self.discard_head = nn.Linear(embed_dim, 1)

        # CLS token → logit per pip-school choice
        self.pip_school_head = nn.Linear(embed_dim, n_pip_school_actions)

        # ── Critic head ──────────────────────────────────────────
        self.value_head = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 4),
            nn.GELU(),
            nn.Linear(embed_dim * 4, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, 1),
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=0.01)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    # ──────────────────────────────────────────────────────────────
    # Forward
    # ──────────────────────────────────────────────────────────────

    def forward(
        self,
        cards:       torch.Tensor,   # (B, MAX_TOTAL_CARDS, card_dim)
        players:     torch.Tensor,   # (B, P, player_dim)
        effects:     torch.Tensor,   # (B, MAX_EFFECT_TOKENS, effect_token_dim)
        game:        torch.Tensor,   # (B, game_dim)
        action_mask: torch.Tensor,   # (B, N_ACTIONS)
    ):
        B = cards.shape[0]
        H = self.hand_size
        C = self.max_total_cards
        P = self.max_players
        X = self.max_effect_tokens
        T = self.n_target_slots

        card_tokens   = self.card_encoder(cards)       # (B, C, E)
        player_tokens = self.player_encoder(players)   # (B, P, E)
        effect_tokens = self.effect_encoder(effects)   # (B, X, E)
        game_emb      = self.game_proj(game)           # (B, E)

        cls    = self.cls_token.expand(B, -1, -1) + game_emb.unsqueeze(1)              # (B, 1, E)
        tokens = torch.cat([cls, card_tokens, player_tokens, effect_tokens], dim=1)    # (B, 1+C+P+X, E)

        out        = self.transformer(tokens)           # (B, 1+C+P+X, E)
        cls_out    = out[:, 0]                          # (B, E)
        card_out   = out[:, 1 : 1 + C]                 # (B, C, E)
        player_out = out[:, 1 + C : 1 + C + P]         # (B, P, E)

        # Action heads operate only on hand-card tokens (first H slots)
        hand_out = card_out[:, :H]                      # (B, H, E)

        # Pass logit
        pass_logit = self.pass_head(cls_out)            # (B, 1)

        # (card_i, player_j) logits via pair_head — hand cards only
        card_exp   = hand_out.unsqueeze(2).expand(-1, -1, P, -1)    # (B, H, P, E)
        player_exp = player_out.unsqueeze(1).expand(-1, H, -1, -1)  # (B, H, P, E)
        pairs      = torch.cat([card_exp, player_exp], dim=-1)       # (B, H, P, 2E)
        targeted   = self.pair_head(pairs).squeeze(-1)               # (B, H, P)

        # (card_i, null) logit — no target needed
        null_logit = self.null_head(hand_out)                        # (B, H, 1)

        cast_logits = torch.cat([targeted, null_logit], dim=-1)      # (B, H, T)
        cast_logits = cast_logits.reshape(B, H * T)                  # (B, H*T)

        # Discard logits: one per hand-card slot
        discard_logits = self.discard_head(hand_out).squeeze(-1)      # (B, H)

        # Pip-school logits: global decision from CLS
        pip_school_logits = self.pip_school_head(cls_out)             # (B, n_pip_schools)

        logits = torch.cat(
            [pass_logit, cast_logits, discard_logits, pip_school_logits], dim=-1
        )                                                             # (B, N_ACTIONS)

        # Mask illegal actions
        logits = logits.masked_fill(action_mask < 0.5, float("-inf"))

        value = self.value_head(cls_out).squeeze(-1)                 # (B,)
        return logits, value

    # ──────────────────────────────────────────────────────────────
    # Convenience wrappers
    # ──────────────────────────────────────────────────────────────

    @torch.no_grad()
    def act(self, cards, players, effects, game, action_mask):
        """Sample action. Returns (action, log_prob, value), all (B,)."""
        logits, value = self(cards, players, effects, game, action_mask)
        dist   = Categorical(logits=logits)
        action = dist.sample()
        return action, dist.log_prob(action), value

    def evaluate(self, cards, players, effects, game, action_mask, action):
        """Returns (log_prob, value, entropy) for updating PPO."""
        logits, value = self(cards, players, effects, game, action_mask)
        dist = Categorical(logits=logits)
        return dist.log_prob(action), value, dist.entropy()
