"""SQLite database operations for Sheriff of Nottingham."""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "game_records.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db() -> None:
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                played_at   TEXT NOT NULL,
                num_players INTEGER NOT NULL,
                num_rounds  INTEGER NOT NULL,
                winner_name TEXT NOT NULL,
                winner_score INTEGER NOT NULL,
                duration_secs INTEGER,
                scores_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name     TEXT NOT NULL,
                games_played    INTEGER DEFAULT 0,
                games_won       INTEGER DEFAULT 0,
                total_score     INTEGER DEFAULT 0,
                total_smuggles  INTEGER DEFAULT 0,
                total_caught    INTEGER DEFAULT 0,
                UNIQUE(player_name)
            )
        """)
        conn.commit()


def save_game(scores: List[Dict], num_rounds: int, duration_secs: int = 0) -> int:
    """Persist a completed game and update player stats. Returns new game id."""
    played_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    winner = scores[0]

    # stall_counts uses CardType enum keys — convert to strings for JSON
    serialisable = []
    for entry in scores:
        e = dict(entry)
        if "stall_counts" in e:
            e["stall_counts"] = {str(k): v for k, v in e["stall_counts"].items()}
        serialisable.append(e)
    scores_json = json.dumps(serialisable)

    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO games
               (played_at, num_players, num_rounds, winner_name, winner_score,
                duration_secs, scores_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (played_at, len(scores), num_rounds, winner["name"],
             winner["total"], duration_secs, scores_json)
        )
        game_id = cur.lastrowid

        # Update player_stats for non-AI players
        for rank, entry in enumerate(scores):
            if entry.get("is_ai"):
                continue
            name = entry["name"]
            won = 1 if rank == 0 else 0
            conn.execute(
                """INSERT INTO player_stats (player_name, games_played, games_won,
                   total_score, total_smuggles, total_caught)
                   VALUES (?, 1, ?, ?, 0, 0)
                   ON CONFLICT(player_name) DO UPDATE SET
                       games_played = games_played + 1,
                       games_won    = games_won + ?,
                       total_score  = total_score + ?""",
                (name, won, entry["total"], won, entry["total"])
            )
        conn.commit()
    return game_id


def get_recent_games(limit: int = 20) -> List[Dict]:
    """Retrieve recent game records."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, played_at, num_players, num_rounds,
                      winner_name, winner_score, duration_secs, scores_json
               FROM games
               ORDER BY id DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["scores"] = json.loads(d.pop("scores_json"))
        results.append(d)
    return results


def get_player_stats(player_name: Optional[str] = None) -> List[Dict]:
    """Retrieve player statistics, optionally filtered by name."""
    with get_connection() as conn:
        if player_name:
            rows = conn.execute(
                "SELECT * FROM player_stats WHERE player_name = ?", (player_name,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM player_stats ORDER BY games_won DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_all_stats_summary() -> Dict:
    """High-level stats for the history screen."""
    with get_connection() as conn:
        total_games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        top_player = conn.execute(
            "SELECT player_name, games_won FROM player_stats ORDER BY games_won DESC LIMIT 1"
        ).fetchone()
    return {
        "total_games": total_games,
        "top_player": dict(top_player) if top_player else None,
    }