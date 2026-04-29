"""Game history and statistics screen — pygame version."""
import pygame
from gui import theme
from gui.widgets import Button, ScrollView
from storage import database


class HistoryScreen:

    TAB_RECENT = 0
    TAB_STATS  = 1

    def __init__(self, app):
        self.app = app
        self._tab = self.TAB_RECENT
        self._scroll_recent = ScrollView(self._content_rect(), theme.BG_MID)
        self._scroll_stats  = ScrollView(self._content_rect(), theme.BG_MID)
        self._expanded_games: set = set()  # game ids whose rows are expanded
        self._games = database.get_recent_games(20)
        self._stats = database.get_player_stats()
        self._summary = database.get_all_stats_summary()
        self._back_btn = None
        self._dirty = True
        self._build_buttons()

    # ── Geometry ──────────────────────────────────────────────────────── #

    def _content_rect(self) -> pygame.Rect:
        W, H = self.app.screen.get_size()
        return pygame.Rect(0, 80, W, H - 80 - 60)  # below header, above back btn

    def _build_buttons(self):
        W, H = self.app.screen.get_size()
        self._back_btn = Button(
            pygame.Rect(W // 2 - 110, H - 52, 220, 44),
            "Back to Menu",
            bg=theme.BTN_BG, hover_bg=theme.BTN_HOVER,
            font=theme.FONT_H2, on_click=self.app.show_main_menu)

    # ── Tab header rects ─────────────────────────────────────────────── #

    def _tab_rects(self):
        W, _ = self.app.screen.get_size()
        cx = W // 2
        return [
            pygame.Rect(cx - 220, 48, 200, 32),
            pygame.Rect(cx + 20,  48, 200, 32),
        ]

    # ── Events ─────────────────────────────────────────────────────────── #

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._scroll_recent.rect = self._content_rect()
            self._scroll_stats.rect  = self._content_rect()
            self._build_buttons()
            self._dirty = True
            return

        self._back_btn.handle_event(event)

        # Tab clicks
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self._tab_rects()):
                if r.collidepoint(event.pos):
                    self._tab = i
                    self._dirty = True
                    return

        scroll = self._scroll_recent if self._tab == self.TAB_RECENT else self._scroll_stats
        if scroll.handle_scroll(event):
            self._dirty = True
            return

        # Row expand clicks (recent tab)
        if self._tab == self.TAB_RECENT:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cr = self._scroll_recent.rect
                if cr.collidepoint(event.pos):
                    cy = event.pos[1] - cr.y + self._scroll_recent.scroll_y
                    for gid, row_rect in self._recent_row_rects:
                        if row_rect.collidepoint(event.pos[0] - cr.x, cy):
                            if gid in self._expanded_games:
                                self._expanded_games.discard(gid)
                            else:
                                self._expanded_games.add(gid)
                            self._dirty = True
                            return

    def update(self, dt_ms: int):
        pass

    # ── Drawing ─────────────────────────────────────────────────────────── #

    def draw(self, surface):
        W, H = surface.get_size()
        surface.fill(theme.BG_DARK)

        # Header
        ts = theme.FONT_H1.render("Game History & Statistics",
                                   True, theme.ACCENT_GOLD)
        surface.blit(ts, (W // 2 - ts.get_width() // 2, 10))

        # Tabs
        tab_labels = ["Recent Games", "Player Stats"]
        for i, (r, lbl) in enumerate(zip(self._tab_rects(), tab_labels)):
            bg = theme.BG_LIGHT if i == self._tab else theme.BG_MID
            bdr = theme.ACCENT_GOLD if i == self._tab else theme.BORDER
            pygame.draw.rect(surface, bg, r, border_radius=5)
            pygame.draw.rect(surface, bdr, r, 1, border_radius=5)
            fg = theme.ACCENT_GOLD if i == self._tab else theme.TEXT_MUTED
            ls = theme.FONT_H2.render(lbl, True, fg)
            surface.blit(ls, (r.centerx - ls.get_width() // 2,
                               r.centery - ls.get_height() // 2))

        # Content area
        cr = self._content_rect()
        pygame.draw.rect(surface, theme.BG_MID, cr)

        if self._tab == self.TAB_RECENT:
            self._draw_recent(surface, cr)
        else:
            self._draw_stats(surface, cr)

        # Separator
        pygame.draw.line(surface, theme.BORDER,
                         (0, H - 62), (W, H - 62), 1)

        self._back_btn.draw(surface)

    # ── Recent tab ───────────────────────────────────────────────────── #

    def _draw_recent(self, surface, cr: pygame.Rect):
        scroll = self._scroll_recent
        scroll.rect = cr
        games = self._games

        # Build content surface
        content_w = cr.width
        self._recent_row_rects = []

        if not games:
            surf = pygame.Surface((content_w, 100))
            surf.fill(theme.BG_MID)
            ms = theme.FONT_BODY.render("No games recorded yet. Play a game first!",
                                        True, theme.TEXT_MUTED)
            surf.blit(ms, (content_w // 2 - ms.get_width() // 2, 40))
            surface.set_clip(cr)
            surface.blit(surf, (cr.x, cr.y))
            surface.set_clip(None)
            return

        # Build scrollable content
        col_x   = [10, 50, 230, 300, 360, 520]
        col_w   = [30, 170, 60, 50, 150, 80]
        headers = ["#", "Date", "Players", "Rounds", "Winner", "Score"]
        ROW_H   = 26
        DETAIL_H = 20

        # Calculate total height
        total_h = ROW_H + 4  # header
        for game in games:
            total_h += ROW_H
            if game["id"] in self._expanded_games:
                total_h += len(game.get("scores", [])) * DETAIL_H + 4

        surf = pygame.Surface((content_w, max(total_h + 20, cr.height)))
        surf.fill(theme.BG_MID)

        # Header row
        y = 4
        pygame.draw.rect(surf, theme.BG_DARK, pygame.Rect(0, y, content_w, ROW_H))
        for h, x in zip(headers, col_x):
            hs = theme.FONT_H2.render(h, True, theme.ACCENT_GOLD_L)
            surf.blit(hs, (x, y + 4))
        y += ROW_H + 2
        pygame.draw.line(surf, theme.BORDER, (0, y), (content_w, y), 1)
        y += 2

        for game in games:
            row_bg = theme.BG_MID if games.index(game) % 2 == 0 else tuple(
                min(255, c + 8) for c in theme.BG_MID)
            row_rect = pygame.Rect(0, y, content_w, ROW_H)
            pygame.draw.rect(surf, row_bg, row_rect)
            self._recent_row_rects.append((game["id"], row_rect))

            vals = [
                str(game["id"]),
                game["played_at"][:16],
                str(game["num_players"]),
                str(game["num_rounds"]),
                game["winner_name"],
                str(game["winner_score"]),
            ]
            for val, x in zip(vals, col_x):
                vs = theme.FONT_BODY.render(val, True, theme.TEXT_LIGHT)
                surf.blit(vs, (x, y + 4))
            y += ROW_H

            if game["id"] in self._expanded_games:
                for s in game.get("scores", []):
                    detail = (f"  {s['name']}: {s['total']}g  "
                              f"(stall:{s['stall_value']}  bonus:{s['bonus']})")
                    ds = theme.FONT_SMALL.render(detail, True, theme.TEXT_MUTED)
                    surf.blit(ds, (30, y + 2))
                    y += DETAIL_H
                y += 4

        hint_s = theme.FONT_SMALL.render(
            "(Click a row to expand score details)", True, theme.TEXT_MUTED)
        surf.blit(hint_s, (content_w // 2 - hint_s.get_width() // 2, y + 4))

        scroll.content_h = total_h + 30
        scroll.clamp_scroll()

        surface.set_clip(cr)
        surface.blit(surf, (cr.x, cr.y - scroll.scroll_y))
        surface.set_clip(None)

        # Scrollbar
        if scroll.content_h > cr.height:
            ratio = cr.height / scroll.content_h
            sb_h = max(20, int(cr.height * ratio))
            sb_y = int(cr.y + scroll.scroll_y / scroll.content_h * cr.height)
            pygame.draw.rect(surface, theme.BORDER,
                             pygame.Rect(cr.right - 6, sb_y, 5, sb_h), border_radius=2)

    # ── Stats tab ────────────────────────────────────────────────────── #

    def _draw_stats(self, surface, cr: pygame.Rect):
        scroll = self._scroll_stats
        scroll.rect = cr
        stats   = self._stats
        summary = self._summary

        content_w = cr.width

        if not stats:
            surf = pygame.Surface((content_w, 100))
            surf.fill(theme.BG_MID)
            ms = theme.FONT_BODY.render("No player statistics yet.",
                                        True, theme.TEXT_MUTED)
            surf.blit(ms, (content_w // 2 - ms.get_width() // 2, 40))
            surface.set_clip(cr)
            surface.blit(surf, (cr.x, cr.y))
            surface.set_clip(None)
            return

        ROW_H = 28
        col_x = [10, 180, 280, 350, 430]
        headers = ["Player", "Played", "Won", "Win %", "Avg Score"]
        total_h = ROW_H * 2 + 40 + len(stats) * ROW_H + 20

        surf = pygame.Surface((content_w, max(total_h, cr.height)))
        surf.fill(theme.BG_MID)

        y = 8
        # Summary banner
        sum_s = theme.FONT_BODY.render(
            f"Total games played: {summary['total_games']}", True, theme.TEXT_LIGHT)
        surf.blit(sum_s, (10, y))
        tp = summary.get("top_player")
        if tp:
            top_s = theme.FONT_BODY.render(
                f"Top winner: {tp['player_name']} ({tp['games_won']} wins)",
                True, theme.ACCENT_GOLD)
            surf.blit(top_s, (280, y))
        y += sum_s.get_height() + 6
        pygame.draw.line(surf, theme.BORDER, (0, y), (content_w, y), 1)
        y += 8

        # Header
        pygame.draw.rect(surf, theme.BG_DARK, pygame.Rect(0, y, content_w, ROW_H))
        for h, x in zip(headers, col_x):
            hs = theme.FONT_H2.render(h, True, theme.ACCENT_GOLD_L)
            surf.blit(hs, (x, y + 4))
        y += ROW_H + 2
        pygame.draw.line(surf, theme.BORDER, (0, y), (content_w, y), 1)
        y += 2

        for i, s in enumerate(stats):
            played = s["games_played"]
            won    = s["games_won"]
            pct    = f"{won / played * 100:.0f}%" if played else "—"
            avg    = f"{s['total_score'] // played}g" if played else "—"
            vals   = [s["player_name"], str(played), str(won), pct, avg]

            row_bg = theme.BG_MID if i % 2 == 0 else tuple(min(255, c + 8) for c in theme.BG_MID)
            pygame.draw.rect(surf, row_bg, pygame.Rect(0, y, content_w, ROW_H))
            for val, x in zip(vals, col_x):
                vs = theme.FONT_BODY.render(val, True, theme.TEXT_LIGHT)
                surf.blit(vs, (x, y + 4))
            y += ROW_H

        scroll.content_h = y + 10
        scroll.clamp_scroll()

        surface.set_clip(cr)
        surface.blit(surf, (cr.x, cr.y - scroll.scroll_y))
        surface.set_clip(None)

        if scroll.content_h > cr.height:
            ratio = cr.height / scroll.content_h
            sb_h = max(20, int(cr.height * ratio))
            sb_y = int(cr.y + scroll.scroll_y / scroll.content_h * cr.height)
            pygame.draw.rect(surface, theme.BORDER,
                             pygame.Rect(cr.right - 6, sb_y, 5, sb_h), border_radius=2)
