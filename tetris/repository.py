# tetris/repository.py
import json
import datetime as dt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .db import get_conn

# ---------- Usuários ----------

def create_user(username: str, password_hash: str, email: str | None = None) -> int | None:
    sql = text("""
        INSERT INTO users (username, email, password_hash)
        VALUES (:u, :e, :p)
    """)
    try:
        with get_conn() as conn:
            res = conn.execute(sql, {"u": username, "e": email, "p": password_hash})
            conn.commit()
            return res.lastrowid
    except Exception as e:
        print("[DB] create_user falhou:", e)
        return None

def get_user_by_username(username: str):
    sql = text("SELECT id, username, password_hash FROM users WHERE username = :u")
    try:
        with get_conn() as conn:
            row = conn.execute(sql, {"u": username}).mappings().first()
            return dict(row) if row else None
    except Exception as e:
        print("[DB] get_user_by_username falhou:", e)
        return None

# ---------- Partidas / games ----------

def start_game(user_id: int, rng_seed: int | None) -> int | None:
    sql = text("""
        INSERT INTO games (user_id, started_at, rng_seed, status)
        VALUES (:uid, :st, :seed, 'in_progress')
    """)
    now = dt.datetime.utcnow()
    try:
        with get_conn() as conn:
            res = conn.execute(sql, {"uid": user_id, "st": now, "seed": rng_seed})
            conn.commit()
            return res.lastrowid
    except Exception as e:
        print("[DB] start_game falhou:", e)
        return None

def finish_game(game_id: int, final_score: int, lines: int,
                level: int, duration_ms: int, status: str = "completed") -> None:
    if game_id is None:
        # DB off / partida não registrada
        return
    sql = text("""
        UPDATE games
        SET finished_at = :fin,
            final_score = :score,
            lines_cleared = :lines,
            level_reached = :lvl,
            duration_ms = :dur,
            status = :st
        WHERE id = :gid
    """)
    now = dt.datetime.utcnow()
    try:
        with get_conn() as conn:
            conn.execute(sql, {
                "fin": now, "score": final_score, "lines": lines,
                "lvl": level, "dur": duration_ms, "st": status, "gid": game_id
            })
            conn.commit()
    except Exception as e:
        print("[DB] finish_game falhou:", e)

# ---------- Saves ----------

def upsert_saved_game(user_id: int, game_id: int | None, state: dict) -> None:
    payload = json.dumps(state)
    # se sua coluna for JSON mesmo:
    sql = text("""
        INSERT INTO saved_games (user_id, game_id, state_json, is_active)
        VALUES (:uid, :gid, CAST(:js AS JSON), 1)
        ON DUPLICATE KEY UPDATE
            game_id = VALUES(game_id),
            state_json = VALUES(state_json),
            is_active = 1,
            updated_at = CURRENT_TIMESTAMP
    """)
    try:
        with get_conn() as conn:
            conn.execute(sql, {"uid": user_id, "gid": game_id, "js": payload})
            conn.commit()
    except Exception as e:
        print("[DB] upsert_saved_game falhou:", e)

def load_active_save(user_id: int) -> dict | None:
    sql = text("""
        SELECT state_json
        FROM saved_games
        WHERE user_id = :uid AND is_active = 1
        ORDER BY updated_at DESC
        LIMIT 1
    """)
    try:
        with get_conn() as conn:
            row = conn.execute(sql, {"uid": user_id}).first()
            if not row:
                return None
            # se a coluna for JSON, row[0] já vem como dict; se for TEXT, faz loads
            val = row[0]
            if isinstance(val, str):
                return json.loads(val)
            return val
    except Exception as e:
        print("[DB] load_active_save falhou:", e)
        return None

# ---------- Replay ----------

def save_replay(game_id: int | None, replay_events: list[dict]) -> None:
    if game_id is None:
        return
    payload = json.dumps(replay_events)
    sql = text("""
        INSERT INTO game_replays (game_id, replay_data)
        VALUES (:gid, :data)
    """)
    try:
        with get_conn() as conn:
            conn.execute(sql, {"gid": game_id, "data": payload})
            conn.commit()
    except Exception as e:
        print("[DB] save_replay falhou:", e)

def load_replay(game_id: int) -> list[dict] | None:
    sql = text("SELECT replay_data FROM game_replays WHERE game_id = :gid")
    try:
        with get_conn() as conn:
            row = conn.execute(sql, {"gid": game_id}).first()
            if not row:
                return None
            return json.loads(row[0])
    except Exception as e:
        print("[DB] load_replay falhou:", e)
        return None

# ---------- Ranking ----------

def get_global_leaderboard(limit: int = 10):
    sql = text("""
        SELECT u.username, g.final_score, g.lines_cleared, g.level_reached, g.finished_at
        FROM games g
        JOIN users u ON u.id = g.user_id
        WHERE g.status = 'completed'
        ORDER BY g.final_score DESC, g.finished_at ASC
        LIMIT :lim
    """)
    try:
        with get_conn() as conn:
            rows = conn.execute(sql, {"lim": limit}).mappings().all()
            return [dict(r) for r in rows]
    except Exception as e:
        print("[DB] get_global_leaderboard falhou:", e)
        return []
