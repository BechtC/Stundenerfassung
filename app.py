"""
Stundenerfassung - Hauptanwendung
Streamlit-basiertes Tool für persönliche Zeiterfassung und Rechnungsstellung.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import database as db
from rechnung_pdf import rechnung_als_pdf, monatsexport_als_pdf
from kalkulator import stundensatz_berechnen, auf_naechste_runden
from zeitraum import zeitraum_waehlen
import charts
import statistik

# --- Init ---
db.init_db()

# --- Tagesbackup (darf den App-Start nie verhindern) ---
try:
    db.backup_erstellen(Path(__file__).parent / "backups")
except Exception as backup_fehler:
    print(f"WARNUNG: Backup fehlgeschlagen: {backup_fehler}")

# --- Timer-Tray-App automatisch mitstarten (nur einmal, nie blockierend) ---
# Läuft die Stundenerfassung (egal ob aus AI-Tool-OS oder start.bat), erscheint
# automatisch das Timer-Icon im Windows-Infobereich. Dieser Aufruf steht bewusst
# auf Modul-Ebene (läuft einmal beim Server-Start, unabhängig von einer Browser-
# Session); der Mehrfachstart-Schutz liegt im Lockfile in tray_starten_falls_noetig().
try:
    import tray_timer
    tray_timer.tray_starten_falls_noetig()
except Exception as tray_fehler:
    print(f"WARNUNG: Tray-Autostart fehlgeschlagen: {tray_fehler}")

# --- Timer Session State aus DB wiederherstellen (Reload-Resistenz) ---
if "timer_aktiv" not in st.session_state:
    laufender = db.laufenden_timer_laden()
    if laufender:
        st.session_state.timer_aktiv = True
        st.session_state.timer_eintrag_id = laufender["id"]
        st.session_state.timer_stundensatz = laufender["stundensatz"]
        st.session_state.timer_startzeit = laufender["startzeit"]
        st.session_state.timer_projekt_name = laufender["projekt_name"]
        st.session_state.timer_projekt_farbe = laufender.get("projekt_farbe", "#AAAAAA")
        st.session_state.timer_unterthema_name = laufender.get("unterthema_name")
        st.session_state.timer_beschreibung = laufender.get("beschreibung", "")
        st.session_state.timer_kategorie = laufender.get("kategorie", "Produktiv")
    else:
        st.session_state.timer_aktiv = False

if "stopp_dialog_offen" not in st.session_state:
    st.session_state.stopp_dialog_offen = False

if "edit_eintrag" not in st.session_state:
    st.session_state.edit_eintrag = None

if "loesch_projekt" not in st.session_state:
    st.session_state.loesch_projekt = None

st.set_page_config(
    page_title="Stundenerfassung",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Theme + MagicBento-Effekte (Dark Theme, Glow, Spotlight, Tilt)
from theme import inject_theme
inject_theme()

# --- Sidebar Navigation ---
st.sidebar.title("Stundenerfassung")
seite = st.sidebar.radio("Navigation", [
    "Zeiterfassung",
    "Dashboard",
    "Statistik",
    "Projekte",
    "Rechnungen",
    "Einstellungen",
])

# --- Live-Tracker Sidebar ---
st.sidebar.divider()

if st.session_state.timer_aktiv:
    # --- Aktiver Timer: JS-Uhr + Stopp-Button ---
    startzeit_iso = st.session_state.timer_startzeit
    projekt_label = st.session_state.timer_projekt_name
    if st.session_state.timer_unterthema_name:
        projekt_label += f" › {st.session_state.timer_unterthema_name}"
    from datetime import datetime as dt
    startzeit_anzeige = dt.fromisoformat(startzeit_iso).strftime("%H:%M")

    timer_farbe = st.session_state.get("timer_projekt_farbe", "#AAAAAA") or "#AAAAAA"
    st.sidebar.markdown(
        f'<span style="color:{timer_farbe}">●</span> **⏱ {projekt_label}**',
        unsafe_allow_html=True
    )
    st.sidebar.caption(f"Gestartet: {startzeit_anzeige}")

    import streamlit.components.v1 as components
    components.html(f"""
        <div id="timer" style="font-size:2em; font-family:monospace; color:#e0e0e0;
             text-align:center; padding:8px 0;">00:00:00</div>
        <script>
          const start = new Date("{startzeit_iso}");
          function tick() {{
            const diff = Math.floor((new Date() - start) / 1000);
            const h = String(Math.floor(diff/3600)).padStart(2,'0');
            const m = String(Math.floor((diff%3600)/60)).padStart(2,'0');
            const s = String(diff%60).padStart(2,'0');
            document.getElementById('timer').textContent = h+':'+m+':'+s;
          }}
          tick();
          setInterval(tick, 1000);
        </script>
    """, height=60)

    if st.sidebar.button("⏹ Stoppen", type="primary", use_container_width=True):
        st.session_state.stopp_dialog_offen = True
        st.rerun()

else:
    # --- Kein aktiver Timer: Recently Used + Neuer Timer ---
    recently = db.recently_used_laden()

    if recently:
        st.sidebar.markdown("**Zuletzt verwendet:**")
        for r in recently:
            rfarbe = r.get("projekt_farbe") or "#AAAAAA"
            label = f"▶ {r['projekt_name']}"
            if r.get("unterthema_name"):
                label += f" › {r['unterthema_name']}"
            if st.sidebar.button(label, key=f"recent_{r['projekt_id']}_{r['unterthema_id']}",
                                  use_container_width=True):
                projekte = db.projekte_laden()
                projekt = next((p for p in projekte if p["id"] == r["projekt_id"]), None)
                stundensatz = projekt["stundensatz"] if projekt else 0.0
                eid = db.timer_starten(
                    projekt_id=r["projekt_id"],
                    unterthema_id=r["unterthema_id"],
                    kategorie=r.get("kategorie", "Produktiv"),
                    beschreibung="",
                    stundensatz=stundensatz,
                )
                st.session_state.timer_aktiv = True
                st.session_state.timer_eintrag_id = eid
                st.session_state.timer_stundensatz = stundensatz
                laufender = db.laufenden_timer_laden()
                st.session_state.timer_startzeit = laufender["startzeit"]
                st.session_state.timer_projekt_name = laufender["projekt_name"]
                st.session_state.timer_projekt_farbe = laufender.get("projekt_farbe", "#AAAAAA")
                st.session_state.timer_unterthema_name = laufender.get("unterthema_name")
                st.session_state.timer_beschreibung = ""
                st.session_state.timer_kategorie = r.get("kategorie", "Produktiv")
                st.rerun()

    st.sidebar.markdown("**Neuer Timer:**")
    projekte = db.projekte_laden()
    if not projekte:
        st.sidebar.caption("Bitte erst ein Projekt anlegen.")
    else:
        projekt_namen = {p["name"]: p for p in projekte}
        gew_projekt_name = st.sidebar.selectbox("Projekt", list(projekt_namen.keys()),
                                                 key="timer_projekt_select")
        gew_projekt = projekt_namen[gew_projekt_name]

        unterthemen = db.unterthemen_laden(gew_projekt["id"])
        ut_namen = {"(Kein Unterthema)": None}
        ut_namen.update({u["name"]: u["id"] for u in unterthemen})
        gew_ut = st.sidebar.selectbox("Unterthema", list(ut_namen.keys()),
                                       key="timer_ut_select")
        ut_id = ut_namen[gew_ut]

        timer_kat = st.sidebar.selectbox("Kategorie", db.KATEGORIEN, key="timer_kat_select")
        timer_kommentar = st.sidebar.text_input("Kommentar", key="timer_kommentar")

        # Multi-Tab-Schutz
        laufender = db.laufenden_timer_laden()
        if laufender:
            st.sidebar.warning(f"Bereits läuft: {laufender['projekt_name']}")
        elif st.sidebar.button("▶ Starten", type="primary", use_container_width=True):
            eid = db.timer_starten(
                projekt_id=gew_projekt["id"],
                unterthema_id=ut_id,
                kategorie=timer_kat,
                beschreibung=timer_kommentar,
                stundensatz=gew_projekt["stundensatz"],
            )
            st.session_state.timer_aktiv = True
            st.session_state.timer_eintrag_id = eid
            st.session_state.timer_stundensatz = gew_projekt["stundensatz"]
            laufender = db.laufenden_timer_laden()
            st.session_state.timer_startzeit = laufender["startzeit"]
            st.session_state.timer_projekt_name = laufender["projekt_name"]
            st.session_state.timer_projekt_farbe = laufender.get("projekt_farbe", "#AAAAAA")
            st.session_state.timer_unterthema_name = laufender.get("unterthema_name")
            st.session_state.timer_beschreibung = timer_kommentar
            st.session_state.timer_kategorie = timer_kat
            st.rerun()

# --- Stopp-Dialog ---
@st.dialog("Timer stoppen")
def stopp_dialog():
    from datetime import datetime as dt, timedelta
    startzeit = dt.fromisoformat(st.session_state.timer_startzeit)
    jetzt = dt.now()

    st.write(f"**Projekt:** {st.session_state.timer_projekt_name}" +
             (f" › {st.session_state.timer_unterthema_name}"
              if st.session_state.timer_unterthema_name else ""))
    st.caption(f"Gestartet: {startzeit.strftime('%d.%m.%Y %H:%M')} Uhr")

    # Endzeit-Eingabe: vorbelegt mit jetzt — bei vergessenem Ausstempeln
    # einfach die tatsächliche Schlusszeit wählen, die Dauer folgt automatisch.
    endzeit_uhr = st.time_input("Endzeit", value=jetzt.time(), step=300)
    endzeit = dt.combine(startzeit.date(), endzeit_uhr)
    if endzeit < startzeit:
        # Über-Mitternacht-Fall: gewählte Uhrzeit liegt vor der Start-Uhrzeit
        endzeit += timedelta(days=1)

    diff_sek = int((endzeit - startzeit).total_seconds())
    stunden_dezimal = round(diff_sek / 3600, 2)
    h, m = divmod(diff_sek // 60, 60)
    st.caption(f"{startzeit.strftime('%H:%M')} → {endzeit.strftime('%H:%M')} "
               f"= {h}h {m}min ({stunden_dezimal}h)")

    # key enthält die Endzeit: bei Endzeit-Änderung setzt Streamlit das Feld
    # auf den neu berechneten Wert zurück; manuelles Umtippen gewinnt sonst.
    dauer = st.number_input("Dauer (Stunden)", min_value=0.0, max_value=24.0,
                            value=stunden_dezimal, step=0.25,
                            key=f"stopp_dauer_{endzeit_uhr}",
                            help="Folgt der Endzeit — hier nur ändern, wenn du "
                                 "die Dauer direkt setzen willst.")
    kat = st.selectbox("Kategorie", db.KATEGORIEN,
                       index=db.KATEGORIEN.index(st.session_state.timer_kategorie)
                       if st.session_state.timer_kategorie in db.KATEGORIEN else 0)
    kommentar = st.text_area("Kommentar", value=st.session_state.timer_beschreibung, height=80)

    c1, c2 = st.columns(2)
    if c1.button("Speichern", type="primary", use_container_width=True):
        db.timer_stoppen(st.session_state.timer_eintrag_id, beschreibung=kommentar,
                         endzeit=endzeit)
        db.zeiteintrag_aktualisieren(st.session_state.timer_eintrag_id,
                                     stunden=round(dauer, 2), kategorie=kat)
        st.session_state.timer_aktiv = False
        st.session_state.stopp_dialog_offen = False
        st.rerun()
    if c2.button("Abbrechen", use_container_width=True):
        st.session_state.stopp_dialog_offen = False
        st.rerun()

if st.session_state.stopp_dialog_offen:
    stopp_dialog()

# --- Projekt-Lösch-Dialog ---
@st.dialog("Projekt löschen")
def loesch_dialog():
    projekt = st.session_state.loesch_projekt
    stats = db.projekt_statistik(projekt["id"])

    if stats["rechnungen"] > 0:
        st.warning(f"**{projekt['name']}** hat {stats['rechnungen']} Rechnung(en) — "
                   "Belege müssen erhalten bleiben. Bitte deaktivieren statt löschen.")
        d1, d2 = st.columns(2)
        if d1.button("Deaktivieren", type="primary", use_container_width=True):
            db.projekt_aktualisieren(projekt["id"], aktiv=0)
            st.session_state.loesch_projekt = None
            st.rerun()
        if d2.button("Abbrechen", use_container_width=True):
            st.session_state.loesch_projekt = None
            st.rerun()
    else:
        st.warning(f"Löscht **{projekt['name']}** mit {stats['zeiteintraege']} "
                   f"Zeiteinträgen und {stats['unterthemen']} Unterthemen "
                   "unwiderruflich.")
        d1, d2 = st.columns(2)
        if d1.button("Endgültig löschen", type="primary", use_container_width=True):
            db.projekt_loeschen(projekt["id"])
            st.session_state.loesch_projekt = None
            st.rerun()
        if d2.button("Abbrechen", use_container_width=True):
            st.session_state.loesch_projekt = None
            st.rerun()

if st.session_state.loesch_projekt:
    loesch_dialog()

# --- Auffälliges Live-Timer-Banner im Hauptbereich (alle Seiten) ---
import streamlit.components.v1 as components

if st.session_state.timer_aktiv:
    _startzeit_iso = st.session_state.timer_startzeit
    _projekt_label = st.session_state.timer_projekt_name
    if st.session_state.timer_unterthema_name:
        _projekt_label += f" › {st.session_state.timer_unterthema_name}"
    _farbe = st.session_state.get("timer_projekt_farbe", "#AAAAAA") or "#AAAAAA"
    _label_js = json.dumps(_projekt_label)
    components.html(f"""
        <div style="background:{_farbe}22; border:2px solid {_farbe};
             border-radius:10px; padding:10px 18px; margin-bottom:6px;
             display:flex; align-items:center; gap:16px; font-family:sans-serif;">
          <span style="font-size:2.4em;">⏱</span>
          <div style="flex:1;">
            <div style="font-size:1.1em; font-weight:600; color:{_farbe};">
              {_projekt_label}</div>
            <div id="bigtimer" style="font-size:2.4em; font-family:monospace;
                 font-weight:700; line-height:1.1;">00:00:00</div>
          </div>
          <span style="font-size:0.9em; opacity:0.7;">läuft…</span>
        </div>
        <script>
          const start = new Date("{_startzeit_iso}");
          const projekt = {_label_js};
          function tick() {{
            const diff = Math.floor((new Date() - start) / 1000);
            const h = String(Math.floor(diff/3600)).padStart(2,'0');
            const m = String(Math.floor((diff%3600)/60)).padStart(2,'0');
            const s = String(diff%60).padStart(2,'0');
            document.getElementById('bigtimer').textContent = h+':'+m+':'+s;
            // Tab-Titel live mittickern (sichtbar in Chrome-Tableiste / Alt-Tab)
            window.parent.document.title = "⏱ "+h+":"+m+":"+s+" · "+projekt;
          }}
          tick();
          setInterval(tick, 1000);
        </script>
    """, height=90)
else:
    # Kein Timer aktiv → Tab-Titel zurücksetzen (falls von vorher gesetzt)
    components.html("""
        <script>window.parent.document.title = "Stundenerfassung";</script>
    """, height=0)

# ============================================================
# ZEITERFASSUNG
# ============================================================
if seite == "Zeiterfassung":
    st.header("Zeiterfassung")

    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Neuer Eintrag")

        datum = st.date_input("Datum", value=date.today())
        projekte = db.projekte_laden()

        if not projekte:
            st.warning("Bitte zuerst ein Projekt anlegen unter 'Projekte'.")
        else:
            projekt_namen = {p["name"]: p["id"] for p in projekte}
            gewaehltes_projekt = st.selectbox("Projekt", list(projekt_namen.keys()))
            projekt_id = projekt_namen[gewaehltes_projekt]

            unterthemen = db.unterthemen_laden(projekt_id)
            unterthema_id = None
            if unterthemen:
                ut_namen = {"(Kein Unterthema)": None}
                ut_namen.update({u["name"]: u["id"] for u in unterthemen})
                gewaehltes_ut = st.selectbox("Unterthema", list(ut_namen.keys()))
                unterthema_id = ut_namen[gewaehltes_ut]

            stunden = st.number_input("Stunden", min_value=0.25, max_value=24.0,
                                       value=1.0, step=0.25)
            kategorie = st.selectbox("Kategorie", db.KATEGORIEN)
            beschreibung = st.text_area("Beschreibung", height=80)

            if st.button("Eintrag speichern", type="primary", use_container_width=True):
                db.zeiteintrag_erstellen(
                    datum=datum.isoformat(),
                    projekt_id=projekt_id,
                    unterthema_id=unterthema_id,
                    stunden=stunden,
                    beschreibung=beschreibung,
                    kategorie=kategorie,
                )
                st.success(f"{stunden}h für '{gewaehltes_projekt}' gespeichert!")
                st.rerun()

    with col2:
        def _eintrag_karte(e):
            """Eine Eintrags-Karte mit Bearbeiten/Löschen — für heute + Historie."""
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
                pfarbe = e.get("projekt_farbe") or "#AAAAAA"
                pname = f'<span style="color:{pfarbe}">●</span> **{e["projekt_name"]}**'
                if e.get("unterthema_name"):
                    pname += f' › {e["unterthema_name"]}'
                c1.markdown(pname, unsafe_allow_html=True)
                c2.write(e.get("beschreibung", ""))
                c3.write(f"{e['stunden']:.2f}h")
                if c4.button("✏", key=f"edit_{e['id']}", help="Bearbeiten"):
                    st.session_state.edit_eintrag = e
                    st.rerun()
                if c5.button("X", key=f"del_{e['id']}", help="Löschen"):
                    db.zeiteintrag_loeschen(e["id"])
                    st.rerun()

        st.subheader("Heutige Einträge")
        heute = date.today().isoformat()
        eintraege = db.zeiteintraege_laden(datum_von=heute, datum_bis=heute)

        if eintraege:
            gesamt = sum(e["stunden"] for e in eintraege)
            st.metric("Heute gesamt", f"{gesamt:.2f} Stunden")
            for e in eintraege:
                _eintrag_karte(e)
        else:
            st.info("Noch keine Einträge heute.")

        # --- Vergangene Einträge (chronologisch, neueste oben) ---
        st.divider()
        st.subheader("Vergangene Einträge")
        hist_von, hist_bis = zeitraum_waehlen("hist", default_preset="Dieser Monat")

        alle_projekte = db.projekte_laden(nur_aktive=False)
        hist_projekt_optionen = {"Alle Projekte": None}
        hist_projekt_optionen.update({p["name"]: p["id"] for p in alle_projekte})
        hist_projekt_name = st.selectbox("Projekt filtern",
                                         list(hist_projekt_optionen.keys()),
                                         key="hist_projekt")
        hist_projekt_id = hist_projekt_optionen[hist_projekt_name]

        # Heutiger Tag ist oben schon gelistet — Historie endet gestern.
        gestern = date.today() - timedelta(days=1)
        hist_bis_effektiv = min(hist_bis, gestern)

        if hist_von > hist_bis_effektiv:
            historie = []
        else:
            historie = db.zeiteintraege_laden(datum_von=hist_von.isoformat(),
                                              datum_bis=hist_bis_effektiv.isoformat(),
                                              projekt_id=hist_projekt_id)

        if historie:
            WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
            # Nach Datum gruppieren — Query liefert bereits datum DESC.
            tage = {}
            for e in historie:
                tage.setdefault(e["datum"], []).append(e)
            for tag, tag_eintraege in tage.items():
                tag_datum = date.fromisoformat(tag)
                tag_summe = sum(e["stunden"] for e in tag_eintraege)
                label = (f"{WOCHENTAGE[tag_datum.weekday()]} "
                         f"{tag_datum.strftime('%d.%m.%Y')} — {tag_summe:.2f}h")
                with st.expander(label):
                    for e in tag_eintraege:
                        _eintrag_karte(e)
        else:
            st.caption("Keine Einträge im gewählten Zeitraum.")

        # --- Bearbeiten-Dialog (heutige + vergangene Einträge) ---
        if st.session_state.edit_eintrag is not None:
            @st.dialog("Eintrag bearbeiten")
            def edit_dialog(eintrag):
                from datetime import datetime as dt, time as dtime
                st.write(f"**Projekt:** {eintrag['projekt_name']}" +
                         (f" › {eintrag['unterthema_name']}"
                          if eintrag.get("unterthema_name") else ""))

                e_datum = st.date_input("Datum",
                                        value=date.fromisoformat(eintrag["datum"]))

                # Startzeit: aus DB falls vorhanden (Timer-Eintrag), sonst 08:00.
                if eintrag.get("startzeit"):
                    start_default = dt.fromisoformat(eintrag["startzeit"]).time()
                else:
                    start_default = dtime(8, 0)
                # Endzeit-Default = Start + bisherige Dauer
                _start_dt = dt.combine(e_datum, start_default)
                _ende_dt = _start_dt + timedelta(hours=float(eintrag["stunden"]))

                cs, ce = st.columns(2)
                start_uhr = cs.time_input("Start", value=start_default, step=300)
                ende_uhr = ce.time_input("Ende", value=_ende_dt.time(), step=300)

                start_dt = dt.combine(e_datum, start_uhr)
                ende_dt = dt.combine(e_datum, ende_uhr)
                if ende_dt < start_dt:
                    # Über-Mitternacht-Fall
                    ende_dt += timedelta(days=1)

                diff_sek = int((ende_dt - start_dt).total_seconds())
                stunden_dezimal = round(diff_sek / 3600, 2)
                h, m = divmod(diff_sek // 60, 60)
                st.caption(f"{start_dt.strftime('%H:%M')} → {ende_dt.strftime('%H:%M')} "
                           f"= {h}h {m}min ({stunden_dezimal}h)")

                # key enthält Start+Ende: Feld folgt den Uhrzeiten,
                # manuelles Umtippen gewinnt (wie im Stopp-Dialog).
                dauer = st.number_input("Dauer (Stunden)", min_value=0.0,
                                        max_value=24.0, value=stunden_dezimal,
                                        step=0.25,
                                        key=f"edit_dauer_{start_uhr}_{ende_uhr}",
                                        help="Folgt Start/Ende — hier nur ändern, "
                                             "wenn du die Dauer direkt setzen willst.")
                kat_wert = eintrag.get("kategorie", "Produktiv")
                kat = st.selectbox("Kategorie", db.KATEGORIEN,
                                   index=db.KATEGORIEN.index(kat_wert)
                                   if kat_wert in db.KATEGORIEN else 0)
                kommentar = st.text_area("Beschreibung",
                                         value=eintrag.get("beschreibung", "") or "",
                                         height=80)
                c1, c2 = st.columns(2)
                if c1.button("Speichern", type="primary", use_container_width=True):
                    db.zeiteintrag_aktualisieren(eintrag["id"],
                                                 datum=e_datum.isoformat(),
                                                 startzeit=start_dt.isoformat(),
                                                 stunden=round(dauer, 2),
                                                 kategorie=kat,
                                                 beschreibung=kommentar)
                    st.session_state.edit_eintrag = None
                    st.rerun()
                if c2.button("Abbrechen", use_container_width=True):
                    st.session_state.edit_eintrag = None
                    st.rerun()
            edit_dialog(st.session_state.edit_eintrag)

        st.divider()
        st.subheader("Letzte 7 Tage")
        vor_7_tagen = (date.today() - timedelta(days=7)).isoformat()
        letzte_woche = db.zeiteintraege_laden(datum_von=vor_7_tagen)
        if letzte_woche:
            df = pd.DataFrame(letzte_woche)
            df_grouped = df.groupby("datum")["stunden"].sum().reset_index()
            tage_stats = [{"datum": r["datum"], "gesamt_stunden": r["stunden"]}
                          for _, r in df_grouped.iterrows()]
            st.plotly_chart(
                charts.linie_tagesverlauf(tage_stats,
                                          date.today() - timedelta(days=7),
                                          date.today()),
                use_container_width=True)


# ============================================================
# DASHBOARD
# ============================================================
elif seite == "Dashboard":
    st.header("Dashboard")

    von, bis = zeitraum_waehlen("dash", default_preset="Dieser Monat")

    von_str = von.isoformat()
    bis_str = bis.isoformat()

    # KPIs
    eintraege = db.zeiteintraege_laden(datum_von=von_str, datum_bis=bis_str)
    if eintraege:
        gesamt_stunden = sum(e["stunden"] for e in eintraege)
        gesamt_betrag = sum(e["stunden"] * (e.get("stundensatz") or 0) for e in eintraege)
        tage = len(set(e["datum"] for e in eintraege))
        schnitt = gesamt_stunden / tage if tage > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Gesamtstunden", f"{gesamt_stunden:.1f}h")
        k2.metric("Gesamtbetrag", f"{gesamt_betrag:,.2f} EUR")
        k3.metric("Arbeitstage", tage)
        k4.metric("Schnitt/Tag", f"{schnitt:.1f}h")

        st.divider()

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("Stunden pro Projekt")
            stats_projekt = db.statistik_pro_projekt(von_str, bis_str)
            if stats_projekt:
                farben_map = {p["name"]: p["farbe"]
                              for p in db.projekte_laden(nur_aktive=False)}
                st.plotly_chart(charts.bar_projekte(stats_projekt, farben_map),
                                use_container_width=True)

        with col_chart2:
            st.subheader("Stunden pro Kategorie")
            stats_kat = db.statistik_pro_kategorie(von_str, bis_str)
            if stats_kat:
                st.plotly_chart(charts.bar_kategorien(stats_kat),
                                use_container_width=True)

        st.divider()
        st.subheader("Tagesverlauf")
        tage_stats = db.stunden_pro_tag(von_str, bis_str)
        if tage_stats:
            st.plotly_chart(charts.linie_tagesverlauf(tage_stats, von, bis),
                            use_container_width=True)

        st.divider()
        st.subheader("Alle Einträge")
        df_all = pd.DataFrame(eintraege)
        anzeige_spalten = ["datum", "projekt_name", "unterthema_name", "stunden",
                           "kategorie", "beschreibung"]
        vorhandene = [s for s in anzeige_spalten if s in df_all.columns]
        st.dataframe(df_all[vorhandene], use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Export")
        ex_col1, ex_col2, ex_col3 = st.columns(3)
        with ex_col1:
            export_jahr = st.number_input("Jahr", min_value=2020, max_value=2030,
                                          value=date.today().year, step=1, key="ex_jahr")
        with ex_col2:
            export_monat = st.selectbox("Monat", list(range(1, 13)),
                                        index=date.today().month - 1,
                                        format_func=lambda m: date(2000, m, 1).strftime("%B"),
                                        key="ex_monat")
        with ex_col3:
            projekt_optionen = {"Alle Projekte": None}
            for e in eintraege:
                projekt_optionen[e["projekt_name"]] = e["projekt_id"]
            gew_export_projekt = st.selectbox("Projekt", list(projekt_optionen.keys()),
                                              key="ex_projekt")
            export_projekt_id = projekt_optionen[gew_export_projekt]

        export_daten = db.zeiteintraege_monat_laden(
            int(export_jahr), int(export_monat), projekt_id=export_projekt_id
        )
        if export_daten:
            df_export = pd.DataFrame(export_daten)[
                [c for c in ["datum", "projekt_name", "unterthema_name",
                              "stunden", "kategorie", "beschreibung"] if c in pd.DataFrame(export_daten).columns]
            ]
            dateiname = f"stundenerfassung_{int(export_jahr)}-{int(export_monat):02d}"
            if export_projekt_id:
                dateiname += f"_{gew_export_projekt.replace(' ', '_')}"
            dl_col1, dl_col2 = st.columns(2)
            dl_col1.download_button(
                label=f"CSV herunterladen ({len(export_daten)} Einträge)",
                data=df_export.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                file_name=f"{dateiname}.csv",
                mime="text/csv",
            )
            firma = db.firmendaten_laden()
            pdf_bytes = monatsexport_als_pdf(
                firma, int(export_jahr), int(export_monat), export_daten,
                projekt_filter=gew_export_projekt if export_projekt_id else None
            )
            dl_col2.download_button(
                label=f"PDF herunterladen ({len(export_daten)} Einträge)",
                data=pdf_bytes,
                file_name=f"{dateiname}.pdf",
                mime="application/pdf",
            )
        else:
            st.info("Keine Einträge für diesen Monat/Projekt.")
    else:
        st.info("Keine Einträge im gewählten Zeitraum.")


# ============================================================
# STATISTIK
# ============================================================
elif seite == "Statistik":
    st.header("Statistik")

    von, bis = zeitraum_waehlen("stat", default_preset="Dieses Jahr")
    eintraege = db.zeiteintraege_laden(datum_von=von.isoformat(),
                                       datum_bis=bis.isoformat())

    if not eintraege:
        st.info("Keine Einträge im gewählten Zeitraum.")
    else:
        summen = statistik.projekt_summen(eintraege)
        ziele_map = {z["projekt_id"]: z["stunden_ziel"]
                     for z in db.ziele_laden(bis.year)}

        st.subheader("Stunden pro Projekt")
        for zeile_start in range(0, len(summen), 3):
            cols = st.columns(3)
            for col, s in zip(cols, summen[zeile_start:zeile_start + 3]):
                with col:
                    with st.container(border=True):
                        st.markdown(
                            f'<span style="color:{s["farbe"]}">●</span> **{s["projekt"]}**',
                            unsafe_allow_html=True)
                        ziel = ziele_map.get(s["projekt_id"])
                        if ziel:
                            f = statistik.fortschritt(s["gesamt_stunden"], ziel)
                            st.progress(f["anteil"], text=f["text"])
                        else:
                            stunden_txt = f"{s['gesamt_stunden']:.1f}".replace(".", ",")
                            st.markdown(f"### {stunden_txt} h")

        st.divider()
        heatmap_jahr_wert = bis.year
        st.subheader(f"Jahres-Heatmap {heatmap_jahr_wert}")
        jahres_eintraege = db.zeiteintraege_laden(
            datum_von=f"{heatmap_jahr_wert}-01-01",
            datum_bis=f"{heatmap_jahr_wert}-12-31")
        matrix = statistik.heatmap_matrix(jahres_eintraege, heatmap_jahr_wert)
        st.plotly_chart(charts.heatmap_jahr(matrix, heatmap_jahr_wert),
                        use_container_width=True)

        st.divider()
        st.subheader("Wochentags-Analyse")
        wochentage = statistik.stunden_pro_wochentag(eintraege, von, bis)
        st.plotly_chart(charts.bar_wochentage(wochentage), use_container_width=True)

        st.divider()
        st.subheader("Trend")
        heute = date.today()
        vormonat_start = (heute.replace(day=1) - timedelta(days=1)).replace(day=1)
        kpi_eintraege = db.zeiteintraege_laden(datum_von=vormonat_start.isoformat(),
                                               datum_bis=heute.isoformat())
        kpi = statistik.monats_kpi(kpi_eintraege, heute)
        delta = kpi["aktuell"] - kpi["vormonat"]
        t1, t2 = st.columns(2)
        t1.metric("Dieser Monat", f"{kpi['aktuell']:.1f}h".replace(".", ","),
                  delta=f"{delta:+.1f}h vs. Vormonat".replace(".", ","))
        t2.metric("Vormonat", f"{kpi['vormonat']:.1f}h".replace(".", ","))
        trend = statistik.wochen_trend(eintraege)
        if trend:
            st.plotly_chart(charts.trend_wochen(trend), use_container_width=True)

        st.divider()
        st.subheader("Tageszeit-Analyse")
        tageszeit = statistik.tageszeit_verteilung(eintraege)
        if tageszeit["mit_startzeit"] > 0:
            st.plotly_chart(charts.bar_tageszeit(tageszeit["verteilung"]),
                            use_container_width=True)
            st.caption(f"Basiert auf {tageszeit['mit_startzeit']} von "
                       f"{tageszeit['gesamt']} Einträgen "
                       f"(nur Timer-Einträge haben eine Startzeit).")
        else:
            st.info("Noch keine Timer-Einträge mit Startzeit im Zeitraum — "
                    "starte den Live-Tracker, um die Tageszeit-Analyse zu füllen.")

        st.divider()
        st.subheader("Streak")
        alle_daten = [e["datum"] for e in db.zeiteintraege_laden()]
        streak = statistik.streak_berechnen(alle_daten)
        s1, s2 = st.columns(2)
        s1.metric("Aktuelle Serie", f"{streak['aktuell']} Tage")
        s2.metric("Längste Serie", f"{streak['laengste']} Tage")
        st.caption("Serie = Tage mit Einträgen in Folge. Wochenenden ohne "
                   "Eintrag unterbrechen nicht, der heutige Tag zählt noch offen.")

        st.divider()
        st.subheader("Projektverteilung")
        st.plotly_chart(charts.donut_projekte(summen), use_container_width=True)


# ============================================================
# PROJEKTE
# ============================================================
elif seite == "Projekte":
    st.header("Projekte verwalten")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Neues Projekt")

        with st.expander("Stundensatz berechnen"):
            k_netto = st.number_input("Wunsch-Nettoeinkommen (EUR/Monat)", min_value=0.0,
                                      value=3000.0, step=100.0, key="k_netto")
            k_tage = st.number_input("Arbeitstage pro Monat", min_value=1, max_value=31,
                                     value=20, step=1, key="k_tage")
            k_nfh = st.number_input("Nicht-fakturierbare Stunden/Tag", min_value=0.0,
                                    max_value=7.5, value=1.0, step=0.5, key="k_nfh")
            k_puffer = st.number_input("Ausfallpuffer (%)", min_value=0, max_value=99,
                                       value=20, step=5, key="k_puffer")
            k_rund = st.selectbox("Rundung", [1, 5, 10], index=1, key="k_rund",
                                  format_func=lambda x: f"auf {x} EUR")
            if st.button("Berechnen", key="k_berechnen"):
                try:
                    roh = stundensatz_berechnen(k_netto, k_tage, k_nfh, k_puffer)
                    st.session_state["k_ergebnis"] = {
                        "roh": roh,
                        "gerundet": auf_naechste_runden(roh, k_rund),
                    }
                except ValueError as e:
                    st.session_state.pop("k_ergebnis", None)
                    st.error(str(e))

            # Ergebnis lebt in session_state, damit der Übernehmen-Button
            # Reruns überdauert (Buttons in Buttons funktionieren nicht)
            k_ergebnis = st.session_state.get("k_ergebnis")
            if k_ergebnis:
                st.info(f"Rohwert: **{k_ergebnis['roh']:.2f} EUR/h** → "
                        f"Gerundet: **{k_ergebnis['gerundet']} EUR/h**")
                if st.button(f"Stundensatz {k_ergebnis['gerundet']} EUR übernehmen",
                             key="k_uebernehmen"):
                    st.session_state["k_vorschlag"] = float(k_ergebnis["gerundet"])
                    st.session_state.pop("k_ergebnis", None)
                    st.rerun()

        with st.form("neues_projekt"):
            p_name = st.text_input("Projektname")
            p_satz_default = st.session_state.pop("k_vorschlag", 80.0)
            p_satz = st.number_input("Stundensatz (EUR)", min_value=0.0,
                                     value=p_satz_default, step=5.0)
            p_kunde = st.text_input("Kunde")
            p_adresse = st.text_area("Kundenadresse", height=80)
            submitted = st.form_submit_button("Projekt anlegen", type="primary")

            if submitted and p_name:
                try:
                    db.projekt_erstellen(p_name, p_satz, p_kunde, p_adresse)
                    st.success(f"Projekt '{p_name}' angelegt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")

    with col2:
        st.subheader("Vorhandene Projekte")
        projekte = db.projekte_laden(nur_aktive=False)
        ziel_jahr = date.today().year
        ziele_map = {z["projekt_id"]: z["stunden_ziel"] for z in db.ziele_laden(ziel_jahr)}

        for p in projekte:
            farbe = p.get("farbe", "#AAAAAA") or "#AAAAAA"
            punkt = f'<span style="color:{farbe}">●</span>'
            with st.expander(f"{'✅' if p['aktiv'] else '❌'} {p['name']} — {p['stundensatz']:.2f} EUR/h"):
                # Farbpicker
                neue_farbe = st.color_picker("Projektfarbe", value=farbe, key=f"farbe_{p['id']}")
                if neue_farbe != farbe:
                    db.projekt_farbe_aktualisieren(p["id"], neue_farbe)
                    st.rerun()
                st.markdown(f"{punkt} Vorschau Farbpunkt", unsafe_allow_html=True)
                st.divider()
                # Jahresziel
                zc1, zc2 = st.columns([3, 1])
                ziel_wert = zc1.number_input(
                    f"Jahresziel {ziel_jahr} (Stunden)", min_value=0.0,
                    value=float(ziele_map.get(p["id"], 0.0)), step=10.0,
                    key=f"ziel_{p['id']}", help="0 = kein Ziel"
                )
                if zc2.button("Ziel speichern", key=f"ziel_save_{p['id']}"):
                    db.ziel_setzen(p["id"], ziel_jahr, ziel_wert)
                    st.rerun()
                st.divider()
                # Unterthemen
                unterthemen = db.unterthemen_laden(p["id"], nur_aktive=False)
                if unterthemen:
                    st.write("**Unterthemen:**")
                    for u in unterthemen:
                        uc1, uc2 = st.columns([4, 1])
                        uc1.write(f"  - {u['name']}")
                        if uc2.button("Entfernen", key=f"del_ut_{u['id']}"):
                            db.unterthema_loeschen(u["id"])
                            st.rerun()

                # Neues Unterthema
                nc1, nc2 = st.columns([3, 1])
                ut_name = nc1.text_input("Neues Unterthema", key=f"ut_input_{p['id']}")
                if nc2.button("Hinzufügen", key=f"add_ut_{p['id']}"):
                    if ut_name:
                        try:
                            db.unterthema_erstellen(p["id"], ut_name)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

                st.divider()
                bc1, bc2 = st.columns(2)
                if p["aktiv"]:
                    if bc1.button("Deaktivieren", key=f"deakt_{p['id']}"):
                        db.projekt_aktualisieren(p["id"], aktiv=0)
                        st.rerun()
                else:
                    if bc1.button("Aktivieren", key=f"akt_{p['id']}"):
                        db.projekt_aktualisieren(p["id"], aktiv=1)
                        st.rerun()
                if bc2.button("Löschen", key=f"del_p_{p['id']}", type="secondary"):
                    st.session_state.loesch_projekt = {"id": p["id"], "name": p["name"]}
                    st.rerun()


# ============================================================
# RECHNUNGEN
# ============================================================
elif seite == "Rechnungen":
    st.header("Rechnungen")

    tab1, tab2 = st.tabs(["Neue Rechnung", "Rechnungsübersicht"])

    with tab1:
        projekte = db.projekte_laden()
        if not projekte:
            st.warning("Bitte zuerst ein Projekt anlegen.")
        else:
            projekt_namen = {p["name"]: p for p in projekte}
            gewaehltes = st.selectbox("Projekt", list(projekt_namen.keys()),
                                       key="re_projekt")
            projekt = projekt_namen[gewaehltes]

            rc1, rc2 = st.columns(2)
            with rc1:
                re_von = st.date_input("Leistungszeitraum von",
                                        value=date.today().replace(day=1), key="re_von")
            with rc2:
                re_bis = st.date_input("Leistungszeitraum bis",
                                        value=date.today(), key="re_bis")

            # Automatische Positionen aus Zeiteinträgen
            eintraege = db.zeiteintraege_laden(
                datum_von=re_von.isoformat(),
                datum_bis=re_bis.isoformat(),
                projekt_id=projekt["id"]
            )

            st.subheader("Positionen")

            if "positionen" not in st.session_state:
                st.session_state.positionen = []

            # Auto-Befüllung aus Zeiteinträgen
            if st.button("Aus Zeiteinträgen befüllen"):
                auto_pos = []
                # Gruppiere nach Unterthema
                gruppen = {}
                for e in eintraege:
                    key = e.get("unterthema_name") or "Allgemein"
                    if key not in gruppen:
                        gruppen[key] = 0.0
                    gruppen[key] += e["stunden"]

                for beschr, stunden in gruppen.items():
                    auto_pos.append({
                        "beschreibung": beschr,
                        "stunden": round(stunden, 2),
                        "stundensatz": projekt["stundensatz"],
                        "betrag": round(stunden * projekt["stundensatz"], 2),
                    })
                st.session_state.positionen = auto_pos
                st.rerun()

            # Manuelle Position hinzufügen
            with st.form("neue_position"):
                pc1, pc2, pc3 = st.columns([3, 1, 1])
                pos_beschr = pc1.text_input("Beschreibung")
                pos_stunden = pc2.number_input("Stunden", min_value=0.0, step=0.25, value=1.0)
                pos_satz = pc3.number_input("Satz (EUR)", min_value=0.0,
                                             value=projekt["stundensatz"], step=5.0)
                if st.form_submit_button("Position hinzufügen"):
                    if pos_beschr:
                        st.session_state.positionen.append({
                            "beschreibung": pos_beschr,
                            "stunden": pos_stunden,
                            "stundensatz": pos_satz,
                            "betrag": round(pos_stunden * pos_satz, 2),
                        })
                        st.rerun()

            # Positionen anzeigen
            if st.session_state.positionen:
                gesamt = 0.0
                for i, pos in enumerate(st.session_state.positionen):
                    pc1, pc2, pc3, pc4 = st.columns([3, 1, 1, 1])
                    pc1.write(pos["beschreibung"])
                    pc2.write(f"{pos['stunden']:.2f}h")
                    pc3.write(f"{pos['stundensatz']:.2f} EUR")
                    pc4.write(f"**{pos['betrag']:.2f} EUR**")
                    gesamt += pos["betrag"]

                st.divider()
                st.markdown(f"### Gesamtbetrag: {gesamt:,.2f} EUR")

                # Kundeninfos
                kunde = st.text_input("Kunde", value=projekt.get("kunde", ""))
                kunde_adresse = st.text_area("Kundenadresse",
                                              value=projekt.get("kunde_adresse", ""), height=80)

                if st.button("Rechnung erstellen & PDF generieren", type="primary",
                             use_container_width=True):
                    firma = db.firmendaten_laden()
                    rechnungsnummer = db.rechnung_erstellen(
                        projekt_id=projekt["id"],
                        kunde=kunde,
                        kunde_adresse=kunde_adresse,
                        datum=date.today().isoformat(),
                        leistungszeitraum_von=re_von.isoformat(),
                        leistungszeitraum_bis=re_bis.isoformat(),
                        positionen_json=json.dumps(st.session_state.positionen),
                        gesamtbetrag=gesamt,
                    )

                    pdf_path = rechnung_als_pdf(
                        rechnungsnummer=rechnungsnummer,
                        firma=firma,
                        kunde=kunde,
                        kunde_adresse=kunde_adresse,
                        datum=date.today().strftime("%d.%m.%Y"),
                        leistungszeitraum_von=re_von.strftime("%d.%m.%Y"),
                        leistungszeitraum_bis=re_bis.strftime("%d.%m.%Y"),
                        positionen=st.session_state.positionen,
                        gesamtbetrag=gesamt,
                    )

                    st.success(f"Rechnung {rechnungsnummer} erstellt!")

                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "PDF herunterladen",
                            data=f.read(),
                            file_name=f"{rechnungsnummer}.pdf",
                            mime="application/pdf",
                        )

                    st.session_state.positionen = []

    with tab2:
        rechnungen = db.rechnungen_laden()
        if rechnungen:
            for r in rechnungen:
                with st.container(border=True):
                    rc1, rc2, rc3, rc4 = st.columns([2, 2, 1, 1])
                    rc1.write(f"**{r['rechnungsnummer']}**")
                    rc2.write(f"{r['kunde']} | {r['projekt_name']}")
                    rc3.write(f"{r['gesamtbetrag']:,.2f} EUR")

                    status_options = ["Entwurf", "Versendet", "Bezahlt", "Storniert"]
                    new_status = rc4.selectbox(
                        "Status", status_options,
                        index=status_options.index(r["status"]),
                        key=f"status_{r['id']}"
                    )
                    if new_status != r["status"]:
                        db.rechnung_status_aendern(r["id"], new_status)
                        st.rerun()

                    pdf_path = Path(__file__).parent / "rechnungen" / f"{r['rechnungsnummer']}.pdf"
                    if pdf_path.exists():
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                "PDF",
                                data=f.read(),
                                file_name=f"{r['rechnungsnummer']}.pdf",
                                mime="application/pdf",
                                key=f"dl_{r['id']}",
                            )
        else:
            st.info("Noch keine Rechnungen erstellt.")


# ============================================================
# EINSTELLUNGEN
# ============================================================
elif seite == "Einstellungen":
    st.header("Firmendaten (Platzhalter)")
    st.caption("Diese Daten erscheinen auf deinen Rechnungen. Passe sie an, sobald du gegründet hast.")

    firma = db.firmendaten_laden()

    with st.form("firmendaten"):
        fc1, fc2 = st.columns(2)
        with fc1:
            firma_name = st.text_input("Firmenname", value=firma.get("firma_name", ""))
            inhaber = st.text_input("Inhaber", value=firma.get("inhaber", ""))
            strasse = st.text_input("Straße", value=firma.get("strasse", ""))
            plz = st.text_input("PLZ", value=firma.get("plz", ""))
            ort = st.text_input("Ort", value=firma.get("ort", ""))
            telefon = st.text_input("Telefon", value=firma.get("telefon", ""))

        with fc2:
            email = st.text_input("E-Mail", value=firma.get("email", ""))
            website = st.text_input("Website", value=firma.get("website", ""))
            steuernummer = st.text_input("Steuernummer", value=firma.get("steuernummer", ""))
            ust_id = st.text_input("USt-IdNr.", value=firma.get("ust_id", ""))
            bank_name = st.text_input("Bank", value=firma.get("bank_name", ""))
            iban = st.text_input("IBAN", value=firma.get("iban", ""))
            bic = st.text_input("BIC", value=firma.get("bic", ""))

        if st.form_submit_button("Speichern", type="primary"):
            db.firmendaten_speichern(
                firma_name=firma_name, inhaber=inhaber, strasse=strasse,
                plz=plz, ort=ort, telefon=telefon, email=email, website=website,
                steuernummer=steuernummer, ust_id=ust_id,
                bank_name=bank_name, iban=iban, bic=bic,
            )
            st.success("Firmendaten gespeichert!")
            st.rerun()
