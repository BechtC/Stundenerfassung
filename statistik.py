"""
Statistik-Berechnungen für die Statistik-Seite.
Reine Funktionen ohne DB- und Streamlit-Abhängigkeiten.
"""

from datetime import date, timedelta


def projekt_summen(eintraege):
    """Summiert Stunden pro Projekt, absteigend sortiert, nur Projekte > 0h."""
    summen = {}
    for e in eintraege:
        pid = e["projekt_id"]
        if pid not in summen:
            summen[pid] = {
                "projekt_id": pid,
                "projekt": e["projekt_name"],
                "farbe": e.get("projekt_farbe") or "#AAAAAA",
                "gesamt_stunden": 0.0,
            }
        summen[pid]["gesamt_stunden"] += e["stunden"]
    ergebnis = [s for s in summen.values() if s["gesamt_stunden"] > 0]
    return sorted(ergebnis, key=lambda s: s["gesamt_stunden"], reverse=True)


def fortschritt(stunden, ziel):
    """Zielfortschritt: anteil (für Balken, max 1.0) + Label im deutschen Format."""
    prozent = round(stunden / ziel * 100)
    stunden_txt = f"{stunden:.1f}".replace(".", ",")
    ziel_txt = f"{ziel:g}".replace(".", ",")
    return {
        "anteil": min(stunden / ziel, 1.0),
        "text": f"{stunden_txt} / {ziel_txt} h ({prozent} %)",
    }


def heatmap_matrix(eintraege, jahr):
    """Kalender-Matrix (GitHub-Style) für ein Jahr.

    Zeile = Wochentag (0=Mo), Spalte = Kalenderwoche. Tage des Jahres ohne
    Eintrag stehen auf 0, Zellen außerhalb des Jahres auf None.
    """
    start = date(jahr, 1, 1)
    anzahl_tage = (date(jahr, 12, 31) - start).days + 1
    offset = start.weekday()  # Padding vor dem 1.1. in Spalte 0
    spalten = (offset + anzahl_tage + 6) // 7

    z = [[None] * spalten for _ in range(7)]
    text = [[""] * spalten for _ in range(7)]
    for i in range(anzahl_tage):
        tag = start + timedelta(days=i)
        z[tag.weekday()][(offset + i) // 7] = 0.0
        text[tag.weekday()][(offset + i) // 7] = tag.isoformat()

    for e in eintraege:
        tag = date.fromisoformat(e["datum"])
        if tag.year != jahr:
            continue
        i = (tag - start).days
        z[tag.weekday()][(offset + i) // 7] += e["stunden"]

    return {"z": z, "text": text}
