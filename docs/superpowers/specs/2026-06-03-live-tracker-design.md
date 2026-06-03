# Live-Tracker Feature — Design Spec

**Datum:** 2026-06-03  
**Status:** Zur Implementierung freigegeben

---

## Überblick

Ein Live-Stoppuhr-Feature das in der Sidebar der Streamlit-App läuft. Ermöglicht minutengenaue Zeiterfassung durch echtes Start/Stop statt nachträglicher Eingabe. Projekt, Unterthema und Kategorie werden vor dem Start gewählt; Kommentar kann beim Stoppen ergänzt/angepasst werden.

---

## Verhalten

### Sidebar — kein aktiver Timer

1. **Recently Used (3 Einträge)** — Schnellstart-Buttons für die 3 zuletzt verwendeten Projekt+Unterthema-Kombinationen. Ein Klick startet den Timer sofort (mit letzter Kategorie vorausgefüllt).
2. **"Neuer Timer" Bereich** — Aufklappbares Formular mit:
   - Projekt (Selectbox, nur aktive)
   - Unterthema (Selectbox, optional)
   - Kategorie (Selectbox, db.KATEGORIEN)
   - Kommentar (Text-Input, optional)
   - **"▶ Starten"** Button

### Sidebar — aktiver Timer

- **JavaScript-Uhr** tickt live im Browser (client-seitig via `st.components.html`), zeigt HH:MM:SS
- Zeigt darunter: Projektname, Unterthema, Startzeit (z.B. "Gestartet: 14:32")
- **"⏹ Stoppen"** Button

### Stopp-Dialog (`st.dialog`)

Öffnet sich nach Klick auf "⏹ Stoppen":
- Dauer (berechnet, read-only angezeigt, z.B. "1h 23min → 1.38h")
- Projekt + Unterthema (read-only)
- Kategorie (editierbar)
- Kommentar (editierbar, vorausgefüllt mit dem beim Start eingegebenen Kommentar)
- Datum (auto = heute, read-only)
- Stundensatz (eingefroren vom Projektsatz zum Zeitpunkt des Starts, nicht sichtbar für User)
- **"Speichern"** Button — schreibt finalen Eintrag
- **"Abbrechen"** Button — Timer läuft weiter (Dialog schließt sich)

---

## Datenbank

### Änderungen an `zeiteintraege`

Zwei neue Spalten (Migration via `ALTER TABLE`):

```sql
ALTER TABLE zeiteintraege ADD COLUMN status TEXT DEFAULT 'fertig';
ALTER TABLE zeiteintraege ADD COLUMN startzeit TEXT;
```

- `status`: `'fertig'` (Standard, alle bisherigen Einträge) | `'laufend'` (aktiver Timer)
- `startzeit`: ISO-8601 Timestamp (z.B. `"2026-06-03T14:32:00"`)

### Laufender Eintrag in DB

Beim Start wird sofort ein Datensatz angelegt:
```
status = 'laufend'
startzeit = datetime.now().isoformat()
datum = date.today().isoformat()
projekt_id, unterthema_id, kategorie, beschreibung = (aus Formular)
stunden = 0  (Platzhalter)
stundensatz = aktueller Projektstundensatz (eingefroren)
```

Beim Speichern (nach Stopp):
```
status = 'fertig'
stunden = berechnete Dauer (gerundet auf 2 Dezimalstellen)
beschreibung = finaler Kommentar aus Dialog
```

### Recently Used

Wird aus der DB ermittelt: die 3 letzten `zeiteintraege` mit `status='fertig'`, gruppiert nach `(projekt_id, unterthema_id)`, sortiert nach `MAX(startzeit)`.

---

## Technische Umsetzung

### JavaScript-Uhr (Sidebar)

```html
<div id="timer" style="font-size:2em; font-family:monospace;">00:00:00</div>
<script>
  const start = new Date("{startzeit_iso}");
  setInterval(() => {
    const diff = Math.floor((new Date() - start) / 1000);
    const h = String(Math.floor(diff/3600)).padStart(2,'0');
    const m = String(Math.floor((diff%3600)/60)).padStart(2,'0');
    const s = String(diff%60).padStart(2,'0');
    document.getElementById('timer').textContent = h+':'+m+':'+s;
  }, 1000);
</script>
```

### Session State

- `st.session_state.timer_aktiv` (bool)
- `st.session_state.timer_eintrag_id` (int, ID des laufenden DB-Eintrags)
- `st.session_state.timer_stundensatz` (float, eingefroren beim Start)
- `st.session_state.stopp_dialog_offen` (bool)

Beim App-Start: DB prüfen ob ein `status='laufend'` Eintrag existiert → Session State wiederherstellen (Reload-Resistenz).

### Dateien die geändert werden

| Datei | Änderung |
|-------|----------|
| `database.py` | Migration + 3 neue Funktionen: `timer_starten()`, `timer_stoppen()`, `recently_used_laden()` |
| `app.py` | Sidebar-Sektion mit Timer-UI + Dialog |

---

## Randfälle

- **App-Reload während Timer läuft:** DB-Eintrag `status='laufend'` wird beim Start erkannt, Session State wiederhergestellt, JS-Uhr startet mit korrekter Startzeit.
- **Kein aktives Projekt vorhanden:** Start-Button deaktiviert, Hinweis "Bitte erst ein Projekt anlegen".
- **Mehrere Browser-Tabs:** Nur ein `status='laufend'` Eintrag erlaubt — beim Start prüfen, ggf. Warnung.
- **Nachträgliche Bearbeitung:** Gespeicherte Einträge sind über die bestehende Zeiterfassung-Seite editierbar (kein neues UI nötig).
- **Stundensatz 0:** Erlaubt (Projekt ohne Stundensatz), kein Blocking.
