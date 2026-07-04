"""
Tests für die Statistik-Berechnungen (Issue #19).
Reine Funktionen — kein Streamlit, keine DB.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from datetime import date

from statistik import (projekt_summen, fortschritt, heatmap_matrix,
                       stunden_pro_wochentag, wochen_trend, tageszeit_verteilung,
                       streak_berechnen)


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


# ============================================================
# Zyklus 8 (Issue #21): Wochen-Trend — ISO-Wochen + Lücken
# ============================================================

def test_wochen_trend_iso_wochen_und_luecken():
    """Aggregation nach ISO-Woche (korrekt über Jahresgrenze), Lücken = 0."""
    eintraege = [
        {"datum": "2025-12-29", "stunden": 2.0},   # Montag → ISO 2026-W01!
        {"datum": "2026-01-02", "stunden": 3.0},   # gleiche ISO-Woche
        {"datum": "2026-01-19", "stunden": 4.0},   # ISO 2026-W04
    ]
    trend = wochen_trend(eintraege)
    wochen = [t["woche"] for t in trend]
    assert wochen == ["2026-W01", "2026-W02", "2026-W03", "2026-W04"]
    assert trend[0]["summe"] == 5.0        # W01: 2h + 3h über Jahresgrenze
    assert trend[1]["summe"] == 0.0        # Lücke aufgefüllt
    assert trend[3]["summe"] == 4.0


def test_wochen_trend_leer():
    assert wochen_trend([]) == []


# ============================================================
# Zyklus 9 (Issue #21): gleitender 4-Wochen-Schnitt
# ============================================================

def test_wochen_trend_gleitender_schnitt():
    """Schnitt über die letzten max. 4 Wochen; bei weniger Wochen über alle."""
    eintraege = [
        {"datum": "2026-06-01", "stunden": 10.0},  # W23
        {"datum": "2026-06-08", "stunden": 20.0},  # W24
        {"datum": "2026-06-15", "stunden": 30.0},  # W25
        {"datum": "2026-06-22", "stunden": 40.0},  # W26
        {"datum": "2026-06-29", "stunden": 50.0},  # W27
    ]
    trend = wochen_trend(eintraege)
    assert trend[0]["schnitt4"] == 10.0            # 1 Woche verfügbar
    assert trend[1]["schnitt4"] == 15.0            # (10+20)/2
    assert trend[3]["schnitt4"] == 25.0            # (10+20+30+40)/4
    assert trend[4]["schnitt4"] == 35.0            # (20+30+40+50)/4 — Fenster rollt


# ============================================================
# Zyklus 10 (Issue #21): Monats-KPI mit Jahreswechsel
# ============================================================

def test_monats_kpi_jahreswechsel():
    """Im Januar ist der Vormonat der Dezember des Vorjahres."""
    from statistik import monats_kpi
    eintraege = [
        {"datum": "2025-12-15", "stunden": 8.0},
        {"datum": "2025-12-20", "stunden": 2.0},
        {"datum": "2026-01-10", "stunden": 5.0},
        {"datum": "2025-11-30", "stunden": 99.0},  # weder aktuell noch Vormonat
    ]
    kpi = monats_kpi(eintraege, heute=date(2026, 1, 15))
    assert kpi == {"aktuell": 5.0, "vormonat": 10.0}


# ============================================================
# Zyklus 11 (Issue #23): Tageszeit-Verteilung
# ============================================================

def test_tageszeit_verteilung_gewichtet_nach_dauer():
    """Startstunde bekommt die Dauer des Eintrags; Einträge ohne startzeit
    fließen nicht ein, werden aber gezählt."""
    eintraege = [
        {"startzeit": "2026-07-01T08:30:00", "stunden": 2.0},
        {"startzeit": "2026-07-02T08:05:12", "stunden": 1.5},
        {"startzeit": "2026-07-02T21:00:00", "stunden": 1.0},
        {"startzeit": None, "stunden": 4.0},        # manuell erfasst
        {"stunden": 3.0},                           # startzeit-Feld fehlt ganz
    ]
    v = tageszeit_verteilung(eintraege)
    assert len(v["verteilung"]) == 24
    assert v["verteilung"][8] == 3.5                # 2h + 1,5h um 8 Uhr
    assert v["verteilung"][21] == 1.0
    assert v["verteilung"][0] == 0.0
    assert v["mit_startzeit"] == 3
    assert v["gesamt"] == 5


def test_tageszeit_verteilung_ohne_startzeiten():
    """Keine Timer-Einträge ⇒ leere Verteilung, mit_startzeit 0, kein Crash."""
    v = tageszeit_verteilung([{"startzeit": None, "stunden": 4.0}])
    assert sum(v["verteilung"]) == 0.0
    assert v["mit_startzeit"] == 0 and v["gesamt"] == 1


# ============================================================
# Zyklus 12 (Issue #24): Streak — Wochenende bricht nicht
# ============================================================

def test_streak_wochenende_bricht_nicht():
    """Fr und Mo belegt, Sa/So leer ⇒ eine Serie von 2 Tagen."""
    # 3.7.2026 = Freitag, 6.7.2026 = Montag
    s = streak_berechnen(["2026-07-03", "2026-07-06"], heute=date(2026, 7, 6))
    assert s == {"aktuell": 2, "laengste": 2}


# ============================================================
# Zyklus 13 (Issue #24): Streak-Randfälle
# ============================================================

def test_streak_leerer_werktag_bricht():
    """Mo+Di belegt, Mi leer, Do belegt ⇒ aktuelle Serie 1, längste 2."""
    # 29.6. Mo, 30.6. Di, 2.7. Do (Mi 1.7. leer)
    s = streak_berechnen(["2026-06-29", "2026-06-30", "2026-07-02"],
                         heute=date(2026, 7, 2))
    assert s == {"aktuell": 1, "laengste": 2}


def test_streak_heute_offen():
    """Heute ohne Eintrag bricht die Serie (noch) nicht."""
    # Gestern (Do 2.7.) belegt, heute Fr 3.7. noch leer ⇒ Serie lebt
    s = streak_berechnen(["2026-07-01", "2026-07-02"], heute=date(2026, 7, 3))
    assert s["aktuell"] == 2
    # Aber: liegt zwischen letztem Eintrag und heute ein leerer Werktag ⇒ 0
    s2 = streak_berechnen(["2026-07-01"], heute=date(2026, 7, 3))  # Do 2.7. leer
    assert s2["aktuell"] == 0
    assert s2["laengste"] == 1


def test_streak_wochenendeintraege_zaehlen():
    """Belegte Wochenendtage verlängern die Serie."""
    # Fr 3.7. + Sa 4.7. + So 5.7. + Mo 6.7. ⇒ Serie 4
    s = streak_berechnen(["2026-07-03", "2026-07-04", "2026-07-05", "2026-07-06"],
                         heute=date(2026, 7, 6))
    assert s == {"aktuell": 4, "laengste": 4}


def test_streak_leere_liste():
    assert streak_berechnen([], heute=date(2026, 7, 4)) == {"aktuell": 0, "laengste": 0}
