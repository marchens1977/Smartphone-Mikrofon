# 🎤 Smartphone-Mikrofon für den Raspberry Pi

Mit diesem kleinen Programm wird dein Handy zur Sprach-Fernbedienung für deinen Raspberry Pi.
Du sprichst ins Handy, und der Pi führt den Befehl aus (z. B. „Öffne YouTube“, „lauter“, „suche nach …“).

## Einrichten (einmalig, am Raspberry Pi im Terminal)

```
mkdir -p ~/smartphone-mikrofon && cd ~/smartphone-mikrofon
wget -N https://raw.githubusercontent.com/marchens1977/Smartphone-Mikrofon/main/sprachsteuerung.py
```

## Starten

```
cd ~/smartphone-mikrofon && python3 sprachsteuerung.py
```

Der Pi zeigt eine Adresse an (z. B. `https://192.168.178.25:8443`).

## Am Handy

1. Handy im selben WLAN wie der Pi.
2. Adresse in Chrome öffnen.
3. Warnung „Verbindung ist nicht privat“ → **Erweitert** → **Weiter zu … (unsicher)**.
4. Auf den grünen 🎤-Knopf tippen, Mikrofon erlauben, sprechen.

## Befehle

„Öffne Browser“, „Öffne YouTube“, „Starte Megabarsch“, „Suche nach …“, „Schreibe …“,
„Lauter“, „Leiser“, „Ton aus“, „Öffne Terminal“, „Öffne Dateien“, „Bildschirmfoto“,
„Wie spät ist es?“, „Hilfe“.

Für „Schreibe …“ einmalig installieren: `sudo apt install wtype xdotool`

Beenden: im Terminal **Strg + C**.

![Vorschau](vorschau.png)
