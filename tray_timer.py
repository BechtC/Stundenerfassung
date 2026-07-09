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

# Merkt sich die zuletzt gewählte Overlay-Position (Drag & Drop bleibt erhalten)
_POSFILE = Path(__file__).parent / ".overlay_pos.json"

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
        self._overlay = None   # wird von main() gesetzt (zum Mitbeenden)
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
        if self._overlay:
            self._overlay.beenden()
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

    def run_detached(self):
        """Startet nur das Tray-Icon (pystray) im aktuellen Thread.
        Das Overlay-Fenster läuft separat im Hauptthread (siehe main())."""
        self._icon.run(setup=lambda icon: threading.Thread(
            target=self._poll_loop, args=(icon,), daemon=True).start())

    def stop(self):
        try:
            self._icon.stop()
        except Exception:
            pass


# ============================================================
# Schwebendes Overlay-Fenster (Always-on-Top, groß, unübersehbar)
# ============================================================

class OverlayFenster:
    """Ein randloses, immer im Vordergrund schwebendes Fenster, das den
    laufenden Timer groß und farbig anzeigt (Timer + Projektname). Sichtbar
    nur solange ein Timer läuft. Mit der Maus frei verschiebbar; Klick auf
    'Stoppen' bucht den Eintrag. tkinter läuft im Hauptthread."""

    def __init__(self, on_stop=None, on_beenden=None):
        import tkinter as tk
        self._tk = tk
        self._on_stop = on_stop            # Callback: Timer stoppen
        self._on_beenden = on_beenden      # Callback: ganze App beenden
        self._drag = {"x": 0, "y": 0}

        self.root = tk.Tk()
        self.root.overrideredirect(True)          # randlos, keine Titelleiste
        self.root.attributes("-topmost", True)    # immer im Vordergrund
        self.root.attributes("-alpha", 0.95)
        # Startposition: gespeicherte Position, sonst oben rechts als Default
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        pos = self._position_laden()
        if pos:
            self.root.geometry(f"300x92+{pos[0]}+{pos[1]}")
        else:
            self.root.geometry(f"300x92+{sw - 320}+20")

        self._rahmen = tk.Frame(self.root, bg="#c0392b", bd=0,
                                highlightthickness=3, highlightbackground="#ffffff")
        self._rahmen.pack(fill="both", expand=True)

        self._projekt_label = tk.Label(
            self._rahmen, text="", bg="#c0392b", fg="#ffffff",
            font=("Segoe UI", 11, "bold"), anchor="w")
        self._projekt_label.pack(fill="x", padx=12, pady=(8, 0))

        self._timer_label = tk.Label(
            self._rahmen, text="00:00:00", bg="#c0392b", fg="#ffffff",
            font=("Consolas", 30, "bold"))
        self._timer_label.pack(fill="x", padx=12)

        # Stoppen-Button (klein, unten rechts im Overlay)
        self._stop_btn = tk.Label(
            self._rahmen, text="■ Stoppen", bg="#7d241a", fg="#ffffff",
            font=("Segoe UI", 9, "bold"), cursor="hand2", padx=8, pady=2)
        self._stop_btn.place(relx=1.0, rely=1.0, anchor="se", x=-6, y=-6)
        self._stop_btn.bind("<Button-1>", self._stop_geklickt)

        # Verschieben per Drag auf Rahmen/Labels; Position beim Loslassen merken
        for w in (self._rahmen, self._projekt_label, self._timer_label):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<ButtonRelease-1>", self._drag_ende)

        self.root.withdraw()   # startet versteckt (nur zeigen wenn Timer läuft)
        self._sichtbar = False
        self._beendet = False

    # --- Fenster verschieben ---
    def _drag_start(self, event):
        self._drag["x"] = event.x
        self._drag["y"] = event.y

    def _drag_move(self, event):
        x = self.root.winfo_x() + (event.x - self._drag["x"])
        y = self.root.winfo_y() + (event.y - self._drag["y"])
        self.root.geometry(f"+{x}+{y}")

    def _drag_ende(self, event):
        # gewählte Position dauerhaft merken (überlebt Stopp/App-Neustart)
        self._position_speichern(self.root.winfo_x(), self.root.winfo_y())

    # --- Positions-Persistenz ---
    def _position_laden(self):
        try:
            import json
            daten = json.loads(_POSFILE.read_text(encoding="utf-8"))
            return int(daten["x"]), int(daten["y"])
        except Exception:
            return None

    def _position_speichern(self, x, y):
        try:
            import json
            _POSFILE.write_text(json.dumps({"x": x, "y": y}), encoding="utf-8")
        except Exception:
            pass

    def _stop_geklickt(self, event):
        if self._on_stop:
            self._on_stop()

    # --- periodische Aktualisierung aus der DB (im Hauptthread via after) ---
    def _aktualisieren(self):
        try:
            laufender = _laufenden_timer()
            if laufender:
                sek = _laufzeit_sekunden(laufender)
                label = laufender.get("projekt_name", "?")
                if laufender.get("unterthema_name"):
                    label += f" › {laufender['unterthema_name']}"
                self._projekt_label.config(text="⏱ " + label)
                self._timer_label.config(text=_format_hms(sek))
                # Farbe: ab WARN_STUNDEN dunkler/dringlicher blinken
                if sek >= WARN_STUNDEN * 3600:
                    # blinken zwischen zwei Rottönen
                    blink = (sek % 2 == 0)
                    farbe = "#e74c3c" if blink else "#7d241a"
                else:
                    farbe = "#c0392b"
                self._rahmen.config(bg=farbe)
                self._projekt_label.config(bg=farbe)
                self._timer_label.config(bg=farbe)
                if not self._sichtbar:
                    self.root.deiconify()
                    self.root.attributes("-topmost", True)
                    self._sichtbar = True
            else:
                if self._sichtbar:
                    self.root.withdraw()
                    self._sichtbar = False
        except Exception:
            pass
        if not self._beendet:
            self.root.after(1000, self._aktualisieren)

    def run(self):
        self._aktualisieren()
        self.root.mainloop()

    def beenden(self):
        self._beendet = True
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass


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


def main():
    """Startet Overlay-Fenster (Hauptthread) + Tray-Icon (Nebenthread)."""
    # Selbstschutz: Läuft bereits ein anderer, lebender Tray-Prozess, sofort
    # beenden — verhindert ein zweites Overlay/Icon (auch bei Start-Race).
    if tray_laeuft_bereits():
        return
    _lockfile_schreiben()
    tray = TrayTimer()

    def stop_timer():
        # aus dem Overlay heraus stoppen (nutzt dieselbe Logik wie das Tray-Menü)
        laufender = _laufenden_timer()
        if not laufender:
            return
        try:
            db.timer_stoppen(laufender["id"],
                             beschreibung=laufender.get("beschreibung", "") or "")
            tray._warnung_gesendet = False
        except Exception:
            pass

    overlay = OverlayFenster(on_stop=stop_timer)
    tray._overlay = overlay

    # Tray-Icon im Hintergrund-Thread (pystray)
    tray_thread = threading.Thread(target=tray.run_detached, daemon=True)
    tray_thread.start()

    try:
        overlay.run()          # blockiert im Hauptthread bis Fenster zerstört
    finally:
        tray.stop()
        _lockfile_entfernen()


if __name__ == "__main__":
    main()
