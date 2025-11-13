from dataclasses import dataclass
from typing import List

@dataclass
class Tetromino:
    shape: List[List[int]]
    color: tuple  # RGB
    x: int = 0
    y: int = 0

    def spawn(self, x, y):
        self.x, self.y = x, y

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def peek_rotate(self):
        rows = len(self.shape)
        cols = len(self.shape[0])
        rotated = [[0 for _ in range(rows)] for _ in range(cols)]
        for r in range(rows):
            for c in range(cols):
                rotated[c][rows - 1 - r] = self.shape[r][c]
        return rotated

    def apply_rotate(self):
        self.shape = self.peek_rotate()
