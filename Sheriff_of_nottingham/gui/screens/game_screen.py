"""Main game screen — poker-table style layout, PvP hot-seat mode."""
import math
import time
import pygame
from typing import List, Callable, Optional, Tuple, Dict
from collections import Counter

from gui import theme
from gui.widgets import Spinner, Dropdown
from game.game_logic import GameEngine, GamePhase, InspectionResult
from game.cards import Card, CardType, LEGAL_GOODS_LIST
from game.player import Player

# ── Layout constants ──────────────────────────────────────────────────────────

HEADER_H  = 62          # top info bar
ACTION_H  = 195         # bottom action zone (current player hand + buttons)
SEAT_R    = 38          # avatar circle radius
CARD_SM_W = 72          # scaled card width in action zone
CARD_SM_H = 100         # scaled card height

# ── Felt / table colours ─────────────────────────────────────────────────────

FELT        = (22, 88, 42)
FELT_LIGHT  = (30, 110, 54)
RAIL        = (52, 28, 8)
RAIL_EDGE   = (76, 46, 14)
RAIL_LIGHT  = (90, 58, 22)

# ── Per-phase accent colours ──────────────────────────────────────────────────

_PHASE_ACCENT = {
    "market":    (72, 180, 255),
    "pack":      (210, 130, 60),
    "sheriff":   (220, 70, 70),
    "round_end": (212, 196, 74),
    "game_end":  (212, 160, 23),
}

# ── Player avatar palette (distinct colours per seat) ────────────────────────

_AVATAR_COLS = [
    (60, 120, 210),   # blue
    (200, 60, 60),    # red
    (60, 180, 80),    # green
    (200, 160, 30),   # gold
    (140, 60, 200),   # purple
]


# ═════════════════════════════════════════════════════════════════════════════

class GameScreen:

    def __init__(self, app, engine: GameEngine, on_game_over: Callable):
        self.app = app
        self.engine = engine
        self.on_game_over = on_game_over
        self._start_time = time.time()

        # Per-phase interactive state
        self._bag_selection: List[Card] = []
        self._hand_over_limit: List[Card] = []
        self._market_drew = 0
        self._decl_type_dd: Optional[Dropdown] = None
        self._decl_qty_sp: Optional[Spinner] = None

        # Result overlay
        self._in_result = False
        self._result_event = None

        # Score cache
        self._scores = None

        # Privacy handoff overlay
        self._privacy_player: Optional[str] = None

        # Round-start announcement (shows sheriff before any merchant turns)
        self._round_intro: bool = False

        # Clickable regions [(pygame.Rect in screen-space, callback)]
        self._clickable: List[Tuple[pygame.Rect, Callable]] = []

        # Animation
        self._fade_alpha = 0
        self._fade_timer = 0.0

        self._phase_key = "market"
        self._pending: Optional[Callable] = None
        self._build_phase()

    # ── Helpers ───────────────────────────────────────────────────────────── #

    def _active_player(self) -> Player:
        e = self.engine
        if e.phase in (GamePhase.MARKET, GamePhase.PACK_BAG):
            m = e.current_merchant
            return m if m is not None else e.players[0]
        if e.phase == GamePhase.INSPECTION:
            return e.sheriff
        return e.players[0]

    def _seat_order(self) -> List[Player]:
        """Active player first, then others in player-list order."""
        active = self._active_player()
        players = self.engine.players
        idx = players.index(active)
        return players[idx:] + players[:idx]

    def _seat_positions(self) -> Dict[str, Tuple[int, int]]:
        W, H = self.app.screen.get_size()
        mid_top = HEADER_H
        mid_bot = H - ACTION_H
        cx = W // 2
        cy = (mid_top + mid_bot) // 2
        rx = int(W * 0.36)
        ry = int((mid_bot - mid_top) * 0.42)
        order = self._seat_order()
        n = len(order)
        positions = {}
        for i, player in enumerate(order):
            a = math.pi * 1.5 - (2 * math.pi / n) * i   # start at bottom, CCW
            x = int(cx + rx * math.cos(a))
            y = int(cy + ry * math.sin(a))
            positions[player.name] = (x, y)
        return positions

    def _accent(self) -> Tuple:
        return _PHASE_ACCENT.get(self._phase_key, theme.ACCENT_GOLD)

    # ── Phase dispatch ────────────────────────────────────────────────────── #

    def _build_phase(self):
        self._clickable.clear()
        self._decl_type_dd = None
        self._decl_qty_sp  = None
        self._fade_alpha = 200
        self._fade_timer = 0.0

        phase = self.engine.phase
        if phase == GamePhase.MARKET:
            self._phase_key = "market"
            # Show round-start announcement at the top of each new round
            if self.engine.current_merchant_index == 0:
                self._round_intro = True
            self._build_market()
        elif phase == GamePhase.PACK_BAG:
            self._phase_key = "pack"
            self._build_pack_bag()
        elif phase == GamePhase.INSPECTION:
            self._phase_key = "sheriff"
            self._build_inspection()
        elif phase == GamePhase.ROUND_END:
            self._phase_key = "round_end"
            self._privacy_player = None
            self._build_round_end()
        elif phase == GamePhase.GAME_END:
            self._phase_key = "game_end"
            self._privacy_player = None
            self._build_game_end()

    def _advance(self):
        self._bag_selection.clear()
        self._hand_over_limit.clear()
        self._market_drew = 0
        self._in_result = False
        self._result_event = None
        self._build_phase()

    # ── Market phase ──────────────────────────────────────────────────────── #

    def _build_market(self):
        merchant = self.engine.current_merchant
        if merchant is None:
            self._pending = self._build_phase
            return
        self._privacy_player = merchant.name
        self._market_drew = 0
        self._hand_over_limit.clear()

    def _market_draw(self):
        if self._market_drew >= 2:
            return
        drawn = self.engine.market_draw_from_deck(self.engine.current_merchant)
        self._market_drew += len(drawn) if drawn else 1
        self._rebuild_clickable()

    def _take_market(self, card: Card):
        if self._market_drew > 0:
            self.app.show_message("Market",
                "You already drew cards.\nYou cannot also take from the market.")
            return
        self.engine.market_take_from_market(self.engine.current_merchant, card)
        self._market_drew = 3
        self._rebuild_clickable()

    def _toggle_discard(self, card: Card):
        merchant = self.engine.current_merchant
        if merchant is None:
            return
        over = merchant.hand_size - self.engine.HAND_SIZE
        if over <= 0:
            return
        for i, c in enumerate(self._hand_over_limit):
            if c is card:
                self._hand_over_limit.pop(i)
                self._rebuild_clickable()
                return
        if len(self._hand_over_limit) < over:
            self._hand_over_limit.append(card)
        self._rebuild_clickable()

    def _market_done(self):
        if self._hand_over_limit:
            self.engine.market_discard(self.engine.current_merchant, self._hand_over_limit[:])
        self.engine.advance_market_phase()
        self._advance()

    # ── Pack bag phase ────────────────────────────────────────────────────── #

    def _build_pack_bag(self):
        merchant = self.engine.current_merchant
        if merchant is None:
            self.engine.phase = GamePhase.INSPECTION
            self.engine.current_merchant_index = 0
            self._pending = self._build_phase
            return
        self._privacy_player = merchant.name
        self._bag_selection.clear()

        W, H = self.app.screen.get_size()
        az_y = H - ACTION_H + 8
        cx = W // 2

        self._decl_type_dd = Dropdown(
            pygame.Rect(cx - 200, az_y + ACTION_H - 56, 170, 32),
            options=[ct.value for ct in LEGAL_GOODS_LIST],
            initial=LEGAL_GOODS_LIST[0].value,
            font=theme.FONT_BODY,
            open_up=True)

        self._decl_qty_sp = Spinner(
            pygame.Rect(cx + 20, az_y + ACTION_H - 56, 110, 32),
            min_val=1, max_val=5, initial=1,
            font=theme.FONT_BODY)

    def _bag_add(self, card: Card):
        if len(self._bag_selection) >= 5:
            self.app.show_message("Bag Full", "Up to 5 cards in the bag.")
            return
        if not any(c is card for c in self._bag_selection):
            self._bag_selection.append(card)
        self._rebuild_clickable()

    def _bag_remove(self, card: Card):
        for i, c in enumerate(self._bag_selection):
            if c is card:
                self._bag_selection.pop(i)
                break
        self._rebuild_clickable()

    def _submit_bag(self):
        if not self._bag_selection:
            self.app.show_message("Empty Bag", "Add at least 1 card.")
            return
        if self._decl_type_dd is None or self._decl_qty_sp is None:
            return
        decl_type = CardType(self._decl_type_dd.selected)
        decl_qty  = self._decl_qty_sp.value
        ok = self.engine.pack_player_bag(
            self.engine.current_merchant, self._bag_selection[:], decl_type, decl_qty)
        if not ok:
            self.app.show_message("Error", "Invalid bag configuration.")
            return
        self._bag_selection.clear()
        self.engine.advance_pack_bag_phase()
        self._advance()

    # ── Inspection phase ──────────────────────────────────────────────────── #

    def _build_inspection(self):
        merchant = self.engine.current_merchant
        if merchant is None:
            self.engine.phase = GamePhase.ROUND_END
            self._pending = self._build_phase
            return
        self._privacy_player = self.engine.sheriff.name

    def _sheriff_let(self, merchant: Player):
        merchant.bag.bribe_offered = 0
        event = self.engine.sheriff_let_through(merchant)
        self._show_result(event)

    def _sheriff_inspect(self, merchant: Player):
        event = self.engine.sheriff_inspect(merchant)
        self._show_result(event)

    def _show_result(self, event):
        self._result_event = event
        self._in_result = True
        self._rebuild_clickable()

    def _continue_inspection(self):
        self._in_result = False
        self._result_event = None
        self.engine.advance_inspection_phase()
        self._advance()

    # ── Round / Game end ──────────────────────────────────────────────────── #

    def _build_round_end(self):
        pass

    def _round_next(self):
        self.engine.end_round()
        self._advance()

    def _build_game_end(self):
        duration = int(time.time() - self._start_time)
        self._scores = self.engine.calculate_final_scores()
        from storage.database import save_game
        try:
            save_game(self._scores, self.engine.total_rounds, duration)
        except Exception:
            pass

    # ── Clickable rebuilder ───────────────────────────────────────────────── #

    def _rebuild_clickable(self):
        """Force a full redraw which re-registers all clickable areas."""
        self._clickable.clear()

    # ── Handle event / update ─────────────────────────────────────────────── #

    def handle_event(self, event):
        # Round-intro screen — tap to dismiss, then privacy screen follows
        if self._round_intro:
            if ((event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
                    or (event.type == pygame.KEYDOWN
                        and event.key not in (pygame.K_ESCAPE, pygame.K_F4))):
                self._round_intro = False
                self._clickable.clear()
            return

        # Privacy overlay — consume all input until dismissed
        if self._privacy_player:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._privacy_player = None
                self._clickable.clear()
            elif event.type == pygame.KEYDOWN and event.key not in (
                    pygame.K_ESCAPE, pygame.K_F4):
                self._privacy_player = None
                self._clickable.clear()
            return

        if event.type == pygame.VIDEORESIZE:
            self._clickable.clear()
            return

        # Overlay widgets (screen-space)
        if self._decl_type_dd and self._decl_type_dd.handle_event(event):
            return
        if self._decl_qty_sp and self._decl_qty_sp.handle_event(event):
            return

        # Clickable areas (screen-space)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, cb in self._clickable:
                if rect.collidepoint(event.pos):
                    cb()
                    return

    def update(self, dt_ms: int):
        if self._pending:
            fn = self._pending
            self._pending = None
            fn()
        if self._fade_alpha > 0:
            self._fade_timer += dt_ms
            self._fade_alpha = max(0, 200 - int(self._fade_timer * 0.80))

    # ══════════════════════════════════════════════════════════════════════
    # DRAWING
    # ══════════════════════════════════════════════════════════════════════

    def draw(self, surface):
        W, H = surface.get_size()
        self._clickable.clear()

        # ── Background
        surface.fill((10, 20, 10))

        # ── Table
        self._draw_table(surface)

        # ── Player seats
        seat_pos = self._seat_positions()
        active = self._active_player()
        for i, player in enumerate(self.engine.players):
            pos = seat_pos.get(player.name)
            if pos:
                self._draw_seat(surface, player, pos, i,
                                is_active=(player is active),
                                is_sheriff=(player is self.engine.sheriff))

        # ── Center table content
        self._draw_center(surface, seat_pos)

        # ── Header bar
        self._draw_header(surface)

        # ── Active player action zone
        if not self._privacy_player:
            self._draw_action_zone(surface, active)

        # ── Overlay widgets
        if not self._privacy_player:
            if self._decl_type_dd:
                self._decl_type_dd.draw(surface)
            if self._decl_qty_sp:
                self._decl_qty_sp.draw(surface)

        # ── Phase fade-in
        if self._fade_alpha > 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, self._fade_alpha))
            surface.blit(ov, (0, 0))

        # ── Round-intro overlay (above fade, below privacy)
        if self._round_intro:
            self._draw_round_intro(surface)

        # ── Privacy overlay (drawn last, on top of everything)
        elif self._privacy_player:
            self._draw_privacy(surface)

    # ── Table ─────────────────────────────────────────────────────────────── #

    def _draw_table(self, surface):
        W, H = surface.get_size()
        mid_top = HEADER_H
        mid_bot = H - ACTION_H
        cx = W // 2
        cy = (mid_top + mid_bot) // 2
        rx = int(W * 0.38)
        ry = int((mid_bot - mid_top) * 0.44)

        # Rail shadow
        shad = pygame.Surface((2*rx+30, 2*ry+30), pygame.SRCALPHA)
        pygame.draw.ellipse(shad, (0, 0, 0, 80),
                            shad.get_rect().inflate(-10, -10))
        surface.blit(shad, (cx - rx - 10, cy - ry - 10))

        # Rail outer
        pygame.draw.ellipse(surface, RAIL_EDGE,
                            pygame.Rect(cx-rx-14, cy-ry-14, 2*(rx+14), 2*(ry+14)))
        # Rail fill
        pygame.draw.ellipse(surface, RAIL,
                            pygame.Rect(cx-rx-10, cy-ry-10, 2*(rx+10), 2*(ry+10)))
        # Rail inner highlight
        pygame.draw.ellipse(surface, RAIL_LIGHT,
                            pygame.Rect(cx-rx-8, cy-ry-8, 2*(rx+8), 2*(ry+8)), 2)

        # Felt
        felt_rect = pygame.Rect(cx-rx, cy-ry, 2*rx, 2*ry)
        pygame.draw.ellipse(surface, FELT, felt_rect)

        # Felt highlight (lighter ellipse at top-center)
        hl_surf = pygame.Surface((2*rx, 2*ry), pygame.SRCALPHA)
        pygame.draw.ellipse(hl_surf, (*FELT_LIGHT, 60),
                            pygame.Rect(rx//4, ry//4, rx, ry))
        surface.blit(hl_surf, felt_rect.topleft)

        # Felt border ring
        pygame.draw.ellipse(surface, (18, 72, 36), felt_rect, 2)

    # ── Player seat ───────────────────────────────────────────────────────── #

    def _draw_seat(self, surface, player: Player, pos: Tuple[int, int],
                   color_idx: int, is_active: bool, is_sheriff: bool):
        x, y = pos
        r = SEAT_R
        col = _AVATAR_COLS[color_idx % len(_AVATAR_COLS)]
        accent = self._accent() if is_active else theme.TEXT_MUTED

        # Glow ring for active player
        if is_active:
            for ring in range(4, 0, -1):
                ga = 18 + ring * 14
                gsurf = pygame.Surface((2*(r+ring*3+2), 2*(r+ring*3+2)), pygame.SRCALPHA)
                pygame.draw.circle(gsurf, (*accent, ga),
                                   (r+ring*3+2, r+ring*3+2), r+ring*3)
                surface.blit(gsurf, (x - r - ring*3 - 2, y - r - ring*3 - 2))

        # Avatar circle shadow
        shad = pygame.Surface((2*r+6, 2*r+6), pygame.SRCALPHA)
        pygame.draw.circle(shad, (0, 0, 0, 70), (r+3, r+3), r)
        surface.blit(shad, (x - r - 1, y - r - 1))

        # Avatar circle fill (gradient simulation: bright top)
        pygame.draw.circle(surface, col, (x, y), r)
        light = tuple(min(255, c + 50) for c in col)
        hl = pygame.Surface((2*r, 2*r), pygame.SRCALPHA)
        pygame.draw.circle(hl, (*light, 80), (r, r-r//3), r*2//3)
        surface.blit(hl, (x-r, y-r))

        # Border ring
        ring_col = accent if is_active else tuple(min(255, c+30) for c in col)
        pygame.draw.circle(surface, ring_col, (x, y), r, 2)

        # Initials
        initials = player.name[:2].upper()
        init_s = theme.FONT_H2.render(initials, True, theme.TEXT_LIGHT)
        surface.blit(init_s, (x - init_s.get_width()//2, y - init_s.get_height()//2))

        # Sheriff crown
        if is_sheriff:
            crown_s = theme.FONT_BODY.render("★", True, theme.ACCENT_GOLD_L)
            surface.blit(crown_s, (x - crown_s.get_width()//2, y - r - crown_s.get_height() - 2))

        # Info panel below avatar
        info_y = y + r + 4
        name_s = theme.FONT_BODY.render(player.name, True,
                                         accent if is_active else theme.TEXT_LIGHT)
        surface.blit(name_s, (x - name_s.get_width()//2, info_y))

        gold_s = theme.FONT_SMALL.render(f"{player.gold}g", True, theme.ACCENT_GOLD)
        surface.blit(gold_s, (x - gold_s.get_width()//2, info_y + name_s.get_height() + 1))

        # Bag indicator (small icon if bag is packed)
        phase = self.engine.phase
        if phase == GamePhase.INSPECTION and player.bag.is_ready:
            bag_s = theme.FONT_SMALL.render("🎒", True, theme.ACCENT_GOLD)
            surface.blit(bag_s, (x - bag_s.get_width()//2,
                                  info_y + name_s.get_height() + gold_s.get_height() + 3))

    # ── Header bar ────────────────────────────────────────────────────────── #

    def _draw_header(self, surface):
        W = surface.get_width()
        accent = self._accent()

        # Bar background
        hbar = pygame.Surface((W, HEADER_H))
        theme.draw_gradient_rect(hbar, pygame.Rect(0, 0, W, HEADER_H),
                                 (20, 20, 20), (12, 12, 12))
        surface.blit(hbar, (0, 0))
        pygame.draw.line(surface, accent, (0, HEADER_H - 2), (W, HEADER_H - 2), 2)

        e = self.engine
        phase_label = {
            "market":    "MARKET PHASE",
            "pack":      "BAG PACKING",
            "sheriff":   "SHERIFF INSPECTION",
            "round_end": "END OF ROUND",
            "game_end":  "GAME OVER",
        }.get(self._phase_key, "")

        # Left: Phase label
        ps = theme.FONT_H2.render(phase_label, True, accent)
        surface.blit(ps, (20, HEADER_H//2 - ps.get_height()//2))

        # Center: Round info
        if e.phase not in (GamePhase.GAME_END,):
            rnd_s = theme.FONT_H1.render(
                f"Round  {e.current_round} / {e.total_rounds}", True, theme.TEXT_LIGHT)
            surface.blit(rnd_s, (W//2 - rnd_s.get_width()//2,
                                  HEADER_H//2 - rnd_s.get_height()//2))

        # Right: Sheriff name + role hint
        if e.phase not in (GamePhase.GAME_END,):
            sh_text = f"★ Sheriff: {e.sheriff.name}"
            if e.phase in (GamePhase.MARKET, GamePhase.PACK_BAG):
                sh_text += "  (inspects later)"
            sh_s = theme.FONT_BODY.render(sh_text, True, theme.SHERIFF_CLR)
            surface.blit(sh_s, (W - sh_s.get_width() - 18,
                                  HEADER_H//2 - sh_s.get_height()//2))

    # ── Center content dispatcher ─────────────────────────────────────────── #

    def _draw_center(self, surface, seat_pos: Dict):
        _ = seat_pos  # available for future seat-aware overlays
        if self._in_result and self._result_event:
            self._draw_center_result(surface)
        elif self.engine.phase == GamePhase.MARKET:
            self._draw_center_market(surface)
        elif self.engine.phase == GamePhase.PACK_BAG:
            self._draw_center_pack(surface)
        elif self.engine.phase == GamePhase.INSPECTION:
            self._draw_center_inspection(surface)
        elif self.engine.phase == GamePhase.ROUND_END:
            self._draw_center_round_end(surface)
        elif self.engine.phase == GamePhase.GAME_END:
            self._draw_center_game_end(surface)

    def _table_center(self) -> Tuple[int, int, int, int]:
        """Returns (cx, cy, half_w, half_h) of usable table interior."""
        W, H = self.app.screen.get_size()
        mid_top = HEADER_H
        mid_bot = H - ACTION_H
        cx = W // 2
        cy = (mid_top + mid_bot) // 2
        rx = int(W * 0.38)
        ry = int((mid_bot - mid_top) * 0.44)
        # Inner usable area (80% of radii)
        return cx, cy, int(rx * 0.75), int(ry * 0.72)

    def _draw_center_panel(self, surface, rect, color=None):
        """Draw a styled panel on the felt."""
        col = color or (16, 60, 28)
        r = pygame.Rect(rect)
        shad = pygame.Surface((r.width+5, r.height+5), pygame.SRCALPHA)
        pygame.draw.rect(shad, (0, 0, 0, 60),
                         pygame.Rect(0, 0, r.width+5, r.height+5), border_radius=9)
        surface.blit(shad, (r.x+3, r.y+3))
        pygame.draw.rect(surface, col, r, border_radius=8)
        pygame.draw.rect(surface, self._accent(), r, 1, border_radius=8)

    # ── Market center ─────────────────────────────────────────────────────── #

    def _draw_center_market(self, surface):
        e = self.engine
        cx, cy, _, hh = self._table_center()
        accent = self._accent()

        # Label
        ls = theme.FONT_H2.render("Market Cards", True, accent)
        surface.blit(ls, (cx - ls.get_width()//2, cy - hh + 4))

        # Market cards row (small scale)
        n = len(e.market_cards)
        card_w, card_h = CARD_SM_W, CARD_SM_H
        gap = 8
        total_w = n * card_w + (n-1) * gap
        sx = cx - total_w // 2
        sy = cy - card_h // 2 + 10
        can_take = not self._privacy_player and self._market_drew == 0
        for i, card in enumerate(e.market_cards):
            r = pygame.Rect(sx + i*(card_w+gap), sy, card_w, card_h)
            theme.draw_card(surface, card, r)
            if can_take:
                if r.collidepoint(pygame.mouse.get_pos()):
                    ov = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                    ov.fill((255, 255, 255, 30))
                    surface.blit(ov, r.topleft)
                    pygame.draw.rect(surface, accent, r, 2, border_radius=7)
                card_ref = card
                self._clickable.append((r, lambda c=card_ref: self._take_market(c)))

        if can_take:
            hint = theme.FONT_SMALL.render(
                "Click a card to take it  —  or draw 2 from deck",
                True, theme.TEXT_MUTED)
            surface.blit(hint, (cx - hint.get_width() // 2, sy + card_h + 5))

        # Deck indicator
        deck_x = cx + total_w//2 + 24
        deck_r = pygame.Rect(deck_x, sy, card_w, card_h)
        theme.draw_card_back(surface, deck_r)
        dc_s = theme.FONT_SMALL.render(f"{len(e.deck._draw_pile)}",
                                        True, theme.TEXT_MUTED)
        surface.blit(dc_s, (deck_x + card_w//2 - dc_s.get_width()//2,
                              sy + card_h + 3))

    # ── Pack-bag center ───────────────────────────────────────────────────── #

    def _draw_center_pack(self, surface):
        e = self.engine
        cx, cy, _, hh = self._table_center()
        accent = self._accent()

        # Show packed bags for all players who've already packed
        packed = [(p, p.bag) for p in e.players if p.bag.is_ready]
        if not packed:
            ls = theme.FONT_BODY.render("Players pack their bags one at a time.",
                                         True, theme.TEXT_MUTED)
            surface.blit(ls, (cx - ls.get_width()//2, cy - ls.get_height()//2))
            return

        lbl = theme.FONT_H2.render("Bags submitted:", True, accent)
        surface.blit(lbl, (cx - lbl.get_width()//2, cy - hh + 4))
        y = cy - hh + lbl.get_height() + 14
        for p, bag in packed:
            line = (f"{p.name}: declared {bag.declared_quantity}"
                    f" {bag.declared_type.value}(s)  [{len(bag.cards)} card(s)]")
            ls = theme.FONT_BODY.render(line, True, theme.TEXT_LIGHT)
            surface.blit(ls, (cx - ls.get_width()//2, y))
            y += ls.get_height() + 6

        # Bag preview for current player (their selected cards)
        if self._bag_selection and not self._privacy_player:
            n = len(self._bag_selection)
            cw, ch = CARD_SM_W, CARD_SM_H
            gap = 6
            total_w = n*cw + (n-1)*gap
            sx = cx - total_w//2
            sy = cy + 10
            bl = theme.FONT_SMALL.render("Your bag preview:", True, accent)
            surface.blit(bl, (cx - bl.get_width()//2, sy - bl.get_height() - 4))
            for i, card in enumerate(self._bag_selection):
                r = pygame.Rect(sx + i*(cw+gap), sy, cw, ch)
                theme.draw_card(surface, card, r)
                self._clickable.append((r, lambda c=card: self._bag_remove(c)))

    # ── Inspection center ─────────────────────────────────────────────────── #

    def _draw_center_inspection(self, surface):
        e = self.engine
        merchant = e.current_merchant
        if merchant is None:
            return
        cx, cy, hw, hh = self._table_center()
        accent = self._accent()

        # Title
        ts = theme.FONT_H1.render(
            f"{e.sheriff.name}  inspects  {merchant.name}'s bag", True, accent)
        surface.blit(ts, (cx - ts.get_width()//2, cy - hh + 4))

        # Declaration panel
        panel_h = 110
        panel_y = cy - panel_h//2 - 20
        panel_rect = pygame.Rect(cx - hw + 10, panel_y, (hw-10)*2, panel_h)
        self._draw_center_panel(surface, panel_rect)

        decl_s = theme.FONT_H2.render(
            f'{merchant.name} declares:  "{merchant.bag.declared_quantity}'
            f'  {merchant.bag.declared_type.value}(s)"',
            True, theme.TEXT_LIGHT)
        surface.blit(decl_s, (cx - decl_s.get_width()//2, panel_y + 16))

        # Face-down cards
        n = len(merchant.bag.cards)
        cw, ch = CARD_SM_W - 8, CARD_SM_H - 11
        gap = 5
        total_w = n*cw + (n-1)*gap
        sx = cx - total_w//2
        card_y = panel_y + 46
        for i in range(n):
            theme.draw_card_back(surface, pygame.Rect(sx + i*(cw+gap), card_y, cw, ch))

        # Actual count hint
        hint = theme.FONT_SMALL.render(
            f"({n} card(s) in bag)", True, theme.TEXT_MUTED)
        surface.blit(hint, (cx - hint.get_width()//2, panel_y + panel_h - 18))

        if not self._privacy_player:
            # Action buttons
            btn_y = cy + hh - 60
            let_r   = pygame.Rect(cx - 230, btn_y, 190, 46)
            insp_r  = pygame.Rect(cx + 40,  btn_y, 190, 46)
            self._draw_btn(surface, let_r,  "Let Through",  theme.BTN_OK_BG)
            self._draw_btn(surface, insp_r, "Inspect Bag",  theme.BTN_DANGER_BG)
            self._clickable.append((let_r,  lambda: self._sheriff_let(merchant)))
            self._clickable.append((insp_r, lambda: self._sheriff_inspect(merchant)))

            hint2 = theme.FONT_SMALL.render(
                "Inspect wrongly → pay 2g/card compensation", True, theme.TEXT_MUTED)
            surface.blit(hint2, (cx - hint2.get_width()//2, btn_y + 52))

    # ── Result center ─────────────────────────────────────────────────────── #

    def _draw_center_result(self, surface):
        event = self._result_event
        cx, cy, hw, hh = self._table_center()

        if event.result == InspectionResult.LET_THROUGH:
            title, clr, bg = "Let Through!", theme.SUCCESS, (8, 44, 18)
            msg = f"{event.merchant_name}'s goods passed unchecked."
        elif event.result == InspectionResult.BRIBE_ACCEPTED:
            title, clr, bg = "Bribe Accepted!", theme.ACCENT_GOLD, (48, 36, 4)
            msg = f"Sheriff accepted {event.bribe}g bribe."
        elif event.result == InspectionResult.HONEST:
            title, clr, bg = "Inspected — Honest!", theme.SUCCESS, (8, 44, 18)
            msg = (f"{event.merchant_name} was truthful. "
                   f"Sheriff pays {abs(event.gold_change_sheriff)}g.")
        else:
            title, clr, bg = "CAUGHT!", theme.DANGER, (56, 8, 8)
            msg = (f"{event.merchant_name} was lying! "
                   f"Penalty: {abs(event.gold_change_merchant)}g.")

        # Result panel
        pr = pygame.Rect(cx - hw + 10, cy - hh + 4, 2*(hw-10), 74)
        pygame.draw.rect(surface, bg, pr, border_radius=10)
        pygame.draw.rect(surface, clr, pr, 2, border_radius=10)
        ts = theme.FONT_H1.render(title, True, clr)
        surface.blit(ts, (cx - ts.get_width()//2, pr.centery - ts.get_height()//2))

        ms = theme.FONT_BODY.render(msg, True, theme.TEXT_LIGHT)
        surface.blit(ms, (cx - ms.get_width()//2, pr.bottom + 10))

        # Actual cards
        n = len(event.actual_cards)
        if n:
            cw, ch = CARD_SM_W, CARD_SM_H
            gap = 6
            total_w = n*cw + (n-1)*gap
            sx = cx - total_w//2
            sy = cy - ch//2 + 10
            al = theme.FONT_SMALL.render("Actual contents:", True, theme.TEXT_MUTED)
            surface.blit(al, (cx - al.get_width()//2, sy - al.get_height() - 3))
            for i, card in enumerate(event.actual_cards):
                theme.draw_card(surface, card, pygame.Rect(sx + i*(cw+gap), sy, cw, ch))

        # Continue button
        cont_r = pygame.Rect(cx - 110, cy + hh - 55, 220, 44)
        self._draw_btn(surface, cont_r, "Continue  →", theme.BTN_BG)
        self._clickable.append((cont_r, self._continue_inspection))

    # ── Round end center ──────────────────────────────────────────────────── #

    def _draw_center_round_end(self, surface):
        e = self.engine
        cx, cy, hw, hh = self._table_center()
        accent = self._accent()

        title = theme.FONT_H1.render(f"End of Round {e.current_round}", True, accent)
        surface.blit(title, (cx - title.get_width()//2, cy - hh + 4))

        events = e.round_events or []
        y = cy - hh + title.get_height() + 16
        if not events:
            ns = theme.FONT_BODY.render("No inspections this round.", True, theme.TEXT_MUTED)
            surface.blit(ns, (cx - ns.get_width()//2, y))
            y += ns.get_height() + 8
        else:
            for ev in events:
                clr = (theme.SUCCESS if ev.result in (
                    InspectionResult.LET_THROUGH, InspectionResult.HONEST,
                    InspectionResult.BRIBE_ACCEPTED) else theme.DANGER)
                result_str = ev.result.value.replace("_", " ").title()
                line = (f"{ev.merchant_name}: {ev.declared_qty}× "
                        f"{ev.declared_type.value} — {result_str}")
                ls = theme.FONT_BODY.render(line, True, clr)
                surface.blit(ls, (cx - ls.get_width()//2, y))
                y += ls.get_height() + 4

        # Gold standings
        y = max(y + 10, cy - 10)
        sorted_p = sorted(e.players, key=lambda p: -p.gold)
        theme.draw_divider(surface, cx - hw + 20, cx + hw - 20, y, theme.BORDER, accent)
        y += 14
        for rank, p in enumerate(sorted_p):
            tag = "  ★ Sheriff" if p is e.sheriff else ""
            line = f"{rank+1}. {p.name}{tag}  —  {p.gold}g"
            col = theme.ACCENT_GOLD if rank == 0 else theme.TEXT_LIGHT
            ls = theme.FONT_BODY.render(line, True, col)
            surface.blit(ls, (cx - ls.get_width()//2, y))
            y += ls.get_height() + 5

        # Next round button
        next_text = "Next Round  →" if e.current_round < e.total_rounds else "Final Scores  →"
        btn_r = pygame.Rect(cx - 120, cy + hh - 55, 240, 46)
        self._draw_btn(surface, btn_r, next_text, theme.BTN_OK_BG)
        self._clickable.append((btn_r, self._round_next))

    # ── Game end center ───────────────────────────────────────────────────── #

    def _draw_center_game_end(self, surface):
        scores = self._scores or []
        cx, cy, hw, hh = self._table_center()
        accent = self._accent()

        title = theme.FONT_H1.render("Game Over!", True, accent)
        surface.blit(title, (cx - title.get_width()//2, cy - hh + 4))

        if scores:
            winner = scores[0]
            ws = theme.FONT_H2.render(
                f"Winner: {winner['name']}  ({winner['total']} gold)", True, theme.ACCENT_GOLD_L)
            surface.blit(ws, (cx - ws.get_width()//2, cy - hh + title.get_height() + 14))

        y = cy - hh + title.get_height() + 44
        col_x = [cx - hw + 20, cx - hw + 110, cx - hw + 240,
                  cx - hw + 340, cx - hw + 420, cx - hw + 500]
        headers = ["Rank", "Player", "Gold", "Stall", "Bonus", "Total"]
        for h, x in zip(headers, col_x):
            hs = theme.FONT_H2.render(h, True, accent)
            surface.blit(hs, (x, y))
        y += 24
        pygame.draw.line(surface, accent, (cx-hw+10, y), (cx+hw-10, y), 1)
        y += 4

        for rank, s in enumerate(scores):
            clr = theme.ACCENT_GOLD if rank == 0 else theme.TEXT_LIGHT
            vals = [str(rank+1), s["name"], str(s["gold"]),
                    str(s["stall_value"]), str(s["bonus"]), str(s["total"])]
            for val, x in zip(vals, col_x):
                vs = theme.FONT_BODY.render(val, True, clr)
                surface.blit(vs, (x, y))
            y += 24

        pygame.draw.line(surface, theme.BORDER, (cx-hw+10, y+4), (cx+hw-10, y+4), 1)
        btn_r = pygame.Rect(cx - 120, cy + hh - 55, 240, 46)
        self._draw_btn(surface, btn_r, "Main Menu", theme.BTN_BG)
        self._clickable.append((btn_r, self.on_game_over))

    # ── Action zone (bottom, active player) ───────────────────────────────── #

    def _draw_action_zone(self, surface, active: Player):
        W, H = surface.get_size()

        # Background
        bg = pygame.Surface((W, ACTION_H))
        theme.draw_gradient_rect(bg, pygame.Rect(0, 0, W, ACTION_H),
                                  (18, 18, 18), (10, 10, 10))
        surface.blit(bg, (0, H - ACTION_H))
        accent = self._accent()
        pygame.draw.line(surface, accent, (0, H - ACTION_H), (W, H - ACTION_H), 2)

        az_y = H - ACTION_H + 8
        phase = self.engine.phase

        # Player label
        tag = " (Sheriff)" if active is self.engine.sheriff else ""
        lbl_s = theme.FONT_H2.render(f"{active.name}{tag}", True, accent)
        surface.blit(lbl_s, (20, az_y + 4))
        gold_s = theme.FONT_BODY.render(f"{active.gold} gold", True, theme.ACCENT_GOLD)
        surface.blit(gold_s, (20, az_y + lbl_s.get_height() + 6))

        if phase == GamePhase.MARKET and not self._in_result:
            self._draw_action_market(surface, active, az_y)
        elif phase == GamePhase.PACK_BAG and not self._in_result:
            self._draw_action_pack(surface, active, az_y)
        elif phase in (GamePhase.INSPECTION, GamePhase.ROUND_END,
                        GamePhase.GAME_END) or self._in_result:
            # Just show stall info — actions are in center
            stl_s = theme.FONT_SMALL.render(
                f"Stall: {active.stall_value}g  |  "
                + "  ".join(f"{ct.value}×{n}"
                             for ct, n in Counter(c.card_type
                                                   for c in active.stall).items()),
                True, theme.TEXT_MUTED)
            surface.blit(stl_s, (20, az_y + 50))

    def _draw_action_market(self, surface, merchant: Player, az_y: int):
        W, _ = surface.get_size()

        # Hand cards
        hand = merchant.hand
        n = len(hand)
        cw, ch = CARD_SM_W, CARD_SM_H
        gap = max(4, min(10, (W - 220 - n*cw) // max(1, n-1) if n > 1 else 10))
        total_w = n*cw + (n-1)*gap
        sx = max(200, (W - 280 - total_w)//2 + 200)
        sy = az_y + (ACTION_H - 16 - ch) // 2

        over = merchant.hand_size - self.engine.HAND_SIZE
        for i, card in enumerate(hand):
            r = pygame.Rect(sx + i*(cw+gap), sy, cw, ch)
            is_discard = any(c is card for c in self._hand_over_limit)
            theme.draw_card(surface, card, r, selected=is_discard)
            if over > 0:
                self._clickable.append((r, lambda c=card: self._toggle_discard(c)))

        if over > 0:
            msg = theme.FONT_SMALL.render(
                f"Discard {over} card(s)  (click cards above)", True, theme.DANGER)
            surface.blit(msg, (sx, sy + ch + 4))

        # Buttons (right side)
        bx = W - 250
        drew_enough = self._market_drew >= 2
        took_market = self._market_drew == 3
        need_discard = over > 0 and len(self._hand_over_limit) < over

        draw_r = pygame.Rect(bx, az_y + 14, 210, 40)
        col = theme.BTN_DISABLED if (drew_enough or took_market) else theme.BTN_OK_BG
        fg  = theme.BTN_DISABLED_FG if (drew_enough or took_market) else theme.BTN_FG
        self._draw_btn(surface, draw_r, "Draw 2 from Deck", col, fg, theme.FONT_BODY)
        if not (drew_enough or took_market):
            self._clickable.append((draw_r, self._market_draw))

        if self._market_drew > 0:
            info_s = theme.FONT_SMALL.render(
                "Drew 2 from deck." if self._market_drew < 3 else "Took 1 from market.",
                True, theme.SUCCESS)
            surface.blit(info_s, (bx, az_y + 58))

        can_done = self._market_drew > 0 and not need_discard
        done_r = pygame.Rect(bx, az_y + ACTION_H - 70, 210, 44)
        col2 = theme.BTN_OK_BG if can_done else theme.BTN_DISABLED
        fg2  = theme.BTN_FG if can_done else theme.BTN_DISABLED_FG
        self._draw_btn(surface, done_r, "Confirm Turn  →", col2, fg2)
        if can_done:
            self._clickable.append((done_r, self._market_done))

    def _draw_action_pack(self, surface, merchant: Player, az_y: int):
        W, _ = surface.get_size()

        # Hand cards
        hand = merchant.hand
        n = len(hand)
        cw, ch = CARD_SM_W, CARD_SM_H
        gap = max(4, min(10, (W - 220 - n*cw) // max(1, n-1) if n > 1 else 10))
        total_w = n*cw + (n-1)*gap
        sx = max(200, (W - 280 - total_w)//2 + 200)
        sy = az_y + 8

        in_bag_set = {i for i, c in enumerate(hand) if any(b is c for b in self._bag_selection)}
        for i, card in enumerate(hand):
            r = pygame.Rect(sx + i*(cw+gap), sy, cw, ch)
            theme.draw_card(surface, card, r, selected=(i in in_bag_set))
            if i in in_bag_set:
                self._clickable.append((r, lambda c=card: self._bag_remove(c)))
            else:
                self._clickable.append((r, lambda c=card: self._bag_add(c)))

        hint = theme.FONT_SMALL.render("Click hand cards to add to bag", True, theme.TEXT_MUTED)
        surface.blit(hint, (sx, sy + ch + 3))

        # Submit button + declaration label
        bx = W - 250
        can_submit = 1 <= len(self._bag_selection) <= 5
        sub_r = pygame.Rect(bx, az_y + ACTION_H - 70, 210, 44)
        col = theme.BTN_OK_BG if can_submit else theme.BTN_DISABLED
        fg  = theme.BTN_FG if can_submit else theme.BTN_DISABLED_FG
        self._draw_btn(surface, sub_r, "Submit Bag  →", col, fg)
        if can_submit:
            self._clickable.append((sub_r, self._submit_bag))

        cnt_s = theme.FONT_SMALL.render(
            f"{len(self._bag_selection)} card(s) in bag", True, self._accent())
        surface.blit(cnt_s, (bx, az_y + ACTION_H - 84))

        decl_lbl = theme.FONT_SMALL.render("Declare:", True, theme.TEXT_MUTED)
        surface.blit(decl_lbl, (bx, az_y + 14))

    # ── Button helper ─────────────────────────────────────────────────────── #

    def _draw_btn(self, surface, rect, text, bg, fg=None, font=None):
        fg   = fg   or theme.BTN_FG
        font = font or theme.FONT_H2
        r = pygame.Rect(rect)

        shad = pygame.Surface((r.width+4, r.height+4), pygame.SRCALPHA)
        pygame.draw.rect(shad, (0, 0, 0, 60),
                         (0, 0, r.width+4, r.height+4), border_radius=8)
        surface.blit(shad, (r.x+2, r.y+2))

        pygame.draw.rect(surface, bg, r, border_radius=7)
        hl = tuple(min(255, c + 40) for c in bg)
        pygame.draw.rect(surface, hl, pygame.Rect(r.x+8, r.y+2, r.width-16, 1))
        pygame.draw.rect(surface, (80, 80, 80), r, 1, border_radius=7)

        ts = font.render(text, True, fg)
        surface.blit(ts, (r.centerx - ts.get_width()//2,
                           r.centery - ts.get_height()//2))

        # Hover highlight
        if r.collidepoint(pygame.mouse.get_pos()):
            ov = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
            ov.fill((255, 255, 255, 18))
            surface.blit(ov, r.topleft)

    # ── Round-intro overlay ───────────────────────────────────────────────── #

    def _draw_round_intro(self, surface):
        e = self.engine
        W, H = surface.get_size()
        cx, cy = W // 2, H // 2

        # Dark overlay over the table
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        surface.blit(ov, (0, 0))

        # Border frame
        for off, clr in [(18, theme.ACCENT_GOLD), (26, theme.BG_LIGHT)]:
            pygame.draw.rect(surface, clr,
                             pygame.Rect(off, off, W - off*2, H - off*2), 1)

        # Round header
        accent = self._accent()
        rd_s = theme.FONT_TITLE.render(
            f"Round  {e.current_round}  of  {e.total_rounds}", True, accent)
        surface.blit(rd_s, (cx - rd_s.get_width()//2, cy - 120))

        theme.draw_divider(surface, cx - 220, cx + 220, cy - 70, theme.BORDER, accent)

        # Sheriff announcement
        sheriff = e.sheriff
        sw = theme.FONT_H2.render("Sheriff this round:", True, theme.TEXT_MUTED)
        surface.blit(sw, (cx - sw.get_width()//2, cy - 52))

        sn = theme.FONT_H1.render(sheriff.name, True, theme.SHERIFF_CLR)
        surface.blit(sn, (cx - sn.get_width()//2, cy - 28))

        # Sheriff star decoration
        star = theme.FONT_H1.render("★", True, theme.ACCENT_GOLD)
        gap = 14
        surface.blit(star, (cx - sn.get_width()//2 - star.get_width() - gap,
                             cy - 28))
        surface.blit(star, (cx + sn.get_width()//2 + gap, cy - 28))

        theme.draw_divider(surface, cx - 220, cx + 220, cy + 12, theme.BORDER, accent)

        # Explanation
        lines = [
            f"{sheriff.name} will NOT take market or bag turns this round.",
            "All other players are merchants.",
            f"{sheriff.name} inspects each bag during the Inspection phase.",
        ]
        y = cy + 30
        for line in lines:
            ls = theme.FONT_BODY.render(line, True, theme.TEXT_LIGHT)
            surface.blit(ls, (cx - ls.get_width()//2, y))
            y += ls.get_height() + 5

        # Tap to begin
        tap = theme.FONT_H2.render("Tap or press any key to begin", True, theme.TEXT_MUTED)
        surface.blit(tap, (cx - tap.get_width()//2, cy + 130))

        # Corner diamonds
        for px, py in [(40, 40), (W-40, 40), (40, H-40), (W-40, H-40)]:
            dsz = 10
            pts = [(px, py-dsz), (px+dsz, py), (px, py+dsz), (px-dsz, py)]
            pygame.draw.polygon(surface, theme.ACCENT_GOLD, pts)

    # ── Privacy overlay ───────────────────────────────────────────────────── #

    def _draw_privacy(self, surface):
        W, H = surface.get_size()

        # Opaque background
        surface.fill((8, 14, 8))
        theme.draw_gradient_rect(surface, (0, 0, W, H),
                                  (12, 24, 12), (6, 10, 6))

        # Triple ornate border
        for off, clr in [(18, theme.ACCENT_GOLD), (26, theme.BG_LIGHT), (34, theme.ACCENT_GOLD_D)]:
            pygame.draw.rect(surface, clr, pygame.Rect(off, off, W-off*2, H-off*2), 1)

        cx, cy = W//2, H//2

        # Large decorative diamond
        dsz = 60
        pts = [(cx, cy - 180 - dsz), (cx+dsz, cy-180),
               (cx, cy - 180 + dsz), (cx-dsz, cy-180)]
        pygame.draw.polygon(surface, theme.ACCENT_GOLD_D, pts)
        pygame.draw.polygon(surface, theme.ACCENT_GOLD, pts, 2)

        # Sheriff star
        star_s = theme.FONT_TITLE.render("★", True, theme.ACCENT_GOLD)
        surface.blit(star_s, (cx - star_s.get_width()//2, cy - 200))

        # "Pass device to" text
        pass_s = theme.FONT_H2.render("Pass the device to", True, theme.TEXT_MUTED)
        surface.blit(pass_s, (cx - pass_s.get_width()//2, cy - 80))

        # Player name (large)
        name_s = theme.FONT_TITLE.render(self._privacy_player or "", True, theme.ACCENT_GOLD_L)
        surface.blit(name_s, (cx - name_s.get_width()//2, cy - 44))

        # Divider
        theme.draw_divider(surface, cx - 200, cx + 200, cy + 30)

        # Tap hint (pulsing hint — just static here)
        tap_s = theme.FONT_H2.render("Tap or press any key to reveal your hand",
                                      True, theme.TEXT_MUTED)
        surface.blit(tap_s, (cx - tap_s.get_width()//2, cy + 56))

        # Corner diamonds
        for px, py in [(50, 50), (W-50, 50), (50, H-50), (W-50, H-50)]:
            for d in range(3, 0, -1):
                ds = 8 + d * 4
                pts2 = [(px, py-ds), (px+ds, py), (px, py+ds), (px-ds, py)]
                pygame.draw.polygon(surface, theme.ACCENT_GOLD_D if d < 3
                                    else theme.ACCENT_GOLD, pts2,
                                    0 if d == 1 else 1)
