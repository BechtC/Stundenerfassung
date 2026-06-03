"""
Testdaten für die Stundenerfassung generieren.
Einmalig ausführen, danach löschen oder ignorieren.
"""

import database as db
from datetime import date, timedelta
import random

db.init_db()

# --- Projekte ---
projekte = [
    ("Webshop Redesign", 95.0, "TechStyle GmbH", "TechStyle GmbH\nHauptstraße 12\n80331 München"),
    ("Mobile App MVP", 110.0, "FitTrack AG", "FitTrack AG\nSportweg 5\n60313 Frankfurt"),
    ("API-Integration", 85.0, "LogiFlow Solutions", "LogiFlow Solutions\nIndustriepark 8\n70173 Stuttgart"),
    ("Interne Tools", 0.0, "", ""),
    ("Consulting Datenbank", 120.0, "MedData GmbH", "MedData GmbH\nKlinikstr. 22\n50667 Köln"),
]

projekt_ids = {}
for name, satz, kunde, adresse in projekte:
    try:
        db.projekt_erstellen(name, satz, kunde, adresse)
    except Exception:
        pass

for p in db.projekte_laden():
    projekt_ids[p["name"]] = p["id"]

# --- Unterthemen ---
unterthemen_map = {
    "Webshop Redesign": ["Planung", "Frontend", "Backend", "Testing", "Deployment"],
    "Mobile App MVP": ["UI/UX Design", "Flutter Entwicklung", "API Anbindung", "QA"],
    "API-Integration": ["Anforderungsanalyse", "Entwicklung", "Dokumentation"],
    "Interne Tools": ["Stundenerfassung", "Automatisierung"],
    "Consulting Datenbank": ["Beratung", "Datenmigration", "Schulung"],
}

unterthema_ids = {}
for projekt_name, uts in unterthemen_map.items():
    pid = projekt_ids.get(projekt_name)
    if not pid:
        continue
    for ut in uts:
        try:
            db.unterthema_erstellen(pid, ut)
        except Exception:
            pass
    for u in db.unterthemen_laden(pid):
        unterthema_ids[(projekt_name, u["name"])] = u["id"]

# --- Zeiteinträge: Letzte 60 Tage ---
heute = date.today()
beschreibungen = {
    ("Webshop Redesign", "Planung"): ["Kickoff-Meeting", "Wireframes besprochen", "Meilensteine definiert"],
    ("Webshop Redesign", "Frontend"): ["Produktseite umgesetzt", "Warenkorb-UI gebaut", "Responsive Fixes"],
    ("Webshop Redesign", "Backend"): ["Checkout-API implementiert", "Payment-Integration", "Datenbank-Schema"],
    ("Webshop Redesign", "Testing"): ["E2E Tests geschrieben", "Bugfixes nach QA"],
    ("Webshop Redesign", "Deployment"): ["Staging aufgesetzt", "CI/CD Pipeline"],
    ("Mobile App MVP", "UI/UX Design"): ["Mockups erstellt", "Design Review", "Farb-/Fontkonzept"],
    ("Mobile App MVP", "Flutter Entwicklung"): ["Login-Screen", "Dashboard Widget", "Push Notifications"],
    ("Mobile App MVP", "API Anbindung"): ["REST Endpoints angebunden", "Auth Flow implementiert"],
    ("Mobile App MVP", "QA"): ["Testfälle definiert", "Beta-Test Feedback eingearbeitet"],
    ("API-Integration", "Anforderungsanalyse"): ["Schnittstellen-Doku gelesen", "Meeting mit Kunde"],
    ("API-Integration", "Entwicklung"): ["OAuth2 Flow", "Daten-Mapping", "Error Handling"],
    ("API-Integration", "Dokumentation"): ["API-Doku geschrieben", "Swagger aktualisiert"],
    ("Interne Tools", "Stundenerfassung"): ["App-Grundgerüst", "DB-Schema entworfen"],
    ("Interne Tools", "Automatisierung"): ["n8n Workflow gebaut", "Backup-Script"],
    ("Consulting Datenbank", "Beratung"): ["Erstgespräch", "Anforderungen aufgenommen", "Konzept präsentiert"],
    ("Consulting Datenbank", "Datenmigration"): ["Altdaten analysiert", "Migrationsskript", "Validierung"],
    ("Consulting Datenbank", "Schulung"): ["Schulungsunterlagen erstellt", "Workshop durchgeführt"],
}

kategorien_gewichte = ["Produktiv"] * 6 + ["Planung"] * 2 + ["Meeting"] * 2 + ["Admin", "Weiterbildung"]

for tage_zurueck in range(60):
    tag = heute - timedelta(days=tage_zurueck)
    if tag.weekday() >= 5:  # Wochenende: manchmal arbeiten
        if random.random() > 0.3:
            continue

    anzahl = random.randint(1, 4)
    for _ in range(anzahl):
        projekt_name = random.choice(list(unterthemen_map.keys()))
        pid = projekt_ids[projekt_name]
        ut_name = random.choice(unterthemen_map[projekt_name])
        ut_id = unterthema_ids.get((projekt_name, ut_name))
        stunden = random.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
        kategorie = random.choice(kategorien_gewichte)
        key = (projekt_name, ut_name)
        beschreibung = random.choice(beschreibungen.get(key, ["Allgemeine Arbeit"]))

        db.zeiteintrag_erstellen(
            datum=tag.isoformat(),
            projekt_id=pid,
            unterthema_id=ut_id,
            stunden=stunden,
            beschreibung=beschreibung,
            kategorie=kategorie,
        )

# --- Firmendaten aktualisieren ---
db.firmendaten_speichern(
    firma_name="CB Digital Solutions",
    inhaber="Christian Becht",
    strasse="Musterstraße 42",
    plz="68159",
    ort="Mannheim",
    telefon="+49 170 1234567",
    email="info@cb-digital.de",
    website="www.cb-digital.de",
    steuernummer="12/345/67890",
    ust_id="DE123456789",
    bank_name="ING",
    iban="DE89 3704 0044 0532 0130 00",
    bic="INGDDEFFXXX",
)

print("Testdaten erfolgreich erstellt!")
print(f"  Projekte: {len(projekte)}")
print(f"  Unterthemen: {sum(len(v) for v in unterthemen_map.values())}")
print(f"  Firmendaten: aktualisiert")

# Zähle Einträge
eintraege = db.zeiteintraege_laden()
print(f"  Zeiteinträge: {len(eintraege)}")
