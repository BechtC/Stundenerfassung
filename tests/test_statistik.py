"""
Tests für die Statistik-Berechnungen (Issue #19).
Reine Funktionen — kein Streamlit, keine DB.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from statistik import projekt_summen, fortschritt, heatmap_matrix


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


# ============================================================
# Zyklus 4 (Issue #22): Heatmap-Matrix — Tag → Zelle
# ============================================================

def test_heatmap_matrix_ordnet_tage_zu():
    """Einträge landen in Zeile=Wochentag (0=Mo), Spalte=Kalenderwoche;
    Tage ohne Eintrag = 0, Zellen vor Jahresbeginn = None."""
    eintraege = [
        {"datum": "2026-01-01", "stunden": 2.0},   # Donnerstag
        {"datum": "2026-01-01", "stunden": 1.5},   # gleicher Tag → summiert
        {"datum": "2026-01-05", "stunden": 4.0},   # Montag, Woche 2
    ]
    m = heatmap_matrix(eintraege, 2026)
    z = m["z"]
    assert len(z) == 7                      # 7 Wochentag-Zeilen
    # 1.1.2026 ist ein Donnerstag → Zeile 3, Spalte 0
    assert z[3][0] == 3.5
    # 5.1.2026 ist ein Montag → Zeile 0, Spalte 1
    assert z[0][1] == 4.0
    # 2.1.2026 (Freitag, im Jahr, kein Eintrag) → 0
    assert z[4][0] == 0.0
    # Mo–Mi vor dem 1.1. gehören nicht zum Jahr → None
    assert z[0][0] is None and z[2][0] is None


# ============================================================
# Zyklus 5 (Issue #22): Jahresgrenzen + Schaltjahr
# ============================================================

def test_heatmap_matrix_ignoriert_fremde_jahre():
    """Einträge aus Nachbarjahren fließen nicht in die Matrix ein."""
    eintraege = [
        {"datum": "2025-12-31", "stunden": 8.0},
        {"datum": "2027-01-01", "stunden": 8.0},
    ]
    m = heatmap_matrix(eintraege, 2026)
    werte = [v for zeile in m["z"] for v in zeile if v is not None]
    assert sum(werte) == 0.0


def test_heatmap_matrix_schaltjahr():
    """2024 (Schaltjahr) hat 366 aktive Zellen, 2026 hat 365."""
    zellen_2024 = [v for zeile in heatmap_matrix([], 2024)["z"] for v in zeile
                   if v is not None]
    zellen_2026 = [v for zeile in heatmap_matrix([], 2026)["z"] for v in zeile
                   if v is not None]
    assert len(zellen_2024) == 366
    assert len(zellen_2026) == 365
