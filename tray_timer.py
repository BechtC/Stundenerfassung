"""Windows-Tray-App für den Live-Timer der Stundenerfassung.

Läuft eigenständig im Infobereich (System Tray) und pollt dieselbe SQLite-DB
wie die Streamlit-App. Zeigt den laufenden Timer an, kann ihn stoppen und warnt,
wenn er verdächtig lange läuft (vergessen zu stoppen) — auch bei geschlossenem
Streamlit-Fenster.

Start:  py tray_timer.py        (mit Konsole)
        pythonw tray_timer.py   (ohne Konsole, für Autostart)

Grundprinzip: Die DB ist die einzige Wahrheitsquelle. Tray-App und Streamlit
teilen sich den status='laufend'-Datensatz in zeiteintraege.
"""

import subprocess
import threading
import time
from datetime import datetime

from PIL import Image, ImageDraw
import pystray

import database as db

# --- Konfiguration ---
POLL_SEKUNDEN = 2            # DB-Abfrage-Intervall
WARN_STUNDEN = 3.0          # ab dieser Laufzeit: rotes Icon + Benachrichtigung
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
APP_URL = "http://localhost:8502"

# --- Farben für das Icon ---
_GRAU = (140, 140, 140)
_GRUEN = (46, 160, 67)
_ROT = (200, 60, 60)


def _icon_bild(farbe):
    """Erzeugt ein einfaches rundes Tray-Icon in der gegebenen Farbe."""
    groesse = 64
    bild = Image.new("RGBA", (groesse, groesse), (0, 0, 0, 0))
    zeichnen = ImageDraw.Draw(bild)
    zeichnen.ellipse([6, 6, groesse - 6, groesse - 6], fill=farbe)
    # kleine Uhrzeiger-Andeutung
    zeichnen.line([groesse // 2, groesse // 2, groesse // 2, 18], fill="white", width=4)
    zeichnen.line([groesse // 2, groesse // 2, 44, groesse // 2], fill="white", width=4)
    return bild


# vorab gerenderte Icons (Icon-Wechsel ist teuer, daher cachen)
_ICONS = {"grau": _icon_bild(_GRAU),
          "gruen": _icon_bild(_GRUEN),
          "rot": _icon_bild(_ROT)}


def _laufenden_timer():
    """Liest den laufenden Timer robust aus der DB (None bei Fehler/keiner)."""
    try:
        return db.laufenden_timer_laden()
    except Exception:
        # DB evtl. kurz durch Streamlit gesperrt — still weiterpollen
        return None


def _laufzeit_sekunden(laufender):
    try:
        start = datetime.fromisoformat(laufender["startzeit"])
        return int((datetime.now() - start).total_seconds())
    except Exception:
        return 0


def _format_hms(sekunden):
    h, rest = divmod(max(sekunden, 0), 3600)
    m, s = divmod(rest, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class TrayTimer:
    def __init__(self):
        self._warnung_gesendet = False
        self._icon = pystray.Icon(
            "stundenerfassung",
            icon=_ICONS["grau"],
            title="Stundenerfassung — kein Timer",
            menu=pystray.Menu(
                pystray.MenuItem(self._status_text, None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Stoppen (jetzt buchen)", self._stoppen,
                                 enabled=self._timer_laeuft),
                pystray.MenuItem("App öffnen", self._app_oeffnen),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Beenden", self._beenden),
            ),
        )

    # --- Menü-Callables (werden bei jedem Öffnen neu evaluiert) ---
    def _status_text(self, item):
        laufender = _laufenden_timer()
        if not laufender:
            return "Kein Timer aktiv"
        label = laufender.get("projekt_name", "?")
        if laufender.get("unterthema_name"):
            label += f" › {laufender['unterthema_name']}"
        return f"⏱ {label} ({_format_hms(_laufzeit_sekunden(laufender))})"

    def _timer_laeuft(self, item):
        return _laufenden_timer() is not None

    # --- Aktionen ---
    def _stoppen(self, icon, item):
        laufender = _laufenden_timer()
        if not laufender:
            return
        try:
            db.timer_stoppen(laufender["id"],
                             beschreibung=laufender.get("beschreibung", "") or "")
            self._warnung_gesendet = False
            icon.notify("Timer gestoppt und gebucht.", "Stundenerfassung")
        except Exception:
            icon.notify("Stoppen fehlgeschlagen (DB gesperrt?).", "Stundenerfassung")

    def _app_oeffnen(self, icon, item):
        try:
            subprocess.Popen([CHROME, f"--app={APP_URL}"])
        except Exception:
            # Fallback: Standardbrowser
            import webbrowser
            webbrowser.open(APP_URL)

    def _beenden(self, icon, item):
        icon.stop()

    # --- Poll-Schleife (eigener Thread) ---
    def _poll_loop(self, icon):
        icon.visible = True
        while True:
            laufender = _laufenden_timer()
            if laufender:
                sek = _laufzeit_sekunden(laufender)
                label = laufender.get("projekt_name", "?")
                icon.title = f"⏱ {_format_hms(sek)} · {label}"
                if sek >= WARN_STUNDEN * 3600:
                    icon.icon = _ICONS["rot"]
                    if not self._warnung_gesendet:
                        icon.notify(
                            f"Timer läuft seit {sek // 3600}h — vergessen zu stoppen?",
                            "Stundenerfassung",
                        )
                        self._warnung_gesendet = True
                else:
                    icon.icon = _ICONS["gruen"]
            else:
                icon.title = "Stundenerfassung — kein Timer"
                icon.icon = _ICONS["grau"]
                self._warnung_gesendet = False

            # Menü neu zeichnen, damit der Zähler im geöffneten Menü mitläuft
            try:
                icon.update_menu()
            except Exception:
                pass
            time.sleep(POLL_SEKUNDEN)

    def run(self):
        self._icon.run(setup=lambda icon: threading.Thread(
            target=self._poll_loop, args=(icon,), daemon=True).start())


if __name__ == "__main__":
    TrayTimer().run()
