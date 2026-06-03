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
from rechnung_pdf import rechnung_als_pdf

# --- Init ---
db.init_db()

st.set_page_config(
    page_title="Stundenerfassung",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stMetric { background: #f8f9fa; padding: 15px; border-radius: 8px; }
    div[data-testid="stSidebar"] { background: #1a1a2e; }
    div[data-testid="stSidebar"] .stMarkdown { color: #e0e0e0; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
st.sidebar.title("Stundenerfassung")
seite = st.sidebar.radio("Navigation", [
    "Zeiterfassung",
    "Dashboard",
    "Projekte",
    "Rechnungen",
    "Einstellungen",
])

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
        st.subheader("Heutige Einträge")
        heute = date.today().isoformat()
        eintraege = db.zeiteintraege_laden(datum_von=heute, datum_bis=heute)

        if eintraege:
            gesamt = sum(e["stunden"] for e in eintraege)
            st.metric("Heute gesamt", f"{gesamt:.2f} Stunden")

            for e in eintraege:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                    c1.write(f"**{e['projekt_name']}**" +
                             (f" > {e['unterthema_name']}" if e.get("unterthema_name") else ""))
                    c2.write(e.get("beschreibung", ""))
                    c3.write(f"{e['stunden']:.2f}h")
                    if c4.button("X", key=f"del_{e['id']}"):
                        db.zeiteintrag_loeschen(e["id"])
                        st.rerun()
        else:
            st.info("Noch keine Einträge heute.")

        st.divider()
        st.subheader("Letzte 7 Tage")
        vor_7_tagen = (date.today() - timedelta(days=7)).isoformat()
        letzte_woche = db.zeiteintraege_laden(datum_von=vor_7_tagen)
        if letzte_woche:
            df = pd.DataFrame(letzte_woche)
            df_grouped = df.groupby("datum")["stunden"].sum().reset_index()
            st.bar_chart(df_grouped.set_index("datum"))


# ============================================================
# DASHBOARD
# ============================================================
elif seite == "Dashboard":
    st.header("Dashboard")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        von = st.date_input("Von", value=date.today().replace(day=1))
    with col_filter2:
        bis = st.date_input("Bis", value=date.today())

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
                df_p = pd.DataFrame(stats_projekt)
                st.bar_chart(df_p.set_index("projekt")["gesamt_stunden"])

        with col_chart2:
            st.subheader("Stunden pro Kategorie")
            stats_kat = db.statistik_pro_kategorie(von_str, bis_str)
            if stats_kat:
                df_k = pd.DataFrame(stats_kat)
                st.bar_chart(df_k.set_index("kategorie")["gesamt_stunden"])

        st.divider()
        st.subheader("Tagesverlauf")
        tage_stats = db.stunden_pro_tag(von_str, bis_str)
        if tage_stats:
            df_t = pd.DataFrame(tage_stats)
            st.line_chart(df_t.set_index("datum")["gesamt_stunden"])

        st.divider()
        st.subheader("Alle Einträge")
        df_all = pd.DataFrame(eintraege)
        anzeige_spalten = ["datum", "projekt_name", "unterthema_name", "stunden",
                           "kategorie", "beschreibung"]
        vorhandene = [s for s in anzeige_spalten if s in df_all.columns]
        st.dataframe(df_all[vorhandene], use_container_width=True, hide_index=True)
    else:
        st.info("Keine Einträge im gewählten Zeitraum.")


# ============================================================
# PROJEKTE
# ============================================================
elif seite == "Projekte":
    st.header("Projekte verwalten")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Neues Projekt")
        with st.form("neues_projekt"):
            p_name = st.text_input("Projektname")
            p_satz = st.number_input("Stundensatz (EUR)", min_value=0.0, value=80.0, step=5.0)
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

        for p in projekte:
            with st.expander(f"{'✅' if p['aktiv'] else '❌'} {p['name']} — {p['stundensatz']:.2f} EUR/h"):
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
                    db.projekt_loeschen(p["id"])
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
