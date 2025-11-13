# tetris/state_codec.py
from .game import TetrisGame
from .board import Board
from .tetromino import Tetromino

def game_to_state(game: TetrisGame) -> dict:
    def piece_to_dict(p: Tetromino | None):
        if p is None:
            return None
        return {
            "shape": p.shape,
            "color": p.color,
            "x": p.x,
            "y": p.y,
        }

    return {
        "board": game.board.grid,
        "current": piece_to_dict(game.current),
        "next_piece": piece_to_dict(game.next_piece),
        "score": game.score,
        "lines": game.lines,
        "level": game.level,
        "fall_interval": game.fall_interval(),  # se for método
        "paused": game.paused,
        "game_over": game.game_over,
    }

def state_to_game(state: dict) -> TetrisGame:
    g = TetrisGame()
    # board
    g.board = Board(len(state["board"][0]), len(state["board"]))
    g.board.grid = state["board"]

    def dict_to_piece(d):
        if d is None:
            return None
        p = Tetromino(d["shape"], tuple(d["color"]))
        p.x = d["x"]
        p.y = d["y"]
        return p

    g.current = dict_to_piece(state["current"])
    g.next_piece = dict_to_piece(state["next_piece"])
    g.score = state["score"]
    g.lines = state["lines"]
    g.level = state["level"]
    # se fall_interval for armazenado internamente, ajusta aqui
    g.paused = state["paused"]
    g.game_over = state["game_over"]
    return g
