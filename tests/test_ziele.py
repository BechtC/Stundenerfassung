"""
Tests für Jahresziele pro Projekt (Issue #17).
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
# Zyklus 1: ziele-Tabelle wird angelegt
# ============================================================

def test_ziele_tabelle_vorhanden(mem_db):
    """init_db() legt die Tabelle ziele an."""
    import sqlite3
    conn = sqlite3.connect(str(mem_db))
    tabellen = [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "ziele" in tabellen


# ============================================================
# Zyklus 2: ziel_setzen() + ziele_laden()
# ============================================================

def test_ziel_setzen_und_laden(mem_db):
    """Gesetztes Jahresziel wird über ziele_laden(jahr) zurückgegeben."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("AI Learning", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.ziel_setzen(pid, 2026, 300.0)
        ziele = db.ziele_laden(2026)
    assert ziele == [{"projekt_id": pid, "stunden_ziel": 300.0}]


# ============================================================
# Zyklus 3: Upsert — erneutes Setzen überschreibt
# ============================================================

def test_ziel_setzen_ueberschreibt(mem_db):
    """Erneutes ziel_setzen für dasselbe Projekt+Jahr ersetzt den Wert."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("AI Learning", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.ziel_setzen(pid, 2026, 300.0)
        db.ziel_setzen(pid, 2026, 400.0)
        ziele = db.ziele_laden(2026)
    assert ziele == [{"projekt_id": pid, "stunden_ziel": 400.0}]


# ============================================================
# Zyklus 4: Wert <= 0 löscht das Ziel
# ============================================================

def test_ziel_setzen_null_loescht(mem_db):
    """ziel_setzen mit Wert <= 0 entfernt ein vorhandenes Ziel."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("AI Learning", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.ziel_setzen(pid, 2026, 300.0)
        db.ziel_setzen(pid, 2026, 0)
        ziele = db.ziele_laden(2026)
    assert ziele == []


# ============================================================
# Zyklus 5: Jahres-Isolation
# ============================================================

def test_ziele_pro_jahr_getrennt(mem_db):
    """Ziele verschiedener Jahre beeinflussen sich nicht."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("AI Learning", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.ziel_setzen(pid, 2025, 200.0)
        db.ziel_setzen(pid, 2026, 300.0)
        db.ziel_setzen(pid, 2026, 0)  # löscht nur 2026
        assert db.ziele_laden(2025) == [{"projekt_id": pid, "stunden_ziel": 200.0}]
        assert db.ziele_laden(2026) == []


# ============================================================
# Zyklus 6: Kaskade — Projekt löschen entfernt Ziele
# ============================================================

def test_ziele_kaskade_bei_projekt_loeschen(mem_db):
    """Löschen eines Projekts entfernt dessen Ziele (ON DELETE CASCADE)."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("Wegwerf", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.ziel_setzen(pid, 2026, 100.0)
        db.projekt_loeschen(pid)
        assert db.ziele_laden(2026) == []
