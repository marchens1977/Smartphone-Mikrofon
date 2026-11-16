# Projekt-Tagebuch: Smartphone-Mikrofon

## 1. Worum geht es?

Das Smartphone des Nutzers (Samsung, Chrome) dient als Sprach-Fernbedienung für seinen Raspberry Pi 400.

- `sprachsteuerung.py` – läuft auf dem Pi (nur Python-Standardbibliothek, keine Installation nötig).
  - Startet einen kleinen Webserver auf Port **8443** mit **https** (selbst erstelltes Zertifikat
    `zertifikat.pem`/`schluessel.pem`, wird beim ersten Start mit `openssl` erzeugt, nicht im Repository).
  - Liefert die Handy-Seite aus (im Python-Code eingebettet, Variable `SEITE`).
  - Das Handy macht die Spracherkennung (Chrome Web Speech API, Deutsch) und schickt den Text an `/befehl`.
  - Befehlsliste `BEFEHLE` oben im Code: Stichwörter → Aktion.
- Fallback: Textfeld, in das man mit dem Mikrofon der Handy-Tastatur sprechen kann.

## 2. Entscheidungen

- Kein echtes Audio-Streaming, sondern Text-Befehle: einfacher und zuverlässiger.
- https ist nötig, weil Chrome das Mikrofon sonst nicht freigibt.
- Lautstärke über `wpctl` (PipeWire), sonst `amixer`. Text schreiben über `wtype` (Wayland) oder `xdotool`.

## 3. Verlauf

| Datum | Was |
|---|---|
| 2026-11-16 | Erste Version (vorher kurz im Repository Angel-Adventure, dann hierher umgezogen) |

## 4. Offene Ideen

- Automatischer Start beim Hochfahren des Pi
- Eigene Befehle des Nutzers ergänzen

## 5. Zusammenarbeit

- Nutzer ist Programmier-Laie: einfaches Deutsch, kleine nummerierte Schritte,
  klar sagen, was Claude übernimmt und was der Nutzer tun muss.
- Claude übernimmt alles, was möglich ist. Vor dem Hochladen testen.
- Hardware: Samsung-Smartphone (Chrome) und Raspberry Pi 400.
