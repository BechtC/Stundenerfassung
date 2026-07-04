"""
Tests für die Statistik-Berechnungen (Issue #19).
Reine Funktionen — kein Streamlit, keine DB.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from datetime import date

from statistik import projekt_summen, fortschritt, heatmap_matrix, stunden_pro_wochentag


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


# ============================================================
# Zyklus 6 (Issue #20): Ø Stunden pro Wochentag
# ============================================================

def test_stunden_pro_wochentag_nulltage_im_nenner():
    """Ø = Summe am Wochentag / Anzahl dieses Wochentags im Zeitraum (Nulltage zählen)."""
    # Zeitraum 1.–28. Juni 2026 = exakt 4 volle Wochen (Mo 1.6. bis So 28.6.)
    eintraege = [
        {"datum": "2026-06-01", "stunden": 4.0},   # Montag
        {"datum": "2026-06-08", "stunden": 2.0},   # Montag
        {"datum": "2026-06-03", "stunden": 3.0},   # Mittwoch
    ]
    daten = stunden_pro_wochentag(eintraege, date(2026, 6, 1), date(2026, 6, 28))
    assert len(daten) == 7 and daten[0]["wochentag"] == "Mo"
    assert daten[0]["summe"] == 6.0
    assert daten[0]["schnitt"] == 1.5      # 6h auf 4 Montage
    assert daten[2]["schnitt"] == 0.75     # 3h auf 4 Mittwoche
    assert daten[6]["summe"] == 0.0        # Sonntag ohne Einträge


def test_stunden_pro_wochentag_kurzer_zeitraum():
    """Zeitraum kürzer als eine Woche: nicht enthaltene Wochentage ⇒ Schnitt 0."""
    # Mi 1.7. bis Fr 3.7.2026 — enthält weder Montag noch Sonntag
    eintraege = [{"datum": "2026-07-02", "stunden": 5.0}]  # Donnerstag
    daten = stunden_pro_wochentag(eintraege, date(2026, 7, 1), date(2026, 7, 3))
    assert daten[3]["schnitt"] == 5.0      # 1 Donnerstag im Zeitraum
    assert daten[0]["schnitt"] == 0.0      # kein Montag im Zeitraum, kein Crash
