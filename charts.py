"""
Plotly-Chart-Builder für Dashboard und Statistik.
Datenaufbereitung als reine Funktionen, Figuren einheitlich gestylt.
"""

from datetime import date, timedelta

import plotly.graph_objects as go

FALLBACK_FARBE = "#AAAAAA"


def tage_auffuellen(tage_stats, von, bis):
    """Vervollständigt eine Tagesreihe: Tage ohne Eintrag bekommen 0 Stunden."""
    vorhanden = {t["datum"]: t["gesamt_stunden"] for t in tage_stats}
    reihe = []
    tag = von
    while tag <= bis:
        iso = tag.isoformat()
        reihe.append({"datum": iso, "gesamt_stunden": vorhanden.get(iso, 0.0)})
        tag += timedelta(days=1)
    return reihe


def bar_projekte(stats_projekt, farben_map):
    """Balkendiagramm Stunden pro Projekt, Balken in Projektfarben."""
    namen = [s["projekt"] for s in stats_projekt]
    stunden = [s["gesamt_stunden"] for s in stats_projekt]
    farben = [farben_map.get(n, FALLBACK_FARBE) for n in namen]
    fig = go.Figure(go.Bar(
        x=namen, y=stunden, marker={"color": farben},
        hovertemplate="%{x}: %{y:.2f}h<extra></extra>",
    ))
    fig.update_layout(margin=dict(t=10, b=10), yaxis_title="Stunden")
    return fig


def bar_kategorien(stats_kat):
    """Balkendiagramm Stunden pro Kategorie."""
    fig = go.Figure(go.Bar(
        x=[s["kategorie"] for s in stats_kat],
        y=[s["gesamt_stunden"] for s in stats_kat],
        marker={"color": "#457B9D"},
        hovertemplate="%{x}: %{y:.2f}h<extra></extra>",
    ))
    fig.update_layout(margin=dict(t=10, b=10), yaxis_title="Stunden")
    return fig


def linie_tagesverlauf(tage_stats, von=None, bis=None):
    """Linien-Chart des Tagesverlaufs; Tage ohne Eintrag erscheinen als 0."""
    if tage_stats:
        daten = sorted(tage_stats, key=lambda t: t["datum"])
        von = von or date.fromisoformat(daten[0]["datum"])
        bis = bis or date.fromisoformat(daten[-1]["datum"])
        reihe = tage_auffuellen(daten, von, bis)
    else:
        reihe = []
    fig = go.Figure(go.Scatter(
        x=[t["datum"] for t in reihe],
        y=[t["gesamt_stunden"] for t in reihe],
        mode="lines+markers", line={"color": "#2A9D8F"},
        hovertemplate="%{x}: %{y:.2f}h<extra></extra>",
    ))
    fig.update_layout(margin=dict(t=10, b=10), yaxis_title="Stunden")
    return fig
