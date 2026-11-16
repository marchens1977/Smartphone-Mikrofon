#!/usr/bin/env python3
"""
Handy-Mikrofon fuer den Raspberry Pi
====================================
Starten auf dem Pi mit:   python3 sprachsteuerung.py
Dann am Handy (gleiches WLAN) die angezeigte Adresse in Chrome oeffnen.

Das Handy wandelt Sprache in Text um und schickt ihn hierher.
Hier wird der Text mit der Befehlsliste unten verglichen und ausgefuehrt.
Es wird nur Python verwendet, das auf dem Pi schon vorhanden ist.
"""

import datetime
import http.server
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import urllib.parse

PORT = 8443
ORDNER = os.path.dirname(os.path.abspath(__file__))
ZERTIFIKAT = os.path.join(ORDNER, "zertifikat.pem")
SCHLUESSEL = os.path.join(ORDNER, "schluessel.pem")


# ---------------------------------------------------------------- Hilfen
def starte(befehl):
    """Startet ein Programm im Hintergrund. Gibt True zurueck, wenn es geklappt hat."""
    if not shutil.which(befehl[0]):
        return False
    subprocess.Popen(befehl, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return True


def starte_erstes(*befehle):
    """Probiert mehrere Programme nacheinander, bis eines vorhanden ist."""
    return any(starte(b) for b in befehle)


def oeffne_seite(adresse):
    starte_erstes(["xdg-open", adresse], ["chromium-browser", adresse], ["chromium", adresse])


def lautstaerke(wpctl_wert, amixer_wert):
    return starte_erstes(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", wpctl_wert],
                         ["amixer", "-q", "set", "Master", amixer_wert])


# ---------------------------------------------------------------- Befehle
# Jeder Befehl: (Liste von Woertern, die vorkommen muessen, Funktion)
# Die Funktion bekommt den Rest des Satzes und gibt eine Antwort fuers Handy zurueck.

def befehl_suche(rest):
    if not rest:
        return "Wonach soll ich suchen? Sag z. B. 'suche nach Barsch'."
    oeffne_seite("https://www.google.de/search?q=" + urllib.parse.quote(rest))
    return f"Ich suche nach: {rest}"


FEHLT_TIPPHILFE = ("Zum Tippen fehlt ein Hilfsprogramm. Am Pi das Einrichten nochmal ausführen "
                   "oder eingeben: sudo apt install wtype xdotool")


def tippe(text=None, taste=None):
    """Tippt Text (oder drueckt eine Taste) im gerade aktiven Fenster am Pi.
    Wayland (Standard beim Pi 400) braucht 'wtype', das aeltere X11 braucht 'xdotool'."""
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wtype"):
        befehl = ["wtype", "-k", taste] if taste else ["wtype", "--", text]
    elif shutil.which("xdotool"):
        befehl = ["xdotool", "key", taste] if taste else ["xdotool", "type", "--delay", "20", "--", text]
    else:
        return False
    subprocess.run(befehl, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    return True


def diktiere(text):
    """Diktier-Modus: alles Gesagte wird am Pi eingetippt.
    Endet der Satz mit 'senden' oder 'absenden', wird danach Enter gedrueckt."""
    text = text.strip()
    enter = False
    for wort in ("absenden", "senden", "abschicken"):
        if text.lower().rstrip(" .!?").endswith(wort):
            text = text.rstrip(" .!?")[: -len(wort)].rstrip(" ,.")
            enter = True
            break
    if text and not tippe(text + ("" if enter else " ")):
        return FEHLT_TIPPHILFE
    if enter and not tippe(taste="Return"):
        return FEHLT_TIPPHILFE
    return (f"Getippt: {text}" if text else "") + (" ⏎ gesendet" if enter else "")


def befehl_schreibe(rest):
    if not rest:
        return "Was soll ich schreiben?"
    return f"Geschrieben: {rest}" if tippe(rest) else FEHLT_TIPPHILFE


def befehl_screenshot(_):
    datei = os.path.expanduser(datetime.datetime.now().strftime("~/Bildschirmfoto_%Y-%m-%d_%H-%M-%S.png"))
    if starte_erstes(["grim", datei], ["scrot", datei]):
        return "Bildschirmfoto gespeichert im Home-Ordner."
    return "Kein Programm fuer Bildschirmfotos gefunden."


def befehl_uhrzeit(_):
    return "Es ist " + datetime.datetime.now().strftime("%H:%M") + " Uhr."


def befehl_hilfe(_):
    return ("Du kannst sagen: öffne Browser, öffne YouTube, suche nach …, schreibe …, "
            "lauter, leiser, Ton aus, öffne Terminal, öffne Dateien, Bildschirmfoto, "
            "wie spät ist es, starte Megabarsch.")


BEFEHLE = [
    (["hilfe"],                lambda r: befehl_hilfe(r)),
    (["was kannst du"],        lambda r: befehl_hilfe(r)),
    (["suche nach"],           befehl_suche),
    (["suche"],                befehl_suche),
    (["google"],               befehl_suche),
    (["schreibe"],             befehl_schreibe),
    (["schreib"],              befehl_schreibe),
    (["youtube"],              lambda r: (oeffne_seite("https://www.youtube.com"), "YouTube wird geöffnet.")[1]),
    (["megabarsch"],           lambda r: (oeffne_seite("https://marchens1977.github.io/Angel-Adventure/"), "Viel Spaß beim Angeln!")[1]),
    (["angelspiel"],           lambda r: (oeffne_seite("https://marchens1977.github.io/Angel-Adventure/"), "Viel Spaß beim Angeln!")[1]),
    (["browser"],              lambda r: (oeffne_seite("https://www.google.de"), "Browser wird geöffnet.")[1]),
    (["internet"],             lambda r: (oeffne_seite("https://www.google.de"), "Browser wird geöffnet.")[1]),
    (["terminal"],             lambda r: "Terminal wird geöffnet." if starte_erstes(["lxterminal"], ["x-terminal-emulator"]) else "Kein Terminal gefunden."),
    (["dateien"],              lambda r: "Dateimanager wird geöffnet." if starte_erstes(["pcmanfm"], ["nautilus"]) else "Kein Dateimanager gefunden."),
    (["dateimanager"],         lambda r: "Dateimanager wird geöffnet." if starte_erstes(["pcmanfm"], ["nautilus"]) else "Kein Dateimanager gefunden."),
    (["lauter"],               lambda r: "Lauter." if lautstaerke("10%+", "10%+") else "Lautstärke ließ sich nicht ändern."),
    (["leiser"],               lambda r: "Leiser." if lautstaerke("10%-", "10%-") else "Lautstärke ließ sich nicht ändern."),
    (["ton aus"],              lambda r: "Ton aus/an." if starte_erstes(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], ["amixer", "-q", "set", "Master", "toggle"]) else "Ging nicht."),
    (["ton an"],               lambda r: "Ton aus/an." if starte_erstes(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], ["amixer", "-q", "set", "Master", "toggle"]) else "Ging nicht."),
    (["stumm"],                lambda r: "Ton aus/an." if starte_erstes(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], ["amixer", "-q", "set", "Master", "toggle"]) else "Ging nicht."),
    (["bildschirmfoto"],       befehl_screenshot),
    (["screenshot"],           befehl_screenshot),
    (["uhrzeit"],              befehl_uhrzeit),
    (["wie spät"],             befehl_uhrzeit),
]


def verarbeite(text):
    satz = re.sub(r"[.,!?]", "", text.lower()).strip()
    for woerter, funktion in BEFEHLE:
        if all(w in satz for w in woerter):
            # Alles nach dem Befehlswort ist der "Rest" (z. B. der Suchbegriff)
            rest = satz.split(woerter[-1], 1)[1].strip()
            rest_original = text.strip()[len(text.strip()) - len(rest):].strip(" .!?") if rest else ""
            try:
                return funktion(rest_original or rest)
            except Exception as fehler:  # Damit das Programm nie abstuerzt
                return f"Fehler: {fehler}"
    return f"Nicht verstanden: „{text}“. Sag „Hilfe“ für alle Befehle."


# ---------------------------------------------------------------- Handy-Seite
SEITE = """<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pi-Mikrofon</title>
<style>
 *{box-sizing:border-box}
 body{font-family:sans-serif;background:#12202b;color:#eee;margin:0;padding:16px;text-align:center}
 h1{font-size:1.4em;margin:8px 0 16px}
 #mic{width:180px;height:180px;border-radius:50%;border:none;font-size:80px;background:#2e7d32;color:#fff;margin:10px auto;display:block}
 #mic.an{background:#c62828;animation:p 1s infinite}
 @keyframes p{50%{transform:scale(1.07)}}
 #status{min-height:1.5em;font-size:1.1em;margin:8px 0}
 form{display:flex;gap:8px;margin:20px 0}
 input{flex:1;min-width:0;font-size:1.2em;padding:12px;border-radius:8px;border:none}
 button.s{font-size:1.2em;padding:12px 18px;border-radius:8px;border:none;background:#1565c0;color:#fff}
 #log{text-align:left;font-size:1em}
 .du{color:#9ecbff;margin-top:10px}.pi{color:#b9f6ca}
 small{color:#999}
 #modi{display:flex;gap:8px;margin-bottom:6px}
 #modi button{flex:1;font-size:1.1em;padding:12px;border-radius:8px;border:2px solid #456;background:#1b2e3c;color:#ccc}
 #modi button.aktiv{background:#f9a825;color:#000;border-color:#f9a825;font-weight:bold}
 #tasten{display:none;gap:8px;margin-top:8px}
 #tasten button{flex:1;font-size:1.2em;padding:14px;border-radius:8px;border:none;background:#455a64;color:#fff}
 body.diktat #tasten{display:flex}
 body.diktat #mic{background:#f9a825}
 body.diktat #mic.an{background:#c62828}
 #info{font-size:.95em;color:#bbb;min-height:2.4em}
</style></head><body>
<h1>🎤 Pi-Mikrofon</h1>
<div id="modi"><button id="mBefehl">🗣️ Befehle</button><button id="mDiktat">⌨️ Diktieren</button></div>
<div id="info"></div>
<button id="mic">🎤</button>
<div id="status">Tippe auf das Mikrofon und sprich.</div>
<form id="f"><input id="t" placeholder="…oder hier tippen / Tastatur-Mikrofon" autocomplete="off"><button class="s">➤</button></form>
<div id="tasten"><button id="bLoesch">⌫ Löschen</button><button id="bEnter">⏎ Senden</button></div>
<div id="log"></div>
<small>Sag „Hilfe“, um alle Befehle zu sehen.</small>
<script>
const st=document.getElementById('status'),log=document.getElementById('log'),mic=document.getElementById('mic');
let modus=localStorage.getItem('modus')||'befehl';
function setzeModus(m){modus=m;localStorage.setItem('modus',m);
  document.body.classList.toggle('diktat',m=='diktat');
  document.getElementById('mBefehl').classList.toggle('aktiv',m=='befehl');
  document.getElementById('mDiktat').classList.toggle('aktiv',m=='diktat');
  document.getElementById('info').textContent=m=='diktat'
   ?'Was du sagst, wird am Pi dort eingetippt, wo der Strich blinkt (z. B. im Claude-Chat). Sag am Ende „senden“, um Enter zu drücken.'
   :'Sag einen Befehl, z. B. „Öffne YouTube“. „Hilfe“ zeigt alle Befehle.';}
document.getElementById('mBefehl').onclick=()=>setzeModus('befehl');
document.getElementById('mDiktat').onclick=()=>setzeModus('diktat');
setzeModus(modus);
async function taste(m,anzeige){
  try{const r=await fetch('befehl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({modus:m})});
      st.textContent=(await r.json()).antwort;}catch(e){st.textContent='Pi nicht erreichbar.';}}
document.getElementById('bEnter').onclick=()=>taste('enter');
document.getElementById('bLoesch').onclick=()=>taste('loeschen');
async function sende(text){
  if(!text.trim())return;
  log.insertAdjacentHTML('afterbegin','<div class="pi">…</div>');
  log.insertAdjacentHTML('afterbegin','<div class="du">Du: '+text.replace(/</g,'&lt;')+'</div>');
  try{const r=await fetch('befehl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,modus})});
      const d=await r.json();log.children[1].textContent='Pi: '+d.antwort;}
  catch(e){log.children[1].textContent='Pi nicht erreichbar.';}
}
document.getElementById('f').onsubmit=e=>{e.preventDefault();const t=document.getElementById('t');sende(t.value);t.value='';};
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
if(!SR){mic.disabled=true;mic.style.background='#555';
  st.textContent='Spracherkennung hier nicht möglich – nutze das Mikrofon deiner Handy-Tastatur im Textfeld.';}
else{
  const sr=new SR();sr.lang='de-DE';sr.interimResults=true;
  sr.onstart=()=>{mic.classList.add('an');st.textContent='Ich höre zu …';};
  sr.onresult=e=>{const r=e.results[e.results.length-1];st.textContent=r[0].transcript;if(r.isFinal)sende(r[0].transcript);};
  const HINWEIS={
   'audio-capture':'Kein Mikrofon gefunden. Bitte prüfen: 1) Android-Einstellungen → Apps → Chrome → Berechtigungen → Mikrofon → „Erlauben“. 2) Schnelleinstellungen (vom oberen Rand wischen) → „Mikrofonzugriff“ einschalten. 3) Andere Apps schließen, die das Mikrofon nutzen (z. B. Claude-App, Sprachaufnahme).',
   'not-allowed':'Mikrofon gesperrt. Tippe oben links neben der Adresse auf das Symbol → Berechtigungen → Mikrofon → „Zulassen“. Dann Seite neu laden.',
   'service-not-allowed':'Spracherkennung gesperrt. Seite neu laden und Mikrofon erlauben.',
   'network':'Das Handy braucht Internet für die Spracherkennung.',
   'no-speech':'Ich habe nichts gehört. Bitte nochmal tippen und deutlich sprechen.',
   'aborted':'Abgebrochen.'};
  sr.onerror=e=>{st.textContent=HINWEIS[e.error]||('Fehler: '+e.error);};
  sr.onend=()=>{mic.classList.remove('an');};
  let erlaubt=false;
  mic.onclick=async()=>{
    // Beim ersten Mal das Mikrofon direkt anfragen, damit Android/Chrome die Erlaubnis abfragt.
    if(!erlaubt&&navigator.mediaDevices){
      try{const s=await navigator.mediaDevices.getUserMedia({audio:true});s.getTracks().forEach(t=>t.stop());erlaubt=true;}
      catch(e){st.textContent=(e.name=='NotFoundError'||e.name=='NotReadableError')?HINWEIS['audio-capture']:HINWEIS['not-allowed'];return;}
    }
    try{sr.start();}catch(e){sr.stop();}};
}
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _antworte(self, code, typ, daten):
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def do_GET(self):
        self._antworte(200, "text/html; charset=utf-8", SEITE.encode())

    def do_POST(self):
        laenge = int(self.headers.get("Content-Length", 0))
        try:
            daten = json.loads(self.rfile.read(laenge))
        except Exception:
            daten = {}
        text = daten.get("text", "")
        modus = daten.get("modus", "befehl")
        try:
            if modus == "enter":
                antwort = "⏎ Enter gedrückt" if tippe(taste="Return") else FEHLT_TIPPHILFE
            elif modus == "loeschen":
                antwort = "⌫ gelöscht" if tippe(taste="BackSpace") else FEHLT_TIPPHILFE
            elif modus == "diktat":
                antwort = diktiere(text)
            else:
                antwort = verarbeite(text)
        except Exception as fehler:
            antwort = f"Fehler: {fehler}"
        print(f"  Gehört: {text!r}  ->  {antwort}")
        self._antworte(200, "application/json", json.dumps({"antwort": antwort}).encode())

    def log_message(self, *args):
        pass  # keine unnoetigen Meldungen im Terminal


def eigene_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "IP-ADRESSE-DES-PI"
    finally:
        s.close()


def main():
    # Das Handy erlaubt das Mikrofon nur ueber eine "sichere" Verbindung (https).
    # Dafuer wird einmalig ein eigenes Zertifikat erstellt.
    https = True
    if not os.path.exists(ZERTIFIKAT):
        try:
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                            "-keyout", SCHLUESSEL, "-out", ZERTIFIKAT, "-days", "3650",
                            "-subj", "/CN=raspberrypi"], check=True, capture_output=True)
        except Exception:
            https = False
    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError:
        # Das Programm laeuft schon (z. B. automatisch beim Start des Pi)
        print("=" * 50)
        print("  Das Pi-Mikrofon läuft bereits!")
        print("  Adresse fürs Handy:")
        print()
        print(f"     https://{eigene_ip()}:{PORT}")
        print("=" * 50)
        try:
            input("\n  Enter drücken zum Schließen ...")
        except EOFError:
            pass
        return
    if https:
        kontext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        kontext.load_cert_chain(ZERTIFIKAT, SCHLUESSEL)
        server.socket = kontext.wrap_socket(server.socket, server_side=True)
    adresse = f"{'https' if https else 'http'}://{eigene_ip()}:{PORT}"
    print("=" * 50)
    print("  Pi-Mikrofon läuft!")
    print("  Öffne am Handy in Chrome diese Adresse:")
    print()
    print("     " + adresse)
    print()
    print("  Beenden: Strg + C drücken")
    print("=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")


if __name__ == "__main__":
    main()
