from __future__ import annotations

import time
import arcade
from arcade.gui import UIManager, UIFlatButton, UIInputText
from arcade.gui.events import UITextInputEvent

from .game import TetrisGame
from .constants import *
from . import repository, state_codec


# ---------- helpers da estilização 8-bit ----------

def _clamp(x: int) -> int:
    return max(0, min(255, x))


def _shade(rgb: tuple, factor: float) -> tuple:
    r, g, b, *a = rgb
    alpha = a[0] if a else 255
    return (
        _clamp(int(r * factor)),
        _clamp(int(g * factor)),
        _clamp(int(b * factor)),
        alpha,
    )


def _mix(rgb: tuple, other: tuple, t: float) -> tuple:
    r1, g1, b1, *a1 = rgb
    r2, g2, b2, *a2 = other
    alpha1 = a1[0] if a1 else 255
    alpha2 = a2[0] if a2 else 255
    return (
        _clamp(int(r1 + (r2 - r1) * t)),
        _clamp(int(g1 + (g2 - g1) * t)),
        _clamp(int(b1 + (b2 - b1) * t)),
        _clamp(int(alpha1 + (alpha2 - alpha1) * t)),
    )


def draw_block_8bit(left: float, bottom: float, size: float, base: tuple):
    u = max(1.0, size / 8.0)
    border_col = _shade(base, 0.55)
    fill_col = base
    light_col = _mix(base, (255, 255, 255, 255), 0.35)
    dark_col = _shade(base, 0.75)
    shine = (255, 255, 255, 100)

    arcade.draw_lbwh_rectangle_filled(left, bottom, size, size, border_col)
    arcade.draw_lbwh_rectangle_filled(
        left + u, bottom + u, size - 2 * u, size - 2 * u, fill_col
    )
    arcade.draw_lbwh_rectangle_filled(
        left + u, bottom + size - 2 * u, size - 3 * u, u, light_col
    )
    arcade.draw_lbwh_rectangle_filled(
        left + u, bottom + u, u, size - 3 * u, light_col
    )
    arcade.draw_lbwh_rectangle_filled(
        left + 2 * u, bottom + u, size - 3 * u, u, dark_col
    )
    arcade.draw_lbwh_rectangle_filled(
        left + size - 2 * u, bottom + 2 * u, u, size - 3 * u, dark_col
    )
    arcade.draw_lbwh_rectangle_filled(
        left + 2 * u, bottom + size - 3 * u, u, u, shine
    )
    arcade.draw_lbwh_rectangle_filled(
        left + 3 * u, bottom + size - 4 * u, u, u, shine
    )


# ---------- paleta retrô ----------

RETRO_BG = (12, 32, 28, 255)
RETRO_PANEL = (20, 50, 46, 255)
RETRO_PANEL_DARK = (8, 24, 20, 255)
RETRO_ACCENT = (110, 255, 140, 255)
RETRO_ACCENT_2 = (255, 200, 80, 255)
RETRO_TEXT = (200, 255, 220, 255)

RETRO_FONT = ("Press Start 2P", "Kenney Future", "Arial")

RETRO_BUTTON_STYLE = {
    "normal": {
        "font_name": RETRO_FONT,
        "font_size": 10,
        "font_color": (220, 235, 245, 255),
        "bg_color": (22, 40, 60, 255),
        "border_width": 3,
        "border_color": RETRO_ACCENT,
    },
    "hover": {
        "font_name": RETRO_FONT,
        "font_size": 10,
        "font_color": (255, 255, 255, 255),
        "bg_color": (38, 70, 90, 255),
        "border_width": 3,
        "border_color": RETRO_ACCENT_2,
    },
    "press": {
        "font_name": RETRO_FONT,
        "font_size": 9,
        "font_color": (210, 225, 235, 255),
        "bg_color": (10, 20, 30, 255),
        "border_width": 3,
        "border_color": RETRO_ACCENT_2,
    },
    "disabled": {
        "font_name": RETRO_FONT,
        "font_size": 10,
        "font_color": (120, 120, 120, 255),
        "bg_color": (40, 40, 40, 255),
        "border_width": 2,
        "border_color": (80, 80, 80, 255),
    },
}


# ============================================================
#                    INPUT DE SENHA COM BOLINHAS
# ============================================================


class UIBulletPasswordInput(UIInputText):
    """
    Input de senha que mostra ••• em vez do texto real.
    self.text continua guardando a senha verdadeira.
    """

    def on_event(self, event):
        # evita que ENTER crie quebra de linha dentro do campo
        if isinstance(event, UITextInputEvent):
            event.text = event.text.replace("\n", "").replace("\r", "")
        return super().on_event(event)

    def do_render(self, surface):
        # hack simples: troca self.text por bolinhas só enquanto desenha
        layout = getattr(self, "layout", None)
        caret = getattr(self, "caret", None)

        if layout is None or caret is None:
            # fallback: render normal se essa versão do arcade não tiver esses atributos
            return super().do_render(surface)

        layout.begin_update()
        pos = caret.position
        real_text = self.text

        self.text = "•" * len(real_text)
        super().do_render(surface)
        self.text = real_text

        caret.position = pos
        layout.end_update()


# ============================================================
#                           LOGIN
# ============================================================


class LoginView(arcade.View):
    """
    Tela de login/registro com leaderboard em card ao lado.
    """

    def __init__(self):
        super().__init__()
        self.ui = UIManager()

        self.username_input: UIInputText | None = None
        self.password_input: UIBulletPasswordInput | None = None
        self.status_text: arcade.Text | None = None

        self.title: arcade.Text | None = None
        self.subtitle: arcade.Text | None = None

        # layout dos cards
        self.card_width = 0
        self.card_height = 260
        self.login_panel_x = 0
        self.leader_panel_x = 0
        self.panel_y = 0

        self.leaderboard_lines: list[str] = []

    def on_show_view(self):
        self.window.set_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        arcade.set_background_color(RETRO_BG)
        self.ui.enable()
        self.ui.clear()

        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2

        # títulos
        self.title = arcade.Text(
            "TETRIS RETRÔ",
            center_x,
            WINDOW_HEIGHT - 70,
            RETRO_ACCENT,
            24,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )
        self.subtitle = arcade.Text(
            "Digite seu usuário e senha ou registre-se",
            center_x,
            WINDOW_HEIGHT - 100,
            RETRO_TEXT,
            10,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )

        # ----- layout dos dois cards -----
        inner_margin = 32
        gap = 24
        total_inner_width = WINDOW_WIDTH - 2 * inner_margin
        self.card_width = (total_inner_width - gap) / 2
        self.panel_y = center_y - self.card_height / 2
        self.login_panel_x = inner_margin
        self.leader_panel_x = self.login_panel_x + self.card_width + gap

        login_center_x = self.login_panel_x + self.card_width / 2
        login_center_y = center_y

        # ----- inputs -----
        input_width = self.card_width * 0.70
        input_height = 28

        self.username_input = UIInputText(
            width=input_width,
            height=input_height,
            text="",
        )
        self.username_input.placeholder_text = "Usuário"
        self.username_input.center_x = login_center_x
        self.username_input.center_y = login_center_y + 25

        self.password_input = UIBulletPasswordInput(
            width=input_width,
            height=input_height,
            text="",
        )
        self.password_input.placeholder_text = "Senha"
        self.password_input.center_x = login_center_x
        self.password_input.center_y = login_center_y - 15

        # ----- botões -----
        btn_width = self.card_width * 0.32
        btn_height = 32

        btn_login = UIFlatButton(
            text="ENTRAR",
            width=btn_width,
            height=btn_height,
            style=RETRO_BUTTON_STYLE,
        )
        btn_login.center_x = login_center_x - btn_width * 0.55
        btn_login.center_y = login_center_y - 65

        btn_register = UIFlatButton(
            text="REGISTRAR",
            width=btn_width,
            height=btn_height,
            style=RETRO_BUTTON_STYLE,
        )
        btn_register.center_x = login_center_x + btn_width * 0.55
        btn_register.center_y = login_center_y - 65

        # status (abaixo dos cards)
        self.status_text = arcade.Text(
            "",
            center_x,
            self.panel_y - 30,
            RETRO_ACCENT_2,
            10,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )

        self.ui.add(self.username_input)
        self.ui.add(self.password_input)
        self.ui.add(btn_login)
        self.ui.add(btn_register)

        @btn_login.event("on_click")
        def _on_login(_):
            self._handle_login()

        @btn_register.event("on_click")
        def _on_register(_):
            self._handle_register()

        self._build_leaderboard()

    # ---------- leaderboard ----------

    def _build_leaderboard(self):
        self.leaderboard_lines = []
        lb = repository.get_global_leaderboard(10)
        if not lb:
            self.leaderboard_lines.append("sem partidas ainda...")
            return

        rank = 1
        for row in lb:
            username = row["username"]
            score = row["final_score"]
            line = f"{rank:2d}. {username[:12]:<12} - {score:6d}"
            self.leaderboard_lines.append(line)
            rank += 1

    # ---------- desenho ----------

    def on_draw(self):
        self.clear()

        # fundo + moldura externa
        arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, RETRO_BG)
        arcade.draw_lbwh_rectangle_filled(
            16, 16, WINDOW_WIDTH - 32, WINDOW_HEIGHT - 32, RETRO_PANEL_DARK
        )
        arcade.draw_lbwh_rectangle_outline(
            16, 16, WINDOW_WIDTH - 32, WINDOW_HEIGHT - 32, RETRO_ACCENT, 3
        )

        # títulos
        self.title.draw()
        self.subtitle.draw()

        # card login
        arcade.draw_lbwh_rectangle_filled(
            self.login_panel_x,
            self.panel_y,
            self.card_width,
            self.card_height,
            RETRO_PANEL,
        )
        arcade.draw_lbwh_rectangle_outline(
            self.login_panel_x,
            self.panel_y,
            self.card_width,
            self.card_height,
            RETRO_ACCENT,
            2,
        )
        login_title = arcade.Text(
            "LOGIN",
            self.login_panel_x + self.card_width / 2,
            self.panel_y + self.card_height - 30,
            RETRO_ACCENT,
            12,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )
        login_title.draw()

        # card leaderboard
        arcade.draw_lbwh_rectangle_filled(
            self.leader_panel_x,
            self.panel_y,
            self.card_width,
            self.card_height,
            RETRO_PANEL,
        )
        arcade.draw_lbwh_rectangle_outline(
            self.leader_panel_x,
            self.panel_y,
            self.card_width,
            self.card_height,
            RETRO_ACCENT,
            2,
        )
        lb_title = arcade.Text(
            "TOP 10 GLOBAL",
            self.leader_panel_x + self.card_width / 2,
            self.panel_y + self.card_height - 30,
            RETRO_ACCENT_2,
            12,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )
        lb_title.draw()

        x_text = self.leader_panel_x + 20
        y_text = self.panel_y + self.card_height - 55
        for line in self.leaderboard_lines:
            t = arcade.Text(
                line,
                x_text,
                y_text,
                RETRO_TEXT,
                9,
                anchor_x="left",
                anchor_y="top",
                font_name=RETRO_FONT,
            )
            t.draw()
            y_text -= 18

        self.ui.draw()

        if self.status_text:
            self.status_text.draw()

    def on_hide_view(self):
        self.ui.disable()

    # ---------- helpers login ----------

    def _get_creds(self):
        u = self.username_input.text.strip() if self.username_input else ""
        p = self.password_input.text if self.password_input else ""
        return u, p

    def _set_status(self, msg: str):
        if self.status_text:
            self.status_text.text = msg

    def _handle_login(self):
        username, password = self._get_creds()
        if not username or not password:
            self._set_status("Informe usuário e senha.")
            return

        user = repository.authenticate_user(username, password)
        if not user:
            self._set_status("Usuário ou senha inválidos.")
            return

        self._set_status("Login OK, carregando...")
        self.window.show_view(MainMenuView(user_id=user["id"]))

    def _handle_register(self):
        username, password = self._get_creds()
        if not username or not password:
            self._set_status("Informe usuário e senha para registrar.")
            return

        user_id, err = repository.create_user_account(username, password)
        if err:
            self._set_status(err)
            return

        self._set_status("Usuário criado! Entrando...")
        self.window.show_view(MainMenuView(user_id=user_id))


# ============================================================
#                        MENU PRINCIPAL
# ============================================================


class MainMenuView(arcade.View):
    """
    Menu após login: mostra nick, recorde e opções de jogo/replay.
    """

    def __init__(self, user_id: int):
        super().__init__()
        self.ui = UIManager()
        self.user_id = user_id

        self.user = repository.get_user_by_id(user_id)
        self.best_score = repository.get_user_best_score(user_id)

        self.header_text: arcade.Text | None = None
        self.username_text: arcade.Text | None = None
        self.subheader_text: arcade.Text | None = None

        self.btn_new_game: UIFlatButton | None = None
        self.btn_replay: UIFlatButton | None = None

    def on_show_view(self):
        self.window.set_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        arcade.set_background_color(RETRO_BG)
        self.ui.enable()
        self.ui.clear()

        username = self.user["username"] if self.user else "Jogador"
        best = self.best_score or 0

        sidebar_left = BOARD_WIDTH * CELL_SIZE
        right_center_x = sidebar_left + SIDEBAR_WIDTH / 2

        self.header_text = arcade.Text(
            "Bem-vindo(a),",
            right_center_x,
            WINDOW_HEIGHT - 50,
            RETRO_TEXT,
            11,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )
        self.username_text = arcade.Text(
            username.upper(),
            right_center_x,
            WINDOW_HEIGHT - 80,
            RETRO_ACCENT,
            20,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )
        self.subheader_text = arcade.Text(
            f"Seu recorde: {best} pontos",
            right_center_x,
            WINDOW_HEIGHT - 110,
            RETRO_TEXT,
            11,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )

        panel_left = BOARD_WIDTH * CELL_SIZE
        panel_w = SIDEBAR_WIDTH
        panel_center_x = panel_left + panel_w / 2
        center_y = WINDOW_HEIGHT / 2

        btn_w = panel_w - 40
        btn_h = 40
        gap = 16

        self.btn_new_game = UIFlatButton(
            text="NOVO JOGO",
            width=btn_w,
            height=btn_h,
            style=RETRO_BUTTON_STYLE,
        )
        self.btn_new_game.center_x = panel_center_x
        self.btn_new_game.center_y = center_y + btn_h / 2 + gap / 2

        self.btn_replay = UIFlatButton(
            text="REPLAY DE PARTIDA",
            width=btn_w,
            height=btn_h,
            style=RETRO_BUTTON_STYLE,
        )
        self.btn_replay.center_x = panel_center_x
        self.btn_replay.center_y = center_y - btn_h / 2 - gap / 2

        self.ui.add(self.btn_new_game)
        self.ui.add(self.btn_replay)

        # vê se existe jogo salvo ativo
        saved_state = repository.load_active_save(self.user_id)
        if saved_state:
            # mostra pro usuário que é continuação
            self.btn_new_game.text = "CONTINUAR PARTIDA"

            @self.btn_new_game.event("on_click")
            def _start_classic(_):
                self.window.show_view(
                    PlayfieldView(user_id=self.user_id, loaded_state=saved_state)
                )
        else:
            self.btn_new_game.text = "NOVO JOGO"

            @self.btn_new_game.event("on_click")
            def _start_classic(_):
                self.window.show_view(PlayfieldView(user_id=self.user_id))

        @self.btn_replay.event("on_click")
        def _open_replay(_):
            self.window.show_view(ReplaySelectView(self.user_id))

    def _draw_playfield_frame(self):
        pf_w = BOARD_WIDTH * CELL_SIZE
        pf_h = BOARD_HEIGHT * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(-6, -6, pf_w + 12, pf_h + 12, RETRO_PANEL_DARK)
        arcade.draw_lbwh_rectangle_outline(
            -6, -6, pf_w + 12, pf_h + 12, (60, 90, 80, 255), 3
        )
        arcade.draw_lbwh_rectangle_outline(
            -9, -9, pf_w + 18, pf_h + 18, (20, 40, 34, 255), 3
        )
        for r in range(BOARD_HEIGHT + 1):
            arcade.draw_line(
                0, r * CELL_SIZE, pf_w, r * CELL_SIZE, (30, 60, 50, 255)
            )
        for c in range(BOARD_WIDTH + 1):
            arcade.draw_line(
                c * CELL_SIZE, 0, c * CELL_SIZE, pf_h, (30, 60, 50, 255)
            )

    def _draw_sidebar_background(self):
        left = BOARD_WIDTH * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, RETRO_PANEL)
        arcade.draw_lbwh_rectangle_outline(
            left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, RETRO_ACCENT, 2
        )

    def on_draw(self):
        self.clear()

        arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, RETRO_BG)
        arcade.draw_lbwh_rectangle_filled(
            12, 12, WINDOW_WIDTH - 24, WINDOW_HEIGHT - 24, RETRO_PANEL_DARK
        )
        arcade.draw_lbwh_rectangle_outline(
            12, 12, WINDOW_WIDTH - 24, WINDOW_HEIGHT - 24, RETRO_ACCENT, 3
        )

        self._draw_playfield_frame()
        self._draw_sidebar_background()

        if self.header_text:
            self.header_text.draw()
        if self.username_text:
            self.username_text.draw()
        if self.subheader_text:
            self.subheader_text.draw()

        self.ui.draw()

    def on_hide_view(self):
        self.ui.disable()


# ============================================================
#                  SELEÇÃO DE PARTIDA PARA REPLAY
# ============================================================


class ReplaySelectView(arcade.View):
    def __init__(self, user_id: int):
        super().__init__()
        self.ui = UIManager()
        self.user_id = user_id
        self.info_text: arcade.Text | None = None

    def on_show_view(self):
        self.window.set_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        arcade.set_background_color(RETRO_BG)
        self.ui.enable()
        self.ui.clear()

        center_x = WINDOW_WIDTH / 2

        self.info_text = arcade.Text(
            "Selecione uma partida para replay",
            center_x,
            WINDOW_HEIGHT - 80,
            RETRO_ACCENT,
            14,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )

        games = repository.get_user_recent_games(self.user_id, limit=10)
        y = WINDOW_HEIGHT - 130

        if not games:
            self.info_text.text = "Você ainda não tem partidas concluídas."
        else:
            for g in games:
                finished = g["finished_at"]
                when = finished.strftime("%d/%m %H:%M") if finished else "?"
                label = (
                    f"{when} | {g['final_score']} pts, "
                    f"lvl {g['level_reached']}, {g['lines_cleared']} linhas"
                )

                btn = UIFlatButton(
                    text=label,
                    width=WINDOW_WIDTH - 160,
                    height=30,
                    style=RETRO_BUTTON_STYLE,
                )
                btn.center_x = center_x
                btn.center_y = y
                y -= 40

                game_id = g["id"]

                @btn.event("on_click")
                def _make_cb(_, gid=game_id):
                    self.window.show_view(ReplayView(self.user_id, gid))

                self.ui.add(btn)

        btn_back = UIFlatButton(
            text="VOLTAR",
            width=160,
            height=32,
            style=RETRO_BUTTON_STYLE,
        )
        btn_back.center_x = center_x
        btn_back.center_y = 60
        self.ui.add(btn_back)

        @btn_back.event("on_click")
        def _go_back(_):
            self.window.show_view(MainMenuView(self.user_id))

    def on_draw(self):
        self.clear()
        arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, RETRO_BG)
        arcade.draw_lbwh_rectangle_filled(
            12, 12, WINDOW_WIDTH - 24, WINDOW_HEIGHT - 24, RETRO_PANEL_DARK
        )
        arcade.draw_lbwh_rectangle_outline(
            12, 12, WINDOW_WIDTH - 24, WINDOW_HEIGHT - 24, RETRO_ACCENT, 3
        )

        if self.info_text:
            self.info_text.draw()

        self.ui.draw()

    def on_hide_view(self):
        self.ui.disable()

# ============================================================
#                             REPLAY
# ============================================================
class ReplayView(arcade.View):
    """
    Tela de replay de uma partida.
    Recria o TetrisGame com a mesma rng_seed salva no banco e reaplica os inputs gravados.
    """

    def __init__(self, user_id: int, game_id: int):
        super().__init__()
        self.user_id = user_id
        self.game_id = game_id

        arcade.set_background_color(RETRO_BG)

        # pega a seed do jogo no banco e recria o game garantindo a mesma sequência de peças
        rng_seed = repository.get_game_rng_seed(game_id)
        self.game = TetrisGame(rng_seed=rng_seed)

        # eventos de replay: lista de dicts {"t": float, "key": int}
        self.events = repository.load_replay(game_id) or []
        self.event_index = 0
        self._start_time = time.time()

        # coordenadas da sidebar
        self.sidebar_left = BOARD_WIDTH * CELL_SIZE
        self.sidebar_center_x = self.sidebar_left + SIDEBAR_WIDTH / 2

        # texto de info alinhado no centro da porção direita (sidebar)
        self.info_text = arcade.Text(
            f"Replay jogo #{game_id}  |  ESC/M: voltar",
            self.sidebar_center_x,
            WINDOW_HEIGHT - 40,
            RETRO_ACCENT,
            11,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )

        # HUD lateral
        left = self.sidebar_left + 10
        top = WINDOW_HEIGHT - 70
        self.txt_score = arcade.Text(
            "",
            left,
            top,
            RETRO_TEXT,
            12,
            anchor_x="left",
            anchor_y="top",
            font_name=RETRO_FONT,
        )
        self.txt_level = arcade.Text(
            "",
            left,
            top - 20,
            RETRO_TEXT,
            12,
            anchor_x="left",
            anchor_y="top",
            font_name=RETRO_FONT,
        )
        self.txt_lines = arcade.Text(
            "",
            left,
            top - 40,
            RETRO_TEXT,
            12,
            anchor_x="left",
            anchor_y="top",
            font_name=RETRO_FONT,
        )

    def on_show_view(self):
        self.window.set_size(WINDOW_WIDTH, WINDOW_HEIGHT)

    def on_draw(self):
        self.clear()
        # fundo + moldura geral
        arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, RETRO_BG)
        arcade.draw_lbwh_rectangle_filled(
            12, 12, WINDOW_WIDTH - 24, WINDOW_HEIGHT - 24, RETRO_PANEL_DARK
        )
        arcade.draw_lbwh_rectangle_outline(
            12, 12, WINDOW_WIDTH - 24, WINDOW_HEIGHT - 24, RETRO_ACCENT, 3
        )

        self._draw_playfield()
        self._draw_sidebar()
        self.info_text.draw()

    def _draw_playfield(self):
        pf_w = BOARD_WIDTH * CELL_SIZE
        pf_h = BOARD_HEIGHT * CELL_SIZE

        arcade.draw_lbwh_rectangle_filled(-6, -6, pf_w + 12, pf_h + 12, RETRO_PANEL)
        arcade.draw_lbwh_rectangle_outline(
            -6, -6, pf_w + 12, pf_h + 12, (60, 90, 80, 255), 3
        )
        arcade.draw_lbwh_rectangle_outline(
            -9, -9, pf_w + 18, pf_h + 18, (20, 40, 34, 255), 3
        )
        for r in range(BOARD_HEIGHT + 1):
            arcade.draw_line(
                0, r * CELL_SIZE, pf_w, r * CELL_SIZE, (30, 60, 50, 255)
            )
        for c in range(BOARD_WIDTH + 1):
            arcade.draw_line(
                c * CELL_SIZE, 0, c * CELL_SIZE, pf_h, (30, 60, 50, 255)
            )

        # células fixas do tabuleiro
        for r in range(self.game.board.height):
            for c in range(self.game.board.width):
                val = self.game.board.get_cell(r, c)
                if val:
                    cx = c * CELL_SIZE + CELL_SIZE / 2
                    cy = (BOARD_HEIGHT - 1 - r) * CELL_SIZE + CELL_SIZE / 2
                    draw_block_8bit(cx - CELL_SIZE / 2, cy - CELL_SIZE / 2, CELL_SIZE, val)

        # peça atual
        s = self.game.current.shape
        color = self.game.current.color
        for r in range(len(s)):
            for c in range(len(s[0])):
                if s[r][c]:
                    bx = self.game.current.x + c
                    by = self.game.current.y + r
                    cx = bx * CELL_SIZE + CELL_SIZE / 2
                    cy = (BOARD_HEIGHT - 1 - by) * CELL_SIZE + CELL_SIZE / 2
                    draw_block_8bit(cx - CELL_SIZE / 2, cy - CELL_SIZE / 2, CELL_SIZE, color)

    def _draw_sidebar(self):
        left = self.sidebar_left
        arcade.draw_lbwh_rectangle_filled(left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, RETRO_PANEL)
        arcade.draw_lbwh_rectangle_outline(
            left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, RETRO_ACCENT, 2
        )

        self.txt_score.text = f"Pontuação: {self.game.score}"
        self.txt_level.text = f"Nível: {self.game.level}"
        self.txt_lines.text = f"Linhas: {self.game.lines}"

        self.txt_score.draw()
        self.txt_level.draw()
        self.txt_lines.draw()

    def on_update(self, delta_time: float):
        # timeline do replay baseada no tempo desde o início
        elapsed = time.time() - self._start_time

        # aplica todos os eventos cujo tempo já passou
        while (
            self.event_index < len(self.events)
            and self.events[self.event_index]["t"] <= elapsed
        ):
            ev = self.events[self.event_index]
            self._apply_event(ev)
            self.event_index += 1

        # avança gravidade normalmente
        self.game.tick(delta_time)

    def _apply_event(self, ev: dict):
        key = ev.get("key")
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

    def on_key_press(self, key, modifiers):
        if key in (arcade.key.ESCAPE, arcade.key.M):
            self.window.show_view(MainMenuView(self.user_id))

# ============================================================
#                        TELA DO TABULEIRO
# ============================================================


class PlayfieldView(arcade.View):
    """
    Tabuleiro principal do Tetris, ligado ao backend de jogo e repositório.
    """

    def __init__(self, user_id: int, loaded_state: dict | None = None):
        super().__init__()
        arcade.set_background_color(RETRO_BG)

        self.user_id = user_id
        self.rng_seed = int(time.time_ns())

        if loaded_state is not None:
            self.game = state_codec.state_to_game(loaded_state)
        else:
            self.game = TetrisGame(rng_seed=self.rng_seed)

        self.game_id = repository.start_game(self.user_id, self.rng_seed)
        self._start_time = time.time()
        self._finished_persisted = False
        self._replay_events: list[dict] = []

        left = BOARD_WIDTH * CELL_SIZE + 10
        top = WINDOW_HEIGHT - 20
        self.txt_score = arcade.Text("", left, top, RETRO_TEXT, 14, anchor_x="left", anchor_y="top")
        self.txt_level = arcade.Text("", left, top - 24, RETRO_TEXT, 14, anchor_x="left", anchor_y="top")
        self.txt_lines = arcade.Text("", left, top - 48, RETRO_TEXT, 14, anchor_x="left", anchor_y="top")
        self.txt_speed = arcade.Text("", left, top - 72, RETRO_TEXT, 12, anchor_x="left", anchor_y="top")
        self.txt_next = arcade.Text("Próxima:", left, top - 104, RETRO_TEXT, 14, anchor_x="left", anchor_y="top")

        base_y = 120
        self.txt_controls = [
            arcade.Text("Controles:", left, base_y + 60, RETRO_TEXT, 12, anchor_y="baseline"),
            arcade.Text("← → mover", left, base_y + 40, RETRO_TEXT, 12, anchor_y="baseline"),
            arcade.Text("↑ rotacionar", left, base_y + 24, RETRO_TEXT, 12, anchor_y="baseline"),
            arcade.Text("↓ cair suave", left, base_y + 8, RETRO_TEXT, 12, anchor_y="baseline"),
            arcade.Text("Espaço: queda rápida", left, base_y - 8, RETRO_TEXT, 12, anchor_y="baseline"),
            arcade.Text(
                "P: Pausa  |  R: Menu (se Game Over)  |  M: Menu",
                left,
                base_y - 24,
                RETRO_TEXT,
                11,
                anchor_y="baseline",
            ),
        ]

        self.txt_paused = arcade.Text(
            "PAUSADO",
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT / 2 + 30,
            RETRO_TEXT,
            20,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )
        self.txt_paused_hint = arcade.Text(
            "P: Continuar  |  ESC/M: Volta ao Menu (salva jogo)",
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT / 2 - 5,
            RETRO_TEXT,
            13,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )
        self.txt_game_over = arcade.Text(
            "GAME OVER — pressione R para voltar ao menu",
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT / 2,
            RETRO_TEXT,
            16,
            anchor_x="center",
            anchor_y="center",
            font_name=RETRO_FONT,
        )

    def on_show_view(self):
        self.window.set_size(WINDOW_WIDTH, WINDOW_HEIGHT)

    def on_draw(self):
        self.clear()
        self._draw_playfield()
        self._draw_sidebar()

        if self.game.paused:
            arcade.draw_lbwh_rectangle_filled(
                0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, (0, 0, 0, 160)
            )
            self.txt_paused.draw()
            self.txt_paused_hint.draw()

        if self.game.game_over:
            arcade.draw_lbwh_rectangle_filled(
                0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, (0, 0, 0, 160)
            )
            self.txt_game_over.draw()

    def _draw_playfield(self):
        pf_w = BOARD_WIDTH * CELL_SIZE
        pf_h = BOARD_HEIGHT * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(-6, -6, pf_w + 12, pf_h + 12, RETRO_PANEL_DARK)
        arcade.draw_lbwh_rectangle_outline(
            -6, -6, pf_w + 12, pf_h + 12, (80, 80, 80, 255), 3
        )
        arcade.draw_lbwh_rectangle_outline(
            -9, -9, pf_w + 18, pf_h + 18, (30, 30, 30, 255), 3
        )

        for r in range(BOARD_HEIGHT + 1):
            arcade.draw_line(0, r * CELL_SIZE, pf_w, r * CELL_SIZE, (40, 40, 40, 255))
        for c in range(BOARD_WIDTH + 1):
            arcade.draw_line(c * CELL_SIZE, 0, c * CELL_SIZE, pf_h, (40, 40, 40, 255))

        for r in range(self.game.board.height):
            for c in range(self.game.board.width):
                val = self.game.board.get_cell(r, c)
                if val:
                    cx = c * CELL_SIZE + CELL_SIZE / 2
                    cy = (BOARD_HEIGHT - 1 - r) * CELL_SIZE + CELL_SIZE / 2
                    draw_block_8bit(cx - CELL_SIZE / 2, cy - CELL_SIZE / 2, CELL_SIZE, val)

        s = self.game.current.shape
        color = self.game.current.color
        for r in range(len(s)):
            for c in range(len(s[0])):
                if s[r][c]:
                    bx = self.game.current.x + c
                    by = self.game.current.y + r
                    cx = bx * CELL_SIZE + CELL_SIZE / 2
                    cy = (BOARD_HEIGHT - 1 - by) * CELL_SIZE + CELL_SIZE / 2
                    draw_block_8bit(cx - CELL_SIZE / 2, cy - CELL_SIZE / 2, CELL_SIZE, color)

    def _draw_sidebar(self):
        left = BOARD_WIDTH * CELL_SIZE
        arcade.draw_lbwh_rectangle_filled(left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, RETRO_PANEL)
        arcade.draw_lbwh_rectangle_outline(
            left, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, RETRO_ACCENT, 2
        )

        self.txt_score.text = f"Pontuação: {self.game.score}"
        self.txt_level.text = f"Nível: {self.game.level}"
        self.txt_lines.text = f"Linhas: {self.game.lines}"
        self.txt_speed.text = f"Velocidade: {1.0 / self.game.fall_interval():.2f} quedas/s"

        self.txt_score.draw()
        self.txt_level.draw()
        self.txt_lines.draw()
        self.txt_speed.draw()
        self.txt_next.draw()
        for t in self.txt_controls:
            t.draw()

        s = self.game.next_piece.shape
        color = self.game.next_piece.color
        scale = 0.5
        px = left + 20
        py_top = WINDOW_HEIGHT - 150
        for r in range(len(s)):
            for c in range(len(s[0])):
                if s[r][c]:
                    cx = px + c * CELL_SIZE * scale + (CELL_SIZE * scale) / 2
                    cy = py_top - r * CELL_SIZE * scale - (CELL_SIZE * scale) / 2
                    draw_block_8bit(
                        cx - (CELL_SIZE * scale) / 2,
                        cy - (CELL_SIZE * scale) / 2,
                        CELL_SIZE * scale,
                        color,
                    )

    def on_update(self, delta_time: float):
        self.game.tick(delta_time)

        if self.game.game_over and not self._finished_persisted:
            self._finished_persisted = True
            now = time.time()
            duration_ms = int((now - self._start_time) * 1000)

            repository.finish_game(
                self.game_id,
                user_id=self.user_id,
                final_score=self.game.score,
                lines=self.game.lines,
                level=self.game.level,
                duration_ms=duration_ms,
                status="completed",
            )
            repository.save_replay(self.game_id, self._replay_events)

    def on_key_press(self, key, modifiers):
        # salvar e voltar pro menu (M ou ESC)
        if key in (arcade.key.M, arcade.key.ESCAPE):
            # garante que o jogo não volte “pausado” quando continuar
            self.game.paused = False
            state = state_codec.game_to_state(self.game)
            repository.upsert_saved_game(self.user_id, self.game_id, state)
            self.window.show_view(MainMenuView(user_id=self.user_id))
            return

        if key == arcade.key.P:
            self.game.toggle_pause()
            return

        if self.game.game_over:
            if key == arcade.key.R:
                self.window.show_view(MainMenuView(user_id=self.user_id))
            return

        if self.game.paused:
            return

        # registra evento pro replay
        if key in (
            arcade.key.LEFT,
            arcade.key.RIGHT,
            arcade.key.DOWN,
            arcade.key.UP,
            arcade.key.X,
            arcade.key.W,
            arcade.key.SPACE,
        ):
            self._replay_events.append(
                {"t": time.time() - self._start_time, "key": key}
            )

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
