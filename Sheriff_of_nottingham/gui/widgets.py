"""Reusable pygame UI widgets for Sheriff of Nottingham."""
import pygame
from gui import theme


class Button:
    """A clickable button with drop shadow, inner highlight and hover glow."""

    def __init__(self, rect, text, bg=None, fg=None, font=None,
                 hover_bg=None, disabled=False, on_click=None):
        self.rect     = pygame.Rect(rect)
        self.text     = text
        self.bg       = bg       if bg       is not None else theme.BTN_BG
        self.fg       = fg       if fg       is not None else theme.BTN_FG
        self.font     = font or theme.FONT_BODY
        self.hover_bg = hover_bg if hover_bg is not None else theme.BTN_HOVER
        self.disabled = disabled
        self.on_click = on_click
        self._hovered = False

    def _screen_rect(self, scroll=(0, 0)):
        return self.rect.move(-scroll[0], -scroll[1])

    def set_disabled(self, val: bool):
        self.disabled = val

    # ── Events ─────────────────────────────────────────────────────────── #

    def handle_event(self, event, scroll=(0, 0)) -> bool:
        sr = self._screen_rect(scroll)
        if event.type == pygame.MOUSEMOTION:
            self._hovered = sr.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if sr.collidepoint(event.pos) and not self.disabled:
                if self.on_click:
                    self.on_click()
                return True
        return False

    # ── Draw ───────────────────────────────────────────────────────────── #

    def draw(self, surface, scroll=(0, 0)):
        sr = self._screen_rect(scroll)
        clip = surface.get_clip()
        if clip.width > 0 and not clip.colliderect(sr):
            return

        if self.disabled:
            col = theme.BTN_DISABLED
            fg  = theme.BTN_DISABLED_FG
        elif self._hovered:
            col = self.hover_bg
            fg  = self.fg
        else:
            col = self.bg
            fg  = self.fg

        # Drop shadow
        shad = pygame.Surface((sr.width + 4, sr.height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shad, (0, 0, 0, 52),
                         (0, 0, sr.width + 4, sr.height + 4), border_radius=9)
        surface.blit(shad, (sr.x + 2, sr.y + 2))

        # Fill
        pygame.draw.rect(surface, col, sr, border_radius=7)

        # Inner top highlight (1 px lighter strip just inside top edge)
        highlight = tuple(min(255, c + 45) for c in col)
        hl_rect = pygame.Rect(sr.x + 8, sr.y + 2, sr.width - 16, 1)
        pygame.draw.rect(surface, highlight, hl_rect)

        # Border — gold when hovered, normal otherwise
        bdr = theme.ACCENT_GOLD if (self._hovered and not self.disabled) else theme.BORDER
        pygame.draw.rect(surface, bdr, sr, 1, border_radius=7)

        # Text
        ts = self.font.render(self.text, True, fg)
        surface.blit(ts, (sr.centerx - ts.get_width()  // 2,
                           sr.centery - ts.get_height() // 2))


class TextInput:
    """Single-line text entry field."""

    CURSOR_BLINK_MS = 530

    def __init__(self, rect, font=None, initial="", max_len=40,
                 bg=None, fg=None, border=None):
        self.rect   = pygame.Rect(rect)
        self.font   = font or theme.FONT_BODY
        self.text   = initial
        self.max_len = max_len
        self.bg     = bg     if bg     is not None else theme.BG_LIGHT
        self.fg     = fg     if fg     is not None else theme.TEXT_LIGHT
        self.border = border if border is not None else theme.BORDER
        self.active = False
        self._cursor_timer   = 0
        self._cursor_visible = True

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                self.active = False
            elif event.unicode and len(self.text) < self.max_len:
                self.text += event.unicode
            return True
        return False

    def update(self, dt_ms: int):
        if self.active:
            self._cursor_timer += dt_ms
            if self._cursor_timer >= self.CURSOR_BLINK_MS:
                self._cursor_timer   = 0
                self._cursor_visible = not self._cursor_visible
        else:
            self._cursor_visible = False

    def draw(self, surface):
        r = self.rect

        # Inner shadow (subtle dark strip at top)
        pygame.draw.rect(surface, self.bg, r, border_radius=5)
        shadow_clr = tuple(max(0, c - 18) for c in self.bg)
        pygame.draw.rect(surface, shadow_clr,
                         pygame.Rect(r.x + 1, r.y + 1, r.width - 2, 3), border_radius=3)

        # Border — gold glow when active
        bdr_clr = theme.ACCENT_GOLD if self.active else self.border
        border_w = 2 if self.active else 1
        pygame.draw.rect(surface, bdr_clr, r, border_w, border_radius=5)

        display = self.text + ("|" if self._cursor_visible and self.active else "")
        ts = self.font.render(display, True, self.fg)
        surface.blit(ts, (r.x + 7, r.centery - ts.get_height() // 2))


class RadioGroup:
    """Horizontal set of radio-button options."""

    def __init__(self, x, y, options, initial=None, font=None,
                 fg=None, selected_fg=None, bg=None, selected_bg=None,
                 on_change=None):
        self.font        = font        or theme.FONT_BODY
        self.fg          = fg          if fg          is not None else theme.TEXT_LIGHT
        self.selected_fg = selected_fg if selected_fg is not None else theme.ACCENT_GOLD
        self.bg          = bg          if bg          is not None else theme.BG_MID
        self.selected_bg = selected_bg if selected_bg is not None else theme.BG_LIGHT
        self.on_change   = on_change
        self.selected    = initial if initial is not None else (options[0] if options else None)
        self._rects   = []
        self._options = options
        self._build(x, y)

    def _build(self, x, y):
        self._rects.clear()
        cx = x
        for opt in self._options:
            ts = self.font.render(str(opt), True, self.fg)
            w  = ts.get_width()  + 22
            h  = ts.get_height() + 12
            self._rects.append((pygame.Rect(cx, y, w, h), opt))
            cx += w + 8

    @property
    def bottom(self):
        if self._rects:
            return max(r.bottom for r, _ in self._rects)
        return 0

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, opt in self._rects:
                if rect.collidepoint(event.pos):
                    if self.selected != opt:
                        self.selected = opt
                        if self.on_change:
                            self.on_change(opt)
                    return True
        return False

    def draw(self, surface):
        for rect, opt in self._rects:
            sel = (opt == self.selected)
            col = self.selected_bg if sel else self.bg
            bdr = theme.ACCENT_GOLD if sel else theme.BORDER

            # Drop shadow for selected
            if sel:
                shad = pygame.Surface((rect.width + 3, rect.height + 3), pygame.SRCALPHA)
                pygame.draw.rect(shad, (0, 0, 0, 44),
                                 (0, 0, rect.width + 3, rect.height + 3), border_radius=6)
                surface.blit(shad, (rect.x + 2, rect.y + 2))

            pygame.draw.rect(surface, col, rect, border_radius=5)

            if sel:
                hl = tuple(min(255, c + 38) for c in col)
                pygame.draw.rect(surface, hl,
                                 pygame.Rect(rect.x + 5, rect.y + 2, rect.width - 10, 1))

            pygame.draw.rect(surface, bdr, rect, 1, border_radius=5)

            fg = self.selected_fg if sel else self.fg
            ts = self.font.render(str(opt), True, fg)
            surface.blit(ts, (rect.centerx - ts.get_width()  // 2,
                               rect.centery - ts.get_height() // 2))


class Spinner:
    """Integer value widget with – and + buttons."""

    BTN_W = 30

    def __init__(self, rect, min_val=1, max_val=5, initial=1, font=None,
                 bg=None, fg=None, on_change=None):
        self.rect    = pygame.Rect(rect)
        self.min_val = min_val
        self.max_val = max_val
        self.value   = max(min_val, min(max_val, initial))
        self.font    = font or theme.FONT_BODY
        self.bg      = bg if bg is not None else theme.BG_LIGHT
        self.fg      = fg if fg is not None else theme.TEXT_LIGHT
        self.on_change = on_change
        self._build()

    def _build(self):
        r = self.rect
        self._dec_rect = pygame.Rect(r.x, r.y, self.BTN_W, r.height)
        self._inc_rect = pygame.Rect(r.right - self.BTN_W, r.y, self.BTN_W, r.height)
        self._val_rect = pygame.Rect(r.x + self.BTN_W, r.y,
                                     r.width - 2 * self.BTN_W, r.height)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._dec_rect.collidepoint(event.pos):
                self._change(-1); return True
            if self._inc_rect.collidepoint(event.pos):
                self._change(1);  return True
        return False

    def _change(self, delta):
        self.value = max(self.min_val, min(self.max_val, self.value + delta))
        if self.on_change:
            self.on_change(self.value)

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=5)
        pygame.draw.rect(surface, theme.BORDER, self.rect, 1, border_radius=5)

        for btn_rect, label in ((self._dec_rect, "-"), (self._inc_rect, "+")):
            pygame.draw.rect(surface, theme.BTN_BG, btn_rect, border_radius=5)
            hl = tuple(min(255, c + 40) for c in theme.BTN_BG)
            pygame.draw.rect(surface, hl,
                             pygame.Rect(btn_rect.x + 4, btn_rect.y + 2,
                                         btn_rect.width - 8, 1))
            pygame.draw.rect(surface, theme.BORDER, btn_rect, 1, border_radius=5)
            ts = self.font.render(label, True, self.fg)
            surface.blit(ts, (btn_rect.centerx - ts.get_width()  // 2,
                               btn_rect.centery - ts.get_height() // 2))

        vs = self.font.render(str(self.value), True, self.fg)
        surface.blit(vs, (self._val_rect.centerx - vs.get_width()  // 2,
                           self._val_rect.centery - vs.get_height() // 2))


class Dropdown:
    """Single-select dropdown list (drawn on top of everything)."""

    ITEM_H = 30

    def __init__(self, rect, options, initial=None, font=None,
                 bg=None, fg=None, on_change=None, open_up=False):
        self.rect     = pygame.Rect(rect)
        self.options  = list(options)
        self.selected = initial if initial is not None else (options[0] if options else "")
        self.font     = font or theme.FONT_BODY
        self.bg       = bg if bg is not None else theme.BG_LIGHT
        self.fg       = fg if fg is not None else theme.TEXT_LIGHT
        self.on_change = on_change
        self.expanded  = False
        self.open_up   = open_up
        self._hovered_index = -1

    def _dropdown_rect(self):
        list_h = self.ITEM_H * len(self.options)
        if self.open_up:
            return pygame.Rect(self.rect.x, self.rect.top - list_h,
                               self.rect.width, list_h)
        return pygame.Rect(self.rect.x, self.rect.bottom,
                           self.rect.width, list_h)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.expanded = not self.expanded
                return True
            if self.expanded:
                dr = self._dropdown_rect()
                if dr.collidepoint(event.pos):
                    idx = (event.pos[1] - dr.top) // self.ITEM_H
                    if 0 <= idx < len(self.options):
                        new_val = self.options[idx]
                        if new_val != self.selected:
                            self.selected = new_val
                            if self.on_change:
                                self.on_change(new_val)
                    self.expanded = False
                    return True
                self.expanded = False
        if event.type == pygame.MOUSEMOTION and self.expanded:
            dr = self._dropdown_rect()
            if dr.collidepoint(event.pos):
                self._hovered_index = (event.pos[1] - dr.top) // self.ITEM_H
            else:
                self._hovered_index = -1
        return False

    def draw(self, surface):
        # Collapsed header
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=5)
        bdr = theme.ACCENT_GOLD if self.expanded else theme.BORDER
        bdr_w = 2 if self.expanded else 1
        pygame.draw.rect(surface, bdr, self.rect, bdr_w, border_radius=5)

        ts = self.font.render(self.selected, True, self.fg)
        surface.blit(ts, (self.rect.x + 8,
                           self.rect.centery - ts.get_height() // 2))
        arrow = ("v" if self.expanded else "^") if self.open_up else ("^" if self.expanded else "v")
        as_ = self.font.render(arrow, True, theme.ACCENT_GOLD)
        surface.blit(as_, (self.rect.right - as_.get_width() - 8,
                            self.rect.centery - as_.get_height() // 2))

        if not self.expanded:
            return

        dr = self._dropdown_rect()

        # Shadow behind expanded list
        shad = pygame.Surface((dr.width + 4, dr.height + 4), pygame.SRCALPHA)
        pygame.draw.rect(shad, (0, 0, 0, 60),
                         (0, 0, dr.width + 4, dr.height + 4), border_radius=5)
        surface.blit(shad, (dr.x + 2, dr.y + 2))

        pygame.draw.rect(surface, self.bg, dr, border_radius=5)
        pygame.draw.rect(surface, theme.BORDER, dr, 1, border_radius=5)

        for i, opt in enumerate(self.options):
            item_rect = pygame.Rect(dr.x, dr.y + i * self.ITEM_H,
                                    dr.width, self.ITEM_H)
            if i == self._hovered_index:
                pygame.draw.rect(surface, theme.BG_LIGHT, item_rect)
            ts = self.font.render(str(opt), True, self.fg)
            surface.blit(ts, (item_rect.x + 8,
                               item_rect.centery - ts.get_height() // 2))
            if i > 0:
                pygame.draw.line(surface, theme.BORDER,
                                 (dr.x + 4, item_rect.y), (dr.right - 4, item_rect.y), 1)


class ScrollView:
    """Clips a region of the screen and scrolls content within it."""

    def __init__(self, screen_rect, bg_color=None):
        self.rect      = pygame.Rect(screen_rect)
        self.bg        = bg_color or theme.BG_DARK
        self.scroll_y  = 0
        self.content_h = 0

    def clamp_scroll(self):
        max_s = max(0, self.content_h - self.rect.height)
        self.scroll_y = max(0, min(self.scroll_y, max_s))

    def handle_scroll(self, event) -> bool:
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_y -= event.y * 32
                self.clamp_scroll()
                return True
        return False

    def content_pos(self, screen_pos):
        return (screen_pos[0] - self.rect.x,
                screen_pos[1] - self.rect.y + self.scroll_y)

    def screen_y(self, content_y: int) -> int:
        return self.rect.y + content_y - self.scroll_y

    def begin(self, surface):
        surface.set_clip(self.rect)
        pygame.draw.rect(surface, self.bg, self.rect)

    def end(self, surface):
        surface.set_clip(None)
