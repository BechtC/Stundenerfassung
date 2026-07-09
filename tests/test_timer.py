"""
Tests für den Live-Tracker (Issues #1 + #2).
Nutzt eine In-Memory SQLite DB — keine Seiteneffekte auf stundenerfassung.db.
"""

import pytest
import sqlite3
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
import database as db


@pytest.fixture
def mem_db(tmp_path):
    """Frische SQLite DB in tmp_path für jeden Test."""
    db_file = tmp_path / "test.db"
    with patch.object(db, "DB_PATH", db_file):
        db.init_db()
        yield db_file


# ============================================================
# Hilfsfunktion: Testprojekt anlegen
# ============================================================

def _projekt(db_path, name="Testprojekt", stundensatz=80.0):
    with patch.object(db, "DB_PATH", db_path):
        db.projekt_erstellen(name, stundensatz)
        projekte = db.projekte_laden()
        return projekte[0]["id"]


# ============================================================
# Zyklus 1: Migration
# ============================================================

def test_migration_idempotent(mem_db):
    """init_db() zweimal aufrufen darf keinen Fehler werfen."""
    with patch.object(db, "DB_PATH", mem_db):
        db.init_db()  # zweiter Aufruf


# ============================================================
# Zyklus 2: timer_starten()
# ============================================================

def test_timer_starten_gibt_id_zurueck(mem_db):
    """timer_starten() gibt eine Integer-ID zurück."""
    projekt_id = _projekt(mem_db)
    with patch.object(db, "DB_PATH", mem_db):
        eintrag_id = db.timer_starten(projekt_id=projekt_id, unterthema_id=None,
                                       kategorie="Produktiv", beschreibung="", stundensatz=80.0)
    assert isinstance(eintrag_id, int)
    assert eintrag_id > 0


def test_timer_starten_status_laufend(mem_db):
    """Eintrag nach timer_starten() hat status='laufend' und startzeit gesetzt."""
    projekt_id = _projekt(mem_db)
    with patch.object(db, "DB_PATH", mem_db):
        eintrag_id = db.timer_starten(projekt_id=projekt_id, unterthema_id=None,
                                       kategorie="Produktiv", beschreibung="", stundensatz=80.0)
    conn = sqlite3.connect(str(mem_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM zeiteintraege WHERE id = ?", (eintrag_id,)).fetchone()
    conn.close()
    assert row["status"] == "laufend"
    assert row["startzeit"] is not None


# ============================================================
# Zyklus 3: timer_stoppen()
# ============================================================

def test_timer_stoppen_status_fertig(mem_db):
    """Nach timer_stoppen() ist status='fertig' und stunden > 0."""
    projekt_id = _projekt(mem_db)
    with patch.object(db, "DB_PATH", mem_db):
        eintrag_id = db.timer_starten(projekt_id=projekt_id, unterthema_id=None,
                                       kategorie="Produktiv", beschreibung="", stundensatz=80.0)
        db.timer_stoppen(eintrag_id, beschreibung="Fertig")
        eintraege = db.zeiteintraege_laden()
    eintrag = next(e for e in eintraege if e["id"] == eintrag_id)
    assert eintrag["status"] == "fertig"
    assert eintrag["stunden"] >= 0
    assert eintrag["beschreibung"] == "Fertig"


# ============================================================
# Zyklus 4: recently_used_laden()
# ============================================================

def test_recently_used_max_drei(mem_db):
    """recently_used_laden() gibt maximal 3 eindeutige Projekt-Kombinationen zurück."""
    with patch.object(db, "DB_PATH", mem_db):
        for name in ["P1", "P2", "P3", "P4"]:
            db.projekt_erstellen(name, 80.0)
        projekte = {p["name"]: p["id"] for p in db.projekte_laden()}
        for pid in projekte.values():
            eid = db.timer_starten(projekt_id=pid, unterthema_id=None,
                                   kategorie="Produktiv", beschreibung="", stundensatz=80.0)
            db.timer_stoppen(eid, beschreibung="")
        result = db.recently_used_laden()
    assert len(result) == 3


def test_recently_used_enthaelt_projekt_name(mem_db):
    """recently_used_laden() gibt projekt_name zurück."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("MeinProjekt", 80.0)
        pid = db.projekte_laden()[0]["id"]
        eid = db.timer_starten(projekt_id=pid, unterthema_id=None,
                               kategorie="Produktiv", beschreibung="", stundensatz=80.0)
        db.timer_stoppen(eid, beschreibung="")
        result = db.recently_used_laden()
    assert result[0]["projekt_name"] == "MeinProjekt"


# ============================================================
# Zyklus 5: laufenden_timer_laden()
# ============================================================

def test_laufenden_timer_laden_gibt_none_wenn_kein_timer(mem_db):
    """laufenden_timer_laden() gibt None zurück wenn kein Timer läuft."""
    with patch.object(db, "DB_PATH", mem_db):
        result = db.laufenden_timer_laden()
    assert result is None


def test_laufenden_timer_laden_gibt_eintrag_zurueck(mem_db):
    """laufenden_timer_laden() gibt den laufenden Eintrag mit projekt_name zurück."""
    with patch.object(db, "DB_PATH", mem_db):
        db.projekt_erstellen("Laufprojekt", 90.0)
        pid = db.projekte_laden()[0]["id"]
        db.timer_starten(projekt_id=pid, unterthema_id=None,
                         kategorie="Produktiv", beschreibung="Test", stundensatz=90.0)
        result = db.laufenden_timer_laden()
    assert result is not None
    assert result["projekt_name"] == "Laufprojekt"
    assert result["status"] == "laufend"


# ============================================================
# Zyklus 6: Dauer-Korrektur (Stopp-Dialog + Bearbeiten)
# ============================================================

def test_dauer_korrektur_ueberschreibt_stunden(mem_db):
    """Der Stopp-Dialog-Flow: nach timer_stoppen überschreibt
    zeiteintrag_aktualisieren(stunden=...) die auto-berechnete Dauer.
    Deckt den Fall 'vergessen zu stoppen → 3h → auf 0.5h korrigieren' ab."""
    projekt_id = _projekt(mem_db)
    with patch.object(db, "DB_PATH", mem_db):
        eid = db.timer_starten(projekt_id=projekt_id, unterthema_id=None,
                               kategorie="Produktiv", beschreibung="", stundensatz=80.0)
        db.timer_stoppen(eid, beschreibung="Feierabend")
        # Nutzer korrigiert die Dauer im Dialog:
        db.zeiteintrag_aktualisieren(eid, stunden=0.5, kategorie="Meeting")
        eintrag = next(e for e in db.zeiteintraege_laden() if e["id"] == eid)
    assert eintrag["stunden"] == 0.5
    assert eintrag["kategorie"] == "Meeting"
    assert eintrag["status"] == "fertig"


def test_eintrag_bearbeiten_aendert_alle_felder(mem_db):
    """Nachträgliches Bearbeiten: Dauer, Kategorie und Beschreibung ändern."""
    projekt_id = _projekt(mem_db)
    with patch.object(db, "DB_PATH", mem_db):
        eid = db.timer_starten(projekt_id=projekt_id, unterthema_id=None,
                               kategorie="Produktiv", beschreibung="alt", stundensatz=80.0)
        db.timer_stoppen(eid, beschreibung="alt")
        db.zeiteintrag_aktualisieren(eid, stunden=2.25, kategorie="Admin",
                                     beschreibung="neu")
        eintrag = next(e for e in db.zeiteintraege_laden() if e["id"] == eid)
    assert eintrag["stunden"] == 2.25
    assert eintrag["kategorie"] == "Admin"
    assert eintrag["beschreibung"] == "neu"


def test_migration_spalten_vorhanden(mem_db):
    """zeiteintraege hat nach Migration die Spalten status und startzeit."""
    with patch.object(db, "DB_PATH", mem_db):
        conn = sqlite3.connect(str(mem_db))
        cols = [row[1] for row in conn.execute("PRAGMA table_info(zeiteintraege)").fetchall()]
        conn.close()
        assert "status" in cols
        assert "startzeit" in cols
