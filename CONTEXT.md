# CONTEXT.md — Stundenerfassung

Persönliches Stundenerfassungs- und Rechnungsstellungs-Tool. Solo-Nutzer (Christian Becht). Streamlit-Web-App, läuft lokal im Chrome App-Mode auf Port 8502.

## Domain Language

| Begriff | Bedeutung |
|---------|-----------|
| **Zeiteintrag** | Ein gebuchter Arbeitsblock: Datum, Projekt, optionales Unterthema, Stunden, Kategorie, Beschreibung |
| **Projekt** | Auftraggeber-Kontext mit Stundensatz (EUR/h) und Kundendaten. Kann aktiv oder inaktiv sein. |
| **Unterthema** | Optionale Unterebene eines Projekts (z.B. "Backend", "Meetings") |
| **Stundensatz** | EUR pro Stunde, am Projekt hinterlegt. Wird beim Zeiteintrag eingefroren. |
| **Kategorie** | Art der Tätigkeit (definiert in `database.KATEGORIEN`, z.B. "Entwicklung", "Beratung") |
| **Rechnung** | PDF-Dokument aus gruppierten Zeiteinträgen. Format: `RE-{JAHR}-{NNNN}` |
| **Position** | Eine Zeile in einer Rechnung (Beschreibung, Stunden, Stundensatz, Betrag) |
| **Firmendaten** | Singleton-Datensatz (id=1) mit Absenderinfos für Rechnungs-PDFs |
| **Kleinunternehmerregelung** | §19 UStG — keine Umsatzsteuer auf Rechnungen (Default) |
| **Live-Tracker** | Geplantes Feature: Echtzeit-Stoppuhr in der Sidebar zum minutengenauen Erfassen |
| **Laufender Eintrag** | Zeiteintrag mit `status='laufend'` — aktiver Timer, noch nicht abgeschlossen |

## Architektur

- **`app.py`** — Streamlit-Hauptanwendung, 5 Seiten: Zeiterfassung, Dashboard, Projekte, Rechnungen, Einstellungen
- **`database.py`** — Einziger DB-Zugangspunkt. Context Manager `get_connection()`. 5 Tabellen: `projekte`, `unterthemen`, `zeiteintraege`, `rechnungen`, `firmen_daten`
- **`rechnung_pdf.py`** — PDF-Generierung via ReportLab. Ausgabe nach `rechnungen/`

## Technische Randbedingungen

- Port **8502** (8501 belegt durch Trading Risk App)
- SQLite-Datei: `stundenerfassung.db` (gitignored — enthält persönliche Daten)
- Beträge: deutsches Format (Punkt als Tausender, Komma als Dezimal)
- Rechnungs-PDFs: gitignored — enthält persönliche Kundendaten
- `CLAUDE.local.md`: gitignored — persönliche Overrides

## Aktuelle DB-Tabellen

```
projekte        — id, name, stundensatz, kunde, kunde_adresse, aktiv
unterthemen     — id, projekt_id, name, aktiv
zeiteintraege   — id, datum, projekt_id, unterthema_id, stunden, kategorie, beschreibung, status, startzeit
rechnungen      — id, rechnungsnummer, projekt_id, kunde, gesamtbetrag, status, datum, ...
firmen_daten    — id=1 (Singleton), firma_name, inhaber, strasse, plz, ort, email, iban, ...
```

## Entwicklungs-Workflow (MattPocock Skills)

Jede neue Feature-Entwicklung folgt diesem Ablauf:

```
/grill-me        → Anforderungen klären (eine Frage nach der anderen)
                   Ergebnis: gemeinsames Verständnis was gebaut wird

Spec schreiben   → docs/superpowers/specs/YYYY-MM-DD-<thema>-design.md
                   Enthält: Verhalten, DB-Änderungen, technische Umsetzung, Randfälle

/to-issues       → Spec in GitHub Issues aufbrechen (vertikale Slices)
                   Jedes Issue = ein unabhängig implementierbarer Schritt
                   Reihenfolge: von unten (DB) nach oben (UI)

/tdd             → Implementierung mit Red-Green-Refactor Loop
                   Erst Test schreiben (ROT) → dann Code (GRÜN) → dann aufräumen
                   Tests in tests/ mit In-Memory SQLite (kein Seiteneffekt auf echte DB)

Commit + Push    → git commit + git push nach jedem abgeschlossenen Issue
Issues schließen → via GitHub MCP oder manuell auf github.com
```

**Wichtige Skills:**
- `/grill-me` — Anforderungen ausarbeiten
- `/grill-with-docs` — wie grill-me, aber pflegt zusätzlich CONTEXT.md und ADRs
- `/to-issues` — Plan in GitHub Issues umwandeln
- `/tdd` — Test-Driven Development
- `/diagnose` — strukturiertes Debugging
- `/improve-codebase-architecture` — Codequalität verbessern (regelmäßig laufen lassen)
