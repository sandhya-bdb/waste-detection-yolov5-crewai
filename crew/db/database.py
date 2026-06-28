"""
SQLite Database for WasteGuard Society AI
Stores all waste complaint tickets
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "waste_tickets.db")


def init_db():
    """Initialize the SQLite database and create tables if not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            waste_type  TEXT,
            category    TEXT,
            urgency     TEXT,
            location    TEXT,
            status      TEXT    DEFAULT 'Open',
            assigned_to TEXT    DEFAULT 'Cleaning Staff',
            reported_by TEXT,
            disposal_tip TEXT,
            resolved_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    # print("✅ Database initialized.")


def create_ticket(waste_type: str, category: str, urgency: str,
                  location: str, reported_by: str, disposal_tip: str = "") -> int:
    """Create a new complaint ticket. Returns the ticket ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets 
            (timestamp, waste_type, category, urgency, location, status, assigned_to, reported_by, disposal_tip)
        VALUES (?, ?, ?, ?, ?, 'Open', 'Cleaning Staff', ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        waste_type, category, urgency, location, reported_by, disposal_tip
    ))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id


def update_ticket_status(ticket_id: int, status: str):
    """Update a ticket's status. If 'Resolved', records resolved timestamp."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "Resolved" else None
    cursor.execute(
        "UPDATE tickets SET status=?, resolved_at=? WHERE id=?",
        (status, resolved_at, ticket_id)
    )
    conn.commit()
    conn.close()


def get_all_tickets() -> list:
    """Return all tickets as a list of dicts, newest first."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY timestamp DESC")
    tickets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tickets


def get_ticket(ticket_id: int) -> dict:
    """Return a single ticket by ID."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}


def get_stats(time_range: str = "all") -> dict:
    """Return aggregate stats for the RWA dashboard. time_range can be '24h', '7d', or 'all'."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    where_clause = ""
    if time_range == "24h":
        where_clause = "WHERE timestamp >= datetime('now', '-1 day')"
    elif time_range == "7d":
        where_clause = "WHERE timestamp >= datetime('now', '-7 days')"
        
    and_clause = ""
    if where_clause:
        and_clause = f"AND {where_clause[6:]}"

    cursor.execute(f"SELECT COUNT(*) FROM tickets {where_clause}")
    total = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM tickets WHERE status='Open' {and_clause}")
    open_count = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM tickets WHERE status='Resolved' {and_clause}")
    resolved_count = cursor.fetchone()[0]

    cursor.execute(f"SELECT category, COUNT(*) as cnt FROM tickets {where_clause} GROUP BY category ORDER BY cnt DESC")
    by_category = [{"category": r[0], "count": r[1]} for r in cursor.fetchall()]
    conn.close()
    return {
        "total": total,
        "open": open_count,
        "resolved": resolved_count,
        "by_category": by_category
    }
