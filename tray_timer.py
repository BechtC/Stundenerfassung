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

import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

import database as db

# --- Konfiguration ---
POLL_SEKUNDEN = 2            # DB-Abfrage-Intervall
WARN_STUNDEN = 3.0          # ab dieser Laufzeit: rotes Icon + Benachrichtigung
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
APP_URL = "http://localhost:8502"

# Lockfile mit der PID des laufenden Tray-Prozesses (verhindert Mehrfachstart)
_LOCKFILE = Path(__file__).parent / ".tray.pid"

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
        _lockfile_schreiben()
        try:
            self._icon.run(setup=lambda icon: threading.Thread(
                target=self._poll_loop, args=(icon,), daemon=True).start())
        finally:
            _lockfile_entfernen()


# ============================================================
# Autostart-Hilfen (werden von app.py beim App-Start aufgerufen)
# ============================================================

def _pid_laeuft(pid):
    """True, wenn ein Prozess mit dieser PID existiert (Windows)."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        return str(pid) in out
    except Exception:
        return False


def _lockfile_schreiben():
    try:
        _LOCKFILE.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass


def _lockfile_entfernen():
    try:
        _LOCKFILE.unlink(missing_ok=True)
    except Exception:
        pass


def tray_laeuft_bereits():
    """Prüft anhand des Lockfiles, ob schon ein Tray-Prozess aktiv ist.
    Räumt ein verwaistes Lockfile (Prozess tot) selbst auf."""
    if not _LOCKFILE.exists():
        return False
    try:
        pid = int(_LOCKFILE.read_text(encoding="utf-8").strip())
    except Exception:
        _lockfile_entfernen()
        return False
    if _pid_laeuft(pid):
        return True
    _lockfile_entfernen()  # verwaist
    return False


def tray_starten_falls_noetig():
    """Startet die Tray-App als eigenständigen Hintergrundprozess (ohne
    Konsolenfenster), falls noch keine läuft. Idempotent — mehrfacher Aufruf
    (z.B. Streamlit-Reruns) startet nur einmal. Wirft nie eine Exception nach
    außen, damit der App-Start nie blockiert wird."""
    try:
        if tray_laeuft_bereits():
            return False
        skript = str(Path(__file__).resolve())
        # pythonw.exe = Python ohne Konsolenfenster; Fallback auf sys.executable
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        exe = str(pythonw) if pythonw.exists() else sys.executable
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        subprocess.Popen([exe, skript], cwd=str(Path(__file__).parent),
                         creationflags=flags, close_fds=True)
        return True
    except Exception as fehler:
        print(f"WARNUNG: Tray-Autostart fehlgeschlagen: {fehler}")
        return False


if __name__ == "__main__":
    TrayTimer().run()
