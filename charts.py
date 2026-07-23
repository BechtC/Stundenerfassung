"""
Plotly-Chart-Builder für Dashboard und Statistik.
Datenaufbereitung als reine Funktionen, Figuren einheitlich gestylt.
"""

from datetime import date, timedelta

import plotly.graph_objects as go

import theme

FALLBACK_FARBE = "#AAAAAA"


def _layout(fig, **kwargs):
    """Einheitliches Dark-Layout passend zum Bento-Theme."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": theme.TEXT},
        margin=dict(t=10, b=10),
        **kwargs,
    )
    fig.update_xaxes(gridcolor=theme.CARD_BORDER, zerolinecolor=theme.CARD_BORDER)
    fig.update_yaxes(gridcolor=theme.CARD_BORDER, zerolinecolor=theme.CARD_BORDER)
    return fig


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
    return _layout(fig, yaxis_title="Stunden")


def bar_kategorien(stats_kat):
    """Balkendiagramm Stunden pro Kategorie."""
    fig = go.Figure(go.Bar(
        x=[s["kategorie"] for s in stats_kat],
        y=[s["gesamt_stunden"] for s in stats_kat],
        marker={"color": theme.SECONDARY},
        hovertemplate="%{x}: %{y:.2f}h<extra></extra>",
    ))
    return _layout(fig, yaxis_title="Stunden")


def donut_projekte(summen):
    """Donut-Chart der Stundenverteilung pro Projekt in Projektfarben."""
    fig = go.Figure(go.Pie(
        labels=[s["projekt"] for s in summen],
        values=[s["gesamt_stunden"] for s in summen],
        marker={"colors": [s["farbe"] for s in summen]},
        hole=0.45,
        hovertemplate="%{label}: %{value:.2f}h (%{percent})<extra></extra>",
    ))
    return _layout(fig)


def bar_wochentage(daten):
    """Balken Mo–So: Höhe = Ø Stunden pro Wochentag, Tooltip mit Summe."""
    fig = go.Figure(go.Bar(
        x=[d["wochentag"] for d in daten],
        y=[d["schnitt"] for d in daten],
        customdata=[[d["summe"]] for d in daten],
        marker={"color": theme.ACCENT},
        hovertemplate="%{x}: Ø %{y:.2f}h (Summe %{customdata[0]:.1f}h)<extra></extra>",
    ))
    return _layout(fig, yaxis_title="Ø Stunden")


def bar_tageszeit(verteilung):
    """Histogramm der Startstunden 0–23 Uhr, gewichtet nach Dauer."""
    fig = go.Figure(go.Bar(
        x=[f"{h} Uhr" for h in range(24)],
        y=verteilung,
        marker={"color": theme.ACCENT_LIGHT},
        hovertemplate="%{x}: %{y:.2f}h<extra></extra>",
    ))
    return _layout(fig, yaxis_title="Stunden")


def trend_wochen(trend):
    """Wochensummen als Balken + gleitender 4-Wochen-Schnitt als Linie."""
    wochen = [t["woche"] for t in trend]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=wochen, y=[t["summe"] for t in trend],
        name="Wochenstunden", marker={"color": theme.ACCENT_DIM},
        hovertemplate="%{x}: %{y:.1f}h<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=wochen, y=[t["schnitt4"] for t in trend],
        name="4-Wochen-Schnitt", mode="lines",
        line={"color": theme.CONTRAST, "width": 2},
        hovertemplate="%{x}: Ø %{y:.1f}h<extra></extra>",
    ))
    return _layout(fig, yaxis_title="Stunden",
                   legend={"orientation": "h", "y": 1.1})


MONATS_LABELS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                 "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def heatmap_jahr(matrix, jahr):
    """GitHub-Style Kalender-Heatmap eines Jahres (Zeile=Wochentag, Spalte=Woche)."""
    fig = go.Figure(go.Heatmap(
        z=matrix["z"],
        text=matrix["text"],
        y=["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        colorscale=[[0, "#141b20"], [1, theme.ACCENT]],
        xgap=2, ygap=2,
        hovertemplate="%{text}: %{z:.2f}h<extra></extra>",
        hoverongaps=False,
        showscale=False,
    ))
    # Monatsnamen an der Spalte ihres Monatsersten
    start = date(jahr, 1, 1)
    offset = start.weekday()
    tick_pos = [(offset + (date(jahr, m, 1) - start).days) // 7 for m in range(1, 13)]
    return _layout(
        fig,
        xaxis={"tickvals": tick_pos, "ticktext": MONATS_LABELS, "showgrid": False},
        yaxis={"autorange": "reversed", "showgrid": False},
        height=220,
    )


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
        mode="lines+markers", line={"color": theme.ACCENT},
        hovertemplate="%{x}: %{y:.2f}h<extra></extra>",
    ))
    return _layout(fig, yaxis_title="Stunden")
