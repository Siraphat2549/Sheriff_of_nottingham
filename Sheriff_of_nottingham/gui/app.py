"""Pygame application host — manages the game loop and screen transitions."""
import pygame
import sys
from typing import List, Dict

from gui import theme
from storage import database


class App:
    FPS = 60

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Sheriff of Nottingham")
        self.screen = pygame.display.set_mode(
            (theme.WINDOW_W, theme.WINDOW_H), pygame.RESIZABLE)
        theme.init_fonts()

        try:
            database.initialize_db()
        except Exception as e:
            print(f"[DB] Could not initialise database: {e}")

        self._clock = pygame.time.Clock()
        self._current_screen = None
        self._dt = 0

        # Lazy imports to avoid circular deps at module level
        from gui.screens.main_menu import MainMenuScreen
        self._set_screen(MainMenuScreen(self))

    # ── Screen management ─────────────────────────────────────────────── #

    def _set_screen(self, screen):
        self._current_screen = screen

    def show_main_menu(self):
        from gui.screens.main_menu import MainMenuScreen
        self._set_screen(MainMenuScreen(self))

    def show_setup(self):
        from gui.screens.setup_screen import SetupScreen
        self._set_screen(SetupScreen(self))

    def start_game(self, player_configs: List[Dict]):
        from gui.screens.game_screen import GameScreen
        from game.game_logic import GameEngine
        engine = GameEngine()
        try:
            engine.setup_game(player_configs)
        except ValueError as e:
            # Return to setup with an error message
            from gui.screens.setup_screen import SetupScreen
            self._set_screen(SetupScreen(self, error=str(e)))
            return
        self._set_screen(GameScreen(self, engine, on_game_over=self.show_main_menu))

    def show_history(self):
        from gui.screens.history_screen import HistoryScreen
        self._set_screen(HistoryScreen(self))

    def confirm_quit(self):
        self._confirm("Quit", "Are you sure you want to quit?", self._quit)

    def _quit(self):
        pygame.quit()
        sys.exit()

    # ── Confirm dialog ────────────────────────────────────────────────── #

    def _confirm(self, title: str, message: str, on_yes):
        """Simple blocking confirm dialog drawn over the current screen."""
        W, H = self.screen.get_size()
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))

        dw, dh = 420, 200
        dx, dy = (W - dw) // 2, (H - dh) // 2
        dialog_rect = pygame.Rect(dx, dy, dw, dh)

        yes_rect = pygame.Rect(dx + 40, dy + 130, 140, 44)
        no_rect  = pygame.Rect(dx + 240, dy + 130, 140, 44)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if yes_rect.collidepoint(event.pos):
                        on_yes()
                        return
                    if no_rect.collidepoint(event.pos):
                        return

            self._current_screen.draw(self.screen)
            self.screen.blit(overlay, (0, 0))
            pygame.draw.rect(self.screen, theme.BG_MID, dialog_rect, border_radius=8)
            pygame.draw.rect(self.screen, theme.BORDER, dialog_rect, 2, border_radius=8)

            ts = theme.FONT_H2.render(title, True, theme.ACCENT_GOLD)
            self.screen.blit(ts, (dialog_rect.centerx - ts.get_width() // 2, dy + 20))

            ms = theme.FONT_BODY.render(message, True, theme.TEXT_LIGHT)
            self.screen.blit(ms, (dialog_rect.centerx - ms.get_width() // 2, dy + 65))

            for rect, text, bg, hbg in [
                (yes_rect, "Yes", theme.BTN_OK_BG, theme.BTN_OK_HOVER),
                (no_rect,  "No",  theme.BTN_DANGER_BG, theme.BTN_DANGER_HOVER),
            ]:
                col = hbg if rect.collidepoint(pygame.mouse.get_pos()) else bg
                pygame.draw.rect(self.screen, col, rect, border_radius=5)
                pygame.draw.rect(self.screen, theme.BORDER, rect, 1, border_radius=5)
                ts = theme.FONT_H2.render(text, True, theme.BTN_FG)
                self.screen.blit(ts, (rect.centerx - ts.get_width() // 2,
                                      rect.centery - ts.get_height() // 2))

            pygame.display.flip()
            self._clock.tick(self.FPS)

    def show_message(self, title: str, message: str):
        """Blocking info dialog."""
        W, H = self.screen.get_size()
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))

        lines = message.split("\n")
        dw = max(400, max(theme.FONT_BODY.size(ln)[0] for ln in lines) + 60)
        dh = 80 + len(lines) * 22 + 60
        dx, dy = (W - dw) // 2, (H - dh) // 2
        dialog_rect = pygame.Rect(dx, dy, dw, dh)
        ok_rect = pygame.Rect(dx + dw // 2 - 70, dy + dh - 54, 140, 40)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                if event.type in (pygame.KEYDOWN,):
                    if event.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                        return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if ok_rect.collidepoint(event.pos):
                        return

            self._current_screen.draw(self.screen)
            self.screen.blit(overlay, (0, 0))
            pygame.draw.rect(self.screen, theme.BG_MID, dialog_rect, border_radius=8)
            pygame.draw.rect(self.screen, theme.BORDER, dialog_rect, 2, border_radius=8)

            ts = theme.FONT_H2.render(title, True, theme.ACCENT_GOLD)
            self.screen.blit(ts, (dialog_rect.centerx - ts.get_width() // 2, dy + 18))

            for i, ln in enumerate(lines):
                ls = theme.FONT_BODY.render(ln, True, theme.TEXT_LIGHT)
                self.screen.blit(ls, (dialog_rect.centerx - ls.get_width() // 2,
                                      dy + 50 + i * 22))

            col = theme.BTN_OK_HOVER if ok_rect.collidepoint(pygame.mouse.get_pos()) else theme.BTN_OK_BG
            pygame.draw.rect(self.screen, col, ok_rect, border_radius=5)
            ts = theme.FONT_BODY.render("OK", True, theme.BTN_FG)
            self.screen.blit(ts, (ok_rect.centerx - ts.get_width() // 2,
                                  ok_rect.centery - ts.get_height() // 2))

            pygame.display.flip()
            self._clock.tick(self.FPS)

    # ── Main loop ─────────────────────────────────────────────────────── #

    def run(self):
        while True:
            self._dt = self._clock.tick(self.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.confirm_quit()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pass  # screens handle escape themselves if needed
                elif event.type == pygame.VIDEORESIZE:
                    pass  # RESIZABLE mode handles this automatically
                if self._current_screen:
                    self._current_screen.handle_event(event)

            if self._current_screen:
                self._current_screen.update(self._dt)
                self._current_screen.draw(self.screen)

            pygame.display.flip()
