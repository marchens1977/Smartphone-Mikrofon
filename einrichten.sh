#!/bin/bash
# Richtet das Smartphone-Mikrofon auf dem Raspberry Pi ein:
#  - laedt die neueste Version herunter
#  - startet es automatisch, wenn der Pi hochfaehrt
#  - legt einen Eintrag im Startmenue an (zeigt die Adresse fuers Handy)
ORDNER="$HOME/smartphone-mikrofon"
mkdir -p "$ORDNER" "$HOME/.config/autostart" "$HOME/.local/share/applications"
wget -q -O "$ORDNER/sprachsteuerung.py" https://raw.githubusercontent.com/marchens1977/Smartphone-Mikrofon/main/sprachsteuerung.py

# Hilfsprogramme zum Eintippen am Pi (fuer den Diktier-Modus)
if ! command -v wtype >/dev/null || ! command -v xdotool >/dev/null; then
  echo "Installiere Hilfsprogramme zum Tippen (kann 1 Minute dauern) ..."
  sudo apt-get install -y wtype xdotool >/dev/null 2>&1 || \
    (sudo apt-get update >/dev/null 2>&1 && sudo apt-get install -y wtype xdotool >/dev/null 2>&1) || \
    echo "Hinweis: Installation hat nicht geklappt. Später: sudo apt install wtype xdotool"
fi

# Automatischer Start (unsichtbar im Hintergrund)
cat > "$HOME/.config/autostart/smartphone-mikrofon.desktop" <<EOT
[Desktop Entry]
Type=Application
Name=Smartphone-Mikrofon (Autostart)
Exec=python3 $ORDNER/sprachsteuerung.py
Terminal=false
EOT

# Eintrag im Startmenue (Himbeere -> Zubehoer)
cat > "$HOME/.local/share/applications/smartphone-mikrofon.desktop" <<EOT
[Desktop Entry]
Type=Application
Name=Smartphone-Mikrofon
Comment=Handy als Sprachsteuerung - zeigt die Adresse fuers Handy
Exec=python3 $ORDNER/sprachsteuerung.py
Icon=audio-input-microphone
Terminal=true
Categories=Utility;
EOT

# Alte Version beenden und neue gleich im Hintergrund starten
pkill -f "sprachsteuerung.py" 2>/dev/null
sleep 1
nohup python3 "$ORDNER/sprachsteuerung.py" >/dev/null 2>&1 &
sleep 2

IP=$(hostname -I | awk '{print $1}')
echo
echo "=================================================="
echo "  Fertig eingerichtet!"
echo "  Das Pi-Mikrofon läuft jetzt und startet ab sofort"
echo "  automatisch, wenn der Pi hochfährt."
echo
echo "  Adresse fürs Handy:   https://$IP:8443"
echo
echo "  Adresse vergessen? Startmenü (Himbeere) ->"
echo "  Zubehör -> Smartphone-Mikrofon"
echo "=================================================="
