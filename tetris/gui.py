from __future__ import annotations
import arcade
from arcade.gui import UIManager, UIFlatButton
from .game import TetrisGame
from .constants import *
import time
from . import repository, state_codec

# ---------- helpers da estilização 8-bit ----------
def _clamp(x: int) -> int: return max(0, min(255, x))
def _shade(rgb: tuple, factor: float) -> tuple:
    r, g, b = rgb[:3]
    return (_clamp(int(r * factor)), _clamp(int(g * factor)), _clamp(int(b * factor)))
def _mix(rgb: tuple, other: tuple, t: float) -> tuple:
    r1, g1, b1 = rgb[:3]; r2, g2, b2 = other[:3]
    return (_clamp(int(r1 + (r2 - r1) * t)),
            _clamp(int(g1 + (g2 - g1) * t)),
            _clamp(int(b1 + (b2 - b1) * t)))
def draw_block_8bit(left: float, bottom: float, size: float, base: tuple):
    u = max(1.0, size / 8.0)
    border_col = _shade(base, 0.55)
    fill_col   = base
    light_col  = _mix(base, (255, 255, 255), 0.35)
    dark_col   = _shade(base, 0.75)
    shine      = (255, 255, 255, 100)
    arcade.draw_lbwh_rectangle_filled(left, bottom, size, size, border_col)
    arcade.draw_lbwh_rectangle_filled(left + u, bottom + u, size - 2*u, size - 2*u, fill_col)
    arcade.draw_lbwh_rectangle_filled(left + u, bottom + size - 2*u, size - 3*u, u, light_col)
    arcade.draw_lbwh_rectangle_filled(left + u, bottom + u, u, size - 3*u, light_col)
    arcade.draw_lbwh_rectangle_filled(left + 2*u, bottom + u, size - 3*u, u, dark_col)
    arcade.draw_lbwh_rectangle_filled(left + size - 2*u, bottom + 2*u, u, size - 3*u, dark_col)
    arcade.draw_lbwh_rectangle_filled(left + 2*u, bottom + size - 3*u, u, u, shine)
    arcade.draw_lbwh_rectangle_filled(left + 3*u, bottom + size - 4*u, u, u, shine)

# ============================================================
#                        MENU INICIAL
# ============================================================
class MainMenuView(arcade.View):
    """
    Menu inicial. Não instancia o jogo até o usuário escolher "Tetris clássico".
    O botão "Tetris Avançado (em breve)" é visível, mas não faz nada ao clicar.
    """
    def __init__(self, user_id: int = 1):
        super().__init__()
        self.ui = UIManager()
        self.user_id = user_id  # por enquanto usuário fixo

        # Textos
        self.title: arcade.Text | None = None
        self.hint: arcade.Text | None = None
        self.menu_hdr: arcade.Text | None = None
        self.speed_l1: arcade.Text | None = None
        self.speed_l10: arcade.Text | None = None
        self.choose_lbl: arcade.Text | None = None
        self.soon_lbl: arcade.Text | None = None  # legenda "(em breve)"

        # Botões
        self.btn_classic: UIFlatButton | None = None
        self.btn_advanced: UIFlatButton | None = None  # inativo

    def on_show_view(self):
        self.window.set_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        arcade.set_background_color(arcade.color.BLACK)
        self.ui.enable(); self.ui.clear()

        # Título e dica (topo central)
        self.title = arcade.Text("TETRIS retrô", WINDOW_WIDTH/2, WINDOW_HEIGHT-36,
                                 arcade.color.WHITE, 28, anchor_x="center", anchor_y="top")
        self.hint = arcade.Text("↑ Rotacionar  |  ← → Mover  |  ↓ Queda suave  |  Espaço Queda rápida",
                                WINDOW_WIDTH/2, WINDOW_HEIGHT-64,
                                arcade.color.LIGHT_GRAY, 12, anchor_x="center", anchor_y="top")

        # Painel direito
        sidebar_left = BOARD_WIDTH * CELL_SIZE
        self.menu_hdr = arcade.Text("Menu", sidebar_left + 14, WINDOW_HEIGHT - 24,
                                    arcade.color.WHITE, 16, anchor_x="left", anchor_y="top")

        # Velocidades teóricas (nível 1 e 10)
        v1  = 1.0 / self._fall_interval_for_level(1)
        v10 = 1.0 / self._fall_interval_for_level(10)
        self.speed_l1 = arcade.Text(f"Velocidade (nível 1): {v1:.2f} quedas/s",
                                    sidebar_left + 14, WINDOW_HEIGHT - 110,
                                    arcade.color.WHITE, 12, anchor_x="left", anchor_y="top")
        self.speed_l10 = arcade.Text(f"Velocidade (nível 10): {v10:.2f} quedas/s",
                                     sidebar_left + 14, WINDOW_HEIGHT - 130,
                                     arcade.color.WHITE, 12, anchor_x="left", anchor_y="top")

        # ---- Botões centralizados no painel direito ----
        panel_left = sidebar_left
        panel_center_x = panel_left + SIDEBAR_WIDTH / 2
        panel_center_y = WINDOW_HEIGHT / 2

        btn_w = SIDEBAR_WIDTH - 40
        btn_h = 44
        gap = 12
        total_h = 2 * btn_h + gap
        top_center_y = panel_center_y + total_h / 2

        self.btn_classic  = UIFlatButton(text="Novo jogo — Tetris clássico", width=btn_w, height=btn_h)
        self.btn_advanced = UIFlatButton(text="Novo jogo — Tetris Avançado", width=btn_w, height=btn_h)

        # Posicionamento pelo centro (Arcade 3.x)
        self.btn_classic.center_x  = panel_center_x
        self.btn_classic.center_y  = top_center_y - btn_h / 2
        self.btn_advanced.center_x = panel_center_x
        self.btn_advanced.center_y = self.btn_classic.center_y - (btn_h + gap)

        self.ui.add(self.btn_classic); self.ui.add(self.btn_advanced)

        # Legendas
        self.choose_lbl = arcade.Text("Escolha o modo:",
                                      panel_left + 14,
                                      self.btn_classic.center_y + btn_h / 2 + 24,
                                      arcade.color.LIGHT_GRAY, 12,
                                      anchor_x="left", anchor_y="baseline")
        self.soon_lbl = arcade.Text("(em breve)", self.btn_advanced.center_x,
                                    self.btn_advanced.center_y - btn_h/2 - 16,
                                    arcade.color.GRAY, 11, anchor_x="center", anchor_y="baseline")

        # Handler apenas para o clássico
        @self.btn_classic.event("on_click")
        def _start_classic(_):
            # tenta carregar jogo salvo; se existir, continua
            saved_state = repository.load_active_save(self.user_id)
            if saved_state:
                self.window.show_view(PlayfieldView(user_id=self.user_id, loaded_state=saved_state))
            else:
                self.window.show_view(PlayfieldView(user_id=self.user_id))

        # Intencionalmente NÃO registramos clique no "Avançado" (fica inativo)

    # --- Helpers ---
    def _fall_interval_for_level(self, level: int) -> float:
        capped = min(level, 10)
        mult = 1.0 + (capped - 1) * ((MAX_LEVEL_SPEED_MULTIPLIER - 1.0) / (10 - 1))
        return BASE_FALL_INTERVAL / mult

    def _draw_playfield_frame(self):
        pf_w = BOARD_WIDTH * CELL_SIZE
        pf_h = BOARD_HEIGHT * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(-6, -6, pf_w + 12, pf_h + 12, (20, 20, 20))
        arcade.draw_lbwh_rectangle_outline(-6, -6, pf_w + 12, pf_h + 12, (80, 80, 80), 3)
        arcade.draw_lbwh_rectangle_outline(-9, -9, pf_w + 18, pf_h + 18, (30, 30, 30), 3)
        for r in range(BOARD_HEIGHT + 1):
            arcade.draw_line(0, r * CELL_SIZE, pf_w, r * CELL_SIZE, (35, 35, 35))
        for c in range(BOARD_WIDTH + 1):
            arcade.draw_line(c * CELL_SIZE, 0, c * CELL_SIZE, pf_h, (35, 35, 35))

    def _draw_sidebar(self):
        left = BOARD_WIDTH * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, (10, 10, 10))
        arcade.draw_lbwh_rectangle_outline(left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, (60, 60, 60), 2)
        self.menu_hdr.draw()
        self.speed_l1.draw(); self.speed_l10.draw()
        self.choose_lbl.draw(); self.soon_lbl.draw()

    def on_draw(self):
        self.clear()
        self.title.draw()
        self.hint.draw()
        self._draw_playfield_frame()
        self._draw_sidebar()
        self.ui.draw()

    def on_hide_view(self):
        self.ui.disable()

# ============================================================
#                      TELA DO TABULEIRO
# ============================================================
class PlayfieldView(arcade.View):
    """
    Renderiza o tabuleiro e o painel, e conversa com a lógica do TetrisGame (clássico).
    """
    def __init__(self, user_id: int = 1, loaded_state: dict | None = None):
        super().__init__()
        arcade.set_background_color(arcade.color.BLACK)

        self.user_id = user_id

        # seed pra, no futuro, ter replay determinístico (se você ajustar o RNG do TetrisGame)
        self.rng_seed = int(time.time_ns())

        # estado do jogo (novo ou carregado)
        if loaded_state is not None:
            self.game = state_codec.state_to_game(loaded_state)
            self.game_id = repository.start_game(self.user_id, self.rng_seed)
        else:
            self.game = TetrisGame()
            self.game_id = repository.start_game(self.user_id, self.rng_seed)

        # HUD
        left = BOARD_WIDTH * CELL_SIZE + 10
        top = WINDOW_HEIGHT - 20
        self.txt_score = arcade.Text("", left, top, arcade.color.WHITE, 14, anchor_x="left", anchor_y="top")
        self.txt_level = arcade.Text("", left, top - 24, arcade.color.WHITE, 14, anchor_x="left", anchor_y="top")
        self.txt_lines = arcade.Text("", left, top - 48, arcade.color.WHITE, 14, anchor_x="left", anchor_y="top")
        self.txt_speed = arcade.Text("", left, top - 72, arcade.color.LIGHT_GRAY, 12, anchor_x="left", anchor_y="top")
        self.txt_next  = arcade.Text("Próxima:", left, top - 104, arcade.color.WHITE, 14, anchor_x="left", anchor_y="top")
        base_y = 120
        self.txt_controls = [
            arcade.Text("Controles:", left, base_y + 60, arcade.color.LIGHT_GRAY, 12, anchor_y="baseline"),
            arcade.Text("← → mover", left, base_y + 40, arcade.color.LIGHT_GRAY, 12, anchor_y="baseline"),
            arcade.Text("↑ rotacionar", left, base_y + 24, arcade.color.LIGHT_GRAY, 12, anchor_y="baseline"),
            arcade.Text("↓ cair suave", left, base_y + 8,  arcade.color.LIGHT_GRAY, 12, anchor_y="baseline"),
            arcade.Text("Espaço: queda rápida", left, base_y - 8, arcade.color.LIGHT_GRAY, 12, anchor_y="baseline"),
            arcade.Text("P: Pausa  |  R: Menu (se Game Over)  |  M: Menu (salva)", left, base_y - 24,
                        arcade.color.LIGHT_GRAY, 12, anchor_y="baseline"),
        ]
        self.txt_paused = arcade.Text("PAUSADO", WINDOW_WIDTH/2, WINDOW_HEIGHT/2 + 30,
                                      arcade.color.WHITE, 20, anchor_x="center", anchor_y="center")
        self.txt_game_over = arcade.Text("GAME OVER — pressione R para voltar ao menu",
                                         WINDOW_WIDTH/2, WINDOW_HEIGHT/2,
                                         arcade.color.WHITE, 18, anchor_x="center", anchor_y="center")

        # tracking de tempo e replay
        self._start_time = time.time()
        self._finished_persisted = False
        self._replay_events: list[dict] = []

    def on_show_view(self):
        self.window.set_size(WINDOW_WIDTH, WINDOW_HEIGHT)

    # --------- desenho ---------
    def on_draw(self):
        self.clear()
        self._draw_playfield()
        self._draw_sidebar()
        if self.game.paused:
            arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, (0, 0, 0, 160))
            self.txt_paused.draw()
        if self.game.game_over:
            arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, (0, 0, 0, 160))
            self.txt_game_over.draw()

    def _draw_playfield(self):
        pf_w = BOARD_WIDTH * CELL_SIZE
        pf_h = BOARD_HEIGHT * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(-6, -6, pf_w + 12, pf_h + 12, (20, 20, 20))
        arcade.draw_lbwh_rectangle_outline(-6, -6, pf_w + 12, pf_h + 12, (80, 80, 80), 3)
        arcade.draw_lbwh_rectangle_outline(-9, -9, pf_w + 18, pf_h + 18, (30, 30, 30), 3)
        for r in range(BOARD_HEIGHT + 1):
            arcade.draw_line(0, r * CELL_SIZE, pf_w, r * CELL_SIZE, (40, 40, 40))
        for c in range(BOARD_WIDTH + 1):
            arcade.draw_line(c * CELL_SIZE, 0, c * CELL_SIZE, pf_h, (40, 40, 40))

        # células do tabuleiro
        for r in range(self.game.board.height):
            for c in range(self.game.board.width):
                val = self.game.board.get_cell(r, c)
                if val:
                    cx = c * CELL_SIZE + CELL_SIZE/2
                    cy = (BOARD_HEIGHT - 1 - r) * CELL_SIZE + CELL_SIZE/2
                    draw_block_8bit(cx - CELL_SIZE/2, cy - CELL_SIZE/2, CELL_SIZE, val)

        # peça atual
        s = self.game.current.shape; color = self.game.current.color
        for r in range(len(s)):
            for c in range(len(s[0])):
                if s[r][c]:
                    bx = self.game.current.x + c
                    by = self.game.current.y + r
                    cx = bx * CELL_SIZE + CELL_SIZE/2
                    cy = (BOARD_HEIGHT - 1 - by) * CELL_SIZE + CELL_SIZE/2
                    draw_block_8bit(cx - CELL_SIZE/2, cy - CELL_SIZE/2, CELL_SIZE, color)

    def _draw_sidebar(self):
        left = BOARD_WIDTH * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, (10, 10, 10))
        arcade.draw_lbwh_rectangle_outline(left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, (60, 60, 60), 2)

        self.txt_score.text = f"Pontuação: {self.game.score}"
        self.txt_level.text = f"Nível: {self.game.level}"
        self.txt_lines.text = f"Linhas: {self.game.lines}"
        self.txt_speed.text = f"Velocidade: {1.0 / self.game.fall_interval():.2f} quedas/s"

        self.txt_score.draw(); self.txt_level.draw(); self.txt_lines.draw(); self.txt_speed.draw()
        self.txt_next.draw()
        for t in self.txt_controls: t.draw()

        # preview da próxima
        s = self.game.next_piece.shape; color = self.game.next_piece.color
        scale = 0.5
        px = left + 20; py_top = WINDOW_HEIGHT - 150
        for r in range(len(s)):
            for c in range(len(s[0])):
                if s[r][c]:
                    cx = px + c * CELL_SIZE * scale + (CELL_SIZE * scale)/2
                    cy = py_top - r * CELL_SIZE * scale - (CELL_SIZE * scale)/2
                    draw_block_8bit(cx - (CELL_SIZE*scale)/2, cy - (CELL_SIZE*scale)/2,
                                    CELL_SIZE*scale, color)

    # --------- update ---------
    def on_update(self, delta_time: float):
        self.game.tick(delta_time)

        if self.game.game_over and not self._finished_persisted:
            self._finished_persisted = True
            now = time.time()
            duration_ms = int((now - self._start_time) * 1000)

            # só tenta registrar no DB se tiver game_id válido
            if self.game_id is not None:
                repository.finish_game(
                    self.game_id,
                    final_score=self.game.score,
                    lines=self.game.lines,
                    level=self.game.level,
                    duration_ms=duration_ms,
                    status="completed",
                )
                repository.save_replay(self.game_id, self._replay_events)

    # --------- input ---------
    def on_key_press(self, key, modifiers):
        # registra input pro replay
        t = time.time() - self._start_time
        self._replay_events.append({"t": t, "key": int(key), "mods": int(modifiers)})

        if key == arcade.key.M:
            state = state_codec.game_to_state(self.game)
            # se game_id for None, ainda assim salva (função trata)
            repository.upsert_saved_game(self.user_id, self.game_id, state)
            self.window.show_view(MainMenuView(user_id=self.user_id))
            return

        if key == arcade.key.P:
            self.game.toggle_pause(); return

        if self.game.game_over:
            if key == arcade.key.R:
                self.window.show_view(MainMenuView(user_id=self.user_id))
            return

        if self.game.paused:
            return

        if key == arcade.key.LEFT:
            self.game.move_left()
        elif key == arcade.key.RIGHT:
            self.game.move_right()
        elif key == arcade.key.DOWN:
            self.game.soft_drop()
        elif key in (arcade.key.UP, arcade.key.X, arcade.key.W):
            self.game.rotate()
        elif key == arcade.key.SPACE:
            self.game.hard_drop()
