# Spec: Statistik-Seite, Plotly-Charts, Löschschutz & Backup

**Datum:** 2026-07-04
**Status:** Beschlossen (via /grill-me Interview)

## Ziel

Das Hauptziel des Tools — „Wie viel Zeit habe ich dieses Jahr in Projekt X (z.B. AI Learning) investiert?" — sichtbar machen. Dazu: neue Statistik-Seite mit Jahresbilanz, Wochentags-/Tageszeit-Analysen und Motivation (Streak, Ziele), plus Bugfixes und Datensicherung.

## Entscheidungen (aus dem Interview)

| Frage | Entscheidung |
|---|---|
| Platzierung | Neue 6. Seite „Statistik"; Dashboard bleibt operativer Monatsüberblick |
| Jahresziele | Ja, pro Projekt **und** Jahr (neue Tabelle `ziele`), Pflege im Projekt-Expander |
| Streak-Regel | Werktags-basiert: Sa/So ohne Eintrag bricht die Serie nicht; Wochenend-Einträge zählen mit |
| Tageszeit-Analyse | Nur Timer-Einträge (mit `startzeit`), Hinweis „basiert auf X von Y Einträgen" |
| Plotly-Scope | Alle Charts, auch die bestehenden Dashboard-Charts werden migriert |
| Zeitraum | Gemeinsame Preset-Komponente (Woche/Monat/Quartal/Jahr/Alles + Von/Bis). Statistik-Default: Dieses Jahr. Dashboard-Default: Dieser Monat |
| Projekt löschen | Bestätigungs-Dialog + Kaskade (Zeiteinträge, Unterthemen). **Rechnungen blockieren das Löschen** — dann nur Deaktivieren |
| Backup | Automatisch beim App-Start, 1×/Tag, `backups/`, Retention 30 Tage |

## Verhalten

### Neue Seite „Statistik"

Sidebar-Navigation bekommt den Punkt „Statistik" (zwischen Dashboard und Projekte). Oben die Zeitraum-Presets, Default „Dieses Jahr". Darunter, in dieser Reihenfolge:

1. **Jahres-Counter pro Projekt** — Kacheln je Projekt mit Stunden im Zeitraum (sortiert absteigend, nur Projekte mit > 0h). Existiert für das Jahr ein Ziel: Fortschrittsbalken + „312,5 / 300 h (104 %)". Ohne Ziel: nur der Stundenwert.
2. **Jahres-Heatmap** — GitHub-Style-Kalender (53 Wochen × 7 Tage, Plotly-Heatmap). Farbintensität = Gesamtstunden des Tages, einfarbige Skala (weiß → dunkelgrün), Tooltip mit Datum + Stunden. Gezeigt wird das Kalenderjahr des „Bis"-Datums des gewählten Zeitraums.
3. **Wochentags-Analyse** — Balken Mo–So: Ø Stunden pro Wochentag = Summe der Stunden an diesem Wochentag ÷ Anzahl dieses Wochentags im Zeitraum (Nulltage zählen mit). Tooltip zeigt zusätzlich die Summe.
4. **Trend** — Wochensummen (ISO-Wochen) als Balken + gleitender 4-Wochen-Schnitt als Linie. Darüber KPI-Zeile: aktueller Monat vs. Vormonat als `st.metric` mit Delta.
5. **Tageszeit-Analyse** — Histogramm der Startstunden (0–23 Uhr) aus Timer-Einträgen, gewichtet nach Dauer. Caption: „basiert auf X von Y Einträgen (nur Timer-Einträge haben eine Startzeit)".
6. **Streak-Counter** — zwei Metriken: „Aktuelle Serie" und „Längste Serie" (in Werktagen). Regel: Serie läuft, solange kein **Werktag** komplett ohne Eintrag vergangen ist. Der heutige Tag bricht die Serie nicht, solange er nicht vorbei ist. Einträge am Wochenende verlängern die Serie.
7. **Projektverteilung** — Donut-Chart der Stunden pro Projekt in Projektfarben.

### Zeitraum-Presets (gemeinsame Komponente)

Buttons: „Diese Woche · Dieser Monat · Dieses Quartal · Dieses Jahr · Alles" + weiterhin freie Von/Bis-Datumsfelder. Preset-Klick setzt Von/Bis. Wird auf Statistik **und** Dashboard eingesetzt (unterschiedliche Defaults, siehe oben).

### Plotly-Migration Dashboard

- „Stunden pro Projekt" → Plotly-Bar in Projektfarben
- „Stunden pro Kategorie" → Plotly-Bar
- „Tagesverlauf" → Plotly-Linie, **Lücken-Korrektur**: Tage ohne Eintrag erscheinen als 0 statt übersprungen zu werden
- `st.bar_chart`/`st.line_chart` verschwinden vollständig

### Jahresziele

Im Projekt-Expander (Projekte-Seite): Zahlenfeld „Jahresziel {aktuelles Jahr} (Stunden)" + Speichern. 0 oder leer = kein Ziel. Ziele vergangener Jahre bleiben in der DB erhalten (historischer Vergleich möglich).

### Projekt löschen (Umbau)

- Klick auf „Löschen" öffnet `st.dialog`:
  - Projekt hat **Rechnungen** → kein Löschen möglich. Text: „Projekt hat N Rechnungen — Belege müssen erhalten bleiben. Bitte deaktivieren." Nur Buttons „Deaktivieren" / „Abbrechen".
  - Sonst → Text: „Löscht das Projekt mit N Zeiteinträgen und M Unterthemen unwiderruflich." Buttons „Endgültig löschen" / „Abbrechen".
- Kaskade explizit in einer Transaktion: erst `zeiteintraege`, dann `projekte` (Unterthemen cascaden per FK). Hintergrund: `zeiteintraege.projekt_id` hat keinen `ON DELETE CASCADE` — aktuell crasht das Löschen mit IntegrityError.

### Kalkulator-Bugfix

`app.py:438-445`: verschachtelte Buttons („Berechnen" → „übernehmen") funktionieren in Streamlit nicht — der innere Button verpufft beim Rerun. Fix: Berechnungsergebnis in `st.session_state["k_ergebnis"]` halten; der Übernehmen-Button wird außerhalb des Berechnen-Blocks gerendert, solange ein Ergebnis vorliegt.

### Backup

Beim App-Start (in `app.py` nach `db.init_db()`): existiert `backups/stundenerfassung_{YYYY-MM-DD}.db` für heute nicht, wird die DB dorthin kopiert (`sqlite3` Backup-API oder Datei-Copy bei geschlossener Verbindung); danach werden Backups älter als 30 Tage gelöscht. `backups/` kommt in `.gitignore`. Fehler beim Backup dürfen den App-Start nicht verhindern (Warnung loggen, weiterlaufen).

## DB-Änderungen

```sql
CREATE TABLE IF NOT EXISTS ziele (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    projekt_id INTEGER NOT NULL,
    jahr INTEGER NOT NULL,
    stunden_ziel REAL NOT NULL,
    FOREIGN KEY (projekt_id) REFERENCES projekte(id) ON DELETE CASCADE,
    UNIQUE(projekt_id, jahr)
);
```

Neue/geänderte Funktionen in `database.py`:
- `ziel_setzen(projekt_id, jahr, stunden_ziel)` — Upsert; `stunden_ziel <= 0` löscht das Ziel
- `ziele_laden(jahr)` — Liste `{projekt_id, stunden_ziel}`
- `projekt_statistik(projekt_id)` — Anzahl Zeiteinträge, Unterthemen, Rechnungen (für den Lösch-Dialog)
- `projekt_loeschen(projekt_id)` — wirft `ValueError` bei vorhandenen Rechnungen; löscht sonst Zeiteinträge + Projekt in einer Transaktion
- `backup_erstellen(ziel_ordner, retention_tage=30)` — idempotent pro Tag

## Neue Module (Architektur)

- **`statistik.py`** — reine Berechnungsfunktionen ohne DB/Streamlit (gut testbar): `stunden_pro_wochentag(eintraege, von, bis)`, `wochen_trend(eintraege)`, `streak_berechnen(datums_liste, heute)`, `heatmap_matrix(eintraege, jahr)`, `tageszeit_verteilung(eintraege)`
- **`charts.py`** — Plotly-Figure-Builder: `bar_projekte(...)`, `bar_kategorien(...)`, `linie_tagesverlauf(...)`, `heatmap_jahr(...)`, `donut_projekte(...)`, `trend_wochen(...)`. Projektfarben aus `projekte.farbe`, Fallback `#AAAAAA`
- `app.py` ruft nur DB → statistik → charts auf, bleibt dünn

Neue Dependency: `plotly>=5.0.0` in `requirements.txt`.

## Randfälle

- Zeitraum ohne Einträge → jede Sektion zeigt `st.info`, kein Crash
- Zeitraum über Jahresgrenze → Heatmap zeigt das Jahr des Bis-Datums
- Projekt ohne Farbe (`NULL`) → Fallback-Grau
- Ziel vorhanden, aber 0 Stunden erfasst → Fortschrittsbalken bei 0 %
- Übererfüllung (> 100 %) → Balken voll, Prozentwert läuft weiter („104 %")
- `startzeit` bei allen Einträgen leer → Tageszeit-Sektion zeigt nur Hinweis
- Streak: erster Eintrag überhaupt = Serie 1; Feiertage gelten als normale Werktage (bewusst simpel)
- ISO-Woche 53 / Jahreswechsel im Trend korrekt via `isocalendar()`
- Backup: DB-Datei gesperrt/Kopie schlägt fehl → Warnung, App startet trotzdem

## Tests (tests/, In-Memory SQLite bzw. pure functions)

- `ziele`-CRUD inkl. Upsert und Löschung bei `<= 0`
- `projekt_loeschen`: blockiert bei Rechnungen, kaskadiert Zeiteinträge, Transaktions-Rollback bei Fehler
- `streak_berechnen`: Wochenend-Überbrückung, Bruch durch leeren Werktag, heutiger Tag offen, leere Liste
- `stunden_pro_wochentag`: Nulltage im Nenner, Zeitraum kürzer als eine Woche
- `heatmap_matrix`: Jahresgrenzen, Schaltjahr
- `wochen_trend`: gleitender Schnitt mit < 4 Wochen Daten
- `backup_erstellen`: legt an, ist idempotent pro Tag, räumt alte Dateien auf (tmp-Verzeichnis)

## Umsetzungsreihenfolge (für /to-issues, von unten nach oben)

1. DB: `ziele`-Tabelle + CRUD + `projekt_statistik` + neues `projekt_loeschen` (mit Tests)
2. `backup_erstellen` + Einbindung App-Start + .gitignore
3. `statistik.py` mit allen Berechnungsfunktionen (mit Tests)
4. `charts.py` + Plotly-Dependency
5. Zeitraum-Preset-Komponente + Dashboard-Migration auf Plotly (inkl. Lücken-Korrektur)
6. Statistik-Seite (Sektionen 1–7)
7. Ziele-Pflege-UI im Projekt-Expander
8. Lösch-Dialog UI
9. Kalkulator-Bugfix
