from typing import List
from dataclasses import dataclass, field

@dataclass
class Board:
    width: int
    height: int
    grid: List[List[int]] = field(init=False)

    def __post_init__(self):
        self.grid = [[0 for _ in range(self.width)] for _ in range(self.height)]

    def clear_all(self):
        for r in range(self.height):
            for c in range(self.width):
                self.grid[r][c] = 0

    def is_valid_move(self, shape, x, y):
        for r in range(len(shape)):
            for c in range(len(shape[0])):
                if shape[r][c]:
                    bx = x + c
                    by = y + r
                    if bx < 0 or bx >= self.width or by < 0 or by >= self.height:
                        return False
                    if self.grid[by][bx] != 0:
                        return False
        return True

    def merge(self, piece):
        s = piece.shape
        for r in range(len(s)):
            for c in range(len(s[0])):
                if s[r][c]:
                    bx = piece.x + c
                    by = piece.y + r
                    if 0 <= by < self.height and 0 <= bx < self.width:
                        self.grid[by][bx] = piece.color

    def clear_lines(self) -> int:
        cleared = 0
        r = self.height - 1
        while r >= 0:
            if all(self.grid[r][c] != 0 for c in range(self.width)):
                del self.grid[r]
                self.grid.insert(0, [0 for _ in range(self.width)])
                cleared += 1
            else:
                r -= 1
        return cleared

    def get_cell(self, r, c):
        return self.grid[r][c]
