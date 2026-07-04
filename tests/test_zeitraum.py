"""
Tests für die Zeitraum-Preset-Logik (Issue #18).
Reine Datumsfunktionen — kein Streamlit, keine DB.
"""

from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from zeitraum import preset_zeitraum


# ============================================================
# Zyklus 1: Dieser Monat
# ============================================================

def test_preset_dieser_monat():
    """'Dieser Monat' liefert Monatserster bis heute."""
    von, bis = preset_zeitraum("Dieser Monat", heute=date(2026, 7, 4))
    assert von == date(2026, 7, 1)
    assert bis == date(2026, 7, 4)


# ============================================================
# Zyklus 2: Diese Woche (Montag bis heute, über Monatsgrenze)
# ============================================================

def test_preset_diese_woche():
    """'Diese Woche' beginnt am Montag der laufenden Woche."""
    # 2026-07-04 ist ein Samstag; Montag war der 29.06.
    von, bis = preset_zeitraum("Diese Woche", heute=date(2026, 7, 4))
    assert von == date(2026, 6, 29)
    assert bis == date(2026, 7, 4)


def test_preset_diese_woche_montag():
    """Am Montag selbst ist von == bis == heute."""
    von, bis = preset_zeitraum("Diese Woche", heute=date(2026, 6, 29))
    assert von == date(2026, 6, 29)
    assert bis == date(2026, 6, 29)


# ============================================================
# Zyklus 3: Quartal, Jahr, Alles
# ============================================================

def test_preset_dieses_quartal():
    """'Dieses Quartal' beginnt am Quartalsersten (Juli = Q3)."""
    von, bis = preset_zeitraum("Dieses Quartal", heute=date(2026, 7, 4))
    assert von == date(2026, 7, 1)
    assert bis == date(2026, 7, 4)
    # Randfall: Mitte eines Quartals
    von, _ = preset_zeitraum("Dieses Quartal", heute=date(2026, 5, 20))
    assert von == date(2026, 4, 1)


def test_preset_dieses_jahr():
    """'Dieses Jahr' beginnt am 1. Januar."""
    von, bis = preset_zeitraum("Dieses Jahr", heute=date(2026, 7, 4))
    assert von == date(2026, 1, 1)
    assert bis == date(2026, 7, 4)


def test_preset_alles():
    """'Alles' liefert (None, None) — kein Datumsfilter."""
    assert preset_zeitraum("Alles", heute=date(2026, 7, 4)) == (None, None)
