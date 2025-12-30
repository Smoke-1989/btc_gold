import os
import sys
import time
import json
import secrets
import platform
import signal
import ctypes
import hashlib
import binascii
from multiprocessing import Process, Value, cpu_count, Event, Manager, Array
from datetime import datetime

# --- CONFIGURAÇÃO DE ALTA PERFORMANCE ---
# Desativa garbage collector automático dentro dos workers para evitar pausas
import gc

# --- VERIFICAÇÃO DE DEPENDÊNCIAS CRÍTICAS ---
try:
    from coincurve import PrivateKey
except ImportError:
    print("\n[CRITICAL ERROR] 'coincurve' não encontrado.")
    print("Execute: pip install -r requirements.txt")
    sys.exit()

try:
    import base58
except ImportError:
    print("\n[CRITICAL ERROR] 'base58' não encontrado.")
    print("Execute: pip install -r requirements.txt")
    sys.exit()

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore: RED=GREEN=YELLOW=CYAN=MAGENTA=WHITE=RESET=""
    class Style: BRIGHT=DIM=NORMAL=""

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# --- CONSTANTES ---
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_FILE = os.path.join(FILE_DIR, "alvos.txt")
FOUND_FILE = os.path.join(FILE_DIR, "found_gold.txt")
CHECKPOINT_FILE = os.path.join(FILE_DIR, "checkpoint.json")
MAX_KEY_LIMIT = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# --- DETECÇÃO DE HARDWARE ---
def detect_system_specs():
    print(f"{Fore.CYAN}[SYSTEM DIAGNOSTICS]..........................")
    uname = platform.uname()
    logical_cores = os.cpu_count()
    
    ram_info = "N/A"
    if HAS_PSUTIL:
        mem = psutil.virtual_memory()
        ram_total = round(mem.total / (1024**3), 2)
        ram_info = f"{ram_total} GB"
    
    print(f"{Fore.WHITE}[*] OS      : {uname.system} {uname.release}")
    print(f"{Fore.WHITE}[*] CPU     : {uname.processor}")
    print(f"{Fore.WHITE}[*] CORES   : {logical_cores} (Logical)")
    print(f"{Fore.WHITE}[*] RAM     : {ram_info}")
    print(f"{Fore.CYAN}................................................")
    return logical_cores

# --- LOADERS INTELIGENTES ---
def load_targets_binary(file_path):
    """
    Carrega endereços e converte IMEDIATAMENTE para HASH160 (bytes).
    Evita conversão base58 dentro do loop de mineração.
    """
    targets = set()
    raw_count = 0
    
    if not os.path.exists(file_path):
        return targets, 0

    print(f"{Fore.YELLOW}[*] Processando Database (Binary Mode)...")
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                # Suporte apenas a Legacy Addresses (P2PKH - Começam com 1)
                # Script ignora Bech32 por enquanto para maximizar velocidade em legacy
                if line.startswith("1"):
                    try:
                        # Decode Base58 -> Checksum Validation -> Remove Version Byte (1 byte)
                        # Resultado: 20 bytes do Hash160
                        full_payload = base58.b58decode_check(line)
                        h160 = full_payload[1:] # Remove prefixo 0x00
                        targets.add(h160)
                        raw_count += 1
                    except Exception:
                        continue
                        
        print(f"{Fore.GREEN}[OK] Otimizado: {len(targets)} Alvos únicos (HASH160 Bytes)")
        return targets, raw_count
    except Exception as e:
        print(f"{Fore.RED}[!] Erro ao processar alvos: {e}")
        return set(), 0

# --- ENGINE OTIMIZADA (V2.0) ---
def worker_engine(start_base, multiplier, mode, target_set, counter, found_event, stop_event, stop_on_find, found_list, lock, shared_key_display, core_id, scan_mode):
    """
    ENGINE V2.0:
    - Zero conversões de string no loop.
    - Zero conversões base58 no loop.
    - Comparação Bytes vs Bytes (Hash160).
    - Pipeline dedicado: SHA256 -> RIPEMD160.
    """
    
    # Imports locais para velocidade
    import hashlib
    
    # Pré-bind de funções globais para locais (Small Speedup)
    sha256 = hashlib.sha256
    new_ripemd = lambda: hashlib.new('ripemd160')
    
    # Configurações de Scan
    check_compressed = (scan_mode in [1, 3])
    check_uncompressed = (scan_mode in [2, 3])
    
    current = start_base
    
    # Cache local do set (evita overhead de IPC se fosse compartilhado, mas aqui é Copy-on-Write)
    local_targets = target_set
    
    # Prepara buffer de exibição
    last_update = time.time()
    
    # Desativa GC para loop crítico
    gc.disable()
    
    batch_size = 1000
    batch_counter = 0

    while not stop_event.is_set():
        if stop_on_find and found_event.is_set(): 
            break

        # Geração da Chave Privada
        # Utiliza inteiros nativos do Python (arbitrary precision) que são rápidos
        if mode == "RANDOM":
            current = int.from_bytes(secrets.token_bytes(32), 'big')
        
        try:
            # Coincurve é wrapper C (libsecp256k1), extremamente rápido
            priv_bytes = current.to_bytes(32, 'big')
            pk = PrivateKey(priv_bytes)
        except:
            if mode != "RANDOM": current += 1
            continue

        # --- FLUXO COMPRIMIDO ---
        if check_compressed:
            # Obtém bytes puros (33 bytes)
            pub_bytes_c = pk.public_key.format(compressed=True)
            
            # Hash160 (SHA256 -> RIPEMD160)
            r = new_ripemd()
            r.update(sha256(pub_bytes_c).digest())
            h160_c = r.digest()
            
            # COMPARAÇÃO BINÁRIA (O(1) lookup)
            if h160_c in local_targets:
                found_event.set()
                save_discovery_v2(current, h160_c, "Compressed", found_list, lock)

        # --- FLUXO DESCOMPRIMIDO ---
        if check_uncompressed:
            # Obtém bytes puros (65 bytes)
            pub_bytes_u = pk.public_key.format(compressed=False)
            
            # Hash160
            r = new_ripemd()
            r.update(sha256(pub_bytes_u).digest())
            h160_u = r.digest()
            
            # COMPARAÇÃO BINÁRIA
            if h160_u in local_targets:
                found_event.set()
                save_discovery_v2(current, h160_u, "Uncompressed", found_list, lock)

        # --- ATUALIZAÇÃO E MOVIMENTO ---
        batch_counter += 1
        if batch_counter >= batch_size:
            with counter.get_lock():
                counter.value += batch_size
            
            if core_id == 0:
                # Atualiza display a cada ~0.2s para não spammar lock
                now = time.time()
                if now - last_update > 0.2:
                    try:
                        hex_str = format(current, '064x')
                        shared_key_display.value = hex_str.encode('utf-8')
                    except: pass
                    last_update = now
            
            # Reativa GC brevemente para limpar memória se necessário
            # gc.collect() # (Opcional: Geralmente não necessário se não criamos lixo no loop)
            batch_counter = 0

        # Movimento Matemático
        if mode == "GEOMETRIC":
            current *= multiplier
        elif mode == "LINEAR":
            current += multiplier

# --- SISTEMA DE SALVAMENTO (RECONSTRUÇÃO) ---
def save_discovery_v2(private_int, h160_bytes, type_found, found_list, lock):
    """
    Reconstrói os dados legíveis apenas quando encontra algo.
    """
    priv_hex = format(private_int, '064x')
    
    with lock:
        if priv_hex in found_list: return
        found_list.append(priv_hex)
    
    # Reconstrução para display (Lento, mas só roda 1 vez na vida)
    version_byte = b'\x00'
    payload = version_byte + h160_bytes
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    address_str = base58.b58encode(payload + checksum).decode()
    
    # Gera WIFs
    wif_c = generate_wif(priv_hex, compressed=True)
    wif_u = generate_wif(priv_hex, compressed=False)

    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}" + "█"*75)
    print(f"      💰 JACKPOT: CHAVE ENCONTRADA! 💰")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}" + "█"*75)
    print(f"{Fore.WHITE}[+] TIPO     : {Fore.CYAN}{type_found}")
    print(f"{Fore.WHITE}[+] ENDEREÇO : {Fore.GREEN}{address_str}")
    print(f"{Fore.WHITE}[+] HEX      : {Fore.YELLOW}{priv_hex}")
    print(f"{Fore.WHITE}[+] INT      : {private_int}")
    print(f"{Fore.BLUE}[+] WIF (C)  : {wif_c}")
    print(f"{Fore.BLUE}[+] WIF (U)  : {wif_u}")
    print(f"{Fore.MAGENTA}" + "█"*75 + f"{Style.RESET_ALL}\n")

    with open(FOUND_FILE, "a") as f:
        f.write(f"[{datetime.now()}] FOUND: {address_str} ({type_found})\n")
        f.write(f"HEX: {priv_hex}\n")
        f.write(f"WIF C: {wif_c}\n")
        f.write(f"WIF U: {wif_u}\n")
        f.write("-" * 50 + "\n")

def generate_wif(priv_hex, compressed=True):
    import hashlib, base58
    if compressed:
        extended = bytes.fromhex("80" + priv_hex + "01")
    else:
        extended = bytes.fromhex("80" + priv_hex)
    
    first = hashlib.sha256(extended).digest()
    chk = hashlib.sha256(first).digest()[:4]
    return base58.b58encode(extended + chk).decode()

# --- CHECKPOINTS ---
def save_checkpoint(val):
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump({"last": val, "time": str(datetime.now())}, f)
    except: pass

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f: return int(json.load(f)["last"])
        except: pass
    return 1

# --- MAIN ---
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    if os.name == 'nt': os.system('title BTC GOLD PROFESSIONAL v2.0')

    print(f"{Fore.YELLOW}{Style.BRIGHT}")
    print(r"""
    ██████╗ ████████╗██╗██████╗ ███████╗
    ██╔══██╗╚══██╔══╝██║██╔══██╗██╔════╝
    ██████╔╝   ██║   ██║██║  ██║█████╗  
    ██╔══██╗   ██║   ██║██║  ██║██╔══╝  
    ██████╔╝   ██║   ██║██████╔╝███████╗
    ╚═════╝    ╚═╝   ╚═╝╚═════╝ ╚══════╝
    PROFESSIONAL EDITION v2.0 (BINARY ENGINE)
    """)
    
    cores = detect_system_specs()
    
    # 1. Carregamento Otimizado
    target_set, count = load_targets_binary(TARGET_FILE)
    if count == 0:
        print(f"{Fore.RED}[!] Nenhum alvo válido encontrado em '{TARGET_FILE}'.")
        print("Crie o arquivo com endereços P2PKH (começando com 1).")
        with open(TARGET_FILE, 'w') as f:
            f.write("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH\n")
        sys.exit()

    # 2. Configuração de Modo de Scan
    print(f"\n{Fore.YELLOW}[CONFIGURAÇÃO DE ALVO]")
    print(f"{Fore.WHITE}[1] Apenas Comprimidos (Padrão Moderno - Mais Rápido)")
    print(f"{Fore.WHITE}[2] Apenas Descomprimidos (Legado)")
    print(f"{Fore.WHITE}[3] AMBOS (Verificação Dupla - Mais Lento)")
    
    try:
        scan_choice = input(f"{Fore.GREEN}>> Escolha [1-3]: ").strip()
        scan_mode = int(scan_choice) if scan_choice in ['1','2','3'] else 1
    except: scan_mode = 1

    # 3. Configuração de Movimento
    print(f"\n{Fore.YELLOW}[MODO DE OPERAÇÃO]")
    print(f"{Fore.WHITE}1. {Fore.CYAN}SEQUENCIAL {Fore.WHITE}(Range Attack)")
    print(f"{Fore.WHITE}2. {Fore.CYAN}RANDOM {Fore.WHITE}(Sorte Absoluta)")
    print(f"{Fore.WHITE}3. {Fore.CYAN}GEOMÉTRICO {Fore.WHITE}(Multiplicação)")
    
    try:
        mode_choice = input(f"\n{Fore.GREEN}>> Selecione: ").strip()
    except: sys.exit()

    start_num = 1
    mode = "LINEAR"
    multiplier = 1

    if mode_choice == "1":
        mode = "LINEAR"
        print(f"\n{Fore.YELLOW}[CONFIG SEQUENCIAL]")
        print("Deixe vazio para continuar do Checkpoint ou digite o BIT (ex: 66).")
        bit_in = input(f"{Fore.GREEN}>> Bit Inicial: ")
        
        if bit_in.strip():
            try: start_num = 2 ** (int(bit_in) - 1)
            except: start_num = 1
        else:
            cp = load_checkpoint()
            if cp > 1:
                print(f"{Fore.CYAN}[*] Retomando do checkpoint: {cp}")
                start_num = cp

        # Distribuição de Carga para Sequencial
        # Cada core pega um range: Core 0 (0..1M), Core 1 (1M..2M)...
        # Para evitar overlap, usamos um "Stride" gigante
        # Mas a implementação mais simples é cada worker ter seu offset fixo
        # E todos incrementarem por (CORES * 1)
        multiplier = cores

    elif mode_choice == "2":
        mode = "RANDOM"

    elif mode_choice == "3":
        mode = "GEOMETRIC"
        multiplier = 2 # Padrão dobrar

    # 4. Execução
    manager = Manager()
    found_list = manager.list()
    lock = manager.Lock()
    found_event = Event()
    stop_event = Event()
    counter = Value('L', 0)
    shared_key_display = Array('c', 66)
    shared_key_display.value = b"Starting..."

    print(f"\n{Fore.YELLOW}[*] INICIANDO ENGINE V2.0 EM {cores} NÚCLEOS...")
    
    processes = []
    
    # Distribuição inicial das sementes
    for i in range(cores):
        # Seed inicial diferente para cada worker
        worker_start = start_num + i 
        
        p = Process(target=worker_engine, args=(
            worker_start, multiplier, mode, target_set, counter, 
            found_event, stop_event, True, found_list, lock, shared_key_display, i, scan_mode
        ))
        p.daemon = True
        p.start()
        processes.append(p)

    start_time = time.time()
    
    try:
        while True:
            time.sleep(0.5)
            if found_event.is_set():
                time.sleep(2) # Espera printar
                break
                
            elapsed = time.time() - start_time
            total = counter.value
            
            if elapsed > 0:
                hps = total / elapsed
                
                # Formatação visual profissional
                try: hex_view = shared_key_display.value.decode('utf-8')
                except: hex_view = "SYNC"
                
                status_bar = (
                    f"\r{Fore.BLUE}[RUNNING]{Fore.RESET} "
                    f"Speed: {Fore.GREEN}{hps:,.0f} keys/s{Fore.RESET} | "
                    f"Total: {Fore.WHITE}{total:,}{Fore.RESET} | "
                    f"Last Key: {Fore.YELLOW}{hex_view[-16:]}...{Fore.RESET}"
                )
                sys.stdout.write(status_bar)
                sys.stdout.flush()
                
                # Checkpoint automático a cada minuto
                if mode == "LINEAR" and int(elapsed) % 60 == 0:
                    # Salva a chave mais provável (base + total)
                    # Não é exato por causa do multiprocessamento, mas serve de base segura
                    save_checkpoint(start_num + (total * multiplier))

    except KeyboardInterrupt:
        print(f"\n\n{Fore.RED}[!] Interrupção detectada. Salvando e saindo...")
        if mode == "LINEAR":
            save_checkpoint(start_num + (counter.value * multiplier))
            
    finally:
        stop_event.set()
        for p in processes: p.terminate()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
