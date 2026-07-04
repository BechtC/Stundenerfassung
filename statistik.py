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


WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def stunden_pro_wochentag(eintraege, von, bis):
    """Ø und Summe der Stunden je Wochentag Mo–So.

    Der Durchschnitt teilt durch die Anzahl des Wochentags im Zeitraum —
    Tage ohne Eintrag zählen im Nenner mit.
    """
    summen = [0.0] * 7
    for e in eintraege:
        summen[date.fromisoformat(e["datum"]).weekday()] += e["stunden"]

    anzahl = [0] * 7
    tag = von
    while tag <= bis:
        anzahl[tag.weekday()] += 1
        tag += timedelta(days=1)

    return [{
        "wochentag": WOCHENTAGE[i],
        "summe": summen[i],
        "schnitt": summen[i] / anzahl[i] if anzahl[i] else 0.0,
    } for i in range(7)]


def wochen_trend(eintraege):
    """Wochensummen nach ISO-Woche mit gleitendem 4-Wochen-Schnitt.

    Wochen ohne Eintrag zwischen erster und letzter Woche erscheinen mit 0,
    damit Chart und Schnitt keine Lücken verschweigen.
    """
    summen = {}
    for e in eintraege:
        iso = date.fromisoformat(e["datum"]).isocalendar()
        schluessel = (iso[0], iso[1])
        summen[schluessel] = summen.get(schluessel, 0.0) + e["stunden"]
    if not summen:
        return []

    wochen = []
    jahr, woche = min(summen)
    while (jahr, woche) <= max(summen):
        wochen.append((jahr, woche))
        naechste = date.fromisocalendar(jahr, woche, 1) + timedelta(weeks=1)
        iso = naechste.isocalendar()
        jahr, woche = iso[0], iso[1]

    ergebnis = []
    for i, (j, w) in enumerate(wochen):
        fenster = [summen.get(x, 0.0) for x in wochen[max(0, i - 3):i + 1]]
        ergebnis.append({
            "woche": f"{j}-W{w:02d}",
            "summe": summen.get((j, w), 0.0),
            "schnitt4": sum(fenster) / len(fenster),
        })
    return ergebnis


def monats_kpi(eintraege, heute):
    """Stundensumme des aktuellen Monats und des Vormonats (inkl. Jahreswechsel)."""
    if heute.month == 1:
        vormonat = (heute.year - 1, 12)
    else:
        vormonat = (heute.year, heute.month - 1)

    kpi = {"aktuell": 0.0, "vormonat": 0.0}
    for e in eintraege:
        d = date.fromisoformat(e["datum"])
        if (d.year, d.month) == (heute.year, heute.month):
            kpi["aktuell"] += e["stunden"]
        elif (d.year, d.month) == vormonat:
            kpi["vormonat"] += e["stunden"]
    return kpi


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
