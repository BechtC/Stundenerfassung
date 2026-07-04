"""
Statistik-Berechnungen für die Statistik-Seite.
Reine Funktionen ohne DB- und Streamlit-Abhängigkeiten.
"""


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
