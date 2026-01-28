from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import os
import uuid
import time

# ===== Game Logic =====
from Game import Game, createBotPlayer
from Player import loadPlayer
from Card import CARD_BY_ID

# ===== Auth System =====
from auth_routes import auth
from jwt_utils import decode_jwt
from utils import getRandomPlayerImage

# ===== Database =====
from database import *
from models import *

from socketio.exceptions import ConnectionRefusedError

# --------------------------------------------------------
# Flask + CORS Setup
# --------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "game.db")

ORIGIN = "https://w101-website.vercel.app"

#blahsdkfh
app = Flask(__name__)

# Apply Flask-CORS (still useful for normal routes)
CORS(app,supports_credentials=True,resources={r"/*": {"origins": ORIGIN}},)

app.register_blueprint(auth, url_prefix="/auth")


socketio = SocketIO(app,cors_allowed_origins=[ORIGIN],logger=True,engineio_logger=True,)

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


'''
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = ORIGIN
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    response = jsonify({"error": str(e)})
    response.status_code = 500
    response.headers["Access-Control-Allow-Origin"] = ORIGIN
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

'''
# ========================================================
# In-Memory Data Models
# ========================================================

class LobbyPlayer:
    def __init__(self, user_id, sid, name, image_path, team="A", isBot=False):
        self.id = user_id
        self.name = name
        self.team = team
        self.isReady = False
        self.sid = sid  # socket id
        self.image_path = image_path
        self.isBot = isBot


class Lobby:
    def __init__(self, host_id):
        self.players = {}      # userId → LobbyPlayer
        self.host = host_id
        self.game = None       # becomes Game() after start
        self.started = False
        self.watchers = set()  # socket IDs watching game state

    def team_counts(self):
        amount = {"A": 0, "B": 0}
        for player in self.players.values():
            amount[player.team] += 1
        return amount

    def isReady(self):
        team_counts = self.team_counts()
        if team_counts["A"] == 0 or team_counts["B"] == 0:
            return False
        print("What are we seeing")
        print(list(filter(lambda p: not p.isBot, self.players.values())))
        return all([player.isReady for player in list(filter(lambda p: not p.isBot, self.players.values()))])
    
    def snapshot(self):
        return {
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "team": p.team,
                    "isReady": p.isReady,
                    "image_path": p.image_path
                }
                for p in self.players.values()
            ],
            "host": self.host
        }

    def UID_to_SID(self, uid):
        return self.players[uid].sid
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

from flask import session, request

@socketio.on("connect")
def on_connect(auth):
    print("PLAYER IS CONNECTING")

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
    session["user_id"] = user_id

    print(
        f"[connect] socket {request.sid} authenticated "
        f"as {user_type} {user_id}"
    )

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    user_id =  connected_users.pop(sid, None)

    print(f"[disconnect] user={user_id}, socket={sid}")

    gameID_to_remove = None

    for gameID, lobby in lobbies.items():
        # Find the player associated with this socket
        print(lobby.players.keys())
        if user_id not in lobby.players.keys():
            continue

        del lobby.players[user_id]
        print(f"[disconnect] removed player {user_id} from lobby {gameID}")

        # Mark empty lobby for cleanup
        if not lobby.players:
            gameID_to_remove = gameID

        break  # a socket should only belong to one lobby
    

    if gameID_to_remove is not None:
        del lobbies[gameID_to_remove]
        print(f"[disconnect] removed empty lobby {gameID_to_remove}")




    


# ========================================================
# Menu Events
# ========================================================

@socketio.on("get_player_info")
def get_player_info():
    user_id = session.get("user_id")   # ← works perfectly
    print(user_id)

    if not user_id:
        emit("error", {"msg": "Not authenticated"})
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


@socketio.on("create_game")
def create_game(data):
    user_id = get_user_identity(request.sid)
    if not user_id:
        return {"ok": False, "error": "Not authenticated"}

    gameId = str(uuid.uuid4())[:8]

    lobby = Lobby(host_id=user_id)
    lobbies[gameId] = lobby

    


    player = LobbyPlayer(
        user_id=user_id,
        sid=request.sid,
        name=user_id,
        image_path=get_player_from_db(user_id)["image_path"]
    )
    lobby.players[user_id] = player

    join_room(gameId)
    #emit("game_list", [], broadcast=True)
    list_games()

    return {"gameId": gameId}



@socketio.on("create_bot_game")
def create_bot_game(data):
    user_id = get_user_identity(request.sid)
    gameId = str(uuid.uuid4())[:8]

    lobby = Lobby(host_id=user_id)
    lobbies[gameId] = lobby

    # host joins
    lobby.players[user_id] = LobbyPlayer(user_id, sid=request.sid, name=user_id, image_path=get_player_from_db(user_id)["image_path"])
    lobby.players[user_id].sid = request.sid

#    def __init__(self, user_id, sid, name, image_path, team="A", isBot=False):
    # add bots
    for i in range(3):
        bot_id = f"bot_{i}"
        lobby.players[bot_id] = LobbyPlayer(bot_id, None, f"Bot {i}", getRandomPlayerImage(), team="B", isBot=True)

    join_room(gameId)
    return {"gameId": gameId}


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
        team_counts = lobby.team_counts()
        lobby.players[user_id] = LobbyPlayer(
            user_id, 
            sid=request.sid, 
            name=user_id,
            image_path=get_player_from_db(user_id)["image_path"],
            team=("A" if team_counts["A"] < team_counts["B"] else "B")
        )

    lobby.players[user_id].sid = request.sid

    join_room(gameId)

    # Notify lobby watchers
    socketio.emit("lobby_update", lobby.snapshot(), room=gameId)
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
    user_id = get_user_identity(request.sid)
    lobby = lobbies.get(gameId)
    if not lobby:
        return

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

    if lobby.isReady():
        start_game(data)

    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("switch_team")
def switch_team(data):
    gameId = data["gameId"]
    playerId = data["playerId"]
    new_team = data["team"]

    lobby = lobbies.get(gameId)
    if not lobby:
        return

    if playerId in lobby.players:
        lobby.players[playerId].team = new_team

    socketio.emit("update_lobby_state", lobby.snapshot(), room=gameId)


@socketio.on("start_game")
def start_game(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby:
        return {"ok": False, "error": "Lobby missing"}

    '''
    host_id = lobby.host
    caller = get_user_identity(request.sid)

    if caller != host_id:
        return {"ok": False, "error": "Only host can start"}
    
    # Require all real players ready
    for p in lobby.players.values():
        if not p.id.startswith("bot_") and not p.isReady:
            return {"ok": False, "error": "All players must be ready"}
    '''
    # Build teams for Game()
    teamA = []
    teamB = []

    for p in lobby.players.values():
        # Query DB using user_id...
        player = None
        if not p.isBot: 
            db = SessionLocal()
            try:
                print(p.id)

                player = db.query(PlayerState).filter_by(player_id=p.id).first()

                if not player:
                    emit("error", {"msg": "Player not found"})
                    return
            finally:
                db.close()
            
            player = loadPlayer(player.to_dict())
        
        else:
            player = createBotPlayer(p.name, p.id, p.image_path)


        if p.team == "A":
            teamA.append(player)
        else:
            teamB.append(player)

        

    lobby.game = Game(teamA, teamB)
    lobby.game.begin()
    lobby.started = True

    socketio.emit("game_start", {}, room=gameId)

    if lobby.game.isAllBots(lobby.game.playing_team_i):
        print("WHATTTTTTT")
        attemptTurnResolution(lobby, lobby.game)
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
    
    if len(lobby.players) == 0:
        del lobbies[gameId]
        list_games()
    else:
        get_lobby_state(data)

    


# ========================================================
# Game Events
# ========================================================

'''
@socketio.on("watch_game")
def watch_game(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby or not lobby.started:
        return

    lobby.watchers.add(request.sid)
    join_room(gameId)
'''

@socketio.on("watch_team")
def watch_team(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"error": "Missing game"}
    
    user_id = get_user_identity(request.sid)
    player = lobby.players[user_id]
    if player.team == "A":
        print(f"[join] {user_id} joins room {gameId + ':A'}")
        join_room(gameId + ":A")
    else:
        print(f"[join] {user_id} joins room {gameId + ':B'}")
        join_room(gameId + ":B")

@socketio.on("get_game_state")
def get_game_state(data):
    gameId = data["gameId"]
    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"error": "Missing game"}

    return lobby.game.to_json_public()


def build_player_view(game, player):

    data = player.to_json_private()
    hand = []

    for card_play_info in game.playability[player.user_id]:
        
        if card_play_info["playable"]:
            target_ids = [p.user_id for p in card_play_info["targets"]]

            hand.append({"card": card_play_info["card"].card_def.id, "img_path": card_play_info["card"].card_def.img_path, "playable": True, "targets": target_ids})
        else:
            hand.append({"card": card_play_info["card"].card_def.id, "img_path": card_play_info["card"].card_def.img_path, "playable": False})
    

    data["hand"] = hand

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


def attemptTurnResolution(lobby, game):
    if game.allActionsReceived():
        print("At least we are here!!!!")
        # Resolve actions and collect log
        turn_log = game.resolve_actions()
        turn_log.append({"type": "turn_end", "resting_player": game.opposite_team(aliveOnly=True)[0].user_id})
        turn_log.extend(game.start_turn())

        prepareLog(turn_log)
        
        # Snapshot final authoritative state
        final_game_state = game.to_json_public()

        # Emit ONE event that starts client replay
        for p in game.getPlayers(includeBots=False):
            emit(
                "turn_resolved",
                {
                    "finalGameState": final_game_state,
                    "finalPlayerState": build_player_view(game, p),
                    "log": turn_log,
                },
                to=lobby.UID_to_SID(p.user_id)
            )
        return True
    return False

def prepareLog(log):
    for entry in log:
        if entry["type"] == "result" and entry["result"] == "success":
            entry["card"] = CARD_BY_ID[entry["card"]].img_path



@socketio.on("player_action")
def player_action(data):
    print("DATA")
    print(data)

    gameId = data["gameId"]
    action = data["action"]

    lobby = lobbies.get(gameId)
    if not lobby or not lobby.game:
        return {"ok": False, "error": "Game not found"}
    
    user_id = get_user_identity(request.sid)
    game = lobby.game

    if game.winner:
        print("Game finished")
        game.print_log()
        return {"ok": False, "error": "Game finished"}

    
    if action["type"] == "leave":
        leave_room(gameId)

        team = -1
        if user_id in [player.user_id for player in game.teams[0]]:

            i = [player.user_id for player in game.teams[0]].index(user_id)
            team = 0
        else:
            if user_id in [player.user_id for player in game.teams[1]]:
                i = [player.user_id for player in game.teams[1]].index(user_id)
                team = 1
            else:
                return {"ok": False}
            
        game.teams[team].pop(i)
        leave_room(gameId + f":{'A' if team == 0 else 'B'}")

        emit("game_state_update", lobby.game.to_json_public(), room=gameId)

        if lobby.game.check_end():
            emit("match_finished", game.winner, room=gameId)
        
        return {"ok": True}


    player = game.get_player(user_id)
    if player == None:
        print("[error] Could not get player")
        return {"ok": False}

    if action["type"] == "discard":
        i = action["cardIndex"]
        if not game.player_discard(player, i):
            return {"ok": False}

        #emit("player_state_update", build_player_view(game, player), to=request.sid)
        return {"ok": True}
    
    if action["type"] == "pass":
        if not game.player_pass(player):
            return {"ok": False}
    
    if action["type"] == "cast":
        if not game.player_cast(player, action["cardIndex"], action["target"]):
            return {"ok": False}

    while not game.winner and attemptTurnResolution(lobby, game):
        print("Another round")
        continue
    

    if game.winner:
        emit("match_finished", game.winner, room=gameId)
        game.print_log()

    return {"ok": True}

# ========================================================
# Main Entrypoint
# ========================================================

if __name__ == "__main__":
    #Only for dev use, not on google cloud
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
