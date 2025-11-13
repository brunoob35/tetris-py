# factory.py
import random
from .pieces import I_piece, O_piece, T_piece, S_piece, Z_piece, J_piece, L_piece
from .tetromino import Tetromino

PIECE_FACTORIES = [I_piece, O_piece, T_piece, S_piece, Z_piece, J_piece, L_piece]

def random_piece(rng: random.Random | None = None) -> Tetromino:
    """
    Gera uma peça usando o RNG passado.
    Se rng for None, usa o random global (mantém compatibilidade).
    """
    r = rng or random
    chosen = r.choice(PIECE_FACTORIES)
    tetromino = chosen()
    tetromino.spawn(3, 0)
    return tetromino
