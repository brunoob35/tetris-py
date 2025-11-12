import random
from .pieces import I_piece, O_piece, T_piece, S_piece, Z_piece, J_piece, L_piece
from .tetromino import Tetromino

# random_piece returns a Tetromino
def random_piece() -> Tetromino:
    chosen = random.choice([I_piece, O_piece, T_piece, S_piece, Z_piece, J_piece, L_piece])
    tetromino = chosen()
    tetromino.spawn(3, 0)
    return tetromino
