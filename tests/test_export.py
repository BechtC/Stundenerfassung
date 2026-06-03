"""
Tests für zeiteintraege_monat_laden() (Issue #9).
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


def test_monat_laden_gibt_eintraege_zurueck(mem_db):
    """zeiteintraege_monat_laden() gibt Einträge des richtigen Monats zurück."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("TestProjekt", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.zeiteintrag_erstellen("2026-06-10", pid, 3.0)
        db.zeiteintrag_erstellen("2026-06-25", pid, 2.0)
        db.zeiteintrag_erstellen("2026-07-01", pid, 1.0)  # anderer Monat

        eintraege = db.zeiteintraege_monat_laden(2026, 6)
    assert len(eintraege) == 2
    assert all(e["datum"].startswith("2026-06") for e in eintraege)


def test_monat_laden_anderer_monat_leer(mem_db):
    """zeiteintraege_monat_laden() gibt leere Liste für Monate ohne Einträge."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("TestProjekt", 80.0)
        pid = db.projekte_laden()[0]["id"]
        db.zeiteintrag_erstellen("2026-06-10", pid, 3.0)

        eintraege = db.zeiteintraege_monat_laden(2026, 5)
    assert eintraege == []


def test_monat_laden_mit_projekt_filter(mem_db):
    """zeiteintraege_monat_laden() filtert korrekt nach projekt_id."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("Projekt A", 80.0)
        db.projekt_erstellen("Projekt B", 90.0)
        projekte = db.projekte_laden()
        pid_a = projekte[0]["id"]
        pid_b = projekte[1]["id"]
        db.zeiteintrag_erstellen("2026-06-10", pid_a, 3.0)
        db.zeiteintrag_erstellen("2026-06-15", pid_b, 2.0)

        eintraege = db.zeiteintraege_monat_laden(2026, 6, projekt_id=pid_a)
    assert len(eintraege) == 1
    assert eintraege[0]["projekt_id"] == pid_a
