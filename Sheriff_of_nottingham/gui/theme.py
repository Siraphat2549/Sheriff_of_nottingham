"""Visual theme constants for Sheriff of Nottingham — pygame version."""
import pygame

# ── Palette (RGB tuples) ───────────────────────────────────────────────────
BG_DARK       = (16, 28, 16)
BG_MID        = (36, 60, 36)
BG_LIGHT      = (54, 94, 54)
ACCENT_GOLD   = (212, 168, 30)
ACCENT_GOLD_L = (248, 204, 82)
ACCENT_GOLD_D = (142, 108, 10)
TEXT_LIGHT    = (245, 240, 224)
TEXT_DARK     = (26, 26, 10)
TEXT_MUTED    = (152, 138, 106)
BORDER        = (80, 130, 80)
BORDER_BRIGHT = (112, 172, 112)
DANGER        = (200, 56, 42)
DANGER_L      = (232, 88, 74)
SUCCESS       = (40, 176, 96)
SUCCESS_L     = (72, 210, 128)
SHERIFF_CLR   = (192, 112, 32)

CARD_LEGAL_BG   = (34, 78, 44)
CARD_LEGAL_BG_L = (54, 108, 64)
CARD_LEGAL_FG   = (212, 250, 202)
CARD_CONTRA_BG  = (64, 18, 18)
CARD_CONTRA_BG_L= (92, 36, 36)
CARD_CONTRA_FG  = (250, 174, 142)
CARD_SELECTED   = (222, 184, 48)
CARD_BACK       = (20, 48, 94)
CARD_BACK_L     = (36, 72, 136)
CARD_BACK_FG    = (102, 144, 216)

BTN_BG        = (80, 42, 14)
BTN_FG        = (245, 240, 224)
BTN_HOVER     = (116, 66, 26)
BTN_DANGER_BG = (118, 22, 8)
BTN_DANGER_HOVER = (150, 40, 24)
BTN_OK_BG     = (22, 84, 40)
BTN_OK_HOVER  = (38, 114, 56)
BTN_DISABLED  = (50, 38, 22)
BTN_DISABLED_FG = (106, 96, 80)

# ── Sizes ──────────────────────────────────────────────────────────────────
WINDOW_W   = 1200
WINDOW_H   = 760
CARD_W     = 88
CARD_H     = 122
CARD_PAD   = 8
PANEL_PAD  = 12
SIDEBAR_W  = 240

# ── Fonts (initialised after pygame.init()) ────────────────────────────────
FONT_TITLE  = None
FONT_H1     = None
FONT_H2     = None
FONT_BODY   = None
FONT_SMALL  = None
FONT_CARD   = None
FONT_CARD_SM= None


def init_fonts() -> None:
    global FONT_TITLE, FONT_H1, FONT_H2, FONT_BODY, FONT_SMALL, FONT_CARD, FONT_CARD_SM
    prefer = ["Georgia", "Palatino", "Times New Roman", "serif"]
    name = _find_font(prefer)
    FONT_TITLE   = pygame.font.SysFont(name, 40, bold=True)
    FONT_H1      = pygame.font.SysFont(name, 26, bold=True)
    FONT_H2      = pygame.font.SysFont(name, 17, bold=True)
    FONT_BODY    = pygame.font.SysFont(name, 14)
    FONT_SMALL   = pygame.font.SysFont(name, 12)
    FONT_CARD    = pygame.font.SysFont(name, 13, bold=True)
    FONT_CARD_SM = pygame.font.SysFont(name, 10)


def _find_font(names):
    available = set(f.lower() for f in pygame.font.get_fonts())
    for n in names:
        if n.lower().replace(" ", "") in available or n.lower() in available:
            return n
    return None


# ── Gradient ───────────────────────────────────────────────────────────────

def draw_gradient_rect(surface, rect, color_top, color_bottom, border_radius=0):
    """Fill rect with a vertical gradient; respects border_radius via SRCALPHA mask."""
    r = pygame.Rect(rect)
    if r.height <= 0 or r.width <= 0:
        return
    if border_radius > 0:
        tmp = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        _fill_gradient(tmp, pygame.Rect(0, 0, r.width, r.height),
                       tuple(color_top) + (255,), tuple(color_bottom) + (255,))
        mask = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         (0, 0, r.width, r.height), border_radius=border_radius)
        tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(tmp, r.topleft)
    else:
        _fill_gradient(surface, r, color_top, color_bottom)


def _fill_gradient(surface, rect, color_top, color_bottom):
    r = pygame.Rect(rect)
    h = r.height
    if h <= 0:
        return
    n = len(color_top)
    for i in range(h):
        t = i / h
        c = tuple(int(color_top[k] + (color_bottom[k] - color_top[k]) * t) for k in range(n))
        pygame.draw.line(surface, c, (r.x, r.y + i), (r.right - 1, r.y + i))


# ── Text ───────────────────────────────────────────────────────────────────

def draw_text(surface, text: str, font, color, x: int, y: int,
              align: str = "left", max_width: int = 0) -> int:
    """Render text; return total pixel height used."""
    if not text:
        return 0
    if max_width > 0:
        return _draw_wrapped(surface, text, font, color, x, y, align, max_width)
    surf = font.render(text, True, color)
    bx = _align_x(x, surf.get_width(), align)
    surface.blit(surf, (bx, y))
    return surf.get_height()


def _draw_wrapped(surface, text, font, color, x, y, align, max_width) -> int:
    words = text.split()
    lines, line = [], []
    for word in words:
        test = " ".join(line + [word])
        if font.size(test)[0] <= max_width:
            line.append(word)
        else:
            if line:
                lines.append(" ".join(line))
            line = [word]
    if line:
        lines.append(" ".join(line))
    total_h = 0
    lh = font.get_height() + 2
    for ln in lines:
        surf = font.render(ln, True, color)
        bx = _align_x(x, surf.get_width(), align)
        surface.blit(surf, (bx, y + total_h))
        total_h += lh
    return total_h


def _align_x(x, w, align):
    if align == "center":
        return x - w // 2
    if align == "right":
        return x - w
    return x


# ── Panel helpers ──────────────────────────────────────────────────────────

def draw_panel(surface, rect, color=None, border_color=None, radius=6):
    color = color or BG_MID
    r = pygame.Rect(rect)
    pygame.draw.rect(surface, color, r, border_radius=radius)
    if border_color:
        pygame.draw.rect(surface, border_color, r, 1, border_radius=radius)


def draw_ornate_panel(surface, rect, color=None, accent=None, radius=8,
                      gradient_bottom=None):
    """Panel with drop shadow, optional gradient, double border + corner diamonds."""
    color  = color  or BG_MID
    accent = accent or ACCENT_GOLD
    r = pygame.Rect(rect)

    # Drop shadow
    shad = pygame.Surface((r.width + 5, r.height + 5), pygame.SRCALPHA)
    pygame.draw.rect(shad, (0, 0, 0, 55),
                     (0, 0, r.width + 5, r.height + 5), border_radius=radius + 2)
    surface.blit(shad, (r.x + 3, r.y + 3))

    # Fill
    if gradient_bottom:
        draw_gradient_rect(surface, r, color, gradient_bottom, border_radius=radius)
    else:
        pygame.draw.rect(surface, color, r, border_radius=radius)

    # Outer border
    pygame.draw.rect(surface, accent, r, 2, border_radius=radius)

    # Inner border
    inner = r.inflate(-8, -8)
    if inner.width > 0 and inner.height > 0:
        dim = tuple(max(0, c - 30) for c in accent)
        pygame.draw.rect(surface, dim, inner, 1, border_radius=max(0, radius - 3))

    # Corner diamond ornaments
    dsz = 5
    for cx, cy in (r.topleft, r.topright, r.bottomleft, r.bottomright):
        pts = [(cx, cy - dsz), (cx + dsz, cy), (cx, cy + dsz), (cx - dsz, cy)]
        pygame.draw.polygon(surface, accent, pts)


def draw_divider(surface, x1, x2, y, color=None, accent=None):
    """Ornate horizontal separator with a centre diamond."""
    color  = color  or BORDER
    accent = accent or ACCENT_GOLD
    cx = (x1 + x2) // 2
    pygame.draw.line(surface, color, (x1, y), (cx - 9, y), 1)
    pygame.draw.line(surface, color, (cx + 9, y), (x2, y), 1)
    dsz = 5
    pts = [(cx, y - dsz), (cx + dsz, y), (cx, y + dsz), (cx - dsz, y)]
    pygame.draw.polygon(surface, accent, pts)


# ── Card drawing ───────────────────────────────────────────────────────────

def _draw_item_icon(surface, card_name: str, cx: int, cy: int, size: int) -> None:
    """Draw a pixel-art icon for each item type, centered at (cx, cy)."""
    s = max(8, size)
    cx, cy = int(cx), int(cy)

    if card_name == "Apple":
        pygame.draw.circle(surface, (210, 45, 45), (cx, cy + s // 5), int(s * 0.55))
        pygame.draw.circle(surface, (230, 80, 80), (cx - s // 5, cy), int(s * 0.3))
        pygame.draw.line(surface, (80, 50, 15), (cx, cy - s // 3), (cx + 2, cy - s), 2)
        pygame.draw.polygon(surface, (50, 160, 50), [
            (cx + 1, cy - s // 3),
            (cx + s // 2, cy - int(s * 0.85)),
            (cx + s // 4, cy - s // 5),
        ])

    elif card_name == "Cheese":
        pts = [
            (cx - s, cy + s // 2),
            (cx + s, cy + s // 2),
            (cx + s // 2, cy - s),
        ]
        pygame.draw.polygon(surface, (230, 200, 40), pts)
        pygame.draw.polygon(surface, (180, 148, 0), pts, 2)
        for hx, hy in [(cx - s // 4, cy + s // 5), (cx + s // 3, cy + s // 8), (cx + s // 2, cy - s // 5)]:
            pygame.draw.circle(surface, (170, 138, 0), (hx, hy), max(2, s // 5))

    elif card_name == "Bread":
        body = pygame.Rect(cx - s, cy - s // 4, s * 2, int(s * 0.8))
        pygame.draw.rect(surface, (160, 100, 40), body, border_radius=s // 3)
        dome = pygame.Rect(cx - int(s * 0.8), cy - int(s * 0.9), int(s * 1.6), int(s * 0.8))
        pygame.draw.ellipse(surface, (200, 140, 60), dome)
        pygame.draw.ellipse(surface, (165, 110, 35), dome, 1)
        for x_off in [-s // 3, s // 3]:
            pygame.draw.line(surface, (130, 80, 25),
                             (cx + x_off, cy - int(s * 0.8)),
                             (cx + x_off, cy - int(s * 0.1)), 1)

    elif card_name == "Chicken":
        pygame.draw.circle(surface, (210, 140, 60), (cx, cy - s // 5), int(s * 0.55))
        pygame.draw.ellipse(surface, (210, 140, 60),
                            pygame.Rect(cx - s // 4, cy - s // 3, s // 2, int(s * 0.95)))
        pygame.draw.rect(surface, (238, 225, 205),
                         pygame.Rect(cx - 3, cy + s // 3, 6, s // 2))
        pygame.draw.circle(surface, (238, 225, 205), (cx, cy + s // 3 + s // 2), s // 5)
        for dx in (-s // 4, s // 4):
            pygame.draw.circle(surface, (238, 225, 205), (cx + dx, cy + s // 3), s // 6)

    elif card_name == "Pepper":
        pygame.draw.ellipse(surface, (210, 40, 30),
                            pygame.Rect(cx - s // 3, cy - int(s * 0.75), int(s * 0.66), int(s * 1.3)))
        pygame.draw.ellipse(surface, (240, 70, 60),
                            pygame.Rect(cx - s // 5, cy - int(s * 0.65), s // 3, s // 2))
        pygame.draw.rect(surface, (50, 140, 50),
                         pygame.Rect(cx - s // 4, cy - int(s * 0.82), s // 2, s // 5),
                         border_radius=2)
        pygame.draw.line(surface, (50, 140, 50), (cx, cy - int(s * 0.82)), (cx + s // 4, cy - s), 2)

    elif card_name == "Mead":
        body = pygame.Rect(cx - int(s * 0.65), cy - int(s * 0.75), int(s * 1.1), int(s * 1.35))
        pygame.draw.rect(surface, (180, 130, 40), body, border_radius=3)
        pygame.draw.rect(surface, (140, 100, 20), body, 2, border_radius=3)
        handle = pygame.Rect(cx + int(s * 0.42), cy - s // 5, int(s * 0.5), int(s * 0.65))
        pygame.draw.rect(surface, (140, 100, 20), handle, 3, border_radius=5)
        for i in (-1, 0, 1):
            pygame.draw.circle(surface, (245, 245, 242),
                               (cx + i * s // 4, cy - int(s * 0.62)), s // 4)
        pygame.draw.line(surface, (220, 170, 60),
                         (cx - s // 3, cy - s // 5), (cx - s // 3, cy + s // 3), 2)

    elif card_name == "Silk":
        pts = [
            (cx - s,       cy + s // 5),
            (cx - s // 2,  cy - s // 2),
            (cx,           cy + s // 5),
            (cx + s // 2,  cy - s // 2),
            (cx + s,       cy + s // 5),
            (cx + s,       cy + s // 2),
            (cx + s // 2,  cy - s // 7),
            (cx,           cy + s // 2),
            (cx - s // 2,  cy - s // 7),
            (cx - s,       cy + s // 2),
        ]
        pygame.draw.polygon(surface, (140, 90, 200), pts)
        pygame.draw.polygon(surface, (170, 120, 230), pts, 1)
        pygame.draw.line(surface, (190, 150, 240),
                         (cx - int(s * 0.7), cy + s // 5), (cx - s // 4, cy - s // 3), 2)

    elif card_name == "Crossbow":
        pygame.draw.rect(surface, (130, 85, 35),
                         pygame.Rect(cx - s, cy - s // 7, s * 2, s // 3),
                         border_radius=3)
        pygame.draw.arc(surface, (100, 65, 20),
                        pygame.Rect(cx - int(s * 0.72), cy - int(s * 0.82), int(s * 1.44), int(s * 0.88)),
                        0, 3.14159, 4)
        pygame.draw.line(surface, (220, 195, 155),
                         (cx - int(s * 0.72), cy), (cx + int(s * 0.72), cy), 1)
        pygame.draw.line(surface, (150, 100, 40),
                         (cx - int(s * 0.78), cy - 1), (cx + int(s * 0.55), cy - 1), 2)
        pygame.draw.polygon(surface, (180, 148, 80), [
            (cx + int(s * 0.55), cy - s // 4),
            (cx + int(s * 0.55), cy + s // 4),
            (cx + s,             cy - 1),
        ])


def draw_card(surface, card, rect, selected=False):
    """Draw a polished face-up card with gradient body, inner border and shadow."""
    is_legal = card.is_legal
    bg_top = CARD_LEGAL_BG_L if is_legal else CARD_CONTRA_BG_L
    bg_bot = CARD_LEGAL_BG   if is_legal else CARD_CONTRA_BG
    fg     = CARD_LEGAL_FG   if is_legal else CARD_CONTRA_FG
    bdr    = CARD_SELECTED   if selected  else (BORDER if is_legal else (148, 54, 54))

    r = pygame.Rect(rect)

    # Selection glow — layered rings drawn behind the card body
    if selected:
        for i in range(4, 0, -1):
            ga = 16 + i * 16
            gr = r.inflate(i * 5, i * 5)
            gs = pygame.Surface((gr.width, gr.height), pygame.SRCALPHA)
            pygame.draw.rect(gs, (*CARD_SELECTED, ga),
                           (0, 0, gr.width, gr.height), border_radius=10 + i)
            surface.blit(gs, gr.topleft)

    # Drop shadow
    shad = pygame.Surface((r.width + 4, r.height + 4), pygame.SRCALPHA)
    pygame.draw.rect(shad, (0, 0, 0, 68),
                     (0, 0, r.width + 4, r.height + 4), border_radius=8)
    surface.blit(shad, (r.x + 2, r.y + 2))

    # Gradient body
    draw_gradient_rect(surface, r, bg_top, bg_bot, border_radius=7)

    # Contraband: subtle diagonal stripe texture
    if not is_legal:
        clip_r = r.inflate(-8, -8)
        surface.set_clip(clip_r)
        stripe_clr = tuple(max(0, c - 10) for c in bg_bot)
        for x_off in range(-r.height, r.width + r.height, 16):
            x1 = clip_r.x + x_off
            x2 = x1 + clip_r.height
            pygame.draw.line(surface, stripe_clr, (x1, clip_r.y), (x2, clip_r.bottom), 1)
        surface.set_clip(None)

    # Outer border (thicker when selected)
    pygame.draw.rect(surface, bdr, r, 3 if selected else 2, border_radius=7)

    # Inner decorative border
    inner = r.inflate(-6, -6)
    inner_clr = tuple(min(255, c + 22) for c in bg_top)
    pygame.draw.rect(surface, inner_clr, inner, 1, border_radius=4)

    # Type badge at top centre + corner value pip
    kind     = "LEGAL" if is_legal else "CONTRA"
    kind_clr = (154, 226, 154) if is_legal else (226, 108, 108)
    ks = FONT_CARD_SM.render(kind, True, kind_clr)
    surface.blit(ks, (r.centerx - ks.get_width() // 2, r.top + 4))
    pip_v = FONT_CARD_SM.render(str(card.value), True, fg)
    surface.blit(pip_v, (r.left + 5, r.top + 4))

    # Horizontal rule below badge
    pygame.draw.line(surface, inner_clr,
                     (r.left + 10, r.top + 18), (r.right - 10, r.top + 18), 1)

    # Icon + name
    _draw_item_icon(surface, card.name, r.centerx, r.centery - 10, 22)
    name_s = FONT_CARD.render(card.name, True, fg)
    surface.blit(name_s, (r.centerx - name_s.get_width() // 2, r.centery + 18))

    # Bottom separator + stats
    pygame.draw.line(surface, inner_clr,
                     (r.left + 9, r.bottom - 22), (r.right - 9, r.bottom - 22), 1)
    val_text = f"V:{card.value}  P:{card.penalty}"
    vs = FONT_CARD_SM.render(val_text, True, tuple(min(255, c + 30) for c in fg))
    surface.blit(vs, (r.centerx - vs.get_width() // 2, r.bottom - 17))


def draw_card_back(surface, rect):
    """Draw an ornate face-down card back with crosshatch and diamond centre."""
    r = pygame.Rect(rect)

    # Drop shadow
    shad = pygame.Surface((r.width + 4, r.height + 4), pygame.SRCALPHA)
    pygame.draw.rect(shad, (0, 0, 0, 68),
                     (0, 0, r.width + 4, r.height + 4), border_radius=8)
    surface.blit(shad, (r.x + 2, r.y + 2))

    # Gradient body
    draw_gradient_rect(surface, r, CARD_BACK_L, CARD_BACK, border_radius=7)

    # Outer border
    pygame.draw.rect(surface, CARD_BACK_FG, r, 1, border_radius=7)

    # Inner border
    inner = r.inflate(-6, -6)
    inner_clr = tuple(max(0, c - 22) for c in CARD_BACK_FG)
    pygame.draw.rect(surface, inner_clr, inner, 1, border_radius=4)

    # Diagonal crosshatch clipped to inner rect
    surface.set_clip(inner)
    line_clr = tuple(max(0, c - 28) for c in CARD_BACK_L)
    for x_off in range(-inner.height, inner.width + inner.height, 14):
        x1 = inner.x + x_off
        x2 = x1 - inner.height
        pygame.draw.line(surface, line_clr, (x1, inner.y), (x2, inner.bottom), 1)
    surface.set_clip(None)

    # Centre diamond ornament
    cx, cy = r.centerx, r.centery
    dsz = 20
    pygame.draw.polygon(surface, CARD_BACK_FG,
                        [(cx, cy - dsz), (cx + dsz, cy),
                         (cx, cy + dsz), (cx - dsz, cy)], 1)

    qs = FONT_H1.render("?", True, CARD_BACK_FG)
    surface.blit(qs, (cx - qs.get_width() // 2, cy - qs.get_height() // 2))
