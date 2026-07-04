"""
Zeitraum-Presets für Dashboard und Statistik.
Reine Datumslogik plus wiederverwendbare Streamlit-Komponente.
"""

from datetime import date, timedelta


PRESETS = ["Diese Woche", "Dieser Monat", "Dieses Quartal", "Dieses Jahr", "Alles"]


def preset_zeitraum(preset, heute=None):
    """Liefert (von, bis) für ein Preset. 'Alles' liefert (None, None)."""
    heute = heute or date.today()
    if preset == "Diese Woche":
        return heute - timedelta(days=heute.weekday()), heute
    if preset == "Dieser Monat":
        return heute.replace(day=1), heute
    if preset == "Dieses Quartal":
        quartal_monat = 3 * ((heute.month - 1) // 3) + 1
        return heute.replace(month=quartal_monat, day=1), heute
    if preset == "Dieses Jahr":
        return heute.replace(month=1, day=1), heute
    if preset == "Alles":
        return None, None
    raise ValueError(f"Unbekanntes Preset: {preset}")


# Untere Grenze für das Preset "Alles" (vor allen realen Einträgen)
ALLES_START = date(2020, 1, 1)


def zeitraum_waehlen(key_prefix, default_preset="Dieser Monat"):
    """Streamlit-Komponente: Preset-Buttons + Von/Bis-Felder. Gibt (von, bis) zurück."""
    import streamlit as st

    von_key, bis_key = f"{key_prefix}_von", f"{key_prefix}_bis"
    if von_key not in st.session_state:
        v, b = preset_zeitraum(default_preset)
        st.session_state[von_key] = v
        st.session_state[bis_key] = b

    cols = st.columns(len(PRESETS))
    for col, preset in zip(cols, PRESETS):
        if col.button(preset, key=f"{key_prefix}_{preset}", use_container_width=True):
            v, b = preset_zeitraum(preset)
            st.session_state[von_key] = v or ALLES_START
            st.session_state[bis_key] = b or date.today()

    c1, c2 = st.columns(2)
    von = c1.date_input("Von", key=von_key)
    bis = c2.date_input("Bis", key=bis_key)
    return von, bis
