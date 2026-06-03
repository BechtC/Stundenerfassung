"""
Datenbank-Modul für die Stundenerfassung.
SQLite Backend mit allen CRUD-Operationen.
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "stundenerfassung.db"

PROJEKT_FARBEN = [
    "#E63946", "#2A9D8F", "#E9C46A", "#457B9D", "#F4A261",
    "#8338EC", "#06D6A0", "#FB5607", "#3A86FF", "#A8DADC",
]


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projekte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                stundensatz REAL DEFAULT 0.0,
                kunde TEXT DEFAULT '',
                kunde_adresse TEXT DEFAULT '',
                aktiv INTEGER DEFAULT 1,
                erstellt_am TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS unterthemen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projekt_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                aktiv INTEGER DEFAULT 1,
                FOREIGN KEY (projekt_id) REFERENCES projekte(id) ON DELETE CASCADE,
                UNIQUE(projekt_id, name)
            );

            CREATE TABLE IF NOT EXISTS zeiteintraege (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                datum TEXT NOT NULL,
                projekt_id INTEGER NOT NULL,
                unterthema_id INTEGER,
                stunden REAL NOT NULL,
                beschreibung TEXT DEFAULT '',
                kategorie TEXT DEFAULT 'Produktiv',
                erstellt_am TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (projekt_id) REFERENCES projekte(id),
                FOREIGN KEY (unterthema_id) REFERENCES unterthemen(id)
            );

            CREATE TABLE IF NOT EXISTS rechnungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rechnungsnummer TEXT NOT NULL UNIQUE,
                projekt_id INTEGER NOT NULL,
                kunde TEXT NOT NULL,
                kunde_adresse TEXT DEFAULT '',
                datum TEXT NOT NULL,
                leistungszeitraum_von TEXT NOT NULL,
                leistungszeitraum_bis TEXT NOT NULL,
                positionen TEXT NOT NULL,
                gesamtbetrag REAL NOT NULL,
                status TEXT DEFAULT 'Entwurf',
                erstellt_am TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (projekt_id) REFERENCES projekte(id)
            );

            CREATE TABLE IF NOT EXISTS firmen_daten (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                firma_name TEXT DEFAULT 'Meine Firma GmbH',
                inhaber TEXT DEFAULT 'Max Mustermann',
                strasse TEXT DEFAULT 'Musterstraße 1',
                plz TEXT DEFAULT '12345',
                ort TEXT DEFAULT 'Musterstadt',
                telefon TEXT DEFAULT '+49 123 456789',
                email TEXT DEFAULT 'info@meinefirma.de',
                website TEXT DEFAULT '',
                steuernummer TEXT DEFAULT 'XX/XXX/XXXXX',
                ust_id TEXT DEFAULT 'DEXXXXXXXXX',
                bank_name TEXT DEFAULT 'Musterbank',
                iban TEXT DEFAULT 'DE00 0000 0000 0000 0000 00',
                bic TEXT DEFAULT 'XXXXXXXX'
            );

            INSERT OR IGNORE INTO firmen_daten (id) VALUES (1);
        """)
        # Idempotente Migrationen
        for sql in [
            "ALTER TABLE zeiteintraege ADD COLUMN status TEXT DEFAULT 'fertig'",
            "ALTER TABLE zeiteintraege ADD COLUMN startzeit TEXT",
            "ALTER TABLE projekte ADD COLUMN farbe TEXT",
        ]:
            try:
                conn.execute(sql)
            except Exception:
                pass  # Spalte existiert bereits


# --- Projekte ---

def projekt_erstellen(name, stundensatz=0.0, kunde="", kunde_adresse=""):
    farbe = random.choice(PROJEKT_FARBEN)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO projekte (name, stundensatz, kunde, kunde_adresse, farbe) VALUES (?, ?, ?, ?, ?)",
            (name, stundensatz, kunde, kunde_adresse, farbe)
        )


def projekte_laden(nur_aktive=True):
    with get_connection() as conn:
        if nur_aktive:
            rows = conn.execute("SELECT * FROM projekte WHERE aktiv = 1 ORDER BY name").fetchall()
        else:
            rows = conn.execute("SELECT * FROM projekte ORDER BY name").fetchall()
        result = [dict(r) for r in rows]
        for p in result:
            if not p.get("farbe"):
                p["farbe"] = "#AAAAAA"
        return result


def projekt_aktualisieren(projekt_id, **kwargs):
    allowed = {"name", "stundensatz", "kunde", "kunde_adresse", "aktiv"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [projekt_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE projekte SET {set_clause} WHERE id = ?", values)


def projekt_farbe_aktualisieren(projekt_id, farbe):
    with get_connection() as conn:
        conn.execute("UPDATE projekte SET farbe = ? WHERE id = ?", (farbe, projekt_id))


def projekt_loeschen(projekt_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM projekte WHERE id = ?", (projekt_id,))


# --- Unterthemen ---

def unterthema_erstellen(projekt_id, name):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO unterthemen (projekt_id, name) VALUES (?, ?)",
            (projekt_id, name)
        )


def unterthemen_laden(projekt_id, nur_aktive=True):
    with get_connection() as conn:
        if nur_aktive:
            rows = conn.execute(
                "SELECT * FROM unterthemen WHERE projekt_id = ? AND aktiv = 1 ORDER BY name",
                (projekt_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM unterthemen WHERE projekt_id = ? ORDER BY name",
                (projekt_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def unterthema_loeschen(unterthema_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM unterthemen WHERE id = ?", (unterthema_id,))


# --- Zeiteinträge ---

KATEGORIEN = ["Produktiv", "Planung", "Meeting", "Admin", "Weiterbildung", "Sonstiges"]


def zeiteintrag_erstellen(datum, projekt_id, stunden, unterthema_id=None,
                          beschreibung="", kategorie="Produktiv"):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO zeiteintraege
               (datum, projekt_id, unterthema_id, stunden, beschreibung, kategorie)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datum, projekt_id, unterthema_id, stunden, beschreibung, kategorie)
        )


def zeiteintraege_laden(datum_von=None, datum_bis=None, projekt_id=None):
    query = """
        SELECT z.*, p.name as projekt_name, u.name as unterthema_name, p.stundensatz, p.farbe as projekt_farbe
        FROM zeiteintraege z
        JOIN projekte p ON z.projekt_id = p.id
        LEFT JOIN unterthemen u ON z.unterthema_id = u.id
        WHERE 1=1
    """
    params = []
    if datum_von:
        query += " AND z.datum >= ?"
        params.append(datum_von)
    if datum_bis:
        query += " AND z.datum <= ?"
        params.append(datum_bis)
    if projekt_id:
        query += " AND z.projekt_id = ?"
        params.append(projekt_id)
    query += " ORDER BY z.datum DESC, z.erstellt_am DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- Live-Tracker ---

def timer_starten(projekt_id, unterthema_id, kategorie, beschreibung, stundensatz):
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO zeiteintraege
               (datum, projekt_id, unterthema_id, stunden, beschreibung, kategorie, status, startzeit)
               VALUES (?, ?, ?, 0, ?, ?, 'laufend', ?)""",
            (date.today().isoformat(), projekt_id, unterthema_id,
             beschreibung, kategorie, datetime.now().isoformat())
        )
        return cursor.lastrowid


def timer_stoppen(eintrag_id, beschreibung):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT startzeit FROM zeiteintraege WHERE id = ?", (eintrag_id,)
        ).fetchone()
        startzeit = datetime.fromisoformat(row["startzeit"])
        dauer = round((datetime.now() - startzeit).total_seconds() / 3600, 2)
        conn.execute(
            "UPDATE zeiteintraege SET status='fertig', stunden=?, beschreibung=? WHERE id=?",
            (dauer, beschreibung, eintrag_id)
        )


def recently_used_laden(limit=3):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT z.projekt_id, p.name as projekt_name,
                   z.unterthema_id, u.name as unterthema_name, z.kategorie
            FROM zeiteintraege z
            JOIN projekte p ON z.projekt_id = p.id
            LEFT JOIN unterthemen u ON z.unterthema_id = u.id
            WHERE z.status = 'fertig'
            GROUP BY z.projekt_id, z.unterthema_id
            ORDER BY MAX(z.startzeit) DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def laufenden_timer_laden():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT z.*, p.name as projekt_name, u.name as unterthema_name, p.stundensatz, p.farbe as projekt_farbe
            FROM zeiteintraege z
            JOIN projekte p ON z.projekt_id = p.id
            LEFT JOIN unterthemen u ON z.unterthema_id = u.id
            WHERE z.status = 'laufend'
            LIMIT 1
        """).fetchone()
        return dict(row) if row else None


def zeiteintrag_loeschen(eintrag_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM zeiteintraege WHERE id = ?", (eintrag_id,))


def zeiteintrag_aktualisieren(eintrag_id, **kwargs):
    allowed = {"datum", "projekt_id", "unterthema_id", "stunden", "beschreibung", "kategorie"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [eintrag_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE zeiteintraege SET {set_clause} WHERE id = ?", values)


# --- Statistiken ---

def statistik_pro_projekt(datum_von=None, datum_bis=None):
    query = """
        SELECT p.name as projekt, p.stundensatz,
               SUM(z.stunden) as gesamt_stunden,
               SUM(z.stunden * p.stundensatz) as gesamt_betrag,
               COUNT(z.id) as anzahl_eintraege
        FROM zeiteintraege z
        JOIN projekte p ON z.projekt_id = p.id
        WHERE 1=1
    """
    params = []
    if datum_von:
        query += " AND z.datum >= ?"
        params.append(datum_von)
    if datum_bis:
        query += " AND z.datum <= ?"
        params.append(datum_bis)
    query += " GROUP BY p.id ORDER BY gesamt_stunden DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def statistik_pro_kategorie(datum_von=None, datum_bis=None):
    query = """
        SELECT kategorie, SUM(stunden) as gesamt_stunden, COUNT(id) as anzahl
        FROM zeiteintraege WHERE 1=1
    """
    params = []
    if datum_von:
        query += " AND datum >= ?"
        params.append(datum_von)
    if datum_bis:
        query += " AND datum <= ?"
        params.append(datum_bis)
    query += " GROUP BY kategorie ORDER BY gesamt_stunden DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def stunden_pro_tag(datum_von=None, datum_bis=None):
    query = """
        SELECT datum, SUM(stunden) as gesamt_stunden
        FROM zeiteintraege WHERE 1=1
    """
    params = []
    if datum_von:
        query += " AND datum >= ?"
        params.append(datum_von)
    if datum_bis:
        query += " AND datum <= ?"
        params.append(datum_bis)
    query += " GROUP BY datum ORDER BY datum"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- Firmendaten ---

def firmendaten_laden():
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM firmen_daten WHERE id = 1").fetchone()
        return dict(row) if row else {}


def firmendaten_speichern(**kwargs):
    allowed = {"firma_name", "inhaber", "strasse", "plz", "ort", "telefon",
               "email", "website", "steuernummer", "ust_id", "bank_name", "iban", "bic"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values())
    with get_connection() as conn:
        conn.execute(f"UPDATE firmen_daten SET {set_clause} WHERE id = 1", values)


# --- Rechnungen ---

def naechste_rechnungsnummer():
    jahr = datetime.now().year
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM rechnungen WHERE rechnungsnummer LIKE ?",
            (f"RE-{jahr}-%",)
        ).fetchone()
        nr = row["cnt"] + 1
        return f"RE-{jahr}-{nr:04d}"


def rechnung_erstellen(projekt_id, kunde, kunde_adresse, datum,
                       leistungszeitraum_von, leistungszeitraum_bis,
                       positionen_json, gesamtbetrag):
    rechnungsnummer = naechste_rechnungsnummer()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO rechnungen
               (rechnungsnummer, projekt_id, kunde, kunde_adresse, datum,
                leistungszeitraum_von, leistungszeitraum_bis, positionen, gesamtbetrag)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rechnungsnummer, projekt_id, kunde, kunde_adresse, datum,
             leistungszeitraum_von, leistungszeitraum_bis, positionen_json, gesamtbetrag)
        )
        return rechnungsnummer


def rechnungen_laden():
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT r.*, p.name as projekt_name
               FROM rechnungen r JOIN projekte p ON r.projekt_id = p.id
               ORDER BY r.erstellt_am DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def rechnung_status_aendern(rechnungs_id, status):
    with get_connection() as conn:
        conn.execute("UPDATE rechnungen SET status = ? WHERE id = ?", (status, rechnungs_id))
