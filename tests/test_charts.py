"""
Tests für die Chart-Datenaufbereitung (Issue #18).
Reine Funktionen — kein Streamlit, keine DB.
"""

from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from charts import tage_auffuellen, bar_projekte


# ============================================================
# Zyklus 4: Lücken-Auffüllung Tagesverlauf
# ============================================================

def test_tage_auffuellen_fuellt_luecken_mit_null():
    """Tage ohne Eintrag erscheinen mit 0 Stunden in der Reihe."""
    tage_stats = [
        {"datum": "2026-07-01", "gesamt_stunden": 4.0},
        {"datum": "2026-07-03", "gesamt_stunden": 2.5},
    ]
    reihe = tage_auffuellen(tage_stats, date(2026, 7, 1), date(2026, 7, 4))
    assert reihe == [
        {"datum": "2026-07-01", "gesamt_stunden": 4.0},
        {"datum": "2026-07-02", "gesamt_stunden": 0.0},
        {"datum": "2026-07-03", "gesamt_stunden": 2.5},
        {"datum": "2026-07-04", "gesamt_stunden": 0.0},
    ]


# ============================================================
# Zyklus 5: Projekt-Balken in Projektfarben
# ============================================================

def test_bar_projekte_nutzt_projektfarben():
    """Balken bekommen die Farbe des Projekts, unbekannte den Grau-Fallback."""
    stats = [
        {"projekt": "AI Learning", "gesamt_stunden": 12.0},
        {"projekt": "Ohne Farbe", "gesamt_stunden": 3.0},
    ]
    farben = {"AI Learning": "#E63946"}
    fig = bar_projekte(stats, farben)
    balken_farben = list(fig.data[0].marker.color)
    assert balken_farben == ["#E63946", "#AAAAAA"]
