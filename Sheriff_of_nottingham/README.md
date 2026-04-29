# Sheriff of Nottingham

A fully playable digital implementation of the **Sheriff of Nottingham** board game, built with Python and Pygame. Supports 2–5 human players taking turns on the same device (hot-seat multiplayer).

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [How to Play](#2-how-to-play)
3. [Coding Features](#3-coding-features)
4. [Data Flow](#4-data-flow)
5. [File Structure](#5-file-structure)
6. [How to Run the Code from Scratch](#6-how-to-run-the-code-from-scratch)

---

## 1. Introduction

### About the Board Game

Sheriff of Nottingham is a social deduction and bluffing board game for 2–5 players. Players take turns acting as a **Merchant** trying to smuggle goods into the city, and as the **Sheriff** trying to catch them. Merchants secretly pack a bag and declare its contents to the Sheriff — truthfully or not. The Sheriff must decide whether to inspect the bag or let the merchant pass. Successful smuggling earns high rewards; getting caught means paying heavy penalties.

### Features Implemented

- Full rule set for 2–5 human players with hot-seat turn management
- All 8 card types — 4 legal goods and 4 contraband — with official point values and penalties
- Sheriff rotation so every player serves as Sheriff an equal number of times
- Bribe mechanic — a merchant may offer gold to the Sheriff to avoid inspection
- King and Queen bonus system that rewards collecting the most of a single legal good
- Persistent game history stored in a local SQLite database
- Full Pygame GUI with a poker-table layout, pixel-art card icons, and card selection glow effects
- History screen showing past game records and cumulative per-player statistics

### Objective

Accumulate the most total gold by the end of the game. A player's final score is:

```
Final Score = Gold on Hand + Stall Card Values + King/Queen Bonuses
```

---

## 2. How to Play

### Game Setup

1. Launch the game and click **New Game**.
2. Choose the number of players (2–5) and enter each player's name.
3. All players share the same device — players take turns at the keyboard/mouse.
4. Each player starts with **50 gold** and is dealt a hand of **6 cards**.
5. A face-up **Market** of 5 cards is placed in the centre.

### The Cards

The deck contains **52 cards** total — 40 legal goods and 12 contraband. At game end, the player who collected the **most** of a legal good earns the King bonus; the player with the **second most** earns the Queen bonus.

| | Card | Type | Value | Penalty | Deck Count | King Bonus | Queen Bonus |
|---|---|---|---|---|---|---|---|
| 🍎 | Apple | Legal | 2 | 2 | 10 | +20 | +10 |
| 🧀 | Cheese | Legal | 3 | 3 | 10 | +15 | +10 |
| 🍞 | Bread | Legal | 3 | 3 | 10 | +15 | +10 |
| 🍗 | Chicken | Legal | 4 | 4 | 10 | +10 | +5 |
| 🌶️ | Pepper | Contraband | 9 | 4 | 6 | — | — |
| 🍺 | Mead | Contraband | 7 | 4 | 6 | — | — |
| 🧵 | Silk | Contraband | 11 | 5 | 6 | — | — |
| 🏹 | Crossbow | Contraband | 13 | 6 | 6 | — | — |

> **Value** — gold earned when a card is placed in the stall.  
> **Penalty** — gold paid *per illegal card* to the Sheriff if caught.  
> **King / Queen Bonus** — end-game bonus for having the most / second-most of that legal good in your stall.

### Game Flow

Each round has four phases:

**Phase 1 — Market**
Every merchant (all players except the current Sheriff) draws cards one at a time:
- Draw 2 cards from the deck, **or**
- Take 1 specific card from the 5 face-up market cards.

Discard down to a maximum hand size of 6 if needed.

**Phase 2 — Pack Bag**
Each merchant secretly selects 1–5 cards to place in their bag, then makes a verbal declaration to the Sheriff:
> *"I have [quantity] [legal good type]."*

The declaration **must name a legal good** — any contraband can be hidden inside. A merchant may also whisper a **bribe amount** alongside their declaration.

**Phase 3 — Inspection**
The Sheriff reviews each merchant's bag one at a time and chooses:

| Decision | Outcome |
|---|---|
| **Let Through** | All bag contents go to the merchant's stall. If a bribe was offered and accepted, the merchant pays the bribe to the Sheriff. |
| **Inspect — Honest Bag** | Contents match the declaration exactly. The Sheriff pays **2 gold per card** to the merchant as compensation. |
| **Inspect — Caught Smuggling** | Merchant pays the **penalty value** of every illegal card to the Sheriff. Declared cards still go to the stall; contraband is confiscated. |

**Phase 4 — Round End**
The Sheriff badge passes clockwise to the next player. A new round begins.

### Winning Conditions

The game ends after every player has served as Sheriff an equal number of times:
- 2–4 players: each player is Sheriff **twice**
- 5 players: each player is Sheriff **once**

Final scores are calculated and the player with the highest total wins:

```
Final Score = Gold on Hand + Stall Card Values + King/Queen Bonuses
```

---

## 3. Coding Features

### Major Classes and Functions

#### `GameEngine` — `game/game_logic.py`

The central controller that owns all game state and enforces the rules. No game state is mutated anywhere else.

| Method | Description |
|---|---|
| `setup_game(player_configs)` | Initialises players, shuffles the deck, deals hands, opens the market, sets total rounds |
| `market_draw_from_deck(player)` | Draws 2 cards from the deck into the player's hand |
| `market_take_from_market(player, card)` | Removes a chosen card from the 5-card market and replenishes the gap |
| `market_discard(player, cards)` | Moves excess cards from hand back to the discard pile |
| `pack_player_bag(player, cards, type, qty)` | Validates 1–5 cards, removes them from hand, stores bag declaration |
| `sheriff_inspect(merchant)` | Opens the bag; pays compensation if honest, collects penalty if smuggling caught |
| `sheriff_let_through(merchant)` | Passes the bag to the stall; processes bribe if one was offered |
| `advance_inspection_phase()` | Steps to the next merchant; triggers `ROUND_END` when all are done |
| `end_round()` | Rotates the Sheriff index and starts the next round, or sets `GAME_END` |
| `calculate_final_scores()` | Computes gold + stall value + King/Queen bonuses for every player |

#### `Player` — `game/player.py`

Represents a single human participant.

| Property / Method | Description |
|---|---|
| `gold` | Current gold on hand (starts at 50) |
| `hand` | List of `Card` objects currently held |
| `stall` | Goods successfully passed into the city (persists across rounds) |
| `bag` | The `MerchantBag` for the current round |
| `pack_bag(cards, type, qty)` | Loads the bag with selected cards and a declaration |
| `accept_bag_into_stall()` | Moves all bag contents to the stall after passing inspection |
| `pay_gold(amount)` | Deducts gold, clamped to a minimum of 0; returns actual amount paid |
| `stall_value` | Sum of all card values in the stall |
| `stall_counts` | `Counter` of card types in the stall, used for bonus calculation |

#### `MerchantBag` — `game/player.py`

Holds the bag state for one round. Cleared at the start of each new round.

| Method / Property | Description |
|---|---|
| `is_honest()` | Returns `True` only if every card matches the declared type **and** the count matches declared quantity |
| `is_ready` | Property — `True` when cards are packed and a declaration is set |
| `clear()` | Resets cards, declared type, quantity, and bribe for the next round |

#### `Deck` — `game/deck.py`

Manages the draw pile, discard pile, and face-up market.

| Method / Property | Description |
|---|---|
| `draw()` / `draw_many(n)` | Draw cards; auto-reshuffles the discard pile into the draw pile when empty |
| `discard(card)` / `discard_many(cards)` | Moves cards to the discard pile |
| `market_cards` | Property exposing the top 5 discard cards as the face-up market |
| `take_from_market(card)` | Removes a specific card from the market |

#### `Card` / `CardType` / `CardInfo` — `game/cards.py`

- `CardType` — `Enum` with 8 values: `APPLE`, `CHEESE`, `BREAD`, `CHICKEN`, `PEPPER`, `MEAD`, `SILK`, `CROSSBOW`
- `CardInfo` — `dataclass` storing `value`, `penalty`, `count`, `king_bonus`, `queen_bonus`
- `Card` — wraps a `CardType` with convenience properties: `is_legal`, `is_contraband`, `value`, `penalty`, `name`

#### GUI Modules — `gui/`

| Module | Key Class / Role |
|---|---|
| `app.py` | `App` — owns the Pygame window and 60 FPS game loop; manages screen transitions and modal dialogs |
| `theme.py` | Visual constants (colours, sizes, fonts) and all drawing utilities including `draw_card()` and `_draw_item_icon()` |
| `widgets.py` | Reusable components: `Button`, `TextInput`, `RadioGroup`, `Spinner` |
| `screens/game_screen.py` | Main gameplay screen — poker-table layout, hand display, bag packing dialog, inspection panel |
| `screens/setup_screen.py` | Player count selector (RadioGroup) and name entry (TextInput) for each player |
| `screens/main_menu.py` | Title screen with New Game, History, and Quit buttons |
| `screens/history_screen.py` | Reads `game_records.db` and displays past game records and per-player stats |

#### `database` — `storage/database.py`

| Function | Description |
|---|---|
| `initialize_db()` | Creates `games` and `player_stats` tables if they do not exist |
| `save_game(scores, num_rounds, duration_secs)` | Writes the completed game record; upserts cumulative stats for each player |
| `get_recent_games(limit)` | Returns the most recent game records for the history screen |
| `get_all_stats_summary()` | Returns aggregated win counts, scores, and smuggling stats across all saved games |

### Description of Important Modules

| Module | Role |
|---|---|
| `game/` | Pure game logic with no GUI or database dependency — rules, state, and card data only |
| `gui/` | Pygame presentation layer; reads from `GameEngine` and sends validated user actions back to it |
| `storage/` | Thin SQLite wrapper; called only at startup (load history) and at game end (save result) |

### Key Algorithms

#### King / Queen Bonus Calculation

`GameEngine.calculate_final_scores()` iterates over every legal good type and counts each player's stall using a `Counter`. The player with the highest count earns the King bonus for that good; the player with the second-highest earns the Queen bonus.

```python
for card_type in LEGAL_GOODS:
    amounts = sorted([(player.name, stall_counts[card_type]) for each player],
                     key=descending)
    king_of[card_type]  = amounts[0][0]  # most collected
    queen_of[card_type] = amounts[1][0]  # second most
```

#### Deck Recycling

When the draw pile is empty, `Deck.draw()` copies the entire discard pile, clears it, reshuffles, and uses it as the new draw pile. This ensures the game never stalls due to card shortage.

#### Bag Honesty Check

`MerchantBag.is_honest()` applies two conditions together:
1. The number of cards in the bag equals the declared quantity.
2. Every individual card's type matches the declared type.

If either fails, the Sheriff collects the penalty on all non-matching cards.

#### Phase State Machine

`GameEngine` advances through phases using a `GamePhase` enum:

```
SETUP → MARKET → PACK_BAG → INSPECTION → ROUND_END → (next round) MARKET → ...
                                                    → (final round) GAME_END
```

Each `advance_*_phase()` method increments the merchant index; when all merchants are processed, it triggers the next phase.

---

## 4. Data Flow

```
Player Input (Pygame mouse / keyboard event)
        │
        ▼
  Screen Handler  (gui/screens/*.py)
  • Translates UI actions into GameEngine method calls
  • e.g. "Start Game" button → app.start_game(configs)
  • e.g. "Confirm Bag"  button → engine.pack_player_bag(player, cards, type, qty)
  • e.g. "Inspect"      button → engine.sheriff_inspect(merchant)
        │
        ▼
  GameEngine  (game/game_logic.py)
  • Validates the action against current phase and rules
  • Mutates Player / MerchantBag / Deck state
  • Advances the phase state machine
  • Returns a result (e.g. RoundEvent) for the GUI to display
        │
        ├──► Player objects  (gold, hand, stall, bag)
        │
        ├──► Deck object     (draw pile, discard pile, market)
        │
        ▼  (on GAME_END)
  calculate_final_scores()
        │
        ▼
  database.save_game()  (storage/database.py)
  • Writes game record to  game_records.db  (SQLite)
  • Upserts per-player cumulative stats
        │
        ▼
  GUI Re-render  (App loop at 60 FPS)
  • game_screen.py reads GameEngine state each frame and redraws the table
  • history_screen.py reads from the database via get_recent_games()
```

---

## 5. File Structure

```
Sheriff_of_nottingham/
│
├── main.py                     # Entry point — creates App and starts the game loop
│
├── game/                       # Pure game logic (no GUI or DB dependency)
│   ├── cards.py                # CardType enum, CardInfo dataclass, Card class, CARD_DATA dict
│   ├── deck.py                 # Deck — draw pile, discard pile, market, auto-reshuffle
│   ├── player.py               # Player and MerchantBag classes
│   ├── player_ai.py            # PlayerAI — decision logic (not exposed in current UI)
│   └── game_logic.py           # GameEngine — phase management, rule enforcement, scoring
│
├── gui/                        # Pygame presentation layer
│   ├── app.py                  # App — window, 60 FPS loop, screen transitions, dialogs
│   ├── theme.py                # Colours, sizes, fonts, draw_card(), _draw_item_icon()
│   ├── widgets.py              # Reusable widgets: Button, TextInput, RadioGroup
│   └── screens/
│       ├── main_menu.py        # Title / main menu screen
│       ├── setup_screen.py     # Player count and name entry (all players human)
│       ├── game_screen.py      # Main gameplay — table, hand, bag packing, inspection
│       └── history_screen.py   # Past game records and player statistics
│
├── storage/
│   └── database.py             # SQLite helpers — init, save game, read history
│
├── game_records.db             # SQLite database (auto-created on first run)
├── requirements.txt            # Dependency notes
└── README.md                   # This file
```

### Purpose of Each Module

| File | Purpose |
|---|---|
| `main.py` | Adds the project root to `sys.path` so imports resolve regardless of working directory, then launches `App` |
| `game/cards.py` | Single source of truth for all card data — values, penalties, counts, and bonus rules |
| `game/deck.py` | Self-contained deck that auto-recycles when empty; also exposes the 5-card face-up market |
| `game/player.py` | Stateful player object; separates per-round bag state (`MerchantBag`) from persistent stall/gold state |
| `game/player_ai.py` | PlayerAI heuristics for market, bag packing, and sheriff decisions — present in codebase but not wired to the setup screen |
| `game/game_logic.py` | The only module that mutates game state; all other code reads from or passes through it |
| `gui/app.py` | Owns the Pygame window and clock; routes events to the active screen and handles overlapping dialogs |
| `gui/theme.py` | Centralises every visual constant; `draw_card()` draws gradient card bodies with a pixel-art icon per item |
| `gui/widgets.py` | Generic, reusable UI components that all screens share |
| `gui/screens/` | One file per screen; each owns its own event handling and rendering logic |
| `storage/database.py` | Thin wrapper around `sqlite3`; the rest of the codebase never imports `sqlite3` directly |

---

## 6. How to Run the Code from Scratch

### Prerequisites

- **Python 3.9 or higher** — download from [python.org](https://www.python.org/downloads/)
- **pip** — bundled with Python 3.9+

### Step 1 — Download the Project

```bash
# If using git:
git clone <repository-url>
cd Sheriff_of_nottingham

# Or unzip the downloaded archive and open a terminal in that folder.
```

### Step 2 — Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt.

### Step 3 — Install Requirements

The only third-party dependency is **pygame**.

```bash
pip install pygame
```

> **Linux users only:** if fonts appear broken, also install the system font package:
> ```bash
> sudo apt install fonts-liberation
> ```

### Step 4 — Run the Game

```bash
python main.py
```

The game window (1200 × 760, resizable) opens and displays the main menu.

### Step 5 — Start a Game

1. Click **New Game**.
2. Select the number of players (2–5) using the radio buttons.
3. Enter a unique name for each player.
4. Click **Start Game**.
5. All players share the same device — pass the keyboard and mouse between turns.
6. View past games any time from the **History** button on the main menu.

### Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'pygame'` | Run `pip install pygame` inside the active virtual environment |
| Fonts appear as boxes or squares on Linux | Run `sudo apt install fonts-liberation` and restart |
| Window appears too small | Drag the window edges to resize — the layout scales automatically |
| `game_records.db` error on first run | The file is created automatically; make sure the project folder is not read-only |
