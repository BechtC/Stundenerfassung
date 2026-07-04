"""
Tests für die Statistik-Berechnungen (Issue #19).
Reine Funktionen — kein Streamlit, keine DB.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from statistik import projekt_summen, fortschritt


# ============================================================
# Zyklus 1: Projektsummen — aggregiert, sortiert, gefiltert
# ============================================================

def test_projekt_summen_aggregiert_und_sortiert():
    """Stunden werden pro Projekt summiert und absteigend sortiert."""
    eintraege = [
        {"projekt_id": 1, "projekt_name": "AI Learning", "projekt_farbe": "#E63946", "stunden": 2.0},
        {"projekt_id": 2, "projekt_name": "Trading", "projekt_farbe": "#457B9D", "stunden": 5.0},
        {"projekt_id": 1, "projekt_name": "AI Learning", "projekt_farbe": "#E63946", "stunden": 1.5},
    ]
    summen = projekt_summen(eintraege)
    assert summen == [
        {"projekt_id": 2, "projekt": "Trading", "farbe": "#457B9D", "gesamt_stunden": 5.0},
        {"projekt_id": 1, "projekt": "AI Learning", "farbe": "#E63946", "gesamt_stunden": 3.5},
    ]


def test_projekt_summen_leer():
    """Keine Einträge ⇒ leere Liste, kein Crash."""
    assert projekt_summen([]) == []


# ============================================================
# Zyklus 2: Zielfortschritt unter 100 %
# ============================================================

def test_fortschritt_unter_hundert():
    """150 von 300h ⇒ Anteil 0.5, Label mit deutschem Zahlenformat."""
    f = fortschritt(150.0, 300.0)
    assert f["anteil"] == 0.5
    assert f["text"] == "150,0 / 300 h (50 %)"


# ============================================================
# Zyklus 3: Übererfüllung — Balken voll, Prozent läuft weiter
# ============================================================

def test_fortschritt_ueber_hundert():
    """312,5 von 300h ⇒ Balken bei 1.0 gedeckelt, Prozent über 100."""
    f = fortschritt(312.5, 300.0)
    assert f["anteil"] == 1.0
    assert f["text"] == "312,5 / 300 h (104 %)"
