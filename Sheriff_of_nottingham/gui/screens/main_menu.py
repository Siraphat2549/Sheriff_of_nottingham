"""Main menu screen — pygame version."""
import pygame
from gui import theme
from gui.widgets import Button


class MainMenuScreen:

    def __init__(self, app):
        self.app = app
        self._buttons  = []
        self._bg_surf  = None
        self._bg_size  = (0, 0)
        self._build()

    def _build(self):
        self._buttons.clear()
        W, H = self.app.screen.get_size()
        bw, bh = 310, 54
        cx = W // 2

        entries = [
            ("New Game",     theme.BTN_OK_BG,     theme.BTN_OK_HOVER,     self.app.show_setup),
            ("Game History", theme.BTN_BG,          theme.BTN_HOVER,         self.app.show_history),
            ("Quit",         theme.BTN_DANGER_BG,  theme.BTN_DANGER_HOVER,  self.app.confirm_quit),
        ]
        base_y = H // 2 + 30
        for i, (text, bg, hbg, cb) in enumerate(entries):
            rect = pygame.Rect(cx - bw // 2, base_y + i * (bh + 16), bw, bh)
            self._buttons.append(
                Button(rect, text, bg=bg, fg=theme.BTN_FG,
                       hover_bg=hbg, font=theme.FONT_H1, on_click=cb)
            )

    # ── Static background (rebuilt only on resize) ─────────────────────── #

    def _build_bg(self, W, H):
        surf = pygame.Surface((W, H))

        # Gradient background — dark forest green to slightly warmer mid
        theme.draw_gradient_rect(surf, (0, 0, W, H), theme.BG_DARK, (28, 48, 28))

        # Corner vignette (four dark triangles in the corners)
        vdim = min(W, H) // 3
        vgr = pygame.Surface((W, H), pygame.SRCALPHA)
        for cx, cy in [(0, 0), (W, 0), (0, H), (W, H)]:
            for step in range(vdim, 0, -6):
                alpha = max(0, int(90 * (1 - step / vdim)))
                pygame.draw.circle(vgr, (0, 0, 0, alpha), (cx, cy), step)
        surf.blit(vgr, (0, 0))

        # Three concentric ornate borders
        for i, (clr, off) in enumerate([
            (theme.ACCENT_GOLD,   14),
            (theme.BG_LIGHT,      22),
            (theme.ACCENT_GOLD_D, 30),
        ]):
            pygame.draw.rect(surf, clr,
                             pygame.Rect(off, off, W - off * 2, H - off * 2), 1)

        # Corner diamond ornaments on outermost border
        off, dsz = 14, 9
        for cx, cy in [(off, off), (W - off, off), (off, H - off), (W - off, H - off)]:
            pts = [(cx, cy - dsz), (cx + dsz, cy),
                   (cx, cy + dsz), (cx - dsz, cy)]
            pygame.draw.polygon(surf, theme.ACCENT_GOLD, pts)
            pygame.draw.polygon(surf, theme.ACCENT_GOLD_D, pts, 1)

        # ── Heraldic shield / crest ───────────────────────────────────── #
        self._draw_crest(surf, W // 2, H // 2 - 218)

        # ── Title with drop shadow ────────────────────────────────────── #
        title_y = H // 2 - 162
        shadow_s = theme.FONT_TITLE.render("Sheriff of Nottingham", True, theme.ACCENT_GOLD_D)
        surf.blit(shadow_s, (W // 2 - shadow_s.get_width() // 2 + 2, title_y + 2))
        title_s  = theme.FONT_TITLE.render("Sheriff of Nottingham", True, theme.ACCENT_GOLD_L)
        surf.blit(title_s,  (W // 2 - title_s.get_width()  // 2,     title_y))

        # Ornate dividers around subtitle
        theme.draw_divider(surf, W // 2 - 170, W // 2 + 170, H // 2 - 114)
        sub_s = theme.FONT_BODY.render("A Game of Deception & Bluffing",
                                        True, theme.TEXT_MUTED)
        surf.blit(sub_s, (W // 2 - sub_s.get_width() // 2, H // 2 - 104))
        theme.draw_divider(surf, W // 2 - 170, W // 2 + 170, H // 2 - 82)

        # Footer
        foot_s = theme.FONT_SMALL.render(
            "Smuggle goods past the Sheriff — or pay the price!",
            True, theme.TEXT_MUTED)
        surf.blit(foot_s, (W // 2 - foot_s.get_width() // 2, H - 46))

        return surf

    @staticmethod
    def _draw_crest(surface, cx, cy):
        """Draw a small heraldic shield above the title."""
        sw, sh = 54, 66
        x, y   = cx - sw // 2, cy - sh // 2

        # Shield body (pentagon: flat top, pointed bottom)
        pts = [
            (x,          y),
            (x + sw,     y),
            (x + sw,     y + int(sh * 0.62)),
            (cx,         y + sh),
            (x,          y + int(sh * 0.62)),
        ]
        pygame.draw.polygon(surface, theme.BG_MID, pts)
        pygame.draw.polygon(surface, theme.ACCENT_GOLD, pts, 2)

        # Inner shield outline
        m = 7
        inner = [
            (x + m,      y + m),
            (x + sw - m, y + m),
            (x + sw - m, y + int(sh * 0.62) - 3),
            (cx,         y + sh - m),
            (x + m,      y + int(sh * 0.62) - 3),
        ]
        pygame.draw.polygon(surface, theme.ACCENT_GOLD_D, inner, 1)

        # "SN" initials
        s = theme.FONT_H2.render("SN", True, theme.ACCENT_GOLD)
        surface.blit(s, (cx - s.get_width() // 2, cy - s.get_height() // 2 - 4))

    # ── Events ─────────────────────────────────────────────────────────── #

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._bg_surf = None  # invalidate cache
            self._build()
            return
        for btn in self._buttons:
            btn.handle_event(event)

    def update(self, dt_ms: int):
        pass

    # ── Drawing ────────────────────────────────────────────────────────── #

    def draw(self, surface):
        W, H = surface.get_size()
        if self._bg_surf is None or self._bg_size != (W, H):
            self._bg_surf = self._build_bg(W, H)
            self._bg_size = (W, H)

        surface.blit(self._bg_surf, (0, 0))

        for btn in self._buttons:
            btn.draw(surface)
