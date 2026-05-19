FULLY WORKING TESTED ON FREE PROXY AND UP TO 24 CORE! i set max core usage to 80% 

# 🏭 Telekom Hungary Scraper & Lead Generator (Multi-Core Stealth AI - 2026)

Software industriale automatizzato basato su **Python 3.12** e **Playwright** per l'estrazione massiva e progressiva di anagrafiche commerciali e numeriche dal portale Tudakozó di Telekom Ungheria. Il sistema integra reti neurali ONNX residenti in memoria RAM per il superamento autonomo di barriere di sicurezza complesse ed esegue la ripartizione geometrica del carico di lavoro su architetture multi-core massive.

---

## 🚀 Caratteristiche Chiave dell'Architettura

* **Umanizzazione Biometrica e Curve di Bézier**: Digitazione dei moduli basata su distribuzione gaussiana asimmetrica per lettera (con esitazione biologica ampliata sulla barra spaziatrice). I movimenti del mouse sui widget di Google generano traiettorie paraboliche fluide basate sulle curve di Bézier con decelerazione e inerzia finale per eludere la telemetria comportamentale.
* **Custom reCAPTCHA v2 ONNX Engine (Visivo Primario)**: Sfrutta il modello neurale pre-addestrato specifico `model.onnx` eseguito tramite la libreria ultra-leggera Microsoft `onnxruntime`. Cattura un unico screenshot ad alta risoluzione della griglia intera (evitando le distorsioni dei singoli tasselli) e mappa matematicamente i box rilevati su matrici geometriche dinamiche 3x3 o 4x4, riducendo l'uso di CPU in RAM multiprocesso. https://github.com/DannyLuna17/RecaptchaV2-IA-Solver
* **Whisper-Tiny Residente in RAM (Audio Fallback)**: Intercetta il flusso MP3 vocale di Google e decodifica in memoria le sfide a dettato testuale completo (frasi intere composte da parole e spazi), simulando il tempo di ascolto umano reale in millisecondi prima dell'immissione a tastiera hardware.
* **Divisore Matematico Lineare Equidistante**: Elimina le collisioni inter-processo nella ricerca numerica. Calcola dinamicamente il passo di oscillazione (chunk) dividendo lo spazio numerico totale (10.000.000 per Budapest a 7 cifre, 1.000.000 per le province a 6 cifre) per il numero esatto di core attivati, distribuendo i processi a ventaglio parallelo equidistante a partire da un numero base inserito dall'utente.
* **Login Gate Interattivo Unico**: All'avvio assoluto del Core 1 visivo, il sistema apre una scheda temporanea di standby su Google Accounts per 60 secondi, consentendo all'operatore di eseguire un login manuale su un account Gmail reale. I cookie fiduciari vengono salvati in un profilo persistente sul disco fisso desktop (`telekom_user_profile_core_1`). Questo gate viene memorizzato nella memoria condivisa (`config`) e viene saltato automaticamente (o premendo INVIO nel terminale) durante tutti i successivi cambi proxy di emergenza, erogando un punteggio di fiducia massimo (Fiducia Google 1.0 - Spunta Verde Istantanea).
* **Instant Bypass Guard**: Se l'account Gmail loggato garantisce lo sblocco verde immediato senza mostrare sfide visive, il bot rileva la velocità di uscita anticipata dell'AI, salta le pause artificiali, esegue una riscrittura hardware d'emergenza a velocità massima e forza l'invio dati a Telekom tramite una sosta protetta di 4.5 secondi per dare tempo alle tabelle asincrone di popolarsi prima del polling di lettura.
* **Intercettatore Errore Tecnico Telekom con Rotazione Lineare**: Rileva in tempo reale tramite parsing del testo della pagina la comparsa del banner rosso nativo di Telekom («Technikai hiba»). Se l'IP del proxy viene sanzionato dal server aziendale, il bot esegue un *Graceful Shutdown* (chiusura protetta immediata del contesto per evitare eccezioni orfane di Playwright) e incrementa in avanti lineare l'indice del pool dei proxy validati in HTTPS, muovendosi rigorosamente dal server più performante (minor ping in ms) al meno reattivo senza mai resettarsi o tornare al proxy 1.
* **Isolamento Hardware Multi-Core**: Threading neurale PyTorch forzatamente isolato ad 1 Thread per Core all'avvio assoluto del processo padre per prevenire errori di ridefinizione (*Deadlock*) e sfruttare appieno processori massivi (fino a 32 thread paralleli).

---

## 🛠️ Guida Dettagliata all'Installazione (Primo Avvio)

Segui rigorosamente questa sequenza di comandi all'interno del terminale di Windows posizionandoti nella cartella del progetto (pyprojecktPATH\telekom_scraper`).

### 1. Creazione e Attivazione dell'Ambiente Virtuale (Virtualenv)
Isola le librerie del software per evitare conflitti con altre versioni di Python installate nel computer:
```bash
python -m venv venv
venv\Scripts\activate
```
*(Dopo l'attivazione vedrai la scritta `(venv)` a sinistra nel prompt dei comandi).*

### 2. Aggiornamento e Installazione dei Pacchetti Core
Installa i motori di Playwright, l'ambiente di runtime ONNX per la rete neurale del captcha, le estensioni di rete per i proxy SOCKS, le suite multimediali e i manipolatori audio:
```bash
pip install --upgrade pip
pip install httpx[socks] onnxruntime ultralytics openai-whisper torch torchvision opencv-python pydub numpy keyboard
```

### 3. Installazione dei Binari Multimediali Nativi (FFmpeg)
Per permettere a `pydub` e `whisper` di processare l'audio direttamente in memoria RAM, Windows necessita dei binari di sistema FFmpeg.
1. Scarica la versione *Essentials build* dal sito ufficiale o tramite gestore di pacchetti Windows:
   ```bash
   winget install Gyan.FFmpeg
   ```
2. Assicurati che il percorso dell'eseguibile sia inserito nelle *Variabili di Ambiente di Sistema* di Windows (sotto la voce `PATH`).

### 4. Inizializzazione Hardware dei Browser Playwright
Scarica l'istanza isolata e protetta del motore Chromium ufficiale su cui lavorerà l'automazione visiva/headless:
```bash
playwright install chromium
```

---

## 📂 Struttura File Obbligatoria sul Disco

Prima di avviare il software, assicurati che la gerarchia delle cartelle presenti questa disposizione geometrica sul tuo hard-disk. Il file del modello ONNX scaricato deve essere rinominato tassativamente in `model.onnx`:

```text
telekom_scraper/
│
├── telekom_scraper.py         # Il codice sorgente principale del software
├── model.onnx                 # Pesi ONNX della rete neurale custom reCAPTCHA v2 (DannyLuna17)
├── yolov8n.pt                 # Pesi di backup YOLOv8 per la griglia visiva
│
├── regioni/                   # Cartella contenente i file geografici delle Contee ungheresi
│   ├── Budapest.txt           # Elenco dei comuni interni/quartieri scritti riga per riga
│   └── Pest.txt
│
├── macro_settori/             # Cartella contenente le liste delle parole chiave commerciali
│   ├── Ipar és Gyártás.txt    # Target commerciali (es: raklap, raklap adás vétel)
│   └── Kereskedelem.txt
│
├── proxy_privati.txt          # Elenco ordinato dei tuoi proxy HTTPS/SOCKS privati
└── venv/                      # L'ambiente virtuale di lavoro Python
```

---

## 🚀 Guida all'Avvio Successivo e Utilizzo Quotidiano

Ogni volta che desideri rimettere in funzione la macchina estrattiva, apri il terminale di Windows ed esegui questa sequenza standard:

### 1. Accensione dell'ambiente e lancio
```bash
cd C:\YOURPATH pyprojeckt's\telekom_scraper
venv\Scripts\activate
python telekom_scraper.py
```

### 2. Configurazione del Pannello Interattivo di Boot
Il software ti guiderà passo dopo passo tramite domande nel terminale:

1. **Selezione Obiettivo**: Premi **`b`** per attivare l'estrazione aziendale (*Business*) o **`n`** per la scansione sequenziale dei numeri (*Numerica*).
2. **Selezione Contea/Macro-Settore (Solo Business)**: Digita il numero corrispondente alla contea geografica sul disco (es: `3` per Budapest) e il numero del file di nicchia industriale (es: `9` per il mercato dei pallet).
3. **Selezione Modalità AI**: Scegli **`ai`** per lasciare l'elaborazione interamente in mano a ONNX Runtime e Whisper residenti, oppure **`m`** per la modalità di debug assistito manuale a schermo.
4. **Selezione Canale di Rete (Proxy)**: 
   * Premi **`c`** per viaggiare **In Chiaro** (Consigliato: Sfrutta l'IP pulito del tuo Hotspot telefonico/Casa per azzerare i blocchi e navigare alla massima velocità).
   * Premi **`g`** per attivare il download dinamico dei proxy gratuiti da GitHub (Esegue un pre-screening automatico in HTTPS su Google scartando a monte i nodi che richiedono credenziali `407` o falliscono il tunnel `CONNECT`, ordinandoli dal più veloce in millisecondi al più lento).
   * Premi **`p`** per caricare la tua lista di proxy commerciali dal file `proxy_privati.txt`.
5. **Allocazione Core**: Inserisci il numero di istanze parallele da lanciare. Se inserisci 1 Core, il browser si aprirà in modalità visiva palese per permetterti il monitoraggio, se inserisci più core, solo il Core 1 sarà visibile (master) mentre i restanti core figli gireranno rigorosamente in background (`headless=True`) per non rubarsi il focus hardware della tastiera e non mandare in freeze la CPU.
6. **Inserimento Start Numerico Equidistante**: Inserisci il prefisso desiderato (es. `1`). Lo script calcolerà la distanza matematica dei chunk in base ai core attivi e ti chiederà il numero base (es. `2249090`). Gli spazi vuoti inseriti per errore di digitazione verranno puliti automaticamente dal filtro `.replace()`.
7. **Gestione del Ripristino Progressivo**: Se il software rileva che nella cartella esiste già un file CSV parziale per quell'area (`results_regione_1_core1.csv`), ti domanderà: *Riprendere da dare interrotta? (si/no)*. Scrivi **`si`**. Il Core analizzerà l'ultima riga scritta nel file e salterà istantaneamente i record estratti in precedenza, ripartendo a freddo dall'esatta ordinata di sosta.

---

## 🎮 Controlli di Emergenza e Protezioni Automatizzate

* **Auto-Recovery Errore Audio & Anti-Loop**: Se Whisper riproduce una traccia disturbata e Google respinge la frase testuale o blocca silenziosamente l'erogazione del file MP3 per proxy sanzionato, il modulo rileva il blocco entro 5 secondi, interrompe immediatamente il ciclo dei tentativi interni, solleva l'eccezione controllata `Audio Trascrizione Errata` verso il lavoratore principale, abbatte il contesto visivo ed incrementa linearmente l'indice del proxy per caricare il server successivo più veloce del pool, impedendo ai core di tornare indietro al proxy 1.
* **`CTRL + Q` (Force-Kill Hardware)**: È la scorciatoia globale corazzata registrata a basso livello nel Kernel di Windows. Premendo questa combinazione in qualunque momento sul terminale, lo script interrompe l'esecuzione multi-core e **rade al suolo istantaneamente tutti i processi figli e le istanze Chromium orfane rimaste appese nella RAM**, ripulendo il Task Manager in un millisecondo.
* **Auto-Healing Incessante**: Non è richiesto alcun intervento in caso di anomalie di rete, stati indefiniti o form bloccati. Il modulo distrugge la singola sessione instabile, incrementa l'indice lineare dei proxy ordinati in RAM e rigenera un browser pulito per ricolpire lo stesso record finché non viene estratto con successo sul file CSV.




# 🏭 Telekom Hungary Scraper & Lead Generator (Multi-Core Stealth AI - 2026)

Industrial automated software based on **Python 3.12** and **Playwright** for the massive and progressive extraction of commercial and numerical records from the Telekom Hungary Tudakozó portal. The system integrates ONNX neural networks resident in RAM memory to autonomously overcome complex security barriers and executes geometric workload partitioning across massive multi-core architectures.

---

## 🚀 Key Features of the Architecture

* **Biometric Humanization & Bézier Curves**: Module typing based on asymmetric Gaussian distribution per letter (including expanded biological hesitation on the spacebar). Mouse movements over Google widgets generate fluid parabolic trajectories based on Bézier curves with custom deceleration and final inertia to completely evade behavioral telemetry.
* **Custom reCAPTCHA v2 ONNX Engine (Primary Visual)**: Leverages the specific pre-trained neural model `model.onnx` executed via the ultra-lightweight Microsoft `onnxruntime` library. It captures a single high-resolution screenshot of the entire grid (preventing distortions of individual tiles) and mathematically maps detected boxes to dynamic 3x3 or 4x4 geometric matrices, minimizing CPU usage in multiprocess RAM. https://github.com/DannyLuna17/RecaptchaV2-IA-Solver
* **Resident RAM Whisper-Tiny (Audio Fallback)**: Intercepts Google's vocal MP3 stream and decodes entire dictation sentences (words and spaces) directly in memory, simulating real human listening times in milliseconds before emulating keyboard hardware inputs.
* **Equidistant Linear Mathematical Divider**: Eliminates inter-process collisions during numerical scanning. It dynamically calculates the oscillation step (chunk) by dividing the total numerical space (10,000,000 for Budapest with 7 digits, 1,000,000 for provinces with 6 digits) by the exact number of active cores, distributing parallel processes in an equidistant fan-out shape starting from a baseline number entered by the user.
* **Unique Interactive Login Gate**: Upon the absolute first launch of the visible Core 1, the system opens a temporary standby tab on Google Accounts for 60 seconds, allowing the operator to manually log into a real Gmail account. The trust cookies are saved in a persistent profile on the local desktop drive (`telekom_user_profile_core_1`). This gate state is saved in shared memory (`config`) and is automatically bypassed (or skipped by pressing ENTER in the terminal) during all subsequent emergency proxy rotations, granting maximum trust scores (Google Trust 1.0 - Instant Green Checkmark).
* **Instant Bypass Guard**: If the logged-in Gmail account ensures an immediate green checkmark without showing visual challenges, the bot detects the early exit of the AI, skips artificial pauses, forces an emergency hardware rewrite at maximum speed, and pushes data submission to Telekom followed by a protected 4.5-second delay to allow asynchronous tables to populate before the reading polling engages.
* **Telekom Technical Error Interceptor with Linear Rotation**: Detects the appearance of Telekom's native red error banner («Technikai hiba») in real time via page text parsing. If the proxy IP is rate-limited by the corporate server, the bot executes a *Graceful Shutdown* (immediate protected context closure to avoid orphan Playwright exceptions) and increments the index of the HTTPS-validated proxy pool linearly, moving strictly from the most performant server (lowest ping in ms) to the least responsive without ever resetting or returning to proxy 1.
* **Multi-Core Hardware Isolation**: PyTorch neural threading is strictly isolated to 1 Thread per Core at the absolute launch of the parent process to prevent redefinition errors (*Deadlocks*) and fully exploit massive processors (up to 32 parallel threads).

---

## 🛠️ Detailed Installation Guide (First Startup)

Strictly follow this command sequence inside the Windows terminal, positioning yourself in the project folder (`pyprojecktPATH\telekom_scraper`).

### 1. Creation and Activation of the Virtual Environment (Virtualenv)
Isolate the software libraries to avoid conflicts with other Python versions installed on your computer:
```bash
python -m venv venv
venv\Scripts\activate
```
*(After activation, you will see the `(venv)` text on the left side of the command prompt).*

### 2. Upgrade and Installation of Core Packages
Install Playwright engines, the ONNX runtime environment for the captcha neural network, network extensions for SOCKS proxies, multimedia suites, and audio manipulators:
```bash
pip install --upgrade pip
pip install httpx[socks] onnxruntime ultralytics openai-whisper torch torchvision opencv-python pydub numpy keyboard
```

### 3. Installation of Native Multimedia Binaries (FFmpeg)
To allow `pydub` and `whisper` to process audio directly in RAM memory, Windows requires native FFmpeg system binaries.
1. Download the *Essentials build* version from the official website or via the Windows package manager:
   ```bash
   winget install Gyan.FFmpeg
   ```
2. Ensure that the executable path is added to the Windows *System Environment Variables* (under the `PATH` entry).

### 4. Hardware Initialization of Playwright Browsers
Download the isolated and protected instance of the official Chromium engine on which the visible/headless automation will work:
```bash
playwright install chromium
```

---

## 📂 Mandatory File Structure on Disk

Before launching the software, ensure that the folder hierarchy follows this exact geometric layout on your hard drive. The downloaded model weights file must be strictly renamed to `model.onnx`:

```text
telekom_scraper/
│
├── telekom_scraper.py         # The main software source code
├── model.onnx                 # ONNX weights of the custom reCAPTCHA v2 neural network (DannyLuna17)
├── yolov8n.pt                 # Backup YOLOv8 weights for the visual grid
│
├── regioni/                   # Folder containing the geographical files of Hungarian Counties
│   ├── Budapest.txt           # List of internal municipalities/districts written line by line
│   └── Pest.txt
│
├── macro_settori/             # Folder containing the lists of commercial keywords
│   ├── Ipar és Gyártás.txt    # Commercial targets (e.g., raklap, raklap adás vétel)
│   └── Kereskedelem.txt
│
├── proxy_privati.txt          # List of your ordered SOCKS5/HTTP commercial proxies
└── venv/                      # The virtual working environment folder
```

---

## 🚀 Subsequent Launch & Daily Usage Guide

Every time you want to restart the extraction machine, open the Windows terminal and execute this standard sequence:

### 1. Environment activation and launch
```bash
cd YOURPATH\telekom_scraper
venv\Scripts\activate
python telekom_scraper.py
```

### 2. Interactive Boot Panel Configuration
The software will guide you step-by-step through questions in the terminal:

1. **Target Selection**: Press **`b`** to activate commercial extraction (*Business*) or **`n`** for sequential number scanning (*Numerica*).
2. **County/Macro-Sector Selection (Business Only)**: Type the number corresponding to the geographical county on disk (e.g., `3` for Budapest) and the number of the industrial niche file (e.g., `9` for the pallet market).
3. **AI Mode Selection**: Choose **`ai`** to leave the processing entirely to the resident ONNX Runtime and Whisper engines, or **`m`** for assisted manual debug mode on screen.
4. **Network Channel Selection (Proxy)**: 
   * Press **`c`** to travel **In Plain Text** (Recommended: Leverages the clean IP of your phone Hotspot/Home connection to eliminate blocks and browse at maximum speed).
   * Press **`g`** to activate the dynamic download of free proxies from GitHub (Performs an automatic pre-screening in HTTPS over Google, discarding on-the-fly nodes requiring credentials `407` or failing the `CONNECT` tunnel, sorting them from fastest in milliseconds to slowest).
   * Press **`p`** to load your commercial proxy list from the `proxy_privati.txt` file.
5. **Core Allocation**: Enter the number of parallel browser instances to launch. If you set 1 Core, the browser will open in full visible mode for monitoring; if you enter multiple cores, only Core 1 will be visible (master) while the remaining child processes run strictly hidden (`headless=True`) to avoid hijacking keyboard focus and preventing CPU locks.
6. **Equidistant Numerical Start Input**: Enter the desired area code prefix (e.g., `1`). The script will compute the geometric chunk distance based on active processes and ask you for the baseline number (e.g., `2249090`). Any blank spaces accidentally entered due to typing errors will be automatically cleaned by the `.replace()` filter.
7. **Progressive Recovery Management**: If the software detects that a partial CSV file already exists for that area in the folder (`results_regione_1_core1.csv`), it will ask you: *Resume from where it was interrupted? (si/no)*. Type **`si`**. The Core will instantly analyze the last written row, skip previously extracted targets, and cold-start from the exact sosta coordinates.

---

## 🎮 Emergency Controls & Automated Protections

* **Advanced Audio Fallback & Anti-Loop**: If Whisper decodes a noisy segment and Google rejects the text string or silently blocks the MP3 stream delivery due to a sanctioned proxy, the module detects the freeze within 5 seconds. It breaks the internal loop, raises the handled `Audio Trascrizione Errata` exception to the main worker, destroys the visual context, and increments the proxy index linearly to load the next fastest server in the pool, preventing the core from looping back to proxy 1.
* **`CTRL + Q` (Hardware Force-Kill)**: This is the armored global shortcut registered at the low Windows Kernel level. Pressing this combination at any time in the terminal halts the multi-core execution and **instantly wipes out all child processes and hanging Chromium instances left over in RAM**, cleaning the Task Manager in a millisecond.
* **Incessant Auto-Healing**: No intervention is required if the script encounters network congestion, undefined states, or blocked forms. The module destroys the unstable session, increments the linear index of sorted proxies in RAM, and regenerates a clean browser to keep hammering the same record until it is successfully extracted into the CSV file.

