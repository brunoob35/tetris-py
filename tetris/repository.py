# tetris/repository.py
import json
import datetime as dt
import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from .db import get_conn

# ---------- helpers de senha ----------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

# ---------- Usuários básicos ----------

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
    sql = text("SELECT id, username, email, password_hash FROM users WHERE username = :u")
    try:
        with get_conn() as conn:
            row = conn.execute(sql, {"u": username}).mappings().first()
            return dict(row) if row else None
    except Exception as e:
        print("[DB] get_user_by_username falhou:", e)
        return None

def get_user_by_id(user_id: int):
    sql = text("SELECT id, username, email, password_hash FROM users WHERE id = :id")
    try:
        with get_conn() as conn:
            row = conn.execute(sql, {"id": user_id}).mappings().first()
            return dict(row) if row else None
    except Exception as e:
        print("[DB] get_user_by_id falhou:", e)
        return None

# ---------- APIs de auth de mais alto nível ----------

def create_user_account(username: str, plain_password: str, email: str | None = None):
    """
    Cria usuário novo.
    Retorna (user_id, error_message). Se deu certo, error_message = None.
    """
    existing = get_user_by_username(username)
    if existing:
        return None, "Nome de usuário já existe."

    if not username or not plain_password:
        return None, "Usuário e senha são obrigatórios."

    pw_hash = hash_password(plain_password)
    user_id = create_user(username, pw_hash, email)
    if user_id is None:
        return None, "Erro ao criar usuário no banco."
    return user_id, None

def authenticate_user(username: str, plain_password: str):
    """
    Retorna dict do user se login ok, senão None.
    """
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(plain_password, user["password_hash"]):
        return None
    return user

# ---------- Partidas / games ----------

def start_game(user_id: int, rng_seed: int) -> int | None:
    """
    Cria um registro de jogo em andamento, salvando também a rng_seed
    que será usada depois no replay para recriar a mesma sequência de peças.
    """
    sql = text("""
        INSERT INTO games (user_id, started_at, rng_seed, status)
        VALUES (:uid, :st, :seed, 'in_progress')
    """)
    now = dt.datetime.utcnow()

    try:
        with get_conn() as conn:
            res = conn.execute(
                sql,
                {
                    "uid": user_id,
                    "st": now,
                    "seed": rng_seed,
                },
            )
            conn.commit()
            return res.lastrowid
    except Exception as e:
        print("[DB] start_game falhou:", e)
        return None

def finish_game(game_id: int | None, user_id: int | None, final_score: int, lines: int,
                level: int, duration_ms: int, status: str = "completed") -> None:
    if game_id is None or user_id is None:
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
        # depois de atualizar o game, atualiza high score
        update_high_score(user_id, final_score)
        # limpa save ativo dessa partida/usuário, se tiver
        clear_active_save(user_id)
    except Exception as e:
        print("[DB] finish_game falhou:", e)

# ---------- High score ----------

def update_high_score(user_id: int, score: int) -> None:
    sql_select = text("""
        SELECT best_score FROM user_high_scores WHERE user_id = :uid
    """)
    sql_insert = text("""
        INSERT INTO user_high_scores (user_id, best_score, best_score_at)
        VALUES (:uid, :score, :at)
    """)
    sql_update = text("""
        UPDATE user_high_scores
        SET best_score = :score, best_score_at = :at
        WHERE user_id = :uid
    """)

    now = dt.datetime.utcnow()
    try:
        with get_conn() as conn:
            row = conn.execute(sql_select, {"uid": user_id}).first()
            if not row:
                conn.execute(sql_insert, {"uid": user_id, "score": score, "at": now})
            else:
                current = row[0]
                if score > current:
                    conn.execute(sql_update, {"uid": user_id, "score": score, "at": now})
            conn.commit()
    except Exception as e:
        print("[DB] update_high_score falhou:", e)

# ---------- Saves ----------
def upsert_saved_game(user_id: int, game_id: int | None, state: dict) -> None:
    payload = json.dumps(state)
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
            val = row[0]
            if isinstance(val, str):
                return json.loads(val)
            return val
    except Exception as e:
        print("[DB] load_active_save falhou:", e)
        return None

def clear_active_save(user_id: int) -> None:
    sql = text("""
        UPDATE saved_games
        SET is_active = 0
        WHERE user_id = :uid AND is_active = 1
    """)
    try:
        with get_conn() as conn:
            conn.execute(sql, {"uid": user_id})
            conn.commit()
    except Exception as e:
        print("[DB] clear_active_save falhou:", e)

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


# ---------- Melhor score de um usuário ----------

def get_user_best_score(user_id: int) -> int | None:
    sql = text("SELECT best_score FROM user_high_scores WHERE user_id = :uid")
    try:
        with get_conn() as conn:
            row = conn.execute(sql, {"uid": user_id}).first()
            if not row:
                return None
            return row[0]
    except Exception as e:
        print("[DB] get_user_best_score falhou:", e)
        return None

# ---------- Partidas recentes de um usuário (pra replay) ----------

def get_user_recent_games(user_id: int, limit: int = 10):
    sql = text("""
        SELECT id, final_score, lines_cleared, level_reached, finished_at
        FROM games
        WHERE user_id = :uid AND status = 'completed'
        ORDER BY finished_at DESC
        LIMIT :lim
    """)
    try:
        with get_conn() as conn:
            rows = conn.execute(sql, {"uid": user_id, "lim": limit}).mappings().all()
            return [dict(r) for r in rows]
    except Exception as e:
        print("[DB] get_user_recent_games falhou:", e)
        return []


def get_game_rng_seed(game_id: int) -> int | None:
    """
    Busca a rng_seed salva para um game específico.
    Retorna None se não encontrar ou se der erro.
    """
    sql = text("SELECT rng_seed FROM games WHERE id = :gid")

    try:
        with get_conn() as conn:
            row = conn.execute(sql, {"gid": game_id}).first()
            if not row:
                return None

            # se a Row vier como mapping:
            if isinstance(row, dict) or hasattr(row, "keys"):
                return row["rng_seed"]

            # fallback: acesso posicional
            return row[0]
    except Exception as e:
        print("[DB] get_game_rng_seed falhou:", e)
        return None