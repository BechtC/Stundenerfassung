import math


def stundensatz_berechnen(netto_monat, arbeitstage, nfh_stunden, ausfallpuffer_pct):
    if arbeitstage <= 0:
        raise ValueError("Arbeitstage muss größer als 0 sein.")
    if ausfallpuffer_pct >= 100:
        raise ValueError("Ausfallpuffer muss kleiner als 100% sein.")
    fakturierbare_stunden = arbeitstage * (8 - nfh_stunden) * (1 - ausfallpuffer_pct / 100)
    return round(netto_monat / fakturierbare_stunden, 2)


def auf_naechste_runden(wert, schritt):
    return math.ceil(wert / schritt) * schritt
