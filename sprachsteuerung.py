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
AUFNAHMEN = os.path.expanduser("~/Aufnahmen")   # hier landen die Tonaufnahmen vom Handy
MAX_AUFNAHME = 1024 * 1024 * 1024               # hoechstens 1 GB pro Aufnahme


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
 body.aufnahme #f, body.aufnahme #log, body.aufnahme small{display:none}
 body.aufnahme #mic{background:#c62828;font-size:70px}
 body.aufnahme #mic.an{background:#555;animation:none}
 #uhr{display:none;font-size:2.4em;font-variant-numeric:tabular-nums;margin:4px 0}
 body.aufnahme #uhr{display:block}
 #liste{display:none;text-align:left;margin-top:14px}
 body.aufnahme #liste{display:block}
 .auf{background:#1b2e3c;border-radius:8px;padding:10px;margin:8px 0}
 .auf audio{width:100%;margin:6px 0}
 .auf a,.auf button{color:#9ecbff;background:none;border:none;font-size:1em;margin-right:14px;padding:4px 0}
</style></head><body>
<h1>🎤 Pi-Mikrofon</h1>
<div id="modi"><button id="mBefehl">🗣️ Befehle</button><button id="mDiktat">⌨️ Diktieren</button><button id="mAuf">🔴 Aufnahme</button></div>
<div id="info"></div>
<button id="mic">🎤</button>
<div id="uhr">0:00</div>
<div id="status">Tippe auf das Mikrofon und sprich.</div>
<form id="f"><input id="t" placeholder="…oder hier tippen / Tastatur-Mikrofon" autocomplete="off"><button class="s">➤</button></form>
<div id="tasten"><button id="bLoesch">⌫ Löschen</button><button id="bEnter">⏎ Senden</button></div>
<div id="log"></div>
<small>Sag „Hilfe“, um alle Befehle zu sehen.</small>
<div id="liste"></div>
<script>
const st=document.getElementById('status'),log=document.getElementById('log'),mic=document.getElementById('mic');
let modus=localStorage.getItem('modus')||'befehl';
function setzeModus(m){
  if(rec&&rec.state=='recording'){st.textContent='Erst die Aufnahme stoppen.';return;}
  modus=m;localStorage.setItem('modus',m);
  document.body.classList.toggle('diktat',m=='diktat');
  document.body.classList.toggle('aufnahme',m=='aufnahme');
  document.getElementById('mBefehl').classList.toggle('aktiv',m=='befehl');
  document.getElementById('mDiktat').classList.toggle('aktiv',m=='diktat');
  document.getElementById('mAuf').classList.toggle('aktiv',m=='aufnahme');
  mic.textContent=m=='aufnahme'?'⏺':'🎤';
  document.getElementById('info').textContent=m=='diktat'
   ?'Was du sagst, wird am Pi dort eingetippt, wo der Strich blinkt (z. B. im Claude-Chat). Sag am Ende „senden“, um Enter zu drücken.'
   :m=='aufnahme'
   ?'Tippe auf den roten Knopf, um eine Tonaufnahme zu starten. Nochmal tippen = Stopp. Die Aufnahme wird am Pi im Ordner „Aufnahmen“ gespeichert.'
   :'Sag einen Befehl, z. B. „Öffne YouTube“. „Hilfe“ zeigt alle Befehle.';
  st.textContent=m=='aufnahme'?'Bereit zur Aufnahme.':'Tippe auf das Mikrofon und sprich.';
  if(m=='aufnahme')ladeListe();}
let rec=null;
document.getElementById('mBefehl').onclick=()=>setzeModus('befehl');
document.getElementById('mDiktat').onclick=()=>setzeModus('diktat');
document.getElementById('mAuf').onclick=()=>setzeModus('aufnahme');

// ---------- Tonaufnahme
const uhr=document.getElementById('uhr'),liste=document.getElementById('liste');
let stuecke=[],start=0,tick=null,wach=null;
function zeit(s){s=Math.floor(s);const h=Math.floor(s/3600),m=Math.floor(s/60)%60,x=s%60;
  return (h?h+':'+String(m).padStart(2,'0'):m)+':'+String(x).padStart(2,'0');}
function mb(b){return b<1048576?Math.max(1,Math.round(b/1024))+' KB':(b/1048576).toFixed(1).replace('.',',')+' MB';}
async function ladeListe(){
  try{const d=await (await fetch('aufnahmen')).json();
    liste.innerHTML=d.length?'<b>Gespeichert am Pi:</b>':'<small>Noch keine Aufnahmen am Pi.</small>';
    for(const a of d){const n=encodeURIComponent(a.name),div=document.createElement('div');div.className='auf';
      div.innerHTML='<div>'+a.name.replace(/</g,'&lt;')+' <small>('+mb(a.groesse)+')</small></div>'
       +'<audio controls preload="none" src="aufnahmen/'+n+'"></audio>'
       +'<a href="aufnahmen/'+n+'" download>⬇ Aufs Handy</a><button>🗑 Löschen</button>';
      div.querySelector('button').onclick=async()=>{
        if(!confirm('„'+a.name+'“ wirklich löschen?'))return;
        await fetch('aufnahme-loeschen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:a.name})});
        ladeListe();};
      liste.appendChild(div);}
  }catch(e){liste.innerHTML='<small>Liste nicht ladbar – Pi nicht erreichbar.</small>';}}
async function starteAufnahme(){
  if(!window.MediaRecorder||!navigator.mediaDevices){st.textContent='Aufnehmen ist in diesem Browser nicht möglich. Bitte Chrome nutzen.';return;}
  let strom;
  try{strom=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:true}});}
  catch(e){st.textContent=(e.name=='NotFoundError'||e.name=='NotReadableError')?HINWEIS['audio-capture']:HINWEIS['not-allowed'];return;}
  const typ=['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg'].find(t=>MediaRecorder.isTypeSupported(t))||'';
  rec=new MediaRecorder(strom,typ?{mimeType:typ,audioBitsPerSecond:128000}:{});
  stuecke=[];
  rec.ondataavailable=e=>{if(e.data.size)stuecke.push(e.data);};
  rec.onstop=()=>{strom.getTracks().forEach(t=>t.stop());clearInterval(tick);
    if(wach){wach.release().catch(()=>{});wach=null;}
    mic.classList.remove('an');mic.textContent='⏺';
    hochladen(new Blob(stuecke,{type:rec.mimeType||'audio/webm'}));};
  rec.start(1000);start=Date.now();uhr.textContent='0:00';
  tick=setInterval(()=>uhr.textContent=zeit((Date.now()-start)/1000),500);
  mic.classList.add('an');mic.textContent='⏹';
  st.textContent='🔴 Aufnahme läuft … Bildschirm bitte anlassen.';
  try{wach=await navigator.wakeLock.request('screen');}catch(e){}
}
async function hochladen(blob){
  const endung=blob.type.includes('mp4')?'m4a':blob.type.includes('ogg')?'ogg':'webm';
  st.textContent='Speichere am Pi … ('+mb(blob.size)+')';
  try{const r=await fetch('aufnahme?endung='+endung,{method:'POST',headers:{'Content-Type':blob.type},body:blob});
    const d=await r.json();st.textContent=d.antwort;ladeListe();}
  catch(e){
    // Pi nicht erreichbar: Aufnahme wenigstens am Handy speichern
    const a=document.createElement('a');a.href=URL.createObjectURL(blob);
    a.download='Aufnahme_'+new Date().toISOString().slice(0,19).replace(/[T:]/g,'-')+'.'+endung;
    a.textContent='⬇ Aufnahme aufs Handy speichern';a.style.color='#9ecbff';
    st.textContent='Pi nicht erreichbar! ';st.appendChild(a);}
}
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
const HINWEIS={
   'audio-capture':'Kein Mikrofon gefunden. Bitte prüfen: 1) Android-Einstellungen → Apps → Chrome → Berechtigungen → Mikrofon → „Erlauben“. 2) Schnelleinstellungen (vom oberen Rand wischen) → „Mikrofonzugriff“ einschalten. 3) Andere Apps schließen, die das Mikrofon nutzen (z. B. Claude-App, Sprachaufnahme).',
   'not-allowed':'Mikrofon gesperrt. Tippe oben links neben der Adresse auf das Symbol → Berechtigungen → Mikrofon → „Zulassen“. Dann Seite neu laden.',
   'service-not-allowed':'Spracherkennung gesperrt. Seite neu laden und Mikrofon erlauben.',
   'network':'Das Handy braucht Internet für die Spracherkennung.',
   'no-speech':'Ich habe nichts gehört. Bitte nochmal tippen und deutlich sprechen.',
   'aborted':'Abgebrochen.'};
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
mic.addEventListener('click',()=>{if(modus!='aufnahme')return;
  if(rec&&rec.state=='recording'){rec.stop();st.textContent='Aufnahme gestoppt.';}else starteAufnahme();});
if(!SR){mic.dataset.keinSR=1;
  st.textContent='Spracherkennung hier nicht möglich – nutze das Mikrofon deiner Handy-Tastatur im Textfeld.';}
else{
  const sr=new SR();sr.lang='de-DE';sr.interimResults=true;
  sr.onstart=()=>{mic.classList.add('an');st.textContent='Ich höre zu …';};
  sr.onresult=e=>{const r=e.results[e.results.length-1];st.textContent=r[0].transcript;if(r.isFinal)sende(r[0].transcript);};
  sr.onerror=e=>{st.textContent=HINWEIS[e.error]||('Fehler: '+e.error);};
  sr.onend=()=>{mic.classList.remove('an');};
  let erlaubt=false;
  mic.onclick=async()=>{
    if(modus=='aufnahme')return;
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

    def _json(self, daten):
        self._antworte(200, "application/json", json.dumps(daten).encode())

    def do_GET(self):
        pfad = urllib.parse.urlparse(self.path).path
        if pfad == "/aufnahmen":
            return self._json(liste_aufnahmen())
        if pfad.startswith("/aufnahmen/"):
            return self._sende_aufnahme(urllib.parse.unquote(pfad[len("/aufnahmen/"):]))
        self._antworte(200, "text/html; charset=utf-8", SEITE.encode())

    def _sende_aufnahme(self, name):
        datei = aufnahme_pfad(name)
        if not datei:
            return self._antworte(404, "text/plain", b"nicht gefunden")
        groesse = os.path.getsize(datei)
        typ = {"m4a": "audio/mp4", "ogg": "audio/ogg"}.get(name.rsplit(".", 1)[-1], "audio/webm")
        # "Range" erlaubt dem Handy, in der Aufnahme vor- und zurueckzuspulen
        anfang, ende = 0, groesse - 1
        bereich = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if bereich and groesse:
            if bereich.group(1):
                anfang = int(bereich.group(1))
                if bereich.group(2):
                    ende = min(int(bereich.group(2)), groesse - 1)
            elif bereich.group(2):
                anfang = max(0, groesse - int(bereich.group(2)))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {anfang}-{ende}/{groesse}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", typ)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(max(0, ende - anfang + 1)))
        self.end_headers()
        with open(datei, "rb") as f:
            f.seek(anfang)
            rest = ende - anfang + 1
            while rest > 0:
                stueck = f.read(min(65536, rest))
                if not stueck:
                    break
                self.wfile.write(stueck)
                rest -= len(stueck)

    def _speichere_aufnahme(self, laenge):
        if not 0 < laenge <= MAX_AUFNAHME:
            return "Aufnahme ist leer oder zu groß."
        endung = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("endung", ["webm"])[0]
        if endung not in ("webm", "m4a", "ogg"):
            endung = "webm"
        os.makedirs(AUFNAHMEN, exist_ok=True)
        name = datetime.datetime.now().strftime("Aufnahme_%Y-%m-%d_%H-%M-%S.") + endung
        datei = os.path.join(AUFNAHMEN, name)
        with open(datei + ".teil", "wb") as f:
            while laenge > 0:
                stueck = self.rfile.read(min(65536, laenge))
                if not stueck:
                    break
                f.write(stueck)
                laenge -= len(stueck)
        if laenge > 0:  # Verbindung abgebrochen
            os.remove(datei + ".teil")
            return "Übertragung abgebrochen – bitte nochmal versuchen."
        os.replace(datei + ".teil", datei)
        return f"✅ Gespeichert am Pi: Aufnahmen/{name}"

    def do_POST(self):
        laenge = int(self.headers.get("Content-Length", 0))
        pfad = urllib.parse.urlparse(self.path).path
        if pfad == "/aufnahme":
            antwort = self._speichere_aufnahme(laenge)
            print(f"  Aufnahme: {antwort}")
            return self._json({"antwort": antwort})
        if pfad == "/aufnahme-loeschen":
            try:
                datei = aufnahme_pfad(json.loads(self.rfile.read(laenge)).get("name", ""))
            except Exception:
                datei = None
            if datei:
                os.remove(datei)
            return self._json({"antwort": "Gelöscht." if datei else "Nicht gefunden."})
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


def aufnahme_pfad(name):
    """Gibt den Pfad einer Aufnahme zurueck - nur Dateien direkt im Aufnahmen-Ordner (Sicherheit)."""
    if not name or name != os.path.basename(name) or name.startswith(".") or name.endswith(".teil"):
        return None
    datei = os.path.join(AUFNAHMEN, name)
    return datei if os.path.isfile(datei) else None


def liste_aufnahmen():
    if not os.path.isdir(AUFNAHMEN):
        return []
    namen = [n for n in os.listdir(AUFNAHMEN) if aufnahme_pfad(n)]
    return [{"name": n, "groesse": os.path.getsize(os.path.join(AUFNAHMEN, n))}
            for n in sorted(namen, reverse=True)]


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
