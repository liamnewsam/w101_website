from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
import json as _json
import threading

# ===== Game Logic =====
from Game import Game, createBotPlayer
from Player import Player, loadPlayer
from Card import Card, CARD_BY_ID
from Deck import Deck
from stats import compute_stats, compute_school_chart

# ===== Auth System =====
from auth_routes import auth
from jwt_utils import decode_jwt
from utils import getRandomPlayerImage

# ===== Database =====
from database import *
from models import *
from db_utils import cleanup_expired_guests
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import cast, String

from socketio.exceptions import ConnectionRefusedError

# --------------------------------------------------------
# Flask + CORS Setup
# --------------------------------------------------------
ALLOWED_ORIGINS = [
    "https://w101-website.vercel.app",
    "http://localhost:5173",
]

app = Flask(__name__)

CORS(app, supports_credentials=True, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

app.register_blueprint(auth, url_prefix="/auth")

socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS, logger=False, engineio_logger=False)

from flask import make_response

from werkzeug.exceptions import HTTPException

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    # Only catch real Flask HTTP route errors
    print("HTTP exception:", e)
    return make_response(jsonify({"error": str(e)}), e.code)

@app.route("/favicon.ico")
def favicon():
    return "", 200


@app.route("/cards", methods=["GET"])
def get_cards():
    from Card import CARDS_BY_SCHOOL
    result = {}
    for school, cards in CARDS_BY_SCHOOL.items():
        def norm_level(v):
            return v if isinstance(v, int) and not isinstance(v, bool) else 0
        def norm_pips(p):
            if isinstance(p, dict):
                return sum(p.values())
            return p if isinstance(p, int) else 0
        result[school] = sorted(
            [
                {
                    "id": card.id,
                    "name": card.name,
                    "school": card.school,
                    "pips": norm_pips(card.pips),
                    "pvp_level": norm_level(card.pvp_level),
                    "img_path": card.img_path,
                }
                for card in cards
            ],
            key=lambda c: c["pvp_level"]
        )
    return jsonify(result)


@app.route("/avatars", methods=["GET"])
def list_avatars():
    from config import CHARACTER_IMAGE_PATH
    import os
    try:
        files = sorted(f for f in os.listdir(CHARACTER_IMAGE_PATH) if f.lower().endswith(".png"))
        paths = [os.path.join(CHARACTER_IMAGE_PATH, f).replace("\\", "/") for f in files]
        return jsonify({"avatars": paths})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models", methods=["GET"])
def list_models():
    from rl.inference import list_checkpoints
    try:
        return jsonify({"models": list_checkpoints()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/demo-deck/<school>", methods=["GET"])
def get_demo_deck(school):
    """Return the default deck card IDs from best.pt for the given school."""
    from rl.inference import get_school_best_deck
    school = school.capitalize()
    valid = {"Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"}
    if school not in valid:
        return jsonify({"error": "Invalid school"}), 400
    try:
        card_ids = get_school_best_deck(school)
        return jsonify({"card_ids": card_ids, "school": school})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================================================
# In-Memory Data Models
# ========================================================

BOT_ELO = 1000
ELO_K = 64
ELO_FLOOR = 100

# Level range visible to players: 10–170; ~1 win vs same-level ≈ 1 level (K=64, delta≈32)
_LEVEL_MIN    = 10
_LEVEL_MAX    = 170
_ELO_PER_LEVEL = 32


def _compute_level(elo):
    return max(_LEVEL_MIN, min(_LEVEL_MAX, (elo - ELO_FLOOR) // _ELO_PER_LEVEL + _LEVEL_MIN))


def _compute_elo_changes(lobby, winner_team):
    """Return {player_id: {"elo_change": int, "new_elo": int}} for every human player."""
    human = [p for p in lobby.players.values() if not p.isBot]
    changes = {}
    for p in human:
        opponents = [op for op in lobby.players.values() if op.team != p.team and not op.isBot]
        opp_avg = sum(op.elo for op in opponents) / len(opponents) if opponents else BOT_ELO
        expected = 1 / (1 + 10 ** ((opp_avg - p.elo) / 400))
        actual = 1.0 if p.team == winner_team else 0.0
        delta = round(ELO_K * (actual - expected))
        new_elo = max(ELO_FLOOR, p.elo + delta)
        changes[p.id] = {"elo_change": delta, "new_elo": new_elo}
    return changes


class LobbyPlayer:
    def __init__(self, user_id, sid, name, image_path, school="Balance", level=1, wins=0, losses=0, elo=100, team="A", isBot=False, school_elos=None, deck_data=None, model_path=None, model_config=None):
        self.id = user_id
        self.name = name
        self.team = team
        self.isReady = isBot  # bots are always ready
        self.sid = sid  # socket id
        self.image_path = image_path
        self.isBot = isBot
        self.school = school
        self.level = level
        self.wins = wins
        self.losses = losses
        self.elo = elo              # active school's ELO (used for matchmaking)
        self.school_elos = school_elos or {}
        self.deck_data = deck_data  # set for duplicate-player bots; None uses DECK_MASTER
        self.model_path = model_path      # path to checkpoint if this is an AI model bot
        self.model_config = model_config  # metadata dict from the checkpoint


class Lobby:
    def __init__(self, host_id):
        self.players = {}      # userId → LobbyPlayer
        self.host = host_id
        self.game = None       # becomes Game() after start
        self.started = False
        self.watchers = set()  # socket IDs watching game state
        self.initial_game_state = None   # public state snapshot right after begin()
        self.replay_turns = []           # [{log, finalGameState}] accumulated per turn
        self._turn_lock = threading.Lock()  # prevents double turn resolution under concurrent actions

    def team_counts(self):
        amount = {"A": 0, "B": 0}
        for player in self.players.values():
            amount[player.team] += 1
        return amount

    def isReady(self):
        team_counts = self.team_counts()
        if team_counts["A"] == 0 or team_counts["B"] == 0:
            return False
        return all([player.isReady for player in list(filter(lambda p: not p.isBot, self.players.values()))])
    
    def snapshot(self):
        return {
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "team": p.team,
                    "isReady": p.isReady,
                    "image_path": p.image_path,
                    "school": p.school,
                    "level": p.level,
                    "isBot": p.isBot,
                    "model_path": getattr(p, "model_path", None),
                }
                for p in self.players.values()
            ],
            "host": self.host
        }

    def UID_to_SID(self, uid):
        player = self.players.get(uid)
        return player.sid if player else None
lobbies = {}  # gameId → Lobby


# ========================================================
# Utility
# ========================================================

def get_user_identity(req_sid):
    return connected_users.get(req_sid)


def get_player_from_db(user_id):
    player = None
    db = SessionLocal()
    try:
        player = db.query(PlayerState).filter_by(player_id=user_id).first()
    finally:
        db.close()

    if player:
        return player.to_dict()
    
    return None

# ========================================================
# Socket Auth
# ========================================================

connected_users = {}  # sid → user_id


@socketio.on("connect")
def on_connect(auth):
    token = auth.get("token") if auth else None
    if not token:
        raise ConnectionRefusedError("authentication failed")

    try:
        payload = decode_jwt(token)
        user_id = payload.get("user_id") or payload.get("guest_id")
        user_type = payload.get("type")
    except Exception as e:
        print("Invalid token:", e)
        raise ConnectionRefusedError("authentication failed")

    # Bind socket → identity
    connected_users[request.sid] = user_id

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    user_id = connected_users.pop(sid, None)

    print(f"[disconnect] user={user_id}, socket={sid}")

    for gameID, lobby in list(lobbies.items()):
        if user_id not in lobby.players:
            continue

        print(f"[disconnect] removed player {user_id} from lobby {gameID}")

        if lobby.started:
            _handle_in_game_leave(gameID, lobby, user_id)
        else:
            del lobby.players[user_id]
            if not any(not p.isBot for p in lobby.players.values()):
                del lobbies[gameID]
                print(f"[disconnect] removed empty lobby {gameID}")
            else:
                socketio.emit("update_lobby_state", lobby.snapshot(), room=gameID)

        lobby.players.pop(user_id, None)
        break  # socket belongs to only one lobby




    


# ========================================================
# Menu Events
# ========================================================

@socketio.on("get_player_info")
def get_player_info():
    user_id = get_user_identity(request.sid)

    if not user_id:
        emit("error", {"msg": "Not authenticated"})
        return

    # Demo sessions have no DB record — skip silently
    if str(user_id).startswith("demo_"):
        return
    
    # Query DB using user_id...
    db = SessionLocal()
    try:
        player = db.query(PlayerState).filter_by(player_id=user_id).first()

        if not player:
            emit("error", {"msg": "Player not found"})
            return
        
        emit("player_info", player.to_dict())
    finally:
        db.close()


@socketio.on("get_player_stats")
def get_player_stats():
    user_id = get_user_identity(request.sid)
    if not user_id:
        emit("player_stats", {"error": "Not authenticated"})
        return

    db = SessionLocal()
    try:
        player = db.query(PlayerState).filter_by(player_id=user_id).first()
        if not player:
            emit("player_stats", {"error": "Player not found"})
            return

        school = (player.school or "Balance").lower()
        level  = player._compute_school_level(school)
        stats        = compute_stats(level, school)
        school_chart = compute_school_chart(level, school)
        if stats is None:
            emit("player_stats", {"error": f"Unknown school: {school}"})
            return

        emit("player_stats", {"ok": True, "stats": stats, "school_chart": school_chart})
    except Exception as e:
        print(f"[get_player_stats] ERROR: {e}")
        emit("player_stats", {"error": str(e)})
    finally:
        db.close()


@socketio.on("list_games")
def list_games():
    open_games = []
    for gid, lobby in lobbies.items():
        if not lobby.started:
            open_games.append({
                "gameId": gid,
                "name": f"Lobby {gid}",
                "players": list(lobby.players.keys())
            })
    emit("game_list", open_games, broadcast=True)


def _lobby_player_from_db(db_player, user_id, sid, team="A"):
    """Build a LobbyPlayer from a to_dict() result, using the active school's ELO."""
    school = db_player.get("school", "Balance")
    school_elos = db_player.get("school_elos", {})
    school_elo = school_elos.get(school.lower(), ELO_FLOOR)
    return LobbyPlayer(
        user_id=user_id,
        sid=sid,
        name=db_player.get("name", user_id),
        image_path=db_player["image_path"],
        school=school,
        level=db_player.get("level", _LEVEL_MIN),
        wins=db_player.get("wins", 0),
        losses=db_player.get("losses", 0),
        elo=school_elo,
        team=team,
        school_elos=school_elos,
    )


@socketio.on("create_game")
def create_game(data):
    user_id = get_user_identity(request.sid)
    if not user_id:
        return {"ok": False, "error": "Not authenticated"}

    gameId = str(uuid.uuid4())[:8]

    lobby = Lobby(host_id=user_id)
    lobbies[gameId] = lobby

    


    db_player = get_player_from_db(user_id)
    if not db_player:
        return {"ok": False, "error": "Player not found"}
    lobby.players[user_id] = _lobby_player_from_db(db_player, user_id, request.sid)

    join_room(gameId)
    list_games()

    return {"gameId": gameId}



@socketio.on("create_bot_game")
def create_bot_game(data):
    user_id = get_user_identity(request.sid)
    gameId = str(uuid.uuid4())[:8]

    lobby = Lobby(host_id=user_id)
    lobbies[gameId] = lobby

    # host joins
    db_player = get_player_from_db(user_id)
    if not db_player:
        return {"ok": False, "error": "Player not found"}
    lobby.players[user_id] = _lobby_player_from_db(db_player, user_id, request.sid)

    # add bots
    import random as _random
    BOT_SCHOOLS = ["Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"]
    for i in range(3):
        bot_id = f"bot_{i}"
        lobby.players[bot_id] = LobbyPlayer(
            bot_id, None, f"Bot {i+1}", getRandomPlayerImage(),
            school=_random.choice(BOT_SCHOOLS), level=lobby.players[user_id].level,
            team="B", isBot=True,
        )

    join_room(gameId)
    return {"gameId": gameId}


@socketio.on("create_rl_demo_game")
def create_rl_demo_game(data):
    """Create and immediately start a 1v1 demo game vs a trained RL agent.

    Bypasses the database entirely — the human player state comes from the
    request payload (school, deck card IDs, level=100).
    """
    from rl.inference import load_model, pick_demo_ai_deck, get_school_best_deck
    from stats import compute_stats, compute_school_chart

    user_id = get_user_identity(request.sid)
    if not user_id:
        return {"ok": False, "error": "Not authenticated"}

    player_school   = (data.get("player_school") or "Fire").strip().title()
    player_deck_ids = data.get("player_deck_card_ids") or get_school_best_deck(player_school)
    ai_school       = (data.get("ai_school") or "Balance").strip().title()
    player_name     = data.get("player_name", "Demo Player")

    LEVEL = 100

    # ── Build human player ───────────────────────────────────────────────────
    human_cards = [Card(CARD_BY_ID[cid]) for cid in player_deck_ids if cid in CARD_BY_ID]
    if not human_cards:
        return {"ok": False, "error": "No valid cards in deck"}
    human_deck   = Deck("Demo Deck", human_cards)
    h_stats      = compute_stats(LEVEL, player_school)
    h_chart      = compute_school_chart(LEVEL, player_school)
    human_img    = getRandomPlayerImage()
    human_player = Player(
        player_name, user_id, player_school, human_deck,
        isBot=False, img_path=human_img,
        base_stats=h_stats, school_chart=h_chart,
    )

    # ── Build AI bot ─────────────────────────────────────────────────────────
    ai_deck_ids, _ = pick_demo_ai_deck(ai_school)
    ai_cards = [Card(CARD_BY_ID[cid]) for cid in ai_deck_ids if cid in CARD_BY_ID]
    if not ai_cards:
        # Fallback: use a default deck if the checkpoint deck is broken
        ai_cards = [Card(CARD_BY_ID[cid]) for cid in get_school_best_deck(ai_school) if cid in CARD_BY_ID]
    ai_deck   = Deck("AI Deck", ai_cards)
    bot_id    = f"bot_{uuid.uuid4().hex[:6]}"
    b_stats   = compute_stats(LEVEL, ai_school)
    b_chart   = compute_school_chart(LEVEL, ai_school)
    bot_img   = getRandomPlayerImage()
    bot_player = Player(
        f"AI ({ai_school})", bot_id, ai_school, ai_deck,
        isBot=True, img_path=bot_img,
        base_stats=b_stats, school_chart=b_chart,
    )

    # ── Create lobby ─────────────────────────────────────────────────────────
    gameId = str(uuid.uuid4())[:8]
    lobby  = Lobby(host_id=user_id)
    lobby.is_demo = True
    lobbies[gameId] = lobby

    lobby.players[user_id] = LobbyPlayer(
        user_id=user_id, sid=request.sid, name=player_name,
        image_path=human_img, school=player_school,
        level=LEVEL, team="A",
    )
    lobby.players[bot_id] = LobbyPlayer(
        user_id=bot_id, sid=None, name=f"AI ({ai_school})",
        image_path=bot_img, school=ai_school,
        level=LEVEL, team="B", isBot=True,
    )

    # ── Create game ───────────────────────────────────────────────────────────
    lobby.game = Game([human_player], [bot_player])

    # Wire up the RL model as a callable (model_agents must store callables)
    import os as _os
    ai_model_path = _os.path.join(
        _os.path.dirname(__file__), "rl", "checkpoints", ai_school, "best.pt"
    )
    try:
        from rl.inference import take_model_action
        model, _ = load_model(ai_model_path)
        _game = lobby.game
        lobby.game.model_agents[bot_id] = (
            lambda p, _m=model, _g=_game: take_model_action(_m, _g, p, "cpu")
        )
    except Exception as e:
        print(f"[create_rl_demo_game] Could not load model for {ai_school}: {e}")

    lobby.game.begin()
    lobby.started = True
    lobby.initial_game_state = _json.loads(_json.dumps(lobby.game.to_json_public()))

    join_room(gameId)

    # Handle unlikely edge case: bot team goes first
    if lobby.game.isAllBots(lobby.game.playing_team_i):
        while not lobby.game.winner and attemptTurnResolution(lobby, lobby.game):
            continue

    return {"ok": True, "gameId": gameId}


@socketio.on("join_game")
def join_game(data):
    gameId = data["gameId"]
    user_id = get_user_identity(request.sid)

    if gameId not in lobbies:
        return {"ok": False, "error": "Game not found"}

    lobby = lobbies[gameId]

    if lobby.started:
        return {"ok": False, "error": "Game already started"}

    if user_id not in lobby.players:
        db_player = get_player_from_db(user_id)
        if not db_player:
            return {"ok": False, "error": "Player not found"}
        team_counts = lobby.team_counts()
        lobby.players[user_id] = _lobby_player_from_db(
            db_player, user_id, request.sid,
            team=("A" if team_counts["A"] < team_counts["B"] else "B"),
        )

    lobby.players[user_id].sid = request.sid

    join_room(gameId)

    # Notify lobby watchers
    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)
    return {"ok": True}




# ========================================================
# Lobby Events
# ========================================================

@socketio.on("watch_lobby")
def watch_lobby(data):
    gameId = data["gameId"]
    join_room(gameId)


@socketio.on("update_lobby_state")
def update_lobby_state(data):
    gameId = data["gameId"]
    user_id = get_user_identity(request.sid)
    lobby = lobbies.get(gameId)
    if not lobby:
        return

    emit("update_lobby_state", lobby.snapshot(), room=gameId)

@socketio.on("get_lobby_state")
def get_lobby_state(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby:
        return {}

    return lobby.snapshot()


@socketio.on("player_ready")
def player_ready(data):
    gameId = data["gameId"]
    user_id = get_user_identity(request.sid)

    lobby = lobbies.get(gameId)
    if not lobby:
        return

    if user_id in lobby.players:
        lobby.players[user_id].isReady = not lobby.players[user_id].isReady

    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("switch_team")
def switch_team(data):
    gameId = data["gameId"]
    new_team = data["team"]
    user_id = get_user_identity(request.sid)

    lobby = lobbies.get(gameId)
    if not lobby or user_id not in lobby.players:
        return
    if new_team not in ("A", "B"):
        return

    lobby.players[user_id].team = new_team
    lobby.players[user_id].isReady = False

    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("add_bot")
def add_bot(data):
    import random as _random
    gameId = data["gameId"]
    team = data.get("team", "A")
    caller = get_user_identity(request.sid)

    lobby = lobbies.get(gameId)
    if not lobby or caller != lobby.host:
        return

    BOT_SCHOOLS = ["Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"]
    bot_num = sum(1 for p in lobby.players.values() if p.isBot) + 1
    bot_id = f"bot_{uuid.uuid4().hex[:6]}"

    #Get average level of players:
    total = 0
    n = 0
    for p in lobby.players.values():
        if not p.isBot:
            n += 1
            total += p.level

    avgLevel = total // n
    lobby.players[bot_id] = LobbyPlayer(
        user_id=bot_id,
        sid=None,
        name=f"Bot {bot_num}",
        image_path=getRandomPlayerImage(),
        school=_random.choice(BOT_SCHOOLS),
        level=avgLevel,
        team=team,
        isBot=True,
    )

    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("add_model_bot")
def add_model_bot(data):
    """Add a bot driven by a trained RL model checkpoint."""
    from rl.inference import list_checkpoints
    gameId = data["gameId"]
    team   = data.get("team", "A")
    path   = data.get("model_path")
    caller = get_user_identity(request.sid)

    lobby = lobbies.get(gameId)
    if not lobby or not path or caller != lobby.host:
        return

    # Find metadata for this checkpoint
    model_config = None
    for ckpt in list_checkpoints():
        if ckpt.get("path") == path or ckpt.get("filename") == path:
            model_config = ckpt
            path = ckpt["path"]
            break

    if model_config is None:
        return

    school = model_config.get("agent_school", "Balance")
    level  = model_config.get("agent_level", 1)
    deck_name = model_config.get("agent_deck_name")

    bot_num = sum(1 for p in lobby.players.values() if p.isBot) + 1
    bot_id  = f"bot_{uuid.uuid4().hex[:6]}"
    label   = f"AI ({school} Lv{level}, iter {model_config.get('iteration', '?')})"

    lobby.players[bot_id] = LobbyPlayer(
        user_id=bot_id,
        sid=None,
        name=label,
        image_path=getRandomPlayerImage(),
        school=school,
        level=level,
        team=team,
        isBot=True,
        model_path=path,
        model_config=model_config,
    )

    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("add_duplicate_bot")
def add_duplicate_bot(data):
    gameId = data["gameId"]
    team = data.get("team", "A")

    user_id = get_user_identity(request.sid)
    lobby = lobbies.get(gameId)
    if not lobby or user_id not in lobby.players:
        return

    db_player = get_player_from_db(user_id)
    if not db_player:
        return

    human = lobby.players[user_id]
    bot_num = sum(1 for p in lobby.players.values() if p.isBot) + 1
    bot_id = f"bot_{uuid.uuid4().hex[:6]}"
    lobby.players[bot_id] = LobbyPlayer(
        user_id=bot_id,
        sid=None,
        name=f"Bot {bot_num}",
        image_path=human.image_path,
        school=human.school,
        level=human.level,
        team=team,
        isBot=True,
        deck_data=db_player.get("deck"),
    )

    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("remove_bot")
def remove_bot(data):
    gameId = data["gameId"]
    bot_id = data["botId"]
    caller = get_user_identity(request.sid)

    lobby = lobbies.get(gameId)
    if not lobby or caller != lobby.host:
        return

    player = lobby.players.get(bot_id)
    if player and player.isBot:
        del lobby.players[bot_id]
        socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("start_game")
def start_game(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby:
        return {"ok": False, "error": "Lobby missing"}

    caller = get_user_identity(request.sid)
    if caller != lobby.host:
        return {"ok": False, "error": "Only the host can start the game"}

    for p in lobby.players.values():
        if not p.isBot and not p.isReady:
            return {"ok": False, "error": "All players must be ready"}
    # Build teams for Game()
    teamA = []
    teamB = []
    model_agents = {}  # user_id → (model, device)

    for p in lobby.players.values():
        # Query DB using user_id...
        player = None
        if not p.isBot:
            db = SessionLocal()
            try:
                player = db.query(PlayerState).filter_by(player_id=p.id).first()

                if not player:
                    emit("error", {"msg": "Player not found"})
                    return
            finally:
                db.close()

            player_data = player.to_dict()
            if not player_data.get("deck"):
                emit("error", {"msg": "No deck selected. Please create a deck in the deck editor first."})
                return
            player = loadPlayer(player_data)

        else:
            deck = None
            if p.deck_data:
                cards = [Card(CARD_BY_ID[cid]) for cid in p.deck_data.get("card_ids", []) if cid in CARD_BY_ID]
                deck = Deck(p.deck_data["name"], cards)
            elif p.model_config and p.model_config.get("agent_deck_name"):
                from Deck import DECK_MASTER
                deck_name = p.model_config["agent_deck_name"]
                school = p.school
                # Try to locate the deck by name in DECK_MASTER across difficulties
                for diff in ("moderate", "simple", "easy"):
                    tier = DECK_MASTER.get(diff, {})
                    if school in tier:
                        candidate = tier[school]()
                        if candidate.name == deck_name:
                            deck = candidate
                            break
            player = createBotPlayer(p.name, p.id, p.image_path, school=p.school, deck=deck, difficulty="moderate", level=p.level)

            # Load RL model if this bot has one
            if p.model_path:
                try:
                    from rl.inference import load_model
                    model, _ = load_model(p.model_path)
                    model_agents[player.user_id] = (model, "cpu")
                except Exception as e:
                    print(f"[start_game] Could not load model for bot {p.id}: {e}")


        if p.team == "A":
            teamA.append(player)
        else:
            teamB.append(player)



    lobby.game = Game(teamA, teamB)
    lobby.game.model_agents = model_agents
    lobby.game.begin()
    lobby.started = True
    lobby.initial_game_state = _json.loads(_json.dumps(lobby.game.to_json_public()))

    socketio.emit("game_start", {}, room=gameId)

    if lobby.game.isAllBots(lobby.game.playing_team_i):
        while not lobby.game.winner and attemptTurnResolution(lobby, lobby.game):
            continue
        if lobby.game.winner:
            elo_changes = _compute_elo_changes(lobby, lobby.game.winner)
            match_result = build_match_result(lobby, lobby.game.winner, elo_changes)
            record_match_results(lobby, lobby.game.winner, elo_changes)
            save_game_log(gameId, lobby, match_result)
            socketio.emit("match_finished", match_result, room=gameId)
            del lobbies[gameId]
    return {"ok": True}


@socketio.on("leave_lobby")
def leave_lobby(data):
    gameId = data["gameId"]
    user_id = get_user_identity(request.sid)

    lobby = lobbies.get(gameId)
    if not lobby:
        return

    if user_id in lobby.players:
        del lobby.players[user_id]

    leave_room(gameId)

    if not any(not p.isBot for p in lobby.players.values()):
        del lobbies[gameId]
        list_games()
    else:
        socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)

    


# ========================================================
# Game Events
# ========================================================

@socketio.on("unwatch_game")
def unwatch_game(data):
    gameId = data.get("gameId")
    if gameId:
        leave_room(gameId + ":A")
        leave_room(gameId + ":B")


@socketio.on("watch_team")
def watch_team(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"error": "Missing game"}
    
    user_id = get_user_identity(request.sid)
    player = lobby.players.get(user_id)
    if not player:
        return {"error": "Player not in lobby"}
    if player.team == "A":
        join_room(gameId + ":A")
    else:
        join_room(gameId + ":B")

@socketio.on("get_game_state")
def get_game_state(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"error": "Missing game"}

    return lobby.game.to_json_public()


def build_hand(game, player):
    hand = []
    for card_play_info in game.playability[player.user_id]:
        card = card_play_info["card"]
        entry = {
            "card": card.card_def.id,
            "img_path": card.card_def.img_path,
            "instanceId": card.instance_id,
            "playable": card_play_info["playable"],
        }
        if card_play_info["playable"]:
            entry["targets"] = [p.user_id for p in card_play_info["targets"]]
        hand.append(entry)
    return hand


def build_player_view(game, player):
    data = player.to_json_private()
    data["hand"] = build_hand(game, player)
    data["team"] = 0 if player in game.teams[0] else 1
    return data

@socketio.on("get_player_state")
def get_player_state(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"error": "Missing game"}

    user_id = get_user_identity(request.sid)
    player = lobby.game.get_player(user_id)

    #emit("state_update", lobby.game.to_json_public())
    return build_player_view(lobby.game, player)


VALID_SCHOOLS = {"Fire", "Ice", "Storm", "Life", "Death", "Myth", "Balance"}
VALID_SCHOOLS_LOWER = {"fire", "ice", "storm", "life", "death", "myth", "balance"}


def _handle_in_game_leave(gameID, lobby, user_id):
    """Kill a mid-game player who left/disconnected, notify the room, and handle game end.

    Returns True if the lobby was removed (game over), False if the game continues.
    Caller is responsible for removing user_id from lobby.players afterward.
    """
    game = lobby.game
    player = game.get_player(user_id)

    if player:
        player.health = 0
        # Mark as passed if they haven't acted yet so the turn can still resolve
        if game.player_actions.get(user_id) is None:
            game.player_actions[user_id] = {"type": "pass"}

    # Notify remaining players in the room
    socketio.emit("player_left", {"userId": user_id, "gameState": game.to_json_public()}, room=gameID)

    # Check for immediate game end (e.g. killed the last player on a team)
    game.check_end()

    # Attempt to resolve the current turn if all alive players have now acted
    while not game.winner and attemptTurnResolution(lobby, game):
        continue

    if game.winner:
        elo_changes = _compute_elo_changes(lobby, game.winner)
        match_result = build_match_result(lobby, game.winner, elo_changes)
        record_match_results(lobby, game.winner, elo_changes)
        save_game_log(gameID, lobby, match_result)
        socketio.emit("match_finished", match_result, room=gameID)
        if gameID in lobbies:
            del lobbies[gameID]
        return True

    return False


def build_match_result(lobby, winner_team, elo_changes):
    """Build a match result payload with pre-match Elo and computed deltas."""
    players = []
    for p in lobby.players.values():
        ec = elo_changes.get(p.id, {"elo_change": 0, "new_elo": 0})
        players.append({
            "id": p.id,
            "name": p.name,
            "team": p.team,
            "image_path": p.image_path,
            "school": p.school,
            "level": p.level,
            "elo": 0 if p.isBot else (p.elo or 100),
            "isBot": p.isBot,
            "elo_change": ec["elo_change"],
        })
    return {"winner": winner_team, "players": players}


def record_match_results(lobby, winner_team, elo_changes):
    if getattr(lobby, "is_demo", False):
        return  # demo games don't persist to the database
    """Update wins/losses, per-school ELO, and per-school records in the DB."""
    db = SessionLocal()
    updated = {}  # player_id → fresh to_dict() to push after commit
    try:
        for p in lobby.players.values():
            if p.isBot:
                continue
            ps = db.query(PlayerState).filter_by(player_id=p.id).first()
            if not ps:
                continue
            school_key = (p.school or "balance").lower()

            # Update per-school win/loss counts (display only)
            if p.team == winner_team:
                ps.wins = (ps.wins or 0) + 1
                sw = dict(ps.school_wins or {})
                sw[school_key] = sw.get(school_key, 0) + 1
                ps.school_wins = sw
                flag_modified(ps, "school_wins")
            else:
                ps.losses = (ps.losses or 0) + 1
                sl = dict(ps.school_losses or {})
                sl[school_key] = sl.get(school_key, 0) + 1
                ps.school_losses = sl
                flag_modified(ps, "school_losses")

            # Update per-school ELO (drives level)
            ec = elo_changes.get(p.id)
            if ec:
                se = dict(ps.school_elos or {})
                se[school_key] = ec["new_elo"]
                ps.school_elos = se
                flag_modified(ps, "school_elos")
                ps.elo = ec["new_elo"]  # keep global elo in sync for legacy use

            db.flush()
            updated[p.id] = {"sid": p.sid, "data": ps.to_dict()}
        db.commit()
    except Exception as e:
        print(f"[record_match_results] Error: {e}")
        db.rollback()
        updated = {}
    finally:
        db.close()

    # Push fresh player_info to each player immediately
    for player_id, info in updated.items():
        if info["sid"]:
            socketio.emit("player_info", info["data"], to=info["sid"])


# ========================================================
# Profile Events
# ========================================================

@socketio.on("update_player_school")
def update_player_school(data):
    user_id = get_user_identity(request.sid)
    school = (data.get("school") or "").strip().title()

    if not user_id or school not in VALID_SCHOOLS:
        return {"ok": False, "error": "Invalid school"}

    db = SessionLocal()
    try:
        ps = db.query(PlayerState).filter_by(player_id=user_id).first()
        if not ps:
            return {"ok": False, "error": "Player not found"}
        ps.school = school
        db.commit()
        emit("player_info", ps.to_dict())
        return {"ok": True}
    finally:
        db.close()


@socketio.on("update_player_avatar")
def update_player_avatar(data):
    user_id = get_user_identity(request.sid)
    image_path = (data.get("image_path") or "").strip()

    if not user_id:
        return {"ok": False, "error": "Not authenticated"}

    from config import CHARACTER_IMAGE_PATH
    import os
    valid_paths = {
        os.path.join(CHARACTER_IMAGE_PATH, f).replace("\\", "/")
        for f in os.listdir(CHARACTER_IMAGE_PATH)
        if f.lower().endswith(".png")
    }
    if image_path not in valid_paths:
        return {"ok": False, "error": "Invalid avatar"}

    db = SessionLocal()
    try:
        ps = db.query(PlayerState).filter_by(player_id=user_id).first()
        if not ps:
            return {"ok": False, "error": "Player not found"}
        ps.image_path = image_path
        db.commit()
        emit("player_info", ps.to_dict())
        return {"ok": True}
    finally:
        db.close()


@socketio.on("update_player_name")
def update_player_name(data):
    user_id = get_user_identity(request.sid)
    name = (data.get("name") or "").strip()

    if not user_id:
        return {"ok": False, "error": "Not authenticated"}
    if not name:
        return {"ok": False, "error": "Name cannot be empty"}
    if len(name) > 32:
        return {"ok": False, "error": "Name too long (max 32 characters)"}

    db = SessionLocal()
    try:
        ps = db.query(PlayerState).filter_by(player_id=user_id).first()
        if not ps:
            return {"ok": False, "error": "Player not found"}
        ps.name = name
        db.commit()
        emit("player_info", ps.to_dict())
        return {"ok": True}
    finally:
        db.close()


DECK_MAX_CARDS = 30
DECK_MAX_COPIES = 4


def _validate_deck_cards(card_ids):
    """Returns an error string or None if valid."""
    from Card import CARD_BY_ID
    from collections import Counter
    if len(card_ids) > DECK_MAX_CARDS:
        return f"Deck cannot exceed {DECK_MAX_CARDS} cards"
    counts = Counter(card_ids)
    if any(v > DECK_MAX_COPIES for v in counts.values()):
        return f"Maximum {DECK_MAX_COPIES} copies of any card"
    unknown = [cid for cid in card_ids if cid not in CARD_BY_ID]
    if unknown:
        return f"Unknown card(s): {', '.join(unknown[:3])}"
    return None


@socketio.on("save_deck")
def save_deck(data):
    user_id = get_user_identity(request.sid)
    if not user_id:
        return {"ok": False, "error": "Not authenticated"}

    deck_index = data.get("deckIndex")   # None → create new
    name = (data.get("name") or "New Deck").strip()[:32]
    card_ids = data.get("card_ids", [])

    err = _validate_deck_cards(card_ids)
    if err:
        return {"ok": False, "error": err}

    db = SessionLocal()
    try:
        ps = db.query(PlayerState).filter_by(player_id=user_id).first()
        if not ps:
            return {"ok": False, "error": "Player not found"}

        active_level = ps._compute_school_level(ps.school or "balance")
        for card_id in card_ids:
            card_def = CARD_BY_ID.get(card_id)
            if card_def and card_def.pvp_level and card_def.pvp_level > active_level:
                return {"ok": False, "error": f"Deck contains cards above your current level (Lv.{active_level})"}
        decks = list(ps.decks or [])
        if deck_index is None:
            decks.append({"name": name, "card_ids": card_ids})
            new_index = len(decks) - 1
        else:
            if deck_index < 0 or deck_index >= len(decks):
                return {"ok": False, "error": "Invalid deck index"}
            decks[deck_index] = {"name": name, "card_ids": card_ids}
            new_index = deck_index
        ps.decks = decks
        db.commit()
        emit("player_info", ps.to_dict())
        return {"ok": True, "deckIndex": new_index}
    finally:
        db.close()


@socketio.on("delete_deck")
def delete_deck(data):
    user_id = get_user_identity(request.sid)
    if not user_id:
        return {"ok": False, "error": "Not authenticated"}

    deck_index = data.get("deckIndex")
    if deck_index is None:
        return {"ok": False, "error": "Missing deckIndex"}

    db = SessionLocal()
    try:
        ps = db.query(PlayerState).filter_by(player_id=user_id).first()
        if not ps:
            return {"ok": False, "error": "Player not found"}
        decks = list(ps.decks or [])
        if deck_index < 0 or deck_index >= len(decks):
            return {"ok": False, "error": "Invalid deck index"}
        decks.pop(deck_index)
        # Keep selected_deck_index in bounds
        if (ps.selected_deck_index or 0) >= len(decks):
            ps.selected_deck_index = max(0, len(decks) - 1)
        ps.decks = decks
        db.commit()
        emit("player_info", ps.to_dict())
        return {"ok": True}
    finally:
        db.close()


@socketio.on("update_player_deck")
def update_player_deck(data):
    user_id = get_user_identity(request.sid)
    deck_index = data.get("deckIndex", 0)

    if not user_id:
        return {"ok": False}

    db = SessionLocal()
    try:
        ps = db.query(PlayerState).filter_by(player_id=user_id).first()
        if not ps:
            return {"ok": False, "error": "Player not found"}
        decks = ps.decks or []
        if deck_index < 0 or deck_index >= len(decks):
            return {"ok": False, "error": "Invalid deck index"}

        from Card import CARD_BY_ID
        active_level = ps._compute_school_level(ps.school or "balance")
        for card_id in (decks[deck_index].get("card_ids") or []):
            card_def = CARD_BY_ID.get(card_id)
            if card_def and card_def.pvp_level and card_def.pvp_level > active_level:
                return {"ok": False, "error": f"Deck contains cards above your current level (Lv.{active_level})"}

        ps.selected_deck_index = deck_index
        db.commit()
        emit("player_info", ps.to_dict())
        return {"ok": True}
    finally:
        db.close()


def save_game_log(game_id, lobby, match_result):
    """Persist the full game replay to the database."""
    if getattr(lobby, "is_demo", False):
        return  # demo games are not logged
    if not lobby.initial_game_state or not lobby.replay_turns:
        return
    db = SessionLocal()
    try:
        player_ids = [str(p.id) for p in lobby.players.values() if not p.isBot]
        log_entry = GameLog(
            game_id=game_id,
            winner=match_result["winner"],
            player_ids=player_ids,
            players=match_result["players"],
            initial_game_state=lobby.initial_game_state,
            turns=lobby.replay_turns,
        )
        db.add(log_entry)
        db.commit()
        print(f"[save_game_log] Saved replay for game {game_id} ({len(lobby.replay_turns)} turns)")
    except Exception as e:
        print(f"[save_game_log] Error saving game {game_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _auth_user_id():
    """Extract user_id from Authorization: Bearer <token> header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = decode_jwt(token)
        return payload.get("user_id") or payload.get("guest_id")
    except Exception:
        return None


@app.route("/replays", methods=["GET"])
def get_replays():
    user_id = _auth_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        str_uid = str(user_id)
        logs = (
            db.query(GameLog)
            .filter(cast(GameLog.player_ids, String).like(f'%"{str_uid}"%'))
            .order_by(GameLog.created_at.desc())
            .limit(20)
            .all()
        )
        return jsonify({
            "replays": [
                {
                    "game_id": log.game_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                    "winner": log.winner,
                    "players": log.players,
                }
                for log in logs
            ]
        })
    finally:
        db.close()


@app.route("/replay/<game_id>", methods=["GET"])
def get_replay(game_id):
    user_id = _auth_user_id()
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    db = SessionLocal()
    try:
        log = db.query(GameLog).filter_by(game_id=game_id).first()
        if not log:
            return jsonify({"error": "Replay not found"}), 404
        if str(user_id) not in (log.player_ids or []):
            return jsonify({"error": "Not authorized"}), 403
        return jsonify({
            "game_id": log.game_id,
            "winner": log.winner,
            "players": log.players,
            "initial_game_state": log.initial_game_state,
            "turns": log.turns,
        })
    finally:
        db.close()


def attemptTurnResolution(lobby, game):
    with lobby._turn_lock:
        if not game.allActionsReceived():
            return False
        # Resolve actions and collect log
        turn_log = game.resolve_actions()
        opp = game.opposite_team(aliveOnly=True)
        if opp:
            turn_log.append({"type": "turn_end", "resting_player": opp[0].user_id})
        turn_log.extend(game.start_turn())

        prepareLog(turn_log)

        # Snapshot final authoritative state (deep-copied to avoid live pips reference mutation)
        final_game_state = _json.loads(_json.dumps(game.to_json_public()))

        # Accumulate turn data for replay storage
        lobby.replay_turns.append({"log": turn_log, "finalGameState": final_game_state})

        # Emit ONE event that starts client replay
        for p in game.getPlayers(includeBots=False):
            sid = lobby.UID_to_SID(p.user_id)
            if sid:
                emit(
                    "turn_resolved",
                    {
                        "finalGameState": final_game_state,
                        "finalPlayerState": build_player_view(game, p),
                        "log": turn_log,
                    },
                    to=sid
                )
        return True

def prepareLog(log):
    for entry in log:
        if entry["type"] == "result" and entry["result"] == "success":
            entry["card"] = CARD_BY_ID[entry["card"]].img_path



@socketio.on("set_school_pip")
def set_school_pip(data):
    gameId = data.get("gameId")
    school = (data.get("school") or "").strip().lower()

    if school not in VALID_SCHOOLS_LOWER:
        return {"ok": False, "error": "Invalid school"}

    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"ok": False, "error": "Game not found"}

    user_id = get_user_identity(request.sid)
    player = lobby.game.get_player(user_id)
    if not player:
        return {"ok": False, "error": "Player not found"}

    player.school_pip_select = school
    return {"ok": True}


@socketio.on("player_action")
def player_action(data):
    gameId = data["gameId"]
    action = data["action"]

    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"ok": False, "error": "Game not found"}
    
    user_id = get_user_identity(request.sid)
    game = lobby.game

    if game.winner:
        #print("Game finished")
        #game.print_log()
        return {"ok": False, "error": "Game finished"}

    
    if action["type"] == "leave":
        # Leave the socket rooms first so the leaver doesn't receive further game events
        leave_room(gameId)
        leave_room(gameId + ":A")
        leave_room(gameId + ":B")

        _handle_in_game_leave(gameId, lobby, user_id)
        lobby.players.pop(user_id, None)
        return {"ok": True}


    player = game.get_player(user_id)
    if player == None:
        print("[error] Could not get player")
        return {"ok": False}

    if action["type"] == "discard":
        card_id = action["cardId"]
        if not game.player_discard(player, card_id):
            return {"ok": False}

        return {"ok": True}
    
    if action["type"] == "pass":
        if not game.player_pass(player):
            return {"ok": False}
    
    if action["type"] == "cast":
        if not game.player_cast(player, action["cardIndex"], action["target"]):
            return {"ok": False}

    while not game.winner and attemptTurnResolution(lobby, game):
        continue

    if game.winner:
        elo_changes = _compute_elo_changes(lobby, game.winner)
        match_result = build_match_result(lobby, game.winner, elo_changes)
        record_match_results(lobby, game.winner, elo_changes)
        save_game_log(gameId, lobby, match_result)
        socketio.emit("match_finished", match_result, room=gameId)
        del lobbies[gameId]

    return {"ok": True}

# ========================================================
# Main Entrypoint
# ========================================================

try:
    cleanup_expired_guests()
except Exception as e:
    print(f"[startup] Guest cleanup failed: {e}")

# Add school_wins column to existing databases that predate this feature
try:
    from sqlalchemy import text as _text
    with engine.connect() as _conn:
        existing = [row[1] for row in _conn.execute(_text("PRAGMA table_info(player_state)"))]
        if "school_wins" not in existing:
            _conn.execute(_text("ALTER TABLE player_state ADD COLUMN school_wins JSON"))
            _conn.commit()
            print("[startup] Added school_wins column to player_state")
except Exception as e:
    print(f"[startup] school_wins migration failed: {e}")

try:
    GameLog.__table__.create(engine, checkfirst=True)
    print("[startup] Ensured game_logs table exists")
except Exception as e:
    print(f"[startup] game_logs table creation: {e}")

if __name__ == "__main__":
    import signal, sys
    def _shutdown(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    #Only for dev use, not on google cloud
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
