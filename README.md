# 🏭 Telekom Hungary Scraper & Lead Generator (Multi-Core Stealth AI - 2026)

Software industriale automatizzato basato su **Python 3.12** e **Playwright** per l'estrazione massiva e progressiva di anagrafiche commerciali e numeriche dal portale Tudakozó di Telekom Ungheria. Il sistema integra reti neurali residenti in memoria RAM per il superamento autonomo di barriere di sicurezza complesse, emulando la biometria di un utente umano reale.

---

## 🚀 Caratteristiche Chiave dell'Architettura

* **Umanizzazione Biometrica Avanzata**: Digitazione dei moduli basata su distribuzione gaussiana asimmetrica per lettera e movimenti del mouse a curve paraboliche per azzerare i flag comportamentali.
* **YOLOv8 Geometrico Adattivo (Visivo Primario)**: Rileva dinamicamente matrici fisse e complesse (3x3, 4x3, 4x4) calcolando le coordinate reali dei pixel nell'Iframe per superare i blocchi trasparenti di Google.
* **Whisper-Tiny Residente in RAM (Audio Fallback)**: Intercetta il flusso MP3 asincrono di Google e decodifica istantaneamente in memoria le nuove sfide a dettato testuale complesso (frasi intere composte da parole e spazi), eliminando file orfani sul disco fisso.
* **Isolamento Hardware Multi-Core**: Threading neurale PyTorch forzatamente isolato ad 1 Thread per Core, per prevenire congelamenti (*Deadlock*) e sfruttare appieno processori massivi (fino a 32 thread).
* **Filtro Progressivo e Strategia Incessante**: Set condiviso in RAM in tempo reale per lo scarto immediato dei duplicati inter-processo e congelamento dell'indice in caso di errore per martellare lo stesso bersaglio cambiando sessione.
* **Ripristino Progressivo a Freddo**: All'avvio analizza l'ultima riga scritta nei file CSV calcolando automaticamente il record numerico o l'attività business esatta da cui riprendere l'estrazione.

---

## 🛠️ Guida Dettagliata all'Installazione (Primo Avvio)

Segui rigorosamente questa sequenza di comandi all'interno del terminale di Windows posizionandoti nella cartella del progetto.

### 1. Creazione e Attivazione dell'Ambiente Virtuale (Virtualenv)
Isola le librerie del software per evitare conflitti con altre versioni di Python installate nel computer:
```bash
python -m venv venv
venv\Scripts\activate
```
*(Dopo l'attivazione vedrai la scritta `(venv)` a sinistra nel prompt dei comandi).*

### 2. Aggiornamento e Installazione dei Pacchetti Core
Installa i motori di Playwright, le estensioni di rete per i proxy SOCKS, le suite neurali e i manipolatori d'onda audio:
```bash
pip install --upgrade pip
pip install httpx[socks] ultralytics openai-whisper torch torchvision opencv-python pydub numpy keyboard
```

### 3. Installazione dei Binari Multimediali Nativi (FFmpeg)
Per permettere a `pydub` e `whisper` di processare l'audio direttamente in memoria RAM, Windows necessita dei binari di sistema FFmpeg.
1. Scarica la versione *Essentials build* dal sito ufficiale o tramite gestore di pacchetti Windows:
   ```bash
   winget install Gyan.FFmpeg
   ```
2. Assicurati che il percorso dell'eseguibile sia inserito nelle *Variabili di Ambiente di Sistema* di Windows (sotto la voce `PATH`).

### 4. Inizializzazione Hardware dei Browser Playwright
Scarica l'istanza isolata e protetta del motore Chromium ufficiale su cui lavorerà l'automazione invisibile:
```bash
playwright install chromium
```

---

## 📂 Struttura File Obbligatoria sul Disco

Prima di avviare il software, assicurati che la gerarchia delle cartelle presenti questa disposizione geometrica sul tuo hard-disk:

```text
telekom_scraper/
│
├── telekom_scraper.py         # Il codice sorgente principale del software
├── yolov8n.pt                 # Pesi della rete neurale YOLOv8 (Scaricati in auto al primo boot)
│
├── regioni/                   # Cartella contenente i file geografici delle Contee ungheresi
│   ├── Budapest.txt           # Elenco dei comuni interni/quartieri scritti riga per riga
│   └── Pest.txt
│
├── macro_settori/             # Cartella contenente le liste delle parole chiave commerciali
│   ├── Ipar és Gyártás.txt    # Target commerciali (es: raklap, raklap adás vétel)
│   └── Kereskedelem.txt
│
├── proxy_privati.txt          # OPZIONALE: Elenco dei tuoi proxy dedicati SOCKS5/HTTP
└── venv/                      # L'ambiente virtuale di lavoro Python
```

---

## 🚀 Guida all'Avvio Successivo e Utilizzo Quotidiano

Ogni volta che desideri rimettere in funzione la macchina estrattiva, apri il terminale di Windows ed esegui questa sequenza standard:

### 1. Accensione dell'ambiente e lancio
```bash
cd C:YOUR PATH:pyprojeckt's\telekom_scraper
venv\Scripts\activate
python telekom_scraper.py
```

### 2. Configurazione del Pannello Interattivo di Boot
Il software ti guiderà passo dopo passo tramite domande nel terminale:

1. **Selezione Obiettivo**: Premi **`b`** per attivare l'estrazione aziendale (*Business*) o **`n`** per la scansione sequenziale dei numeri (*Numerica*).
2. **Selezione Contea/Macro-Settore (Solo Business)**: Digita il numero corrispondente alla contea geografica sul disco (es: `3` per Budapest) e il numero del file di nicchia industriale (es: `9` per il mercato dei pallet).
3. **Selezione Modalità AI**: Scegli **`ai`** per lasciare l'elaborazione interamente in mano a YOLOv8 e Whisper residenti, oppure **`m`** per la modalità di debug assistito a schermo.
4. **Selezione Canale di Rete (Proxy)**: 
   * Premi **`c`** per viaggiare **In Chiaro** (Consigliato: Sfrutta l'IP pulito del tuo Hotspot telefonico/Casa per azzerare i blocchi e navigare alla massima velocità).
   * Premi **`g`** per attivare il download dinamico dei proxy gratuiti, inserendo poi il numero della nazione limitrofa desiderata per abbattere la latenza (consigliati nodi *HU* o *DE*).
   * Premi **`p`** per caricare la tua lista di proxy commerciali dal file `proxy_privati.txt`.
5. **Allocazione Core**: Inserisci il numero di istanze browser parallele da lanciare. (Se navighi *In chiaro* o in modalità *Manuale*, imposta sempre **`1`** per focalizzare le prestazioni).
6. **Gestione del Ripristino Progressivo**: Se il software rileva che nella cartella esiste già un file CSV parziale per quell'area, ti domanderà: *Riprendere da dove interrotta? (si/no)*. Scrivi **`si`**. Il Core analizzerà il file e salterà istantaneamente i record estratti in precedenza, ripartendo a freddo dall'esatta ordinata di sosta.

---

## 🎮 Controlli di Emergenza e Protezioni Automatizzate

* **Risoluzione Audio Avanzata Interattiva**: Quando il risolutore visivo incontra una griglia complessa o viene sfidato, il sistema attiva automaticamente il modulo **Whisper Audio in RAM**. Questo intercetta la traccia vocale a frase intera di Google, ne calcola la durata nativa in millisecondi per simulare un tempo di ascolto umano realistico e immette la stringa testuale completa lettera per lettera. L'operazione simula la tastiera hardware reale ed elimina l'uso di JavaScript bloccanti, agendo chirurgicamente sugli XPath verificati `//*[@id="audio-response"]` e `//*[@id="recaptcha-verify-button"]`.
* **Auto-Recovery Errore Audio**: Se Whisper riproduce una traccia disturbata e Google respinge la frase testuale scritta, il Core cattura immediatamente l'avviso di errore, impedisce il congelamento dell'istanza e innesca un hard-reset localizzato immediato della sessione per farsi erogare un nuovo flusso vocale sul medesimo target.
* **`CTRL + Q` (Force-Kill Hardware)**: È la scorciatoia globale corazzata registrata a basso livello nel Kernel di Windows. Premendo questa combinazione in qualunque momento, lo script interrompe l'esecuzione multi-core e **rade al suolo istantaneamente tutti i processi figli e le istanze Chromium orfane rimaste appese nella RAM**, ripulendo il Task Manager in un millisecondo.
* **Auto-Healing Incessante**: Non è richiesto alcun intervento se lo script incontra una congestione di rete o un rifiuto da parte di Google. Il modulo congela autonomamente l'indice del bersaglio, distrugge la sessione instabile e rigenera un browser pulito per ricolpire lo stesso record finché non viene estratto con successo.



This tool is for educational purpose only or for searching a job! dont be Sally always use Knowlage wisely! 


# 🏭 Telekom Hungary Scraper & Lead Generator (Multi-Core Stealth AI - 2026)

Automated industrial software based on **Python 3.12** and **Playwright** for the massive and progressive extraction of commercial and numerical records from the Telekom Hungary Tudakozó portal. The system integrates resident neural networks in RAM memory to autonomously overcome complex security barriers by emulating the biometrics of a real human user.

---

## 🚀 Key Features of the Architecture

* **Advanced Biometric Humanization**: Module typing based on asymmetric Gaussian distribution per letter and mouse movements with parabolic curves to completely eliminate behavioral flags.
* **Adaptive Geometric YOLOv8 (Primary Visual)**: Dynamically detects fixed and complex matrices (3x3, 4x3, 4x4) by calculating the real pixel coordinates inside the Iframe to bypass Google's transparent overlays.
* **Resident RAM Whisper-Tiny (Audio Fallback)**: Intercepts Google's asynchronous MP3 stream and instantly decodes new complex text-dictation challenges (entire sentences composed of words and spaces) directly in memory, eliminating orphan files on the hard drive.
* **Multi-Core Hardware Isolation**: PyTorch neural threading is strictly isolated to 1 Thread per Core to prevent freezes (*Deadlocks*) and fully exploit massive processors (up to 32 threads).
* **Progressive Filtering & Incessant Strategy**: Real-time shared set in RAM for immediate cross-process duplicate discarding and index freezing in case of errors to hammer the exact same target by resetting the session.
* **Cold Progressive Recovery**: At startup, it analyzes the last line written in the CSV files, automatically calculating the exact numerical record or business activity from which to resume extraction.

---

## 🛠️ Detailed Installation Guide (First Startup)

Strictly follow this command sequence inside the Windows terminal, positioning yourself in the project folder.

### 1. Creation and Activation of the Virtual Environment (Virtualenv)
Isolate the software libraries to avoid conflicts with other Python versions installed on your computer:
```bash
python -m venv venv
venv\Scripts\activate
```
*(After activation, you will see the `(venv)` text on the left side of the command prompt).*

### 2. Upgrade and Installation of Core Packages
Install Playwright engines, network extensions for SOCKS proxies, neural suites, and audio wave manipulators:
```bash
pip install --upgrade pip
pip install httpx[socks] ultralytics openai-whisper torch torchvision opencv-python pydub numpy keyboard
```

### 3. Installation of Native Multimedia Binaries (FFmpeg)
To allow `pydub` and `whisper` to process audio directly in RAM memory, Windows requires native FFmpeg system binaries.
1. Download the *Essentials build* version from the official website or via the Windows package manager:
   ```bash
   winget install Gyan.FFmpeg
   ```
2. Ensure that the executable path is added to the Windows *System Environment Variables* (under the `PATH` entry).

### 4. Hardware Initialization of Playwright Browsers
Download the isolated and protected instance of the official Chromium engine on which the invisible automation will work:
```bash
playwright install chromium
```

---

## 📂 Mandatory File Structure on Disk

Before launching the software, ensure that the folder hierarchy follows this exact geometric layout on your hard drive:

```text
telekom_scraper/
│
├── telekom_scraper.py         # The main software source code
├── yolov8n.pt                 # YOLOv8 neural network weights (Auto-downloaded at first boot)
│
├── regioni/                   # Folder containing the geographical files of Hungarian Counties
│   ├── Budapest.txt           # List of internal municipalities/districts written line by line
│   └── Pest.txt
│
├── macro_settori/             # Folder containing the lists of commercial keywords
│   ├── Ipar és Gyártás.txt    # Commercial targets (e.g., raklap, raklap adás vétel)
│   └── Kereskedelem.txt
│
├── proxy_privati.txt          # OPTIONAL: List of your dedicated SOCKS5/HTTP proxies
└── venv/                      # L'ambiente virtuale di lavoro Python
```

---

## 🚀 Subsequent Launch & Daily Usage Guide

Every time you want to restart the extraction machine, open the Windows terminal and execute this standard sequence:

### 1. Environment activation and launch
```bash
cd C:YOUR PATH:pyprojeckt's\telekom_scraper
venv\Scripts\activate
python telekom_scraper.py
```

### 2. Interactive Boot Panel Configuration
The software will guide you step-by-step through questions in the terminal:

1. **Target Selection**: Press **`b`** to activate commercial extraction (*Business*) or **`n`** for sequential number scanning (*Numerica*).
2. **County/Macro-Sector Selection (Business Only)**: Type the number corresponding to the geographical county on disk (e.g., `3` for Budapest) and the number of the industrial niche file (e.g., `9` for the pallet market).
3. **AI Mode Selection**: Choose **`ai`** to leave the processing entirely to the resident YOLOv8 and Whisper engines, or **`m`** for assisted debug mode on screen.
4. **Network Channel Selection (Proxy)**: 
   * Press **`c`** to travel **In Plain Text** (Recommended: Leverages the clean IP of your phone Hotspot/Home connection to eliminate blocks and browse at maximum speed).
   * Press **`g`** to activate the dynamic download of free proxies, then type the number of the desired neighboring nation to cut latency (recommended nodes: *HU* or *DE*).
   * Press **`p`** to load your commercial proxy list from the `proxy_privati.txt` file.
5. **Core Allocation**: Enter the number of parallel browser instances to launch. (If you browse *In plain text* or in *Manual* mode, always set this to **`1`** to focus performance).
6. **Progressive Recovery Management**: If the software detects that a partial CSV file already exists for that area in the folder, it will ask you: *Resume from where it was interrupted? (si/no)*. Type **`si`**. The Core will instantly analyze the file, skip previously extracted records, and cold-start from the exact coordinates where it left off.

---

## 🎮 Emergency Controls & Automated Protections

* **Advanced Audio Fallback Execution**: When the visual puzzle solver hits a complex matrix or is challenged, the system automatically engages the RAM-isolated **Whisper Audio solver**. It intercepts Google’s phrase dictation challenge, calculates the track's native length, simulates human listening times, and types the complete lettered sentence string character-by-character using high-precision hardware emulated keyboard inputs via native `//*[@id="audio-response"]` and `//*[@id="recaptcha-verify-button"]` XPaths.
* **Audio Error Auto-Recovery**: If Whisper intercepts a noisy segment and Google rejects the submitted vocal phrase sentence, the core catches the warning immediately, flags the issue, prevents the instance from freezing, and triggers an instantaneous localized session hard-reset to grab a clean challenge stream for the frozen target.
* **`CTRL + Q` (Hardware Force-Kill)**: This is the armored global shortcut registered at the low Windows Kernel level. Pressing this combination at any time halts the multi-core execution and **instantly wipes out all child processes and hanging Chromium instances left over in RAM**, cleaning the Task Manager in a millisecond.
* **Incessant Auto-Healing**: No intervention is required if the script encounters network congestion or a rejection from Google. The module autonomously freezes the current target index, destroys the unstable session, and regenerates a clean browser to keep hammering the same record until it is successfully extracted.

