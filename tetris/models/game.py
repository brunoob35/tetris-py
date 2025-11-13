from __future__ import annotations

import random
from tetris.models.board import Board
from tetris.models.tetromino import Tetromino
from tetris.core.factory import random_piece
from tetris.core.constants import BOARD_WIDTH, BOARD_HEIGHT, BASE_FALL_INTERVAL, MAX_LEVEL_SPEED_MULTIPLIER

class TetrisGame:
    def __init__(self, rng_seed: int | None = None):
        # RNG determinístico da partida
        self._rng = random.Random(rng_seed) if rng_seed is not None else random.Random()

        self.board = Board(BOARD_WIDTH, BOARD_HEIGHT)

        # peças inicial e próxima usando o RNG interno
        self.current: Tetromino = random_piece(self._rng)
        self.next_piece: Tetromino = random_piece(self._rng)
        self.current.spawn(BOARD_WIDTH // 2 - 2, 0)

        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False

        self._fall_acc = 0.0

    # ----- Progressão de níveis / velocidade -----
    def fall_interval(self) -> float:
        capped = min(self.level, 10)
        mult = 1.0 + (capped - 1) * ((MAX_LEVEL_SPEED_MULTIPLIER - 1.0) / (10 - 1))
        return BASE_FALL_INTERVAL / mult

    # ----- Ciclo de atualização -----
    def tick(self, delta_time: float) -> None:
        if self.paused or self.game_over:
            return
        self._fall_acc += delta_time
        interval = self.fall_interval()
        while self._fall_acc >= interval:
            self._fall_acc -= interval
            self._gravity_step()

    def _gravity_step(self) -> None:
        if self.board.is_valid_move(self.current.shape, self.current.x, self.current.y + 1):
            self.current.move(0, 1)
        else:
            self._lock_piece()

    def _lock_piece(self) -> None:
        self.board.merge(self.current)
        cleared = self.board.clear_lines()
        if cleared:
            self.lines += cleared
            # Pontuação estilo clássico (multiplicado pelo nível)
            self.score += {1: 40, 2: 100, 3: 300, 4: 1200}.get(cleared, 0) * self.level
            self.level = 1 + self.lines // 10  # sobe a cada 10 linhas
        self._spawn_next()

    def _spawn_next(self) -> None:
        self.current = self.next_piece
        self.next_piece = random_piece(self._rng)
        self.current.spawn(BOARD_WIDTH // 2 - 2, 0)

        # Se não couber, é game over (modo clássico)
        if not self.board.is_valid_move(self.current.shape, self.current.x, self.current.y):
            self.game_over = True

    # ----- Entradas do jogador -----
    def move_left(self) -> None:
        if self._can_act():
            if self.board.is_valid_move(self.current.shape, self.current.x - 1, self.current.y):
                self.current.move(-1, 0)

    def move_right(self) -> None:
        if self._can_act():
            if self.board.is_valid_move(self.current.shape, self.current.x + 1, self.current.y):
                self.current.move(1, 0)

    def soft_drop(self) -> None:
        if self._can_act():
            if self.board.is_valid_move(self.current.shape, self.current.x, self.current.y + 1):
                self.current.move(0, 1)
                self.score += 1  # bônus de soft drop

    def hard_drop(self) -> None:
        if not self._can_act():
            return
        steps = 0
        while self.board.is_valid_move(self.current.shape, self.current.x, self.current.y + 1):
            self.current.move(0, 1)
            steps += 1
        self.score += 2 * steps
        self._lock_piece()

    def rotate(self) -> None:
        if not self._can_act():
            return
        rotated = self.current.peek_rotate()
        x, y = self.current.x, self.current.y
        for dx in (0, -1, 1, -2, 2):
            if self.board.is_valid_move(rotated, x + dx, y):
                self.current.shape = rotated
                self.current.x = x + dx
                return

    def toggle_pause(self) -> None:
        if not self.game_over:
            self.paused = not self.paused

    def _can_act(self) -> bool:
        return not self.paused and not self.game_over

    # ----- Reinício (modo clássico) -----
    def reset(self, rng_seed: int | None = None) -> None:
        self.__init__(rng_seed)
