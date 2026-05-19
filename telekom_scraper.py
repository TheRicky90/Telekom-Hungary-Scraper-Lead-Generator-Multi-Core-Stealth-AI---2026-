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

# --- DIZIONARIO OTTIMIZZATO PER MODELLO CUSTOM RECAPTCHA ONNX (LINGUA UNGHERESE) ---
DIZIONARIO_OGGETTI = {
    "motorkerékpár": ["motorcycle"], 
    "motorkerékpárok": ["motorcycle"],
    "kerékpár": ["bicycle"], 
    "kerékpárok": ["bicycle"], 
    "busz": ["bus"], 
    "buszok": ["bus"],
    "jelzőlámpa": ["traffic light"], 
    "jelzőlámpák": ["traffic light"], 
    "tűzcsap": ["fire hydrant"],
    "tűzcsapok": ["fire hydrant"], 
    "autó": ["car"], 
    "autók": ["car"], 
    "gyalogátkelőhely": ["crosswalk"],
    "gyalogátkelőhelyek": ["crosswalk"], 
    "zebra": ["crosswalk"],
    "teherautó": ["truck"],       # Aggiunto: Camion singolare ungherese
    "teherautók": ["truck"],      # Aggiunto: Camion plurale ungherese
    "kamion": ["truck"],          # Aggiunto: Variante colloquiale per tir/camion pesanti
    "kamionok": ["truck"]         # Aggiunto: Variante plurale
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
    """Screening su protocollo sicuro: valida i proxy in HTTPS ed esclude le richieste di credenziali."""
    if not lista_proxy_grezza:
        return []
        
    print(f"\n[*] Avvio screening di sicurezza su {len(lista_proxy_grezza)} proxy...")
    print("📌 CRITERIO HTTPS COMPATIBILE: Verifica dei tunnel SSL/TLS reali (Sito di test: https://google.com).")
    print("📌 FILTRO AUTH INTEGRATO: Scarto automatico di nodi che richiedono password o falliscono il CONNECT.")
    
    proxy_selezionati = []
    SEMAFORO_CONCORRENZA = asyncio.Semaphore(250)
    
    async def test_singolo_proxy_qualita(proxy_grezzo):
        try:
            p_pulito = str(proxy_grezzo).strip().replace(" ", "")
            if not p_pulito:
                return None
                
            if not p_pulito.startswith("http://") and not p_pulito.startswith("https://") and not p_pulito.startswith("socks"):
                proxy_url = f"http://{p_pulito}"
            else:
                proxy_url = p_pulito

            async with SEMAFORO_CONCORRENZA:
                tempo_inizio = asyncio.get_event_loop().time()
                
                mounts = {
                    "http://": httpx.AsyncHTTPTransport(proxy=proxy_url, verify=False),
                    "https://": httpx.AsyncHTTPTransport(proxy=proxy_url, verify=False)
                }
                
                # Test in HTTPS per garantire la massima stabilità con il tunnel crittografato di Playwright
                async with httpx.AsyncClient(mounts=mounts, timeout=7.0, verify=False) as client:
                    headers = {"User-Agent": random.choice(USER_AGENTS)}
                    response = await client.get("https://google.com", headers=headers, follow_redirects=False)
                    
                    # ✅ SINTASSI CORRETTA: Accetta codici validi (200, 302) ed esclude gli errori 407 di credenziali
                    if response.status_code in [200, 301, 302, 404, 403]:
                        ping_effettivo = (asyncio.get_event_loop().time() - tempo_inizio) * 1000
                        if ping_effettivo < 7000:
                            return {"url": proxy_url, "ping": int(ping_effettivo)}
        except Exception:
            pass
        return None

    task_vivi = [test_singolo_proxy_qualita(p) for p in lista_proxy_grezza]
    risultati = await asyncio.gather(*task_vivi)
    
    proxy_validi = [r for r in risultati if r is not None]
    proxy_validi.sort(key=lambda x: x["ping"])
    
    proxy_selezionati = [p["url"] for p in proxy_validi]
    
    print(f"\n[✓] Screening completato! Rilevati {len(proxy_selezionati)} proxy validi in HTTPS e pronti all'uso.")
    if proxy_selezionati:
        print(f"    -> Il proxy più reattivo risponde in: {proxy_validi[0]['ping']}ms")
        if len(proxy_validi) > 1:
            print(f"    -> Il proxy più lento accettato risponde in: {proxy_validi[-1]['ping']}ms")
    
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

async def analizza_e_clicca_griglia_cnn(iframe_context, modello_captcha_onnx, pid_info, core_id=1):
    """Risolutore visivo ONNX avanzato: analizza l'intera griglia con log dinamici isolati per processo."""
    try:
        el_istruzioni = await iframe_context.query_selector(SELETTORE_TESTO_ISTRUZIONI)
        if not el_istruzioni: return False
        
        testo_ricerca = (await el_istruzioni.inner_text()).lower().strip()
        target_yolo = []
        for chiave_it, valori_en in DIZIONARIO_OGGETTI.items():
            if chiave_it in testo_ricerca: target_yolo.extend(valori_en)
                
        if not target_yolo: 
            return False

        selettore_tabella = "table.rc-imageselect-table-33, table.rc-imageselect-table-44, .rc-imageselect-table-33"
        tabella_foto = await iframe_context.query_selector(selettore_tabella)
        if not tabella_foto or not await tabella_foto.is_visible(): return False
        
        box_tabella = await tabella_foto.bounding_box()
        if not box_tabella: return False

        tasselli_hardware = await iframe_context.query_selector_all(SELETTORE_TASSELLI_GRIGLIA)
        totale_tasselli = len(tasselli_hardware) if tasselli_hardware else 9
        
        colonne_totali = 4 if totale_tasselli == 16 else 3
        righe_totali = 4 if totale_tasselli == 16 else 3

        percorso_griglia_intera = f"temp_full_grid_{pid_info}_{random.randint(1000, 9999)}.png"
        await tabella_foto.screenshot(path=percorso_griglia_intera)
        
        img_matrice = cv2.imread(percorso_griglia_intera)
        if img_matrice is None:
            return False
            
        h_immagine, w_immagine, _ = img_matrice.shape
        w_cella_px = w_immagine / colonne_totali
        h_cella_px = h_immagine / righe_totali

        tasselli_da_cliccare = set()

        if modello_captcha_onnx and os.path.exists(percorso_griglia_intera):
            try:
                img_resized = cv2.resize(img_matrice, (640, 640))
                img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
                img_float = img_rgb.astype(np.float32) / 255.0
                img_transpose = np.transpose(img_float, (2, 0, 1))
                input_tensor = np.expand_dims(img_transpose, axis=0)

                nome_input_onnx = modello_captcha_onnx.get_inputs()[0].name
                nome_output_onnx = modello_captcha_onnx.get_outputs()[0].name

                risultati_onnx = modello_captcha_onnx.run([nome_output_onnx], {nome_input_onnx: input_tensor})
                
                scala_x = w_immagine / 640.0
                scala_y = h_immagine / 640.0

                predizioni = risultati_onnx[0]
                if predizioni.shape[0] < predizioni.shape[1]:
                    predizioni = predizioni.T

                for pred in predizioni:
                    cx_box, cy_box, w_box, h_box = pred[0:4]
                    classi_scores = pred[4:]
                    id_classe_max = np.argmax(classi_scores)
                    confidenza_max = classi_scores[id_classe_max]

                    nomi_classi_recaptcha = ["traffic light", "fire hydrant", "bus", "car", "motorcycle", "bicycle", "truck", "crosswalk"]
                    
                    if id_classe_max < len(nomi_classi_recaptcha):
                        nome_rilevato = nomi_classi_recaptcha[id_classe_max]
                        soglia_accettazione = 0.14 if nome_rilevato in ["traffic light", "fire hydrant", "bus"] else 0.20
                        
                        if nome_rilevato in target_yolo and confidenza_max > soglia_accettazione:
                            x_reale_centro = cx_box * scala_x
                            y_reale_centro = cy_box * scala_y
                            
                            colonna_assegnate = int(x_reale_centro / w_cella_px)
                            riga_assegnata = int(y_reale_centro / h_cella_px)
                            
                            indice_tassello_dom = (riga_assegnata * colonne_totali) + colonna_assegnate
                            if 0 <= indice_tassello_dom < totale_tasselli:
                                tasselli_da_cliccare.add(indice_tassello_dom)
            except Exception: pass

        try: os.remove(percorso_griglia_intera)
        except Exception: pass

        bottone_azione = await iframe_context.query_selector(BOTTONE_ZIONE_RECAPTCHA)
        
        if tasselli_da_cliccare:
            # ✅ FIX: Ora il log di tracciamento mostra dinamicamente l'ID reale del processo core attivo
            print(f"[CORE-{core_id}] [🧩 CUSTOM ONNX] Identificati {len(tasselli_da_cliccare)} quadranti validi dal modello Captcha-IA: {list(tasselli_da_cliccare)}")
            
            for idx_tassello in tasselli_da_cliccare:
                try:
                    riga_c = idx_tassello // colonne_totali
                    col_c = idx_tassello % colonne_totali
                    
                    cx = box_tabella["x"] + (col_c * (box_tabella["width"] / colonne_totali)) + (box_tabella["width"] / (colonne_totali * 2))
                    cy = box_tabella["y"] + (riga_c * (box_tabella["height"] / righe_totali)) + (box_tabella["height"] / (righe_totali * 2))
                    
                    await iframe_context.page().mouse.click(
                        cx + random.randint(-4, 4), 
                        cy + random.randint(-4, 4), 
                        force=True, 
                        delay=random.randint(90, 190)
                    )
                    await asyncio.sleep(random.uniform(0.2, 0.45))
                except Exception: pass
                
            await asyncio.sleep(random.uniform(2.5, 3.8))
            
            if bottone_azione: 
                await bottone_azione.click(force=True, delay=120)
            await asyncio.sleep(2.0) 
            return True
        else:
            # ✅ FIX: Log dinamico core allineato anche nel ramo del fallback
            print(f"[CORE-{core_id}] [🧩 CUSTOM ONNX] Nessun oggetto target intercettato dal modello. Passo la mano alla riserva audio Whisper...")
            if bottone_azione:
                await bottone_azione.click(force=True, delay=100)
                await asyncio.sleep(2.0)
                return True
        return False
    except Exception as e: 
        print(f"[!] Errore imprevisto in analizza_e_clicca_griglia_cnn: {e}")
        return False
    
async def gestisci_sistema_sicurezza_a_cascata(page, modello_captcha_onnx, pid_info, core_id=1, modello_whisper=None):
    """Cabina di regia unica: attende la reale comparsa del Captcha, lancia ONNX visivo e attiva Whisper veicolando core_id."""
    try:
        # ⏱️ ATTESA DI MATERIALIZZAZIONE: Diamo tempo al proxy di caricare gli Iframe di sicurezza reali a schermo
        iframe_rilevato = False
        for _ in range(6):
            iframes_test = await page.query_selector_all(SELETTORE_CAPTCHA_IFRAME)
            if iframes_test:
                for f_el in iframes_test:
                    if await f_el.is_visible():
                        iframe_rilevato = True
                        break
            if iframe_rilevato: 
                break
            await page.wait_for_timeout(500)

        if not iframe_rilevato:
            print(f"[CORE-{core_id}] [✓] Nessun captcha visibile a schermo. Procedo direttamente alla lettura...")
            return True

        # --- 🤖 SBLOCCO ANCORA MULTI-CORE BLINDATO ---
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
                        stato_aria = await quadratino.get_attribute("aria-checked")
                        if stato_aria == "true":
                            print(f"[🤖 AI] [✓] [CORE-{core_id}] Autenticazione automatica riuscita tramite cookie Gmail!")
                            return True
                            
                        print(f"[🤖 AI] [CORE-{core_id}] Trovata casella 'Non sono un robot'. Invio attivazione asincrona...")
                        await contesto_ancora.evaluate("(el) => el.click()", quadratino)
                        await page.wait_for_timeout(4000)
        except Exception as e:
            print(f"[w] Errore attivazione casella iniziale sul Core {core_id}: {e}")

        # --- 📸 ANALISI CICLICA DELLE IMMAGINI E AUDIO CON RALLENTAMENTO ---
        tentativi = 0
        while tentativi < 5:
            try:
                iframes = await page.query_selector_all(SELETTORE_CAPTCHA_IFRAME)
                if not iframes or not any(await f.is_visible() for f in iframes): 
                    print(f"[+] AI Successo [CORE-{core_id}] (Il widget è sparito dalla pagina/cerchio verde).")
                    return True
            except Exception:
                await page.wait_for_timeout(1000)
                continue
            
            trovato_in_ciclo = False
            griglia_visibile = False
            
            for iframe_element in iframes:
                try:
                    if not iframe_element or not await iframe_element.is_visible(): continue
                    iframe_context = await iframe_element.content_frame()
                    if not iframe_context: continue
                    
                    griglia_presente = await iframe_context.query_selector(SELETTORE_TASSELLI_GRIGLIA)
                    
                    # 🧩 ATTACCO 1: YOLO VISIVO DINAMICO IN PRIMA LINEA (ONNX ENGINE)
                    if griglia_presente and await griglia_presente.is_visible():
                        trovato_in_ciclo = True
                        griglia_visibile = True
                        tentativi += 1
                        print(f"[*] [CORE-{core_id}] Analisi visiva primaria della griglia tramite YOLOv8...")
                        
                        # ✅ VEICOLAZIONE CORE_ID CORRETTA ED ESPLICITA: Passa l'ID dinamico per isolare log e clic fisici
                        risultato_yolo = await analizza_e_clicca_griglia_cnn(iframe_context, modello_captcha_onnx, pid_info, core_id=core_id)
                        
                        if risultato_yolo:
                            await page.wait_for_timeout(3500)
                            try:
                                v_dati = await page.query_selector(SELETTORE_ZERO_RISULTATI)
                                p_dati = await page.query_selector(CONTAINER_RISULTATI)
                                griglia_ancora_viva = await page.query_selector("iframe[src*='bframe'], .rc-imageselect-challenge")
                                if v_dati or p_dati or not griglia_ancora_viva:
                                    return True
                            except Exception: pass
                        else:
                            return False
                        
                    # 🔄 ATTACCO 2: FALLBACK RISERVA AUDIO (Whisper con dettato testuale completo)
                    if not griglia_presente or tentativi >= 2:
                        bottone_audio_presente = await iframe_context.query_selector("#recaptcha-audio-button, .rc-button-audio")
                        if bottone_audio_presente and await bottone_audio_presente.is_visible():
                            trovato_in_ciclo = True
                            print(f"[*] [CORE-{core_id}] Attivazione paracadute Audio Challenge (Frase intera letterale)...")
                            
                            try:
                                risultato_audio = await risolvi_captcha_audio_whisper(page, iframe_context, core_id, pid_info, modello_whisper)
                            except Exception as e:
                                if "Audio Trascrizione Errata" in str(e): raise e
                                risultato_audio = False

                            if risultato_audio:
                                await page.wait_for_timeout(3000)
                                if await page.query_selector(SELETTORE_ZERO_RISULTATI) or await page.query_selector(CONTAINER_RISULTATI):
                                    return True
                                    
                    if not await iframe_element.is_visible():
                        return True
                        
                except Exception as e: 
                    if "Audio Trascrizione Errata" in str(e): raise e
                    continue
                    
            if trovato_in_ciclo and not griglia_visibile: return True
            if not trovato_in_ciclo: 
                await page.wait_for_timeout(2000)
                if not await page.query_selector("iframe[src*='bframe'], .rc-imageselect-challenge"): return True
                
            await page.wait_for_timeout(2500)
        return False
    except Exception as e: 
        if "Audio Trascrizione Errata" in str(e): raise e
        print(f"[!] Errore imprevisto in gestisci_sistema_sicurezza_a_cascata sul Core {core_id}: {e}")
        return False
    
async def risolvi_captcha_audio_whisper(page, iframe_context, core_id, pid_info, modello_whisper):
    """Trascrive la frase in RAM muovendo il mouse a curve paraboliche di Bézier sui pulsanti di Google."""
    
    # 🕹️ SOTTO-FUNZIONE INTERNA: Calcola ed esegue lo spostamento parabolico fluido verso un obiettivo grafico
    async def muovi_mouse_curva_bezier(pagina_attiva, x_dest, y_dest):
        try:
            # Recupera la posizione di partenza attuale del mouse o la imposta casuale
            posizione_mouse = await pagina_attiva.evaluate("() => ({ x: window.innerWidth / 2, y: window.innerHeight / 2 })")
            x_start, y_start = posizione_mouse["x"], posizione_mouse["y"]
            
            # Calcola un punto di controllo casuale per flettere la retta e generare la parabola hardware
            x_controllo = (x_start + x_dest) / 2 + random.randint(-150, 150)
            y_controllo = (y_start + y_dest) / 2 + random.randint(-150, 150)
            
            passi_curva = random.randint(15, 28) # Numero di micro-passi per dare fluidità
            for passo in range(passi_curva + 1):
                t = passo / passi_curva
                # Equazione quadratica di Bézier per traiettorie biologiche asimmetriche
                x_corrente = (1 - t) ** 2 * x_start + 2 * (1 - t) * t * x_controllo + t ** 2 * x_dest
                y_corrente = (1 - t) ** 2 * y_start + 2 * (1 - t) * t * y_controllo + t ** 2 * y_dest
                
                await pagina_attiva.mouse.move(x_corrente, y_corrente)
                await asyncio.sleep(0.008) # Micro-sosta di attrito cinetico
            await pagina_attiva.wait_for_timeout(random.randint(100, 250))
        except Exception:
            await pagina_attiva.mouse.move(x_dest, y_dest)

    try:
        bottone_audio = await iframe_context.query_selector("#recaptcha-audio-button, .rc-button-audio, button.rc-button-audio")
        if not bottone_audio:
            return False
            
        print(f"[CORE-{core_id}] [🎧 AUDIO] Spostamento a curva di Bézier verso l'icona delle cuffie...")
        box_cuffie = await bottone_audio.bounding_box()
        if box_cuffie:
            x_target = box_cuffie["x"] + box_cuffie["width"] * random.uniform(0.3, 0.7)
            y_target = box_cuffie["y"] + box_cuffie["height"] * random.uniform(0.3, 0.7)
            # Sposta il mouse disegnando la parabola reale dello schermo
            await muovi_mouse_curva_bezier(page, x_target, y_target)
            
        await bottone_audio.click(force=True, delay=random.randint(90, 180))
        
        # Barriera di rilevazione blocco silenzioso Google immutata
        for controllo_blocco in range(10):
            await page.wait_for_timeout(500)
            bloccato = await iframe_context.query_selector(".rc-audiochallenge-error-message, :has-text('Túl sok kérés'), :has-text('Try again later'), :has-text('alternatívát'), :has-text('szokatlan forgalom')")
            if bloccato and await bloccato.is_visible():
                print(f"[CORE-{core_id}] [⚠️ PROXY FLAGGATO] Google ha bloccato l'audio per traffico anomalo. Forza riavvio...")
                raise RuntimeError("Audio Trascrizione Errata")
            el_link_test = await iframe_context.query_selector(".rc-audiochallenge-download-link, a[href*='payload']")
            if el_link_test: break

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
            print(f"[CORE-{core_id}] [⚠️ PROXY FLAGGATO] Nessuna traccia audio erogata da Google. Innesco riavvio...")
            raise RuntimeError("Audio Trascrizione Errata")
            
        audio_bytes = None
        async with httpx.AsyncClient(timeout=25.0, verify=False) as client:
            headers_audio = {"User-Agent": random.choice(USER_AGENTS)}
            response = await client.get(url_audio, headers=headers_audio)
            if response.status_code == 200 and len(response.content) > 0:
                audio_bytes = response.content

        if not audio_bytes: return False

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
        
        if not frase_pulita_finale: return False

        for frame in page.frames:
            campo_testo_audio = await frame.query_selector("xpath=//*[@id='audio-response']")
            if campo_testo_audio:
                box_input = await campo_testo_audio.bounding_box()
                if box_input:
                    # Spostamento geometrico mimetico verso il box di testo delle risposte
                    await muovi_mouse_curva_bezier(page, box_input["x"] + box_input["width"]/2, box_input["y"] + box_input["height"]/2)
                
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
                    box_verify = await bottone_verify.bounding_box()
                    if box_verify:
                        # Spostamento curvilineo verso il pulsante definitivo di convalida
                        await muovi_mouse_curva_bezier(page, box_verify["x"] + box_verify["width"]/2, box_verify["y"] + box_verify["height"]/2)
                        
                    await bottone_verify.click(force=True, delay=random.randint(120, 210))
                    print(f"[CORE-{core_id}] [✓] Frase testuale inviata via hardware.")
                    await page.wait_for_timeout(3000)
                    
                    errore_visibile = await frame.query_selector(".rc-audiochallenge-error-message, :has-text('Nem egyezik'), :has-text('Próbálja újra')")
                    if errore_visibile and await errore_visibile.is_visible():
                        print(f"[CORE-{core_id}] [⚠️ AUDIO ERRORE] Google ha respinto la frase. Sollevo eccezione di riavvio...")
                        raise RuntimeError("Audio Trascrizione Errata")
                        
                    return True
                break
                
        return False
    except Exception as e:
        if "Audio Trascrizione Errata" in str(e): raise e
        print(f"[CORE-{core_id}] [!] Errore modulo Audio Whisper: {e}")
        return False
    
async def inizializza_nuova_sessione(playwright_instance, core_id, lista_proxy_condivisa, tentativo_reset=0, tipo_ricerca="numerica", mostra_browser=False):
    """Inizializza il profilo Chrome sul disco isolando le sessioni dei core figli e garantendo l'oggetto Page reale."""
    tentativi_locali = 0
    url_target_avvio = URL_BUSINESS if tipo_ricerca == "business" else URL_DIRETTO
    
    # ANTI-LOCK GUARD DINAMICO: Il Core 1 (Master) usa la cartella principale stabile.
    # I core figli dal 2 in poi generano sottocartelle isolate per evitare conflitti LOCK di Windows.
    if core_id == 1:
        percorso_profilo_disco = os.path.join(os.path.expanduser("~"), "Desktop", f"telekom_user_profile_core_{core_id}")
    else:
        percorso_profilo_disco = os.path.join(os.path.expanduser("~"), "Desktop", f"telekom_user_profile_core_{core_id}", f"session_{tentativo_reset}")
    
    while tentativi_locali < 10:
        user_agent_scelto = random.choice(USER_AGENTS)
        proxy_config = None
        
        if lista_proxy_condivisa and len(lista_proxy_condivisa) > 0:
            indice_proxy = (core_id - 1 + tentativo_reset + tentativi_locali) % len(lista_proxy_condivisa)
            proxy_string = lista_proxy_condivisa[indice_proxy]
            proxy_config = {"server": proxy_string}
            print(f"[CORE-{core_id}] Apertura sessione {'visiva' if mostra_browser else 'invisibile'} con Proxy [{indice_proxy + 1}/{len(lista_proxy_condivisa)}]: {proxy_string}")
        else:
            if tentativi_locali == 0:
                print(f"[CORE-{core_id}] Apertura sessione {'visiva' if mostra_browser else 'invisibile'} in chiaro (Nessun Proxy).")
        
        argomenti_chromium = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-canvas-aa"
        ]
        
        try:
            context = await playwright_instance.chromium.launch_persistent_context(
                user_data_dir=percorso_profilo_disco,
                headless=not mostra_browser, 
                user_agent=user_agent_scelto,
                viewport={"width": 1280, "height": 720},
                proxy=proxy_config,
                ignore_https_errors=True,
                locale="hu-HU",
                timezone_id="Europe/Budapest",
                args=argomenti_chromium
            )
            
            # ✅ CORREZIONE CHIRURGICA: Estrae l'elemento INDICE 0 reale ([0]) dalla lista.
            # Questo garantisce che 'page' sia l'oggetto Page corretto di Playwright e NON una lista.
            if context.pages:
                page = context.pages[0]
            else:
                page = await context.new_page()
            
            # Ora add_init_script e goto girano sul binario hardware perfetto senza eccezioni
            await page.add_init_script("""() => {
                const nuovo_nav = Object.getPrototypeOf(navigator);
                delete nuovo_nav.webdriver;
                window.chrome = { runtime: {}, loadTimes: Date.now, csi: () => {}, app: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => []});
                Object.defineProperty(navigator, 'languages', {get: () => ['hu-HU', 'hu', 'en-US', 'en']});
            }""")
            
            timeout_navigazione = 45000 if proxy_config else 25000
            
            tempo_inizio_nav = asyncio.get_event_loop().time()
            await page.goto(url_target_avvio, wait_until="commit", timeout=timeout_navigazione)
            latenza_rilevata_ms = (asyncio.get_event_loop().time() - tempo_inizio_nav) * 1000
            
            sosta_iniziale = max(3000, min(8000, int(latenza_rilevata_ms * 1.8)))
            print(f"[CORE-{core_id}] Latenza Proxy: {int(latenza_rilevata_ms)}ms -> Attesa assestamento di {sosta_iniziale / 1000:.2f}s.")
            await page.wait_for_timeout(sosta_iniziale)
            break 
        except Exception as e:
            print(f"[CORE-{core_id}] [w] Errore nel caricamento iniziale del profilo: {e}")
            try: await context.close()
            except Exception: pass
            tentativi_locali += 1
            await asyncio.sleep(2)
    
    if tentativi_locali >= 10: 
        raise RuntimeError("Impossibile stabilire una connessione stabile sul disco.")
    
    # Cookie banner clicker
    try:
        selettori_xpath = ["button#ing-accept-all", "button:has-text('Minden elfogadása')", "button:has-text('Elfogadom')"]
        for sel in selettori_xpath:
            banner_trovato = await page.query_selector(sel)
            if banner_trovato and await banner_trovato.is_visible():
                await page.locator(sel).click(force=True, timeout=5000)
                await page.wait_for_timeout(1000)
                break
    except Exception: pass

    try: 
        input_verificare = INPUT_BUSINESS_NOME if tipo_ricerca == "business" else INPUT_TELEFONOSZAM
        await page.wait_for_selector(input_verificare, state="attached", timeout=15000)
        await page.wait_for_timeout(800)
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

    modello_captcha_onnx = None
    modello_whisper = None
    
    # ✅ FIX MONUMENTALE THREADING ONNX: Vincola la sessione a 1 singolo thread logico per core.
    # Questo sblocca la concorrenza hardware asincrona impedendo i congelamenti (Deadlock) del pool dei core.
    if modalita == "ai":
        try:
            import onnxruntime as ort
            
            opzioni_sessione = ort.SessionOptions()
            opzioni_sessione.intra_op_num_threads = 1
            opzioni_sessione.inter_op_num_threads = 1
            opzioni_sessione.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            
            modello_captcha_onnx = ort.InferenceSession(
                "model.onnx", 
                sess_options=opzioni_sessione, 
                providers=["CPUExecutionProvider"]
            )
            
            import whisper
            modello_whisper = whisper.load_model("tiny")
            print(f"[CORE-{core_id}] [+] AI ONNX Engine (Thread-Isolati) + Whisper agganciati stabilmente in RAM.")
        except Exception as e:
            print(f"[CORE-{core_id}] [!] Errore inizializzazione AI: {e}.")

    # 🎮 FUNZIONE INTERNA: UMANIZZAZIONE DELLA DIGITAZIONE SENZA CRASH ACCENTI
    async def digita_come_un_umano(locator_elemento, testo):
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

    indice_corrente_proxy_ram = config.get("indice_proxy_progressivo", 0)
    config["indice_proxy_progressivo"] = indice_corrente_proxy_ram

    if "login_fatto" not in config:
        config["login_fatto"] = False

    contatore_ricerche = 0

    async with async_playwright() as p:
        
        while (tipo_ricerca == "numerica" and 0 <= numero_corrente <= limite_massimo or tipo_ricerca == "business" and indice_business < len(accoppiate_assegnate)) and not stop_flag.value:
            
            try: 
                context, page = await inizializza_nuova_sessione(p, core_id, lista_proxy_condivisa, tentativo_reset=config["indice_proxy_progressivo"], tipo_ricerca=tipo_ricerca, mostra_browser=mostra_browser)
            except Exception as e:
                print(f"[CORE-{core_id}] [!] Fallimento totale del boot iniziale persistente: {e}. Ruoto proxy...")
                config["indice_proxy_progressivo"] += 1
                await asyncio.sleep(2)
                continue

            # 🎯 GATE DI AUTENTICAZIONE GOOGLE ATOMICO
            if not config["login_fatto"] and mostra_browser and core_id == 1:
                print("\n" + "="*80)
                print("🔑 GATE DI AUTENTICAZIONE GOOGLE ATTIVO (Fase Iniziale Unica)")
                print("   -> Il bot rimarrà in sosta per 60 secondi SOLO ADESSO per salvare i cookie.")
                print("   -> ⏩ LOGIN GIÀ ESISTENTE? Premi il tasto 'INVIO' nel terminale per saltare subito!")
                print("="*80 + "\n")
                
                scheda_login_gmail = await context.new_page()
                try:
                    await scheda_login_gmail.goto("https://google.com", wait_until="commit")
                    
                    loop = asyncio.get_event_loop()
                    task_lettura_input = loop.run_in_executor(None, sys.stdin.readline)
                    
                    for secondo_attesa in range(60, 0, -1):
                        if stop_flag.value: break
                        if task_lettura_input.done():
                            print(f"\n\n[⏩ BYPASS] Rilevato tasto INVIO. Salto la sosta di login...")
                            break
                        sys.stdout.write(f"\r[*] Tempo rimanente per il login (o premi INVIO per saltare): {secondo_attesa}s... ")
                        sys.stdout.flush()
                        await asyncio.sleep(1)
                    print("\n[✓] Autenticazione archiviata sul disco. Avvio scansione automatica continua...\n")
                except Exception: pass
                finally:
                    try: await scheda_login_gmail.close()
                    except Exception: pass
                
                config["login_fatto"] = True

            if tipo_ricerca == "business":
                config["indice_business_corrente"] = indice_business
            else:
                config["partenza"] = numero_corrente
                
            if tipo_ricerca == "numerica":
                numero_stringa_locale = str(numero_corrente).zfill(lunghezza_cifre)
                target_stringa_stampa = f"{prefisso_regione}{numero_stringa_locale}"
                if target_stringa_stampa in NUMERI_DA_IGNORARE:
                    numero_corrente = (numero_corrente + 1) if direzione == "su" else (numero_corrente - 1)
                    try: await context.close()
                    except Exception: pass
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
                    try: await context.close()
                    except Exception: pass
                    config["indice_proxy_progressivo"] += 1
                    continue

            contatore_ricerche += 1
            if contatore_ricerche > RESET_SESSIONE_OGNI_NUMERI:
                try: await context.close()
                except Exception: pass
                config["indice_proxy_progressivo"] += 1
                contatore_ricerche = 1
                continue
            
            print(f"[*] [CORE-{core_id}] Analisi bersaglio: {target_stringa_stampa}")

            try:
                await page.evaluate("""() => {
                    const divs = document.querySelectorAll("div.results, .results, .tudakozo-result-container, div.result-item");
                    divs.forEach(d => d.remove());
                }""")
                await page.wait_for_timeout(400)
            except Exception: pass
            
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
                    await page.wait_for_selector(INPUT_TELEFONOSZAM, timeout=int(10000 * moltiplicatore_attesa))
                    campo_input = page.locator(INPUT_TELEFONOSZAM)
                    await click_hardware_umanizzato(campo_input)
                    await campo_input.clear()
                    await digita_come_un_umano(campo_input, target_stringa_stampa)
                    await page.wait_for_timeout(500)
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
                        try: await context.close()
                        except Exception: pass
                        config["indice_proxy_progressivo"] += 1
                        continue
            else:
                try:
                    await page.evaluate("() => document.body.style.zoom = '1.0'")
                    await page.wait_for_selector(INPUT_BUSINESS_NOME, timeout=int(15000 * moltiplicatore_attesa))
                    
                    input_nome = page.locator(INPUT_BUSINESS_NOME)
                    await click_hardware_umanizzato(input_nome)
                    await input_nome.clear()
                    await digita_come_un_umano(input_nome, categoria_corrente)
                    
                    contenitore_citta_visibile = page.locator("xpath=//*[@id='combobox-input_3']")
                    await contenitore_citta_visibile.click(force=True)
                    await page.wait_for_timeout(1000) 
                    
                    input_citta_reale = page.locator("xpath=//*[@id='combobox-input_3-search-input']")
                    await input_citta_reale.click(force=True)
                    await input_citta_reale.clear()
                    await digita_come_un_umano(input_citta_reale, citta_corrente)
                    await page.wait_for_timeout(2000) 
                    
                    opzione_citta = page.locator(OPZIONE_CITTA_TENDINA)
                    try:
                        await opzione_citta.wait_for(state="attached", timeout=int(5000 * moltiplicatore_attesa))
                        await opzione_citta.click(force=True)
                    except Exception:
                        await page.keyboard.press("ArrowDown")
                        await page.wait_for_timeout(300)
                        await page.keyboard.press("Enter")
                    
                    await page.wait_for_timeout(500)
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(1000)
                    
                    bottone_cerca = page.locator(BOTTONE_CERCA_BUSINESS)
                    await bottone_cerca.click(force=True)
                except Exception:
                    try: await context.close()
                    except Exception: pass
                    config["indice_proxy_progressivo"] += 1
                    continue

            captcha_rilevato = False
            try:
                await page.wait_for_timeout(2000)
                if await page.query_selector(SELETTORE_CAPTCHA_IFRAME): captcha_rilevato = True
            except Exception: pass 
            
            if captcha_rilevato:
                print(f"[!] [CORE-{core_id}] Rilevato CAPTCHA per il bersaglio {target_stringa_stampa}.")
                risolto = False
                tempo_inizio_sblocco = asyncio.get_event_loop().time()
                
                if modalita == "ai" and modello_captcha_onnx is not None:
                    print(f"[*] [CORE-{core_id}] Avvio rischiaramento AI prioritario...")
                    try: 
                        risolto = await gestisci_sistema_sicurezza_a_cascata(page, modello_captcha_onnx, pid_info, core_id=core_id, modello_whisper=modello_whisper)
                    except Exception as e:
                        if "Audio Trascrizione Errata" in str(e):
                            print(f"[🤖 INCESSANTE] [CORE-{core_id}] Rilevato rifiuto audio Google. Eseguo chiusura protetta e ruoto l'indice...")
                            try: await context.close()
                            except Exception: pass
                            config["indice_proxy_progressivo"] += 1
                            continue
                        risolto = False
                
                if not risolto and mostra_browser and not usa_molti_core:
                    for secondo in range(120):
                        if stop_flag.value: break
                        await asyncio.sleep(1)
                        if not await page.query_selector("iframe[src*='bframe'], .rc-imageselect-challenge"):
                            risolto = True; break
                        if await page.query_selector(f"{SELETTORE_ZERO_RISULTATI}, {CONTAINER_RISULTATI}"):
                            risolto = True; break

                if not risolto:
                    print(f"[CORE-{core_id}] [!] Sblocco fallito sul captcha (AI Failed). Ruoto proxy...")
                    try: await context.close()
                    except Exception: pass
                    config["indice_proxy_progressivo"] += 1
                    continue
                
                durata_effettiva_sblocco = asyncio.get_event_loop().time() - tempo_inizio_sblocco
                if durata_effettiva_sblocco < 4.2:
                    print(f"[CORE-{core_id}] [✓] Successo Verde Istantaneo (Fiducia Google 1.0)! Forza invio dati...")
                    try:
                        input_reale = page.locator(INPUT_TELEFONOSZAM if tipo_ricerca == "numerica" else INPUT_BUSINESS_NOME)
                        await input_reale.focus()
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Backspace")
                        if tipo_ricerca == "numerica": await page.keyboard.type(target_stringa_stampa)
                        else: await page.keyboard.type(categoria_corrente)
                        await page.wait_for_timeout(500)
                        await page.keyboard.press("Enter")
                    except Exception: pass
                    await page.wait_for_timeout(4500)
                else:
                    print(f"[CORE-{core_id}] [✓] Captcha risolto tramite AI visiva/audio. Attesa assestamento tabelle asincrone Telekom...")
                    await page.wait_for_timeout(4500)

            # LETTURA RISULTATI CON POLLING DEL DOM PULITO SOTTO PROXY
            await page.wait_for_timeout(int(3500 * moltiplicatore_attesa))
            
            # INTERCETTAZIONE ERRORE TECNICO TELEKOM
            try:
                testo_completo_pagina = (await page.locator("body").inner_text()).lower()
                if "technikai hiba" in testo_completo_pagina or "próbálja újra" in testo_completo_pagina:
                    print(f"[CORE-{core_id}] [🚫 TELEKOM BLOCK] Errore Tecnico Aziendale. Ruoto al proxy ordinato successivo...")
                    try: await context.close()
                    except Exception: pass
                    config["indice_proxy_progressivo"] += 1  
                    continue
            except Exception: pass

            risultato_vuoto = await page.query_selector(SELETTORE_ZERO_RISULTATI)
            container = await page.query_selector(CONTAINER_RISULTATI)
            if not risultato_vuoto and not container:
                try:
                    await page.wait_for_selector(CONTAINER_RISULTATI, timeout=int(10000 * moltiplicatore_attesa))
                    container = await page.query_selector(CONTAINER_RISULTATI)
                except Exception:
                    try:
                        await page.wait_for_selector(SELETTORE_ZERO_RISULTATI, timeout=int(5000 * moltiplicatore_attesa))
                        risultato_vuoto = await page.query_selector(SELETTORE_ZERO_RISULTATI)
                    except Exception: pass

            if risultato_vuoto:
                print(f"[i] [CORE-{core_id}] Riscontro Certo (0 db) per {target_stringa_stampa}. Avanzo.\n")
                if tipo_ricerca == "numerica":
                    with open(nome_file_csv, mode='a', newline='', encoding='utf-8') as f:
                        csv.writer(f).writerow([target_stringa_stampa, "0 db - Nessun Risultato"])
                        f.flush()
                    numero_corrente = (numero_corrente + 1) if direzione == "su" else (numero_corrente - 1)
                else: 
                    indice_business += 1
                    config["indice_business_corrente"] = indice_business
                try: await context.close()
                except Exception: pass
                continue
            elif container:
                try:
                    btn_apri = await container.query_selector(BOTTONE_TENDINA)
                    if btn_apri: await btn_apri.click(force=True); await page.wait_for_selector(SELETTORE_TENDINA_DATI, timeout=6000)
                except Exception: pass
                
                righe_dati = await page.query_selector_all(SELETTORE_RIGHE_DATI)
                coppie = []
                if righe_dati:
                    for linea in righe_dati:
                        el_dt, el_dd = await linea.query_selector("dt"), await linea.query_selector("dd")
                        if el_dt and el_dd: coppie.append(f"{(await el_dt.inner_text()).strip()}: {(await el_dd.inner_text()).strip().replace('\n', ' ')}")
                if not coppie:
                    coppie = [r.strip() for r in (await container.inner_text()).split('\n') if r.strip() and "térkép" not in r.lower()]
                
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
                try: await context.close()
                except Exception: pass
            else:
                print(f"[i] [CORE-{core_id}] Stato indefinito. Ruoto linearmente...")
                try: await context.close()
                except Exception: pass
                config["indice_proxy_progressivo"] += 1
                continue

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
    accoppiate_business = []
    
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

        # Incrociamo le attività estratte dal file di testo con tutti i comuni della regione scelta
        for citta in lista_citta_regione:
            for target_attivita in lista_attivita_settore:
                accoppiate_business.append({"citta": citta, "categoria": target_attivita})

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
    
    # Impostazione della visualizzazione globale base per il controllo di ripristino
    mostra_browser_globale = True if (core_da_usare == 1 or modalita == "m") else False
    usa_molti_core = True if core_da_usare > 2 else False
    lunghezza_cifre = 7 if prefisso_input == 1 else 6

    # ==============================================================================
    # 📐 DIVISIONE LINEARE EQUIDISTANTE MATEMATICA (Sostituisce il vecchio array a 8 elementi fissi)
    # ==============================================================================
    configurazioni_geometriche_interi = []
    if tipo_ricerca_stringa == "numerica":
        # Calcola la capienza totale dell'intervallo numerico (10 milioni per Budapest, 1 milione per province)
        spazio_numerico_totale = 10000000 if prefisso_input == 1 else 1000000
        passo_distanza_core = spazio_numerico_totale // core_da_usare
        print(f"\n📌 SPARTIZIONE DINAMICA: Spazio diviso per {core_da_usare} core. Intercapedine: {passo_distanza_core} unità.")
        
        try:
            # Pulisce gli spazi vuoti digitati accidentalmente per evitare crash di conversione int()
            numero_partenza_base = int(input(f"[?] Inserisci il numero di partenza base (senza prefisso): ").strip().replace(" ", ""))
        except ValueError:
            print("[!] Numero non valido. Impostato di default a 0.")
            numero_partenza_base = 0

        # Calcola i punti di partenza distribuiti a ventaglio parallelo equidistante verso l'alto
        for i in range(core_da_usare):
            partenza_calcolata = (numero_partenza_base + (i * passo_distanza_core)) % spazio_numerico_totale
            configurazioni_geometriche_interi.append({
                "partenza": partenza_calcolata,
                "direzione": "su"
            })

    # ✅ CASSAFORTE DEL RECUPERO: Rileva se ci sono file precedenti
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
        print(f"\n[*] Generazione del piano di lavoro progressivo equidistante per {core_da_usare} Core attivi:")
        for idx in range(core_da_usare):
            nome_file_csv_core = f"results_regione_{controllo_prefisso_file}_core{idx+1}.csv"
            core_id_reale = idx + 1
            
            # ✅ ISOLAMENTO VISIVO HARDWARE MULTI-CORE:
            # Forza solo ed esclusivamente il Core 1 a essere visibile sul monitor desktop (se mostra_browser è True).
            # Tutti i restanti core figli (dal 2 all'8) vengono forzati in background (headless=True)
            # impedendo l'apertura selvaggia di finestre grafiche sul monitor.
            mostra_browser_core_specifico = mostra_browser_globale if core_id_reale == 1 else False
            
            if tipo_ricerca_stringa == "numerica":
                # Estrae la configurazione geometrica distribuita a ventaglio per il Core corrente
                cfg = configurazioni_geometriche_interi[idx]
                
                # Se riprendere è True, aggancia l'ultima riga salvata nel CSV specifico, altrimenti usa lo slot equidistante
                partenza = leggi_ultimo_numero_salvato(nome_file_csv_core, prefisso_input, lunghezza_cifre, cfg["direzione"], cfg["partenza"]) if riprendere else cfg["partenza"]
                
                task_configurati.append(({
                    "tipo_ricerca": "numerica", 
                    "prefisso": prefisso_input, 
                    "partenza": partenza, 
                    "direzione": cfg["direzione"], 
                    "core_id": core_id_reale, 
                    "usa_molti_core": usa_molti_core, 
                    "mostra_browser": mostra_browser_core_specifico, # Passa la schermatura visiva isolata
                    "modalita": modalita, 
                    "filtro_condiviso": anagrafiche_estratte
                }, stop_flag, lista_proxy_condivisa))
                
                print(f"  -> Core {core_id_reale}: Inizio progressivo calcolato da {prefisso_input}{str(partenza).zfill(lunghezza_cifre)} | Direzione: '{cfg['direzione']}' | Visivo: {mostra_browser_core_specifico}")
            else:
                # Distribuzione geometrica delle attività equamente divisa per i core attivi
                sotto_lista = [accoppiate_business[i] for i in range(len(accoppiate_business)) if i % core_da_usare == idx]
                
                # Trova l'esatto record di sosta per il Core specifico nel file business parziale
                indice_partenza_business = leggi_ultimo_indice_business_salvato(nome_file_csv_core, sotto_lista) if riprendere else 0
                
                task_configurati.append(({
                    "tipo_ricerca": "business", 
                    "prefisso": regione_scelta, 
                    "accoppiate": sotto_lista, 
                    "indice_business_corrente": indice_partenza_business, 
                    "core_id": core_id_reale, 
                    "usa_molti_core": usa_molti_core, 
                    "mostra_browser": mostra_browser_core_specifico, # Passa la schermatura visiva isolata
                    "modalita": modalita, 
                    "filtro_condiviso": anagrafiche_estratte
                }, stop_flag, lista_proxy_condivisa))
                
                rimanenti = len(sotto_lista) - indice_partenza_business
                print(f"  -> Core {core_id_reale}: Ripristinato ad indice {indice_partenza_business}. Rimanenti da cercare: {rimanenti}/{len(sotto_lista)} | Visivo: {mostra_browser_core_specifico}")
        
        print("\n[+] Configurazione completata. Avvio parallelo in corso...\n")
        print("📌 SCORCIATOIA DI CHIUSURA ATTIVA: Premi 'CTRL+Q' per arrestare forzatamente lo script in qualsiasi momento.\n")
        
        pool = Pool(processes=core_da_usare)
        keyboard.add_hotkey('ctrl+q', lambda: 'attivazione_kill_hardware_totale' in globals() and attivazione_kill_hardware_totale(stop_flag, pool))
        
        def chiusura_sigint(sig, frame):
            if 'attivazione_kill_hardware_totale' in globals():
                attivazione_kill_hardware_totale(stop_flag, pool)
        signal.signal(signal.SIGINT, chiusura_sigint)
        
        try: pool.map(lavoratore_processo_ponte, task_configurati)
        except SystemExit: pass
