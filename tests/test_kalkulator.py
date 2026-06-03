"""
Tests für Stundensatz-Kalkulator (Issue #10).
Reine Python-Funktionen — keine DB, kein Streamlit.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from kalkulator import stundensatz_berechnen, auf_naechste_runden


# ============================================================
# Zyklus 1: stundensatz_berechnen()
# ============================================================

def test_stundensatz_berechnen_grundfall():
    """Standardberechnung: 4000 EUR, 20 Tage, 1h NFH, 20% Puffer."""
    # Formel: 4000 / (20 * (8-1) * (1 - 0.20)) = 4000 / (20*7*0.8) = 4000/112 ≈ 35.71
    result = stundensatz_berechnen(4000, 20, 1, 20)
    assert abs(result - 35.71) < 0.01


def test_stundensatz_berechnen_ohne_puffer():
    """Berechnung ohne Ausfallpuffer (0%)."""
    # 3000 / (15 * 8 * 1.0) = 3000 / 120 = 25.0
    result = stundensatz_berechnen(3000, 15, 0, 0)
    assert abs(result - 25.0) < 0.01


def test_stundensatz_berechnen_null_arbeitstage():
    """0 Arbeitstage wirft ValueError."""
    with pytest.raises(ValueError):
        stundensatz_berechnen(4000, 0, 1, 20)


def test_stundensatz_berechnen_100_prozent_puffer():
    """100% Ausfallpuffer wirft ValueError (Division durch 0)."""
    with pytest.raises(ValueError):
        stundensatz_berechnen(4000, 20, 1, 100)


# ============================================================
# Zyklus 2: auf_naechste_runden()
# ============================================================

def test_runden_auf_5():
    """35.71 → 40 (nächste 5er)."""
    assert auf_naechste_runden(35.71, 5) == 40


def test_runden_auf_10():
    """35.71 → 40 (nächste 10er)."""
    assert auf_naechste_runden(35.71, 10) == 40


def test_runden_auf_1():
    """35.71 → 36 (nächste 1er)."""
    assert auf_naechste_runden(35.71, 1) == 36


def test_runden_exakt():
    """40.0 bleibt 40 bei Schritt 5."""
    assert auf_naechste_runden(40.0, 5) == 40
