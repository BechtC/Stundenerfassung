# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).
Versionsschema: `v<Major>.<Minor>` — Minor für neue Features, Major für grundlegende Umbauten.

## [Unreleased]

## [v1.6] — 2026-07-23

### Hinzugefügt
- **Endzeit-Eingabe im Stopp-Dialog**: Beim Timer-Stoppen kann jetzt die tatsächliche
  Schlusszeit gewählt werden (z. B. 13:00) — die Dauer wird automatisch aus
  Startzeit → Endzeit berechnet. Löst den Fall „Ausstempeln vergessen" ohne Kopfrechnen.
  Über-Mitternacht-Fälle werden korrekt auf den Folgetag gerechnet.
- **Historie vergangener Einträge** auf der Zeiterfassungsseite: aufklappbar nach Tagen
  (neueste oben, mit Tagessummen), filterbar nach Zeitraum-Presets und Projekt.
- **Nachträgliche Bearbeitung** aller Einträge inkl. **Startzeit**, Endzeit, Datum,
  Dauer, Kategorie und Beschreibung — konsistent zum Stopp-Dialog. Manuell erstellte
  Einträge ohne Startzeit bekommen beim Bearbeiten eine nachgetragen.
- CHANGELOG.md eingeführt + Pre-Commit-Hook, der die Changelog-Pflege bei jedem
  Code-Commit erzwingt.

### Geändert
- `timer_stoppen()` akzeptiert optional eine explizite Endzeit; negative Dauern
  werden auf 0 geklemmt.
- `zeiteintrag_aktualisieren()` erlaubt jetzt auch das Feld `startzeit`.

## [v1.5] — 2026-07

### Hinzugefügt
- MagicBento Dark Theme mit Türkis-Akzent (Glow, Spotlight, Tilt).
- Charts auf Bento-Dark-Theme umgestellt (plotly_dark, Türkis-Palette).

### Behoben
- Sidebar-Selektor elementneutral (section statt div in Streamlit).

## [v1.4] — 2026-07

### Hinzugefügt
- Schwebendes Always-on-Top Timer-Overlay (groß, rot, unübersehbar) mit
  merkbarer Position (Drag & Drop).
- Tray-App im Windows-Infobereich, startet automatisch mit der Stundenerfassung.
- Timer-Dauer im Stopp-Dialog korrigierbar; Tab-Titel zeigt laufenden Timer.

### Behoben
- Doppelstart-Schutz — nur ein Overlay/Tray-Prozess gleichzeitig.

## [v1.3] — 2026-06/07

### Hinzugefügt
- Statistik-Seite: Jahres-Counter, Zielfortschritt, Projekt-Donut (#27),
  Jahres-Heatmap im GitHub-Stil (#28), Wochentags-Analyse (#29),
  Wochen-Trend mit 4-Wochen-Schnitt + Monats-KPIs (#30),
  Tageszeit-Analyse aus Timer-Startzeiten (#31), Streak-Counter werktags-basiert (#32).
- Automatisches Tagesbackup der DB beim App-Start, 30 Tage Retention (#33).
- Projekt-Löschschutz: Bestätigungs-Dialog, Kaskade, Rechnungs-Sperre (#35).

### Behoben
- Kalkulator-Übernehmen-Button überlebt Streamlit-Reruns (#34).

## [v1.2] — 2026-06

### Hinzugefügt
- Farbkodierung für Projekte: Farbpicker, Farbpunkte in Liste, Sidebar und
  Recently-Used (#11, #12).
- CSV-Export im Dashboard (#9) und PDF-Monatsexport (#13).
- Stundensatz-Kalkulator auf der Projekte-Seite (#10).
- Jahresziele pro Projekt mit Pflege-UI (#25).
- Plotly-Charts mit Projektfarben + Zeitraum-Presets im Dashboard (#26).

## [v1.1] — 2026-06

### Hinzugefügt
- Live-Tracker: DB-Schicht mit Migration, `timer_starten`/`timer_stoppen`,
  Recently-Used, laufender Timer (#1, #2).
- Live-Tracker UI: Sidebar, JS-Uhr, Stopp-Dialog, Reload-Resistenz (#3–#6).
- Agent-Workflow-Setup: CONTEXT.md, Issue-Tracker, Domain-Docs.

## [v1.0] — 2026-06

### Hinzugefügt
- Initiale Version: Streamlit-App mit 5 Seiten (Zeiterfassung, Dashboard,
  Projekte, Rechnungen, Einstellungen), SQLite-Backend, PDF-Rechnungen
  mit Kleinunternehmerregelung (§19 UStG), Testdaten-Generator.
