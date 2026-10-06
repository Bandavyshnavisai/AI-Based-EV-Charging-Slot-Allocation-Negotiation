"""
Database Persistence Layer for AI EV Charging Multi-Agent System.

This module provides SQLite storage for agents, stations, charging requests,
negotiation dialogues, confirmed bookings, payment records, and event logs.
"""

import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class DatabaseManager:
    """Manages SQLite database connections and table schemas for the simulation."""

    def __init__(self, db_path: str = "data/ev_charging.db"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        else:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns the managed SQLite connection."""
        return self._conn

    def initialize_schema(self) -> None:
        """Initializes all necessary relational tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Stations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stations (
                    station_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    location TEXT,
                    num_chargers INTEGER NOT NULL,
                    base_price_per_kwh REAL NOT NULL
                )
            """)

            # Chargers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chargers (
                    charger_id TEXT PRIMARY KEY,
                    station_id TEXT NOT NULL,
                    power_kw REAL NOT NULL,
                    status TEXT DEFAULT 'AVAILABLE',
                    FOREIGN KEY(station_id) REFERENCES stations(station_id)
                )
            """)

            # EV Agents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evs (
                    ev_id TEXT PRIMARY KEY,
                    battery_capacity_kwh REAL NOT NULL,
                    current_battery REAL NOT NULL,
                    target_battery REAL NOT NULL,
                    priority TEXT NOT NULL,
                    max_waiting_time INTEGER NOT NULL
                )
            """)

            # Charging Requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS charging_requests (
                    request_id TEXT PRIMARY KEY,
                    ev_id TEXT NOT NULL,
                    preferred_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(ev_id) REFERENCES evs(ev_id)
                )
            """)

            # Negotiation History table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS negotiation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL,
                    round_num INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    proposed_station_id TEXT,
                    proposed_charger_id TEXT,
                    proposed_slot_start TEXT,
                    proposed_slot_end TEXT,
                    action TEXT NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Bookings & Reservations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    booking_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    ev_id TEXT NOT NULL,
                    station_id TEXT NOT NULL,
                    charger_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    total_cost REAL NOT NULL,
                    payment_status TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(request_id) REFERENCES charging_requests(request_id),
                    FOREIGN KEY(ev_id) REFERENCES evs(ev_id),
                    FOREIGN KEY(station_id) REFERENCES stations(station_id),
                    FOREIGN KEY(charger_id) REFERENCES chargers(charger_id)
                )
            """)

            # Multi-Agent Communication & Event Log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_step INTEGER,
                    timestamp TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)
            conn.commit()

    def reset_database(self) -> None:
        """Clears all table contents for fresh simulation runs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            tables = ["event_logs", "bookings", "negotiation_history", "charging_requests", "chargers", "evs", "stations"]
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            conn.commit()

    def insert_station(self, station_id: str, name: str, location: str, num_chargers: int, base_price_per_kwh: float) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO stations (station_id, name, location, num_chargers, base_price_per_kwh)
                VALUES (?, ?, ?, ?, ?)
            """, (station_id, name, location, num_chargers, base_price_per_kwh))
            conn.commit()

    def insert_charger(self, charger_id: str, station_id: str, power_kw: float, status: str = "AVAILABLE") -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO chargers (charger_id, station_id, power_kw, status)
                VALUES (?, ?, ?, ?)
            """, (charger_id, station_id, power_kw, status))
            conn.commit()

    def insert_ev(self, ev_id: str, battery_capacity_kwh: float, current_battery: float, target_battery: float, priority: str, max_waiting_time: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO evs (ev_id, battery_capacity_kwh, current_battery, target_battery, priority, max_waiting_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ev_id, battery_capacity_kwh, current_battery, target_battery, priority, max_waiting_time))
            conn.commit()

    def insert_request(self, request_id: str, ev_id: str, preferred_time: str, duration_minutes: int, priority: str, status: str = "PENDING") -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO charging_requests (request_id, ev_id, preferred_time, duration_minutes, priority, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (request_id, ev_id, preferred_time, duration_minutes, priority, status))
            conn.commit()

    def update_request_status(self, request_id: str, status: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE charging_requests SET status = ? WHERE request_id = ?
            """, (status, request_id))
            conn.commit()

    def log_negotiation(self, request_id: str, round_num: int, sender: str, receiver: str,
                        proposed_station_id: Optional[str], proposed_charger_id: Optional[str],
                        proposed_slot_start: Optional[str], proposed_slot_end: Optional[str],
                        action: str, reason: str = "") -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO negotiation_history (request_id, round_num, sender, receiver,
                    proposed_station_id, proposed_charger_id, proposed_slot_start, proposed_slot_end, action, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (request_id, round_num, sender, receiver,
                  proposed_station_id, proposed_charger_id, proposed_slot_start, proposed_slot_end, action, reason))
            conn.commit()

    def create_booking(self, booking_id: str, request_id: str, ev_id: str, station_id: str,
                       charger_id: str, start_time: str, end_time: str, duration_minutes: int,
                       total_cost: float, payment_status: str, status: str = "CONFIRMED") -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bookings (booking_id, request_id, ev_id, station_id, charger_id,
                    start_time, end_time, duration_minutes, total_cost, payment_status, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (booking_id, request_id, ev_id, station_id, charger_id, start_time, end_time, duration_minutes, total_cost, payment_status, status))
            conn.commit()

    def update_booking_status(self, booking_id: str, status: str, payment_status: Optional[str] = None) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if payment_status:
                cursor.execute("UPDATE bookings SET status = ?, payment_status = ? WHERE booking_id = ?", (status, payment_status, booking_id))
            else:
                cursor.execute("UPDATE bookings SET status = ? WHERE booking_id = ?", (status, booking_id))
            conn.commit()

    def log_event(self, simulation_step: int, timestamp: str, sender: str, receiver: str, event_type: str, message: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO event_logs (simulation_step, timestamp, sender, receiver, event_type, message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (simulation_step, timestamp, sender, receiver, event_type, message))
            conn.commit()

    def get_all_bookings(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bookings ORDER BY start_time ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_event_logs(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_logs ORDER BY log_id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_negotiation_history(self, request_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if request_id:
                cursor.execute("SELECT * FROM negotiation_history WHERE request_id = ? ORDER BY round_num ASC", (request_id,))
            else:
                cursor.execute("SELECT * FROM negotiation_history ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_requests(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM charging_requests ORDER BY created_at ASC")
            return [dict(row) for row in cursor.fetchall()]
