# Proton Verteiler V3

Diese Version ist speziell für Proton Mail Bridge ausgelegt.

## Zweck

- Verwaltung von Empfängern und Gruppen
- Versand an mehrere Adressen separat
- Nutzung von Proton Mail Bridge statt eines externen SMTP-Dienstes
- einfache Start- und Build-Skripte für spätere Distribution

## Voraussetzungen

1. Proton Mail Bridge aktivieren und starten
2. Bridge-SMTP auf einem lokalen Port aktivieren, typischerweise:
   - Host: 127.0.0.1
   - Port: 1025
   - TLS: aktiviert
3. Proton Mail Konto / Mailbox und Bridge-Passwort bereit haben

## Starten

Aus dem V3-Ordner:

```powershell
python -m src.main
```

## Build zu EXE

```powershell
build_exe.bat
```

Das erzeugt eine Windows-EXE mit PyInstaller im Ordner `dist`.

## Wichtige Hinweise

- Die App speichert nur lokale Daten in `data/`
- Zugangsdaten werden nur im laufenden Dialog abgefragt
- Proton Mail Bridge muss lokal auf dem Rechner laufen
- Der SMTP Service von Proton ist nur mit kostenpflichtigen Abonnement's nutzbar

## Datenordner

- `data/settings.json`: gespeicherte Absender
- `data/recipients.json`: Gruppen und Empfänger

## Empfohlene Bridge-Konfiguration

- Host: `127.0.0.1`
- Port: `1025`
- Benutzername: Proton-Mail-Konto oder Mailbox-Adresse
- Passwort: Bridge-Passwort
- Absender: deine Proton-Mail-Adresse

## Sicherheit

- Nur lokale Mail-Bridge-Verbindung
- keine dauerhafte Speicherung von SMTP-Login-Daten
