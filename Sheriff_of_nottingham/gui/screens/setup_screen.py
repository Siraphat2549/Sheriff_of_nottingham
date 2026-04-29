"""Game setup screen — pygame version."""
import pygame
from gui import theme
from gui.widgets import Button, TextInput, RadioGroup


_DEFAULT_NAMES = ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5"]


class SetupScreen:

    MIN_PLAYERS = 2
    MAX_PLAYERS = 5

    def __init__(self, app, error: str = ""):
        self.app = app
        self._error = error
        self._widgets = []
        self._build()

    def _build(self):
        self._widgets.clear()
        W, H = self.app.screen.get_size()
        cx = W // 2
        panel_w = min(700, W - 80)
        panel_x = cx - panel_w // 2

        self._num_players = RadioGroup(
            panel_x + 10, 200,
            options=[2, 3, 4, 5], initial=3,
            font=theme.FONT_BODY,
            on_change=self._on_player_count_change)

        self._player_inputs = []
        self._panel_x = panel_x
        self._panel_w = panel_w
        self._rebuild_player_inputs(3)

        back_btn = Button(
            pygame.Rect(cx - 230, H - 80, 180, 46),
            "Back",
            bg=theme.BTN_BG, hover_bg=theme.BTN_HOVER,
            font=theme.FONT_H2, on_click=self.app.show_main_menu)

        start_btn = Button(
            pygame.Rect(cx + 50, H - 80, 180, 46),
            "Start Game",
            bg=theme.BTN_OK_BG, hover_bg=theme.BTN_OK_HOVER,
            font=theme.FONT_H2, on_click=self._validate_and_start)

        self._buttons = [back_btn, start_btn]

    def _rebuild_player_inputs(self, num_players: int):
        self._player_inputs.clear()
        for i in range(num_players):
            rect = pygame.Rect(
                self._panel_x + 10,
                280 + i * 50,
                self._panel_w // 2 - 20,
                34)
            ti = TextInput(rect, initial=_DEFAULT_NAMES[i])
            self._player_inputs.append(ti)

    def _on_player_count_change(self, value):
        self._rebuild_player_inputs(value)

    # ── Events ─────────────────────────────────────────────────────────── #

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._build()
            return
        self._num_players.handle_event(event)
        for ti in self._player_inputs:
            ti.handle_event(event)
        for btn in self._buttons:
            btn.handle_event(event)

    def update(self, dt_ms: int):
        for ti in self._player_inputs:
            ti.update(dt_ms)

    # ── Validation ─────────────────────────────────────────────────────── #

    def _validate_and_start(self):
        configs = []
        seen = set()

        for i, ti in enumerate(self._player_inputs):
            name = ti.text.strip()
            if not name:
                self.app.show_message("Invalid Name",
                                      f"Player {i + 1} name cannot be empty.")
                return
            if name.lower() in seen:
                self.app.show_message("Duplicate Name",
                                      f"Name '{name}' is already used.\nPlease use unique names.")
                return
            seen.add(name.lower())
            configs.append({"name": name, "is_ai": False})

        self.app.start_game(configs)

    # ── Drawing ────────────────────────────────────────────────────────── #

    def draw(self, surface):
        W, H = surface.get_size()
        cx = W // 2

        # Gradient background + ornate border frame
        theme.draw_gradient_rect(surface, (0, 0, W, H), theme.BG_DARK, (24, 44, 24))
        for off, clr in [(14, theme.ACCENT_GOLD), (22, theme.BG_LIGHT), (30, theme.ACCENT_GOLD_D)]:
            pygame.draw.rect(surface, clr, pygame.Rect(off, off, W - off * 2, H - off * 2), 1)

        # Header with drop shadow + divider
        shadow_ts = theme.FONT_H1.render("Game Setup", True, theme.ACCENT_GOLD_D)
        ts = theme.FONT_H1.render("Game Setup", True, theme.ACCENT_GOLD_L)
        surface.blit(shadow_ts, (cx - shadow_ts.get_width() // 2 + 1, 39))
        surface.blit(ts, (cx - ts.get_width() // 2, 38))
        theme.draw_divider(surface, cx - 160, cx + 160, 70)
        ss = theme.FONT_SMALL.render("All players take turns on the same device",
                                     True, theme.TEXT_MUTED)
        surface.blit(ss, (cx - ss.get_width() // 2, 78))

        panel_w = self._panel_w
        panel_x = self._panel_x

        # Ornate main panel
        panel_h = 270 + len(self._player_inputs) * 50 + 20
        panel_rect = pygame.Rect(panel_x, 100, panel_w, panel_h)
        theme.draw_ornate_panel(surface, panel_rect, color=theme.BG_MID,
                                gradient_bottom=tuple(max(0, c - 8) for c in theme.BG_MID))

        y = 116

        # Number of players
        self._section(surface, panel_x + 14, y, "Number of Players  (2 – 5)")
        y += 26
        self._reposition_radio(self._num_players, panel_x + 14, y)
        self._num_players.draw(surface)
        y += 56

        # Player names
        self._section(surface, panel_x + 14, y, "Player Names")
        y += 26
        for i, ti in enumerate(self._player_inputs):
            lbl = theme.FONT_BODY.render(f"Player {i + 1}:", True, theme.ACCENT_GOLD)
            surface.blit(lbl, (panel_x + 14, y + 8))
            ti.rect = pygame.Rect(panel_x + 90, y, panel_w // 2 - 100, 34)
            ti.draw(surface)
            y += 50

        # Error
        if self._error:
            es = theme.FONT_BODY.render(self._error, True, theme.DANGER)
            surface.blit(es, (cx - es.get_width() // 2, H - 110))

        for btn in self._buttons:
            btn.draw(surface)

    def _section(self, surface, x, y, text):
        ts = theme.FONT_H2.render(text, True, theme.ACCENT_GOLD_L)
        surface.blit(ts, (x, y))
        lw = self._panel_w - 28
        theme.draw_divider(surface, x, x + lw, y + ts.get_height() + 4)

    @staticmethod
    def _reposition_radio(rg: RadioGroup, x: int, y: int):
        cx = x
        for idx, (rect, opt) in enumerate(rg._rects):
            rect.x = cx
            rect.y = y
            cx += rect.width + 8
