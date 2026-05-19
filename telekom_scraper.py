import asyncio
import csv
import os
import random
import logging
import sys
import cv2
import signal
import numpy as np
import httpx
import whisper
import pydub
import io
import subprocess
import keyboard
import math
from multiprocessing import Pool, cpu_count, Manager
from playwright.async_api import async_playwright

# Disabilita i log nativi di sistema per mantenere pulito il terminale
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
logging.getLogger("ultralytics").setLevel(logging.ERROR)

# Forza PyTorch e OpenMP a usare un solo thread interno per evitare conflitti di memoria nel multiprocessing Windows
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# --- CONFIGURAZIONI STRUTTURA REALE TELEKOM ---
URL_HOME = "https://telekom.hu"
URL_DIRETTO = "https://telekom.hu/lakossagi/tudakozo#number"
URL_BUSINESS = "https://telekom.hu/lakossagi/tudakozo#business"

# Selettori Modulo Numerico (#number)
INPUT_TELEFONOSZAM = "input[aria-describedby*='input_4']" 

# Selettori Modulo Aziendale (#business) basati su XPath reali forniti
INPUT_BUSINESS_NOME = "xpath=//*[@id='text-field-input_5']"
INPUT_BUSINESS_CITTA = "xpath=//input[contains(@id, 'combobox-input_3')]"
INPUT_BUSINESS_VIA = "xpath=//input[contains(@id, 'combobox-input_4')]"
INPUT_BUSINESS_CIVICO = "xpath=//*[@id='text-field-input_6']"
# Sostituisci queste due costanti in cima al tuo script
OPZIONE_CITTA_TENDINA = "xpath=/html/body/main/div/div/div[1]/div[2]/div/section[3]/div/form/od-combobox[1]/div[2]/div/div[1]/div/div/span"
BOTTONE_CERCA_BUSINESS = "xpath=/html/body/main/div/div/div[1]/div[2]/div/section[3]/div/form/od-button/button"


# Riscontri e Risultati (Identici per entrambi i moduli di ricerca)
CONTAINER_RISULTATI = ".tudakozo-result-container, div.result-item, div.results"
SELETTORE_ZERO_RISULTATI = "div.results:has-text('Összes találat: 0 db')"
BOTTONE_TENDINA = "button[aria-label='Bővebb információk']"
SELETTORE_TENDINA_DATI = "div.table-dropdown"
SELETTORE_RIGHE_DATI = "div.expanded-content div.line"

# Selettori di Sicurezza (Cookie e CAPTCHA)
BOTTONE_COOKIE = "button:has-text('Elfogadom'), button:has-text('Minden elfogadása'), #accept-cookies, .cookie-accept-btn"
SELETTORE_CAPTCHA_IFRAME = "iframe[title*='recaptcha'], iframe[src*='bframe'], iframe[src*='api2/bframe'], iframe[src*='api2/anchor'], iframe[src*='recaptcha'], iframe[src*='hcaptcha'], .g-recaptcha, div[id*='captcha']"
SELETTORE_TESTO_ISTRUZIONI = ".rc-imageselect-desc-no-canonical, .rc-imageselect-instructions"
SELETTORE_TASSELLI_GRIGLIA = "td.rc-imageselect-tile"
BOTTONE_ZIONE_RECAPTCHA = "#recaptcha-verify-button, #recaptcha-next-button, button:has-text('Verify'), button:has-text('Next'), button:has-text('Avanti'), button:has-text('Verifica')"

RESET_SESSIONE_OGNI_NUMERI = 15

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

PROXY_DI_RISERVA = [
    "http://88.247.143.149:8080", "http://185.121.210.4:80", "http://103.146.177.200:80"
]

# --- DIZIONARIO AGGIORNATO PER RECAPTCHA IN LINGUA UNGHERESE ---
DIZIONARIO_OGGETTI = {
    "motorkerékpár": ["motorcycle", "bicycle"], "motorkerékpárok": ["motorcycle"],
    "kerékpár": ["bicycle"], "kerékpárok": ["bicycle"], "busz": ["bus", "truck"], "buszok": ["bus", "truck"],
    "jelzőlámpa": ["traffic light"], "jelzőlámpák": ["traffic light"], "tűzcsap": ["fire hydrant"],
    "tűzcsapok": ["fire hydrant"], "autó": ["car"], "autók": ["car"], "gyalogátkelőhely": ["crosswalk"],
    "gyalogátkelőhelyek": ["crosswalk"], "zebra": ["crosswalk"], "híd": ["bridge", "pylon"],
    "hidak": ["bridge"], "lépcső": ["stairs"], "lépcsők": ["stairs"], "hegy": ["mountain"],
    "hegyek": ["mountain"], "domb": ["mountain"], "dombok": ["mountain"], "traktor": ["tractor"]
}

NUMERI_DA_IGNORARE = {"13533200", "17595050"}
SEMAFORO_CONCORRENZA = asyncio.Semaphore(50)
LIMITE_PROXY = 48

def leggi_ultimo_numero_salvato(nome_file, prefisso, lunghezza_cifre, direzione, partenza_default):
    """Sincronizza il ripristino numerico leggendo l'ultimo record per calcolare la progressione di partenza."""
    if not os.path.exists(nome_file): 
        return partenza_default
        
    try:
        with open(nome_file, mode='r', encoding='utf-8') as f:
            righe = list(csv.reader(f))
            if len(righe) <= 1: 
                return partenza_default
                
            # Recupera l'ultimo numero registrato nella prima colonna (Logica originale)
            ultimo_numero_completo = righe[-1][0].strip()
            
            # Sottrae in sicurezza la stringa del prefisso per isolare il corpo numerico locale
            prefisso_str = str(prefisso)
            if ultimo_numero_completo.startswith(prefisso_str):
                corpo_locale = ultimo_numero_completo[len(prefisso_str):]
            else:
                corpo_locale = ultimo_numero_completo
                
            # Calcola la progressione matematica in base alla direzione geometrica del core
            numero_isolato = int(corpo_locale)
            return (numero_isolato + 1) if direzione == "su" else (numero_isolato - 1)
            
    except Exception: 
        return partenza_default
    
def leggi_ultimo_indice_business_salvato(nome_file_csv, lista_accoppiate_core):
    """Analizza il CSV del core, trova l'ultimo bersaglio registrato e restituisce l'indice da cui riprendere."""
    if not os.path.exists(nome_file_csv):
        return 0  # Il file non esiste, parte dall'inizio (indice 0)
        
    ultimo_identificativo = None
    try:
        with open(nome_file_csv, mode='r', encoding='utf-8') as f:
            lettore = list(csv.reader(f))
            if len(lettore) > 1:  # Se c'è almeno una riga oltre all'intestazione
                ultimo_identificativo = lettore[-1][0].strip()  # Prende la prima colonna dell'ultima riga
    except Exception as e:
        print(f"[⚠️ RIPRISTINO] Impossibile leggere il CSV precedente: {e}. Parto da 0.")
        return 0

    if not ultimo_identificativo:
        return 0

    print(f"[🔍 RIPRISTINO] Ultimo record rilevato nel CSV aziendale: '{ultimo_identificativo}'")
    
    # Cerchiamo in quale posizione della lista assegnata al core si trova questo bersaglio
    for idx, record in enumerate(lista_accoppiate_core):
        stringa_confronto = f"{record['categoria']} @ {record['citta']}".strip()
        if stringa_confronto == ultimo_identificativo:
            indice_ripartenza = idx + 1
            if indice_ripartenza < len(lista_accoppiate_core):
                print(f"[✓ RIPRISTINO] Trovato! Riprendo dall'indice {indice_ripartenza}/{len(lista_accoppiate_core)}.")
                return indice_ripartenza
            else:
                print("[✓ RIPRISTINO] Questo Core aveva già completato tutti i bersagli assegnati.")
                return len(lista_accoppiate_core)
                
    print("[⚠️ RIPRISTINO] Ultimo record non trovato nella lista attuale. Parto da 0.")
    return 0   
    
async def test_singolo_proxy(proxy_url, url_destinazione):
    if not proxy_url.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
        proxy_url = f"http://{proxy_url}"
    mounts = {"http://": httpx.AsyncHTTPTransport(proxy=proxy_url, verify=False), "https://": httpx.AsyncHTTPTransport(proxy=proxy_url, verify=False)}
    headers_dinamici = {"User-Agent": random.choice(USER_AGENTS), "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "hu-HU,hu;q=0.9"}
    try:
        async with httpx.AsyncClient(mounts=mounts, timeout=10.0, follow_redirects=True, verify=False) as proxy_client:
            response = await proxy_client.get(url_destinazione, headers=headers_dinamici)
            if response.status_code in [200, 403]: return proxy_url
    except Exception: pass
    return None

async def filtra_proxy_funzionanti(lista_proxy_grezza):
    """Screening adattivo per liste pubbliche: Salva i proxy vivi e li ordina dai più veloci ai più lenti."""
    if not lista_proxy_grezza:
        return []
        
    print(f"\n[*] Avvio screening su {len(lista_proxy_grezza)} proxy...")
    print("📌 CRITERIO ADATTIVO: Saranno estratti i server vivi ordinati per latenza (Timeout massimo: 2.5s).")
    
    proxy_selezionati = []
    SEMAFORO_CONCORRENZA = asyncio.Semaphore(150)
    
    async def test_singolo_proxy_qualita(proxy_url):
        try:
            tempo_inizio = asyncio.get_event_loop().time()
            
            async with SEMAFORO_CONCORRENZA:
                mounts = {
                    "http://": httpx.AsyncHTTPTransport(proxy=proxy_url, verify=False),
                    "https://": httpx.AsyncHTTPTransport(proxy=proxy_url, verify=False)
                }
                # Utilizziamo un timeout massimo di 2.5 secondi, sufficiente per i proxy pubblici vivi
                async with httpx.AsyncClient(mounts=mounts, timeout=2.5, verify=False) as client:
                    headers = {"User-Agent": random.choice(USER_AGENTS)}
                    response = await client.get("https://google.com", headers=headers)
                    
                    if response.status_code == 200:
                        ping_effettivo = (asyncio.get_event_loop().time() - tempo_inizio) * 1000
                        return {"url": proxy_url, "ping": int(ping_effettivo)}
        except Exception:
            pass
        return None

    task_vivi = [test_singolo_proxy_qualita(p) for p in lista_proxy_grezza]
    risultati = await asyncio.gather(*task_vivi)
    
    # Filtra ed ordina dal PIÙ VELOCE al PIÙ LENTO
    proxy_validi = [r for r in risultati if r is not None]
    proxy_validi.sort(key=lambda x: x["ping"])
    
    proxy_selezionati = [p["url"] for p in proxy_validi]
    
    print(f"\n[✓] Screening completato! Rilevati {len(proxy_selezionati)} proxy attivi.")
    if proxy_selezionati:
        # ✅ FIX SINTASSI: Lettura corretta del dizionario interno della lista ordinata
        print(f"    -> Il miglior proxy pubblico risponde in: {proxy_validi[0]['ping']}ms")
    
    return proxy_selezionati

async def scarica_proxy_github():
    
    url_all_proxies = "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt"
    print("[*] Download lista proxy aggiornata da GitHub in corso...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as session:
            response = await session.get(url_all_proxies)
            if response.status_code == 200:
                proxies = [r.strip() for r in response.text.split("\n") if r.strip() and not r.strip().startswith("#")]
                return await filtra_proxy_funzionanti(proxies)
    except Exception: pass
    print(f"[i] Livello fallback: Caricamento proxy di riserva...")
    return await filtra_proxy_funzionanti(PROXY_DI_RISERVA)

async def analizza_e_clicca_griglia_cnn(iframe_context, modello_yolo, pid_info):
    """Risolve in modo universale captcha statici da 9, 12 o 16 tasselli calcolando la matrice dal DOM."""
    try:
        el_istruzioni = await iframe_context.query_selector(SELETTORE_TESTO_ISTRUZIONI)
        if not el_istruzioni: return False
        
        testo_ricerca = (await el_istruzioni.inner_text()).lower().strip()
        target_yolo = []
        
        # Mappatura ungherese -> YOLOv8
        for chiave_it, valori_en in DIZIONARIO_OGGETTI.items():
            if chiave_it in testo_ricerca: 
                target_yolo.extend(valori_en)
                
        if not target_yolo: 
            print(f"[⚠️ YOLO] Nessuna corrispondenza nel dizionario per il testo: '{testo_ricerca}'")
            return False

        selettore_tabella_unica = "table.rc-imageselect-table-33, table.rc-imageselect-table-44, .rc-imageselect-table-33, .rc-imageselect-table-44"
        
        tabella_foto = await iframe_context.query_selector(selettore_tabella_unica)
        if not tabella_foto or not await tabella_foto.is_visible(): 
            return False

        box_tabella = await tabella_foto.bounding_box()
        if not box_tabella: return False

        # Contiamo quanti tasselli reali compongono questa griglia specifica
        tasselli_hardware = await iframe_context.query_selector_all(SELETTORE_TASSELLI_GRIGLIA)
        totale_tasselli = len(tasselli_hardware) if tasselli_hardware else 9
        
        # Calcolo adattivo automatico della matrice di righe e colonne
        if totale_tasselli == 16:
            colonne_totali = 4
            righe_totali = 4
            print(f"[🤖 YOLO-GEOMETRICO] Rilevata griglia complessa 4x4 ({totale_tasselli} quadranti).")
        elif totale_tasselli == 12:
            colonne_totali = 4
            righe_totali = 3
            print(f"[🤖 YOLO-GEOMETRICO] Rilevata griglia complessa 4x3 ({totale_tasselli} quadranti).")
        else:
            colonne_totali = 3
            righe_totali = 3
            print(f"[🤖 YOLO-GEOMETRICO] Rilevata griglia standard 3x3 ({totale_tasselli} quadranti).")

        percorso_griglia_intera = f"temp_grid_{pid_info}_{random.randint(1000, 9999)}.png"
        try:
            await tabella_foto.screenshot(path=percorso_griglia_intera)
            await asyncio.sleep(0.15)
        except Exception: return False

        img_completa = cv2.imread(percorso_griglia_intera)
        if img_completa is None or img_completa.size == 0:
            if os.path.exists(percorso_griglia_intera): os.remove(percorso_griglia_intera)
            return False

        altezza_img, larghezza_img, _ = img_completa.shape
        
        # Divisione proporzionale in RAM basata sulla matrice calcolata dal DOM
        h_tassello = altezza_img // righe_totali
        w_tassello = larghezza_img // colonne_totali
        
        tasselli_da_cliccare = []

        # Screening dinamico tarato sui coefficienti reali della matrice
        for indice in range(totale_tasselli):
            riga = indice // colonne_totali
            colonna = indice % colonne_totali
            
            y_inizio = riga * h_tassello
            y_fine = y_inizio + h_tassello
            x_inizio = colonna * w_tassello
            x_fine = x_inizio + w_tassello
            
            ritaglio_tassello = img_completa[y_inizio:y_fine, x_inizio:x_fine]
            percorso_frammento = f"temp_chunk_{pid_info}_{indice}.png"
            cv2.imwrite(percorso_frammento, ritaglio_tassello)
            
            logica_riconoscimento = False
            if os.path.exists(percorso_frammento) and os.path.getsize(percorso_frammento) > 0:
                try:
                    if modello_yolo:
                        risultati_ai = modello_yolo(percorso_frammento, verbose=False)
                        if risultati_ai:
                            for ris in risultati_ai:
                                if ris.boxes is not None:
                                    for box in ris.boxes:
                                        nome_rilevato = modello_yolo.names[int(box.cls)]
                                        soglia_confidenza = 0.10 if nome_rilevato in ["traffic light", "fire hydrant", "bus"] else 0.12
                                        
                                        if nome_rilevato in target_yolo and box.conf.item() > soglia_confidenza:
                                            logica_riconoscimento = True
                                            print(f"    -> Quadrante {indice} ({riga+1}x{colonna+1}): Intercettato '{nome_rilevato}' (Conf: {box.conf.item():.2f})")
                except Exception: pass
            
            try:
                if os.path.exists(percorso_frammento): os.remove(percorso_frammento)
            except Exception: pass

            # ✅ CORRETTO: Variabile riallineata alla sintassi corretta (con la 's')
            if logica_riconoscimento:
                tasselli_da_cliccare.append((indice, riga, colonna))

        if os.path.exists(percorso_griglia_intera): 
            os.remove(percorso_griglia_intera)

        # 3. COMPILAZIONE CLIC CON METRICA DEL MOUSE PROPORZIONALE ADATTIVA
        if tasselli_da_cliccare:
            for indice, riga, colonna in tasselli_da_cliccare:
                if tasselli_hardware and len(tasselli_hardware) > indice:
                    try:
                        # Calcolo dello spazio basato sulla divisione della matrice reale
                        centro_x_click = box_tabella["x"] + (colonna * (box_tabella["width"] / colonne_totali)) + (box_tabella["width"] / (colonne_totali * 2))
                        centro_y_click = box_tabella["y"] + (riga * (box_tabella["height"] / righe_totali)) + (box_tabella["height"] / (righe_totali * 2))
                        
                        await iframe_context.page().mouse.click(centro_x_click, centro_y_click, force=True, delay=random.randint(65, 125))
                        print(f"[🤖 YOLO-STATICO] Selezionato quadrante {indice} (Target cercato: {target_yolo}).")
                        await asyncio.sleep(random.uniform(0.18, 0.38))
                    except Exception: pass
        else:
            print(f"[🤖 YOLO-STATICO] Nessun riscontro per '{target_yolo}' nella tabella visualizzata.")

        # 4. PRESSIONE DEL BOTTONE CONFERMA CON TRAIETTORIA BIOMETRICA
        try:
            bottone_azione = await iframe_context.query_selector(BOTTONE_ZIONE_RECAPTCHA)
            if bottone_azione and await bottone_azione.is_visible():
                await asyncio.sleep(random.uniform(0.7, 1.3))
                box_b = await bottone_azione.bounding_box()
                if box_b:
                    x_u = box_b["x"] + box_b["width"] * random.uniform(0.3, 0.7)
                    y_u = box_b["y"] + box_b["height"] * random.uniform(0.3, 0.7)
                    await iframe_context.page().mouse.move(x_u, y_u, steps=random.randint(5, 10))
                
                await bottone_azione.click(force=True, delay=random.randint(90, 160))
                print("[🤖 YOLO-STATICO] [✓] Griglia inviata per la verifica globale.")
                await asyncio.sleep(3.0)
                return True
        except Exception: pass
            
        return True
    except Exception as e: 
        print(f"[!] Errore nel modulo visivo universale YOLO: {e}")
        return False
    
async def risolvi_captcha_audio_whisper(page, iframe_context, core_id, pid_info, modello_whisper):
    """Trascrive la frase in RAM ed innesca un hard-reset se Google rifiuta l'input trascritto."""
    try:
        bottone_audio = await iframe_context.query_selector("#recaptcha-audio-button, .rc-button-audio, button.rc-button-audio")
        if not bottone_audio:
            return False
            
        print(f"[CORE-{core_id}] [🎧 AUDIO] Clic su modulo vocale...")
        await bottone_audio.evaluate("(btn) => btn.click()")
        
        await page.wait_for_timeout(random.randint(2500, 4000))
        
        bloccato = await iframe_context.query_selector(".rc-audiochallenge-error-message, :has-text('Túl sok kérés'), :has-text('Try again later'), :has-text('alternatívát')")
        if bloccato and await bloccato.is_visible():
            print(f"[CORE-{core_id}] [⚠️ AUDIO ABORT] Sfida vocale inibita da Google.")
            return False

        url_audio = None
        for frame in page.frames:
            try:
                el_link = await frame.query_selector(".rc-audiochallenge-download-link, a[href*='payload']")
                if el_link:
                    url_audio = await el_link.get_attribute("href")
                    if url_audio: break
            except Exception: pass

        if not url_audio:
            try:
                el_link = await iframe_context.query_selector(".rc-audiochallenge-download-link, a[href*='payload']")
                if el_link: url_audio = await el_link.get_attribute("href")
            except Exception: pass

        if not url_audio:
            return False
            
        audio_bytes = None
        async with httpx.AsyncClient(timeout=25.0, verify=False) as client:
            headers_audio = {"User-Agent": random.choice(USER_AGENTS)}
            response = await client.get(url_audio, headers=headers_audio)
            if response.status_code == 200 and len(response.content) > 0:
                audio_bytes = response.content

        if not audio_bytes:
            return False

        segmento_audio = pydub.AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        durata_audio_ms = len(segmento_audio)
        print(f"[CORE-{core_id}] [🎧 AUDIO] Frase ricevuta (Durata: {durata_audio_ms / 1000:.2f}s). Simulazione ascolto umano...")
        await page.wait_for_timeout(durata_audio_ms + random.randint(600, 1400))

        segmento_audio = segmento_audio.set_frame_rate(16000).set_channels(1)
        array_audio_norm = np.frombuffer(segmento_audio.raw_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        risultato_audio = modello_whisper.transcribe(array_audio_norm, fp16=False, language="en")
        frase_trascritta = risultato_audio["text"].strip()
        
        frase_pulita_finale = frase_trascritta.replace(".", "").replace(",", "").replace(";", "").strip()
        print(f"[CORE-{core_id}] [🧠 WHISPER] Frase letterale finale decifrata: '{frase_pulita_finale}'")
        
        if not frase_pulita_finale:
            return False

        for frame in page.frames:
            campo_testo_audio = await frame.query_selector("xpath=//*[@id='audio-response']")
            if campo_testo_audio:
                await campo_testo_audio.click(force=True)
                await page.wait_for_timeout(random.randint(300, 600))
                
                await page.keyboard.press("Control+A")
                await page.wait_for_timeout(random.randint(150, 300))
                await page.keyboard.press("Backspace")
                await page.wait_for_timeout(random.randint(400, 800))
                
                for carattere in frase_pulita_finale:
                    ritardo_tasto = random.gauss(0.12, 0.03)
                    ritardo_reale = max(0.04, min(0.22, ritardo_tasto))
                    if carattere == " ":
                        await asyncio.sleep(random.uniform(0.15, 0.35))
                    await page.keyboard.type(carattere)
                    await asyncio.sleep(ritardo_reale)
                
                await page.wait_for_timeout(random.randint(1000, 1800))
                
                bottone_verify = await frame.query_selector("xpath=//*[@id='recaptcha-verify-button']")
                if bottone_verify:
                    await bottone_verify.click(force=True, delay=random.randint(120, 210))
                    print(f"[CORE-{core_id}] [✓] Frase testuale inviata via hardware.")
                    await page.wait_for_timeout(3000)
                    
                    # 🛡️ INTERCETTAZIONE ERRORE INPUT AUDIO DI GOOGLE:
                    # Se dopo il clic compare il testo di errore rosso ("Riprova" o "Non corrisponde"),
                    # significa che Whisper ha sbagliato parole. Inneschiamo l'Hard-Reset immediato.
                    errore_visibile = await frame.query_selector(".rc-audiochallenge-error-message, :has-text('Nem egyezik'), :has-text('Próbálja újra')")
                    if errore_visibile and await errore_visibile.is_visible():
                        print(f"[CORE-{core_id}] [⚠️ AUDIO ERRORE] Google ha respinto la frase. Sollevo eccezione di riavvio...")
                        raise RuntimeError("Audio Trascrizione Errata")
                        
                    return True
                break
                
        return False
    except Exception as e:
        # Se l'errore è dovuto alla trascrizione errata, lo rilancia verso il lavoratore ponte per cambiare IP
        if "Audio Trascrizione Errata" in str(e):
            raise e
        print(f"[CORE-{core_id}] [!] Errore modulo Audio Whisper: {e}")
        return False
    
async def gestisci_sistema_sicurezza_a_cascata(page, modello_yolo, pid_info, core_id=1, modello_whisper=None):
    """Cabina di regia: Lancia SUBITO YOLO visivo dinamico. Whisper interviene solo come riserva."""
    try:
        # --- ATTIVAZIONE CHECKBOX INIZIALE ---
        try:
            selettori_ancora_iframe = [
                "iframe[title*='reCAPTCHA']", "iframe[src*='anchor']", "xpath=//iframe[contains(@title, 'recaptcha')]"
            ]
            iframe_ancora = None
            for sel in selettori_ancora_iframe:
                iframe_ancora = await page.query_selector(sel)
                if iframe_ancora and await iframe_ancora.is_visible(): break
                    
            if iframe_ancora:
                contesto_ancora = await iframe_ancora.content_frame()
                if contesto_ancora:
                    quadratino = await contesto_ancora.query_selector("#recaptcha-anchor, .recaptcha-checkbox, div.recaptcha-checkbox-border")
                    if quadratino:
                        await contesto_ancora.evaluate("(el) => el.click()", quadratino)
                        await page.wait_for_timeout(4000)
        except Exception: pass

        tentativi = 0
        while tentativi < 5:
            try:
                if await page.query_selector(SELETTORE_ZERO_RISULTATI) or await page.query_selector(CONTAINER_RISULTATI):
                    return True
            except Exception: pass

            try:
                iframes = await page.query_selector_all(SELETTORE_CAPTCHA_IFRAME)
                if not iframes: return True
            except Exception:
                await page.wait_for_timeout(1000)
                continue
            
            trovato_in_ciclo = False
            
            for iframe_element in iframes:
                try:
                    if not iframe_element or not await iframe_element.is_visible(): continue
                    iframe_context = await iframe_element.content_frame()
                    if not iframe_context: continue
                    
                    griglia_presente = await iframe_context.query_selector(SELETTORE_TASSELLI_GRIGLIA)
                    
                    # 🧩 ATTACCO 1: YOLO VISIVO DINAMICO IN PRIMA LINEA
                    if griglia_presente and await griglia_presente.is_visible():
                        trovato_in_ciclo = True
                        tentativi += 1
                        print(f"[*] [CORE-{core_id}] Analisi visiva primaria della griglia tramite YOLOv8...")
                        risultato_yolo = await analizza_e_clicca_griglia_cnn(iframe_context, modello_yolo, pid_info)
                        
                        if risultato_yolo:
                            await page.wait_for_timeout(3000)
                            if await page.query_selector(SELETTORE_ZERO_RISULTATI) or await page.query_selector(CONTAINER_RISULTATI): 
                                return True
                        
                    # 🔄 ATTACCO 2: FALLBACK RISERVA AUDIO (Whisper con dettato testuale completo)
                    if not griglia_presente or tentativi >= 2:
                        bottone_audio_presente = await iframe_context.query_selector("#recaptcha-audio-button, .rc-button-audio")
                        if bottone_audio_presente:
                            trovato_in_ciclo = True
                            print(f"[*] [CORE-{core_id}] Attivazione paracadute Audio Challenge (Frase intera letterale)...")
                            risultato_audio = await risolvi_captcha_audio_whisper(page, iframe_context, core_id, pid_info, modello_whisper)
                            if risultato_audio:
                                await page.wait_for_timeout(2500)
                                if await page.query_selector(SELETTORE_ZERO_RISULTATI) or await page.query_selector(CONTAINER_RISULTATI):
                                    return True
                                    
                    if not await iframe_element.is_visible():
                        return True
                        
                except Exception: continue
                    
            if not trovato_in_ciclo: 
                await page.wait_for_timeout(2000)
                if not await page.query_selector("iframe[src*='bframe'], .rc-imageselect-challenge"): return True
                
            await page.wait_for_timeout(2500)
        return False
    except Exception: 
        return False
    
async def inizializza_nuova_sessione(browser, core_id, lista_proxy_condivisa, tentativo_reset=0, tipo_ricerca="numerica"):
    """Inizializza la sessione mascherando i driver audio e Canvas per eludere i blocchi silenziosi di Google."""
    tentativi_locali = 0
    url_target_avvio = URL_BUSINESS if tipo_ricerca == "business" else URL_DIRETTO
    
    while tentativi_locali < 10:
        user_agent_scelto = random.choice(USER_AGENTS)
        proxy_config = None
        
        if lista_proxy_condivisa and len(lista_proxy_condivisa) > 0:
            indice_proxy = (core_id - 1 + tentativo_reset + tentativi_locali) % len(lista_proxy_condivisa)
            proxy_string = lista_proxy_condivisa[indice_proxy]
            proxy_config = {"server": proxy_string}
            print(f"[CORE-{core_id}] Apertura sessione invisibile con Proxy: {proxy_string}")
        else:
            if tentativi_locali == 0:
                print(f"[CORE-{core_id}] Apertura sessione in chiaro (Nessun Proxy - IP locale attivo).")
        
        context = await browser.new_context(
            user_agent=user_agent_scelto,
            viewport={"width": 1280, "height": 720}, 
            proxy=proxy_config, 
            ignore_https_errors=True, 
            locale="hu-HU", 
            timezone_id="Europe/Budapest"
        )
        
        page = await context.new_page()
        
        # 🎯 BLINDATURA BIOMETRICA AUDIO & CANVAS: Forza l'interprete a dichiarare hardware multimediale vero
        await page.add_init_script("""() => {
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {}, loadTimes: Date.now, csi: () => {}, app: {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4]});
            Object.defineProperty(navigator, 'languages', {get: () => ['hu-HU', 'hu', 'en-US', 'en']});
            
            // Mascheramento driver Audio API (Inganna i controlli di Google sulla velocità delle frequenze vocali)
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const originale = AudioContext.prototype.createAnalyser;
                AudioContext.prototype.createAnalyser = function() {
                    const analyser = originale.apply(this, arguments);
                    const origGetFloat = analyser.getFloatFrequencyData;
                    analyser.getFloatFrequencyData = function(array) {
                        const res = origGetFloat.apply(this, arguments);
                        for(let i=0; i<array.length; i++) array[i] += Math.random() * 0.01;
                        return res;
                    };
                    return analyser;
                };
            }
        }""")
        
        try:
            timeout_navigazione = 45000 if proxy_config else 25000
            await page.goto(url_target_avvio, wait_until="commit", timeout=timeout_navigazione)
            await page.wait_for_timeout(2000)
            break 
        except Exception as e:
            print(f"[CORE-{core_id}] [w] Errore nel caricamento iniziale della pagina: {e}")
            await context.close()
            tentativi_locali += 1
            if not lista_proxy_condivisa and tentativi_locali >= 2: break
            await asyncio.sleep(2)
    
    if tentativi_locali >= 10: 
        raise RuntimeError("Impossibile connettersi al server del portale.")
    
    try:
        selettori_xpath = [
            "button#ing-accept-all",
            "button:has-text('Minden elfogadása')",
            "button:has-text('Elfogadom')",
            "xpath=//*[@id='frame-modals']/div/div/div/div/div/div/button"
        ]
        for sel in selettori_xpath:
            if await page.query_selector(sel):
                await page.locator(sel).click(force=True, timeout=5000)
                print(f"[CORE-{core_id}] [✓] Banner Cookie chiuso tramite: {sel}")
                await page.wait_for_timeout(1500)
                break
    except Exception: pass

    try: 
        input_verificare = INPUT_BUSINESS_NOME if tipo_ricerca == "business" else INPUT_TELEFONOSZAM
        await page.wait_for_selector(input_verificare, timeout=15000)
    except Exception:
        await context.close()
        raise RuntimeError("Aggancio form iniziale non riuscito.")
            
    return context, page

async def esegui_scansione_processo(config, stop_flag, lista_proxy_condivisa):
    tipo_ricerca = config.get("tipo_ricerca", "numerica")
    core_id = config["core_id"]
    usa_molti_core = config["usa_molti_core"]
    mostra_browser = config["mostra_browser"]  
    modalita = config["modalita"]
    prefisso_regione = config["prefisso"]
    pid_info = os.getpid()
    
    filtro_duplicati = config.get("filtro_condiviso", [])
    
    if not mostra_browser: await asyncio.sleep(random.uniform(4, 12) * core_id)
    
    nome_file_csv = f"results_regione_{prefisso_regione}_core{core_id}.csv"
    
    lunghezza_cifre = 7 if prefisso_regione == 1 else 6
    limite_massimo = int("9" * lunghezza_cifre)
    numero_corrente = config.get("partenza", 0)
    direzione = config.get("direzione", "su")
    
    accoppiate_assegnate = config.get("accoppiate", [])
    indice_business = config.get("indice_business_corrente", 0)

    if not os.path.exists(nome_file_csv):
        with open(nome_file_csv, mode='w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["Identificativo", "Anagrafica Completa"])

    modello_yolo = None
    modello_whisper = None
    
    if modalita == "ai":
        try:
            from ultralytics import YOLO
            modello_yolo = YOLO("yolov8n.pt")
            import whisper
            modello_whisper = whisper.load_model("tiny")
            print(f"[CORE-{core_id}] [+] AI locale (YOLO + Whisper) agganciata in RAM.")
        except Exception as e:
            print(f"[CORE-{core_id}] [!] Errore inizializzazione AI: {e}.")

    # 🎮 FUNZIONE INTERNA: UMANIZZAZIONE DELLA DIGITAZIONE SENZA CRASH ACCENTI
    async def digita_come_un_umano(locator_elemento, testo):
        """Digita il testo simulando le esitazioni umane, supportando i caratteri accentati."""
        await locator_elemento.focus()
        for carattere in testo:
            ritardo_gaussiano = random.gauss(0.10, 0.03)
            ritardo_reale = max(0.03, min(0.18, ritardo_gaussiano))
            if random.random() < 0.02: 
                await asyncio.sleep(random.uniform(0.2, 0.5))
            await locator_elemento.type(carattere)
            await asyncio.sleep(ritardo_reale)

    # 🎮 FUNZIONE INTERNA: CLICK UMANIZZATO CON PARABOLA E COORDINATE CASUALI
    async def click_hardware_umanizzato(locator_elemento):
        """Sposta il mouse ed esegue il clic in un punto casuale del pulsante per eludere i controlli."""
        try:
            box = await locator_elemento.bounding_box()
            if box:
                x_casuale = box["x"] + box["width"] * random.uniform(0.2, 0.8)
                y_casuale = box["y"] + box["height"] * random.uniform(0.2, 0.8)
                await page.mouse.move(x_casuale, y_casuale, steps=random.randint(4, 8))
                await page.wait_for_timeout(random.randint(100, 250))
            await locator_elemento.click(force=True)
        except Exception:
            await locator_elemento.click(force=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not mostra_browser)
        
        try: context, page = await inizializza_nuova_sessione(browser, core_id, lista_proxy_condivisa, tipo_ricerca=tipo_ricerca)
        except Exception as e:
            print(f"[CORE-{core_id}] [!] Fallimento totale del boot iniziale: {e}")
            await browser.close()
            raise RuntimeError("Boot Fallito")

        contatore_ricerche = 0
        
        while (tipo_ricerca == "numerica" and 0 <= numero_corrente <= limite_massimo or tipo_ricerca == "business" and indice_business < len(accoppiate_assegnate)) and not stop_flag.value:
            
            if tipo_ricerca == "business":
                config["indice_business_corrente"] = indice_business
                
            if tipo_ricerca == "numerica":
                numero_stringa_locale = str(numero_corrente).zfill(lunghezza_cifre)
                target_stringa_stampa = f"{prefisso_regione}{numero_stringa_locale}"
                if target_stringa_stampa in NUMERI_DA_IGNORARE:
                    numero_corrente = (numero_corrente + 1) if direzione == "su" else (numero_corrente - 1)
                    continue
            else:
                target_corrente = accoppiate_assegnate[indice_business]
                categoria_corrente = target_corrente["categoria"]
                citta_corrente = target_corrente["citta"]
                target_stringa_stampa = f"{categoria_corrente} @ {citta_corrente}"

            if contatore_ricerche > 0 and tipo_ricerca == "business":
                try:
                    await page.goto(URL_BUSINESS, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(random.randint(1000, 2000))
                except Exception:
                    await context.close()
                    context, page = await inizializza_nuova_sessione(browser, core_id, lista_proxy_condivisa, tipo_ricerca=tipo_ricerca)

            contatore_ricerche += 1
            if contatore_ricerche > RESET_SESSIONE_OGNI_NUMERI:
                await context.close()
                context, page = await inizializza_nuova_sessione(browser, core_id, lista_proxy_condivisa, tipo_ricerca=tipo_ricerca)
                contatore_ricerche = 1
            
            print(f"[*] [CORE-{core_id}] Analisi bersaglio: {target_stringa_stampa}")
            
            moltiplicatore_attesa = 1.0
            try:
                tempo_inizio = asyncio.get_event_loop().time()
                await page.evaluate("() => window.performance.timing.responseEnd - window.performance.timing.navigationStart")
                latenza_stimata = (asyncio.get_event_loop().time() - tempo_inizio) * 1000
                if latenza_stimata > 800: moltiplicatore_attesa = min(3.5, latenza_stimata / 700.0)
            except Exception:
                if lista_proxy_condivisa: moltiplicatore_attesa = 2.5

            if tipo_ricerca == "numerica":
                try:
                    await page.wait_for_selector(INPUT_TELEFONOSZAM, timeout=int(6000 * moltiplicatore_attesa))
                    campo_input = page.locator(INPUT_TELEFONOSZAM)
                    await click_hardware_umanizzato(campo_input)
                    await campo_input.clear()
                    await digita_come_un_umano(campo_input, target_stringa_stampa)
                    await page.wait_for_timeout(300)
                    await campo_input.press("Enter")
                except Exception:
                    try:
                        await page.goto(URL_DIRETTO, wait_until="commit", timeout=15000)
                        await page.wait_for_selector(INPUT_TELEFONOSZAM, timeout=15000)
                        campo_input = page.locator(INPUT_TELEFONOSZAM)
                        await click_hardware_umanizzato(campo_input)
                        await campo_input.clear()
                        await digita_come_un_umano(campo_input, target_stringa_stampa)
                        await campo_input.press("Enter")
                    except Exception:
                        await context.close()
                        context, page = await inizializza_nuova_sessione(browser, core_id, lista_proxy_condivisa, tentativo_reset=1, tipo_ricerca=tipo_ricerca)
                        continue
            else:
                try:
                    # ✅ CORREZIONE: Zoom ripristinato stabilmente a 1.0 per garantire screenshot YOLO perfetti
                    await page.evaluate("() => document.body.style.zoom = '1.0'")
                    await page.wait_for_selector(INPUT_BUSINESS_NOME, timeout=int(15000 * moltiplicatore_attesa))
                    
                    # 1. Categoria
                    input_nome = page.locator(INPUT_BUSINESS_NOME)
                    await click_hardware_umanizzato(input_nome)
                    await input_nome.clear()
                    await digita_come_un_umano(input_nome, categoria_corrente)
                    await page.wait_for_timeout(random.randint(500, 1000))
                    
                    # 2. Tendina Città
                    contenitore_citta_visibile = page.locator("xpath=//*[@id='combobox-input_3-label'] | //*[@id='combobox-input_3']")
                    await contenitore_citta_visibile.wait_for(state="attached", timeout=int(15000 * moltiplicatore_attesa))
                    await click_hardware_umanizzato(contenitore_citta_visibile)
                    await page.wait_for_timeout(random.randint(400, 800)) 
                    
                    # 3. Digitazione Città
                    input_citta_reale = page.locator("xpath=//*[@id='combobox-input_3-search-input']")
                    await input_citta_reale.wait_for(state="attached", timeout=int(15000 * moltiplicatore_attesa))
                    await input_citta_reale.evaluate("(el) => el.focus()")
                    await input_citta_reale.clear()
                    await digita_come_un_umano(input_citta_reale, citta_corrente)
                    
                    await page.wait_for_timeout(int(3500 * moltiplicatore_attesa)) 
                    
                    # 4. Selezione riga tendina
                    opzione_citta = page.locator(OPZIONE_CITTA_TENDINA)
                    try:
                        await opzione_citta.wait_for(state="attached", timeout=int(8000 * moltiplicatore_attesa))
                        await click_hardware_umanizzato(opzione_citta)
                    except Exception:
                        await page.keyboard.press("ArrowDown")
                        await page.wait_for_timeout(random.randint(200, 400))
                        await page.keyboard.press("Enter")
                    
                    await page.wait_for_timeout(random.randint(500, 900))
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(random.randint(800, 1500))
                    
                    await page.evaluate("""() => {
                        const divs = document.querySelectorAll("div.results");
                        divs.forEach(d => {
                            if(d.textContent.includes('0 db') || d.textContent.includes('találat')) d.remove();
                        });
                        const items = document.querySelectorAll(".tudakozo-result-container, div.result-item");
                        items.forEach(i => i.remove());
                    }""")
                    await page.wait_for_timeout(400)
                    
                    # 5. Pulsante Cerca
                    bottone_cerca = page.locator(BOTTONE_CERCA_BUSINESS)
                    await bottone_cerca.wait_for(state="attached", timeout=int(15000 * moltiplicatore_attesa))
                    await click_hardware_umanizzato(bottone_cerca)
                    
                except Exception as e:
                    print(f"[CORE-{core_id}] [!] Errore riscontrato sul modulo: {e}. Innesco reset di insistenza...")
                    raise RuntimeError("Form Blocked")

            # 3. VERIFICA SICUREZZA CAPTCHA
            captcha_rilevato = False
            try:
                await page.wait_for_timeout(random.randint(1500, 2200))
                await page.wait_for_selector(SELETTORE_CAPTCHA_IFRAME, state="attached", timeout=int(5000 * moltiplicatore_attesa))
                captcha_rilevato = True
            except Exception: pass 
            
            if captcha_rilevato:
                print(f"[!] [CORE-{core_id}] Rilevato CAPTCHA per il bersaglio {target_stringa_stampa}.")
                risolto = False
                
                if modalita == "ai" and modello_yolo is not None:
                    print(f"[*] [CORE-{core_id}] Avvio rischiaramento AI prioritario...")
                    try: risolto = await gestisci_sistema_sicurezza_a_cascata(page, modello_yolo, pid_info, core_id=core_id, modello_whisper=modello_whisper)
                    except Exception: risolto = False
                
                if not risolto and mostra_browser and not usa_molti_core:
                    import winsound
                    winsound.Beep(1000, 400)
                    print(f" -> [CORE-{core_id}] Sblocco Assistito Attivo. Risolvi nel browser...")
                    for secondo in range(120):
                        if stop_flag.value: break
                        await asyncio.sleep(1)
                        if not await page.query_selector("iframe[src*='bframe'], .rc-imageselect-challenge"):
                            risolto = True; break
                        if await page.query_selector(f"{SELETTORE_ZERO_RISULTATI}, {CONTAINER_RISULTATI}"):
                            risolto = True; break

                if not risolto:
                    print(f"[CORE-{core_id}] [!] Sblocco fallito sul captcha. Cambio sessione hardware...")
                    raise RuntimeError("AI Failed")
                
                # Sosta protetta post sblocco riuscito per dare tempo al portale di ricevere il token
                print(f"[CORE-{core_id}] [✓] Captcha risolto. Attesa assestamento tabelle asincrone Telekom...")
                await page.wait_for_timeout(4500)

            # 4. LETTURA ATOMICA DEI CONTENITORI RISULTATO
            await page.wait_for_timeout(int(3500 * moltiplicatore_attesa))
            risultato_vuoto = await page.query_selector(SELETTORE_ZERO_RISULTATI)
            container = await page.query_selector(CONTAINER_RISULTATI)
            if not risultato_vuoto and not container:
                try:
                    await page.wait_for_selector(CONTAINER_RISULTATI, timeout=int(15000 * moltiplicatore_attesa))
                    container = await page.query_selector(CONTAINER_RISULTATI)
                except Exception:
                    try:
                        await page.wait_for_selector(SELETTORE_ZERO_RISULTATI, timeout=int(8000 * moltiplicatore_attesa))
                        risultato_vuoto = await page.query_selector(SELETTORE_ZERO_RISULTATI)
                    except Exception: pass

            if risultato_vuoto:
                print(f"[i] [CORE-{core_id}] Riscontro Certo (0 db) per {target_stringa_stampa}. Avanzo.\n")
                if tipo_ricerca == "numerica": numero_corrente = (numero_corrente + 1) if direzione == "su" else (numero_corrente - 1)
                else: 
                    indice_business += 1
                    config["indice_business_corrente"] = indice_business
                continue
            elif container:
                btn_apri = await container.query_selector(BOTTONE_TENDINA)
                if btn_apri:
                    try:
                        await page.evaluate("(btn) => btn.click()", btn_apri)
                        await page.wait_for_selector(SELETTORE_TENDINA_DATI, state="visible", timeout=int(12000 * moltiplicatore_attesa))
                        await page.wait_for_timeout(1500)
                    except Exception: pass
                
                righe_dati = await page.query_selector_all(SELETTORE_RIGHE_DATI)
                coppie = []
                if righe_dati:
                    for linea in righe_dati:
                        el_dt, el_dd = await linea.query_selector("dt"), await linea.query_selector("dd")
                        if el_dt and el_dd: coppie.append(f"{(await el_dt.inner_text()).strip()}: {(await el_dd.inner_text()).strip().replace('\n', ' ')}")
                if not coppie:
                    t_aperta = await page.query_selector(SELETTORE_TENDINA_DATI)
                    righe = [r.strip() for r in (await (t_aperta if t_aperta else container).inner_text()).split('\n') if r.strip()]
                    coppie = [r for r in righe if "térkép" not in r.lower() and "bezárás" not in r.lower() and "összes találat" not in r.lower()]
                
                dati_fissati = " | ".join(coppie)
                firma_anagrafica = dati_fissati.strip().lower()
                
                if firma_anagrafica in filtro_duplicati:
                    print(f"[🚫 DUPLICATO SCARTATO] [CORE-{core_id}] {target_stringa_stampa} ha prodotto dati già registrati.\n")
                else:
                    filtro_duplicati.append(firma_anagrafica)
                    with open(nome_file_csv, mode='a', newline='', encoding='utf-8') as f:
                        scrittore = csv.writer(f)
                        scrittore.writerow([target_stringa_stampa, dati_fissati])
                        f.flush()
                    print(f"[REGISTRATO] [CORE-{core_id}] {target_stringa_stampa} -> {dati_fissati}\n")
                
                if tipo_ricerca == "numerica": numero_corrente = (numero_corrente + 1) if direzione == "su" else (numero_corrente - 1)
                else: 
                    indice_business += 1
                    config["indice_business_corrente"] = indice_business
            else:
                print(f"[i] [CORE-{core_id}] Stato indefinito causato dalla rete. Ripristino sessione sullo stesso target...")
                raise RuntimeError("Stato Indefinito")
                
        await context.close(); await browser.close()

def lavoratore_processo_ponte(args):
    config, stop_flag, lista_proxy_condivisa = args
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    core_id = config.get("core_id", 1)
    
    if "indice_business_corrente" not in config:
        config["indice_business_corrente"] = 0
    
    while not stop_flag.value:
        if stop_flag.value: 
            break
            
        try:
            asyncio.run(esegui_scansione_processo(config, stop_flag, lista_proxy_condivisa))
            break
        except Exception as e:
            if stop_flag.value: 
                break
                
            # 🎯 GESTIONE PARACADUTE AUDIO & STRATEGIA INCESSANTE
            # L'indice rimane congelato sul record corrente. Non avanziamo.
            messaggio_errore = str(e)
            if "Audio Trascrizione Errata" in messaggio_errore:
                print(f"[🤖 INCESSANTE] [CORE-{core_id}] Google ha respinto il dettato vocale di Whisper.")
                print(f"[🤖 INCESSANTE] [CORE-{core_id}] Rigenerazione immediata della sessione per forzare un nuovo tentativo...")
            else:
                print(f"[🤖 INCESSANTE] [CORE-{core_id}] Errore riscontrato o anomalia di rete: {messaggio_errore}")
                print(f"[🤖 INCESSANTE] [CORE-{core_id}] Rigenerazione modulo e cambio proxy tra 6 secondi per forzare il bersaglio...")
                
                # Sosta standard solo per errori di rete, per l'errore audio ripartiamo a martello più velocemente
                for _ in range(6):
                    if stop_flag.value: break
                    import time
                    time.sleep(1)
                
            if stop_flag.value: 
                break
            continue
            
    return

def attivazione_kill_hardware_totale(stop_flag, pool):
    """Funzione di Force-Kill hardware attivata via scorciatoia da tastiera (CTRL+Q)."""
    print("\n\n[🛑 FORCE-KILL HARDWARE] Rilevata combinazione CTRL+Q!")
    print("[*] Arresto forzato e rimozione immediata dal processore di tutti i processi ed istanze Chromium...")
    
    # 1. Alza il flag per dire a tutti i thread e cicli while di fermarsi all'istante
    stop_flag.value = True
    
    # 2. Rade al suolo l'albero dei processi (script padre, core figli e browser appesi) via Taskkill
    pid_padre = os.getpid()
    subprocess.Popen(f"taskkill /F /T /PID {pid_padre}", shell=True)
    
    # 3. Chiusura di sicurezza dell'interprete Python
    sys.exit(0)

if __name__ == '__main__':
    # PROTEZIONE NEURALE MULTI-CORE: Configura l'isolamento dei thread PyTorch 
    # all'avvio assoluto del processo padre per prevenire errori di ridefinizione.
    try:
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:
        pass

    print("=========================================================")
    print("      PORTALE TELEKOM - OPERATIVO MULTI-CORE (2026)      ")
    print("=========================================================\n")
    
    # 1. SELEZIONE OBIETTIVO ESTRATTIVO
    tipo_ricerca = ""
    while tipo_ricerca not in ["n", "b"]:
        tipo_ricerca = input("[?] Vuoi eseguire una ricerca Numerica (n) o Aziendale/Business (b)?: ").strip().lower()
    
    tipo_ricerca_stringa = "numerica" if tipo_ricerca == "n" else "business"
    
    # Inizializzazione liste specifiche per la modalità Business
    regione_scelta = ""
    settore_scelto = ""
    lista_citta_regione = []
    lista_attivita_settore = []
    
    if tipo_ricerca_stringa == "business":
        # A. SELEZIONE GEOGRAFICA (REGIONE / CONTEA)
        cartella_regioni = "regioni"
        if not os.path.exists(cartella_regioni) or not os.listdir(cartella_regioni):
            print("[!] Errore: La cartella 'regioni' è vuota o inesistente.")
            sys.exit(1)
            
        file_regioni = [f.replace(".txt", "") for f in os.listdir(cartella_regioni) if f.endswith(".txt")]
        print("\n🌍 REGIONI RILEVATE SUL DISCO:")
        for i, reg in enumerate(file_regioni, 1): print(f"  [{i}] {reg}")
            
        while True:
            try:
                scelta_reg = int(input(f"[?] Inserisci il numero della Contea da scansionare (1-{len(file_regioni)}): ").strip())
                if 1 <= scelta_reg <= len(file_regioni):
                    regione_scelta = file_regioni[scelta_reg - 1]
                    break
            except ValueError: pass

        percorso_file_citta = os.path.join(cartella_regioni, f"{regione_scelta}.txt")
        with open(percorso_file_citta, "r", encoding="utf-8") as f:
            lista_citta_regione = [r.strip() for r in f if r.strip() and not r.startswith("#")]

        # B. SELEZIONE MACRO SETTORE DA FILE TXT
        cartella_macro_settori = "macro_settori"
        if not os.path.exists(cartella_macro_settori) or not os.listdir(cartella_macro_settori):
            print(f"[!] Errore: La cartella '{cartella_macro_settori}' è vuota o inesistente.")
            sys.exit(1)
            
        file_settori = [f.replace(".txt", "") for f in os.listdir(cartella_macro_settori) if f.endswith(".txt")]
        print("\n🏭 MACRO SETTORI AZIENDALI RILEVATE:")
        for i, set_file in enumerate(file_settori, 1): print(f"  [{i}] {set_file}")
        
        while True:
            try:
                scelta_set = int(input(f"[?] Inserisci il numero del Settore Macro da scansionare (1-{len(file_settori)}): ").strip())
                if 1 <= scelta_set <= len(file_settori):
                    settore_scelto = file_settori[scelta_set - 1]
                    break
            except ValueError: pass
            
        # Carica le attività/parole chiave scritte riga per riga dentro il file del settore scelto
        percorso_file_settore = os.path.join(cartella_macro_settori, f"{settore_scelto}.txt")
        with open(percorso_file_settore, "r", encoding="utf-8") as f:
            lista_attivita_settore = [r.strip() for r in f if r.strip() and not r.startswith("#")]
            
        print(f"\n[+] Caricamento Geometrico Semplificato Completato!")
        print(f"  -> Regione: {regione_scelta} ({len(lista_citta_regione)} Comuni)")
        print(f"  -> Settore Estratto: {settore_scelto} ({len(lista_attivita_settore)} Attività/Target da cercare)")

    # 2. SCELTA DELLA MODALITÀ DI LAVORO
    modalita = ""
    while modalita not in ["ai", "m"]:
        modalita = input("\n[?] Scegli modalità: AI automatica con YOLO (ai) o Assistita manuale a schermo (m): ").strip().lower()
    
    # 3. SELEZIONE E FILTRAGGIO DELLA SORGENTE PROXY
    proxy_scelta = input("[?] Usare proxy personalizzati (p), scaricare da GitHub (g) o in chiaro (c)?: ").strip().lower()
    proxy_globali = []
    if proxy_scelta == "p":
        if os.path.exists("proxy_privati.txt"):
            with open("proxy_privati.txt", "r") as f: proxy_globali = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        else:
            p_input = input("Inserisci i proxy personalizzati separati da virgola: ").strip()
            proxy_globali = [p.strip() for p in p_input.split(",") if p.strip()]
        proxy_globali = asyncio.run(filtra_proxy_funzionanti(proxy_globali))
    elif proxy_scelta == "g":
        proxy_globali = asyncio.run(scarica_proxy_github())
        
    # 4. CONFIGURAZIONE DIMENSIONE DEL POOL MULTI-CORE
    core_rilevati = cpu_count()
    print(f"\nHardware hardware rilevato: {core_rilevati} Core totali.")
    core_da_usare = int(input(f"Quanti Core desideri attivare?: ").strip())
    
    prefisso_input = regione_scelta if tipo_ricerca_stringa == "business" else 1
    if tipo_ricerca_stringa == "numerica":
        prefisso_input = int(input("Inserisci il prefisso (1 per Budapest, da 22 a 99 per province): ").strip())
    
    mostra_browser = True if (core_da_usare == 1 or modalita == "m") else False
    usa_molti_core = True if core_da_usare > 2 else False
    lunghezza_cifre = 7 if prefisso_input == 1 else 6

    # Incrociamo le attività estratte dal file di testo con tutti i comuni della regione scelta
    accoppiate_business = []
    if tipo_ricerca_stringa == "business":
        for citta in lista_citta_regione:
            for target_attivita in lista_attivita_settore:
                accoppiate_business.append({"citta": citta, "categoria": target_attivita})

    # Mappa geometrica estesa a 25 slot per evitare sovrapposizioni numeriche civile
    configurazioni_geometriche_interi = [
        {"partenza": 5555555, "direzione": "su"}, {"partenza": 5555555, "direzione": "giu"},
        {"partenza": 1111111, "direzione": "su"}, {"partenza": 9999999, "direzione": "giu"},
        {"partenza": 7500000, "direzione": "su"}, {"partenza": 2500000, "direzione": "giu"},  
        {"partenza": 7500000, "direzione": "giu"}, {"partenza": 2500000, "direzione": "su"}
    ]

    # ✅ CASSAFORTE DEL RECUPERO: Rileva se ci sono file precedenti sia per Business che per Numerica
    riprendere = False
    controllo_prefisso_file = regione_scelta if tipo_ricerca_stringa == "business" else prefisso_input
    
    for idx in range(core_da_usare):
        if os.path.exists(f"results_regione_{controllo_prefisso_file}_core{idx+1}.csv"):
            scelta = input("\n[?] Rilevati file precedenti per questa area. Riprendere da dove interrotta? (si/no): ").strip().lower()
            if scelta in ["si", "s", "y"]: riprendere = True
            break

    # 5. ALLOCAZIONE ED ESECUZIONE PARALLELA CONTROLLATA SUL CORE GENERALE
    with Manager() as manager:
        stop_flag = manager.Value('b', False)
        lista_proxy_condivisa = manager.list(proxy_globali)
        anagrafiche_estratte = manager.list()
        
        task_configurati = []
        print(f"\n[*] Generazione del piano di lavoro progressivo per {core_da_usare} Core attivi:")
        for idx in range(core_da_usare):
            nome_file_csv_core = f"results_regione_{controllo_prefisso_file}_core{idx+1}.csv"
            
            if tipo_ricerca_stringa == "numerica":
                cfg = configurazioni_geometriche_interi[idx % len(configurazioni_geometriche_interi)]
                partenza = leggi_ultimo_numero_salvato(nome_file_csv_core, prefisso_input, lunghezza_cifre, cfg["direzione"], cfg["partenza"]) if riprendere else cfg["partenza"]
                task_configurati.append(({"tipo_ricerca": "numerica", "prefisso": prefisso_input, "partenza": partenza, "direzione": cfg["direzione"], "core_id": idx + 1, "usa_molti_core": usa_molti_core, "mostra_browser": mostra_browser, "modalita": modalita, "filtro_condiviso": anagrafiche_estratte}, stop_flag, lista_proxy_condivisa))
                print(f"  -> Core {idx+1}: Inizio progressivo da {prefisso_input}{str(partenza).zfill(lunghezza_cifre)} | Direzione: '{cfg['direzione']}'")
            else:
                # Distribuzione geometrica delle attività equamente divisa per i core attivi
                sotto_lista = [accoppiate_business[i] for i in range(len(accoppiate_business)) if i % core_da_usare == idx]
                
                # ✅ CALCOLO INDICE PROGRESSIVO BUSINESS: Trova l'esatto record di sosta per il Core specifico
                indice_partenza_business = leggi_ultimo_indice_business_salvato(nome_file_csv_core, sotto_lista) if riprendere else 0
                
                task_configurati.append(({"tipo_ricerca": "business", "prefisso": regione_scelta, "accoppiate": sotto_lista, "indice_business_corrente": indice_partenza_business, "core_id": idx + 1, "usa_molti_core": usa_molti_core, "mostra_browser": mostra_browser, "modalita": modalita, "filtro_condiviso": anagrafiche_estratte}, stop_flag, lista_proxy_condivisa))
                
                rimanenti = len(sotto_lista) - indice_partenza_business
                print(f"  -> Core {idx+1}: Ripristinato ad indice {indice_partenza_business}. Rimanenti da cercare: {rimanenti}/{len(sotto_lista)}")
        
        print("\n[+] Configurazione completata. Avvio parallelo in corso...\n")
        print("📌 SCORCIATOIA DI CHIUSURA ATTIVA: Premi 'CTRL+Q' per arrestare forzatamente lo script in qualsiasi momento.\n")
        
        pool = Pool(processes=core_da_usare)
        keyboard.add_hotkey('ctrl+q', lambda: attivazione_kill_hardware_totale(stop_flag, pool))
        
        def chiusura_sigint(sig, frame):
            attivazione_kill_hardware_totale(stop_flag, pool)
        signal.signal(signal.SIGINT, chiusura_sigint)
        
        try: pool.map(lavoratore_processo_ponte, task_configurati)
        except SystemExit: pass