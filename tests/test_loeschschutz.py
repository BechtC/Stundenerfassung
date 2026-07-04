"""
Tests für den Projekt-Löschschutz (Issue #16).
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


def _projekt_mit_eintrag(name="Testprojekt"):
    db.projekt_erstellen(name, 80.0)
    pid = next(p["id"] for p in db.projekte_laden() if p["name"] == name)
    db.zeiteintrag_erstellen(datum="2026-07-01", projekt_id=pid, stunden=2.0)
    return pid


# ============================================================
# Zyklus 1: Rechnungen blockieren das Löschen
# ============================================================

def test_projekt_mit_rechnung_nicht_loeschbar(mem_db):
    """Projekt mit Rechnungen wirft ValueError; Projekt und Einträge bleiben."""
    with patch.object(db, "DB_PATH", mem_db):
        pid = _projekt_mit_eintrag()
        db.rechnung_erstellen(
            projekt_id=pid, kunde="Kunde", kunde_adresse="",
            datum="2026-07-01", leistungszeitraum_von="2026-07-01",
            leistungszeitraum_bis="2026-07-01",
            positionen_json="[]", gesamtbetrag=160.0,
        )
        with pytest.raises(ValueError):
            db.projekt_loeschen(pid)
        # Nichts wurde angefasst
        assert any(p["id"] == pid for p in db.projekte_laden())
        assert len(db.zeiteintraege_laden(projekt_id=pid)) == 1


# ============================================================
# Zyklus 2: Kaskade ohne Rechnungen — keine Waisen
# ============================================================

def test_projekt_loeschen_kaskadiert_zeiteintraege(mem_db):
    """Ohne Rechnungen verschwinden Projekt, Zeiteinträge und Unterthemen."""
    with patch.object(db, "DB_PATH", mem_db):
        pid = _projekt_mit_eintrag()
        db.unterthema_erstellen(pid, "Backend")
        db.projekt_loeschen(pid)
        assert not any(p["id"] == pid for p in db.projekte_laden(nur_aktive=False))
        assert db.zeiteintraege_laden(projekt_id=pid) == []
        assert db.unterthemen_laden(pid, nur_aktive=False) == []


# ============================================================
# Zyklus 3: projekt_statistik für den Lösch-Dialog
# ============================================================

def test_projekt_statistik_zaehlt(mem_db):
    """Liefert Anzahl Zeiteinträge, Unterthemen und Rechnungen des Projekts."""
    with patch.object(db, "DB_PATH", mem_db):
        pid = _projekt_mit_eintrag()
        db.zeiteintrag_erstellen(datum="2026-07-02", projekt_id=pid, stunden=1.0)
        db.unterthema_erstellen(pid, "Backend")
        stats = db.projekt_statistik(pid)
    assert stats == {"zeiteintraege": 2, "unterthemen": 1, "rechnungen": 0}
