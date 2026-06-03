"""
Tests für Farbkodierung nach Projekt (Issue #8).
Nutzt In-Memory SQLite — keine Seiteneffekte auf stundenerfassung.db.
"""

import pytest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import database as db


@pytest.fixture
def mem_db(tmp_path):
    db_file = tmp_path / "test.db"
    with patch.object(db, "DB_PATH", db_file):
        db.init_db()
        yield db_file


# ============================================================
# Zyklus 1: Migration
# ============================================================

def test_migration_farbe_spalte_vorhanden(mem_db):
    """projekte-Tabelle hat nach Migration die Spalte farbe."""
    import sqlite3
    conn = sqlite3.connect(str(mem_db))
    cols = [row[1] for row in conn.execute("PRAGMA table_info(projekte)").fetchall()]
    conn.close()
    assert "farbe" in cols


# ============================================================
# Zyklus 2: projekt_erstellen() weist Farbe zu
# ============================================================

def test_projekt_erstellen_hat_farbe(mem_db):
    """Neu erstelltes Projekt hat eine Farbe aus PROJEKT_FARBEN."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("TestProjekt", 80.0)
        projekte = db.projekte_laden()
    assert projekte[0]["farbe"] in db.PROJEKT_FARBEN


# ============================================================
# Zyklus 3: projekt_farbe_aktualisieren()
# ============================================================

def test_projekt_farbe_aktualisieren(mem_db):
    """projekt_farbe_aktualisieren() speichert neuen Hex-Wert."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("FarbProjekt", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.projekt_farbe_aktualisieren(pid, "#FF0000")
        projekte = db.projekte_laden()
    assert projekte[0]["farbe"] == "#FF0000"


# ============================================================
# Zyklus 4: Fallback für Projekte ohne Farbe
# ============================================================

def test_projekt_ohne_farbe_fallback(mem_db):
    """projekte_laden() gibt #AAAAAA für Projekte ohne Farbe zurück."""
    import sqlite3
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("OhneFarbe", 80.0)
        pid = db.projekte_laden()[0]["id"]
        # Farbe manuell auf NULL setzen
        conn = sqlite3.connect(str(mem_db))
        conn.execute("UPDATE projekte SET farbe = NULL WHERE id = ?", (pid,))
        conn.commit()
        conn.close()
        projekte = db.projekte_laden()
    assert projekte[0]["farbe"] == "#AAAAAA"
