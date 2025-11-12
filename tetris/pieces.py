from .tetromino import Tetromino

CYAN    = ( 86, 180, 233)
YELLOW  = (240, 228,  66)
MAGENTA = (204, 121, 167)
GREEN   = (  0, 158, 115)
RED     = (213,  94,   0)
BLUE    = (  0, 114, 178)
ORANGE  = (230, 159,   0)

def I_piece(): return Tetromino([[1,1,1,1]], CYAN)
def O_piece(): return Tetromino([[1,1],[1,1]], YELLOW)
def T_piece(): return Tetromino([[0,1,0],[1,1,1]], MAGENTA)
def S_piece(): return Tetromino([[0,1,1],[1,1,0]], GREEN)
def Z_piece(): return Tetromino([[1,1,0],[0,1,1]], RED)
def J_piece(): return Tetromino([[1,0,0],[1,1,1]], BLUE)
def L_piece(): return Tetromino([[0,0,1],[1,1,1]], ORANGE)
