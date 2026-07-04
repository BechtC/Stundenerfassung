"""
Tests für das automatische DB-Backup (Issue #14).
Arbeitet komplett in tmp-Verzeichnissen — keine echte DB, keine Seiteneffekte.
"""

import pytest
from datetime import date, timedelta
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
# Zyklus 1: Backup wird angelegt, idempotent pro Tag
# ============================================================

def test_backup_wird_angelegt(mem_db, tmp_path):
    """Erster Aufruf des Tages legt backups/stundenerfassung_{heute}.db an."""
    ziel = tmp_path / "backups"
    with patch.object(db, "DB_PATH", mem_db):
        db.backup_erstellen(ziel)
    erwartet = ziel / f"stundenerfassung_{date.today().isoformat()}.db"
    assert erwartet.exists()
    assert erwartet.stat().st_size > 0


def test_backup_idempotent_pro_tag(mem_db, tmp_path):
    """Zweiter Aufruf am selben Tag überschreibt das Backup nicht."""
    ziel = tmp_path / "backups"
    with patch.object(db, "DB_PATH", mem_db):
        db.backup_erstellen(ziel)
        backup = ziel / f"stundenerfassung_{date.today().isoformat()}.db"
        backup.write_bytes(b"marker")          # Backup manipulieren
        db.backup_erstellen(ziel)              # darf nicht neu kopieren
    assert backup.read_bytes() == b"marker"


# ============================================================
# Zyklus 2: Retention — Backups älter als 30 Tage werden entfernt
# ============================================================

def test_backup_retention(mem_db, tmp_path):
    """Backups älter als retention_tage verschwinden, jüngere und fremde Dateien bleiben."""
    ziel = tmp_path / "backups"
    ziel.mkdir()
    alt = ziel / f"stundenerfassung_{(date.today() - timedelta(days=31)).isoformat()}.db"
    juenger = ziel / f"stundenerfassung_{(date.today() - timedelta(days=29)).isoformat()}.db"
    fremd = ziel / "stundenerfassung_notizen.db"
    for f in (alt, juenger, fremd):
        f.write_bytes(b"x")

    with patch.object(db, "DB_PATH", mem_db):
        db.backup_erstellen(ziel, retention_tage=30)

    assert not alt.exists()
    assert juenger.exists()
    assert fremd.exists()
