import os
import sys
import time
import json
import secrets
import platform
import signal
import ctypes
from multiprocessing import Process, Value, cpu_count, Event, Manager, Array
from datetime import datetime

# --- VERIFICAÇÃO DE DEPENDÊNCIAS CRÍTICAS ---
try:
    from coincurve import PrivateKey
    BACKEND = "COINCURVE (C-BINDING / FAST)"
except ImportError:
    print("\n[ERRO] A biblioteca 'coincurve' é obrigatória para performance profissional.")
    print("Instale: pip install coincurve")
    sys.exit()

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore: RED=GREEN=YELLOW=CYAN=MAGENTA=WHITE=RESET=""
    class Style: BRIGHT=DIM=NORMAL=""

# Tenta importar psutil para info de hardware
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
    cpu_name = uname.processor
    logical_cores = os.cpu_count()
    
    ram_info = "N/A"
    if HAS_PSUTIL:
        mem = psutil.virtual_memory()
        ram_total = round(mem.total / (1024**3), 2)
        ram_info = f"{ram_total} GB"
    
    print(f"{Fore.WHITE}[*] OS      : {uname.system} {uname.release}")
    print(f"{Fore.WHITE}[*] CPU     : {cpu_name}")
    print(f"{Fore.WHITE}[*] THREADS : {logical_cores} (Ativas)")
    print(f"{Fore.WHITE}[*] RAM     : {ram_info}")
    print(f"{Fore.CYAN}................................................")
    return logical_cores

# --- GERENCIAMENTO DE DADOS ---
class TargetDatabase:
    def __init__(self):
        self.addresses = set()
        self.pubkeys = set()
    
    def load(self):
        if not os.path.exists(TARGET_FILE):
            print(f"{Fore.RED}[!] ERRO: '{TARGET_FILE}' não encontrado.")
            return False
        
        print(f"{Fore.YELLOW}[*] Carregando banco de dados de alvos...")
        try:
            with open(TARGET_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("1") or line.startswith("3") or line.startswith("bc1"):
                        self.addresses.add(line)
                    else:
                        self.pubkeys.add(line)
            
            print(f"{Fore.GREEN}[OK] Database Pronta: {len(self.addresses)} Endereços | {len(self.pubkeys)} PubKeys")
            return True
        except Exception as e:
            print(f"{Fore.RED}[!] Erro ao ler arquivo: {e}")
            return False

# --- WORKER DE MINERAÇÃO ---
def worker_engine(start_base, multiplier, mode, target_addresses, target_pubkeys, counter, found_event, stop_event, stop_on_find, found_list, lock, shared_key_display, core_id):
    """
    Motor Híbrido: Verifica Compressed e Uncompressed.
    """
    import hashlib, base58
    
    sha256 = hashlib.sha256
    new_ripemd160 = lambda: hashlib.new('ripemd160')
    b58encode = base58.b58encode_check
    PREFIX = b'\x00'
    
    current = start_base
    offset_count = 0
    
    while not stop_event.is_set():
        if stop_on_find and found_event.is_set(): 
            break

        if mode == "RANDOM":
            current = int.from_bytes(secrets.token_bytes(32), 'big')
        elif current > MAX_KEY_LIMIT:
            offset_count += 1
            current = start_base + (offset_count * 10000000)

        try:
            priv_bytes = current.to_bytes(32, 'big')
            pk = PrivateKey(priv_bytes)
        except:
            if mode != "RANDOM": current = 1
            continue

        # --- COMPRESSED FLOW ---
        pub_comp_bytes = pk.public_key.format(compressed=True)
        
        if target_pubkeys and pub_comp_bytes.hex() in target_pubkeys:
            save_discovery(current, pub_comp_bytes.hex(), "PubKey (Compressed)", found_list, lock)
            if stop_on_find: found_event.set()

        if target_addresses:
            h160 = new_ripemd160()
            h160.update(sha256(pub_comp_bytes).digest())
            addr_comp = b58encode(PREFIX + h160.digest()).decode()
            
            if addr_comp in target_addresses:
                save_discovery(current, addr_comp, "Address (Compressed)", found_list, lock)
                if stop_on_find: found_event.set()

        # --- UNCOMPRESSED FLOW ---
        pub_uncomp_bytes = pk.public_key.format(compressed=False)
        
        if target_pubkeys and pub_uncomp_bytes.hex() in target_pubkeys:
            save_discovery(current, pub_uncomp_bytes.hex(), "PubKey (Uncompressed)", found_list, lock)
            if stop_on_find: found_event.set()

        if target_addresses:
            h160_u = new_ripemd160()
            h160_u.update(sha256(pub_uncomp_bytes).digest())
            addr_uncomp = b58encode(PREFIX + h160_u.digest()).decode()
            
            if addr_uncomp in target_addresses:
                save_discovery(current, addr_uncomp, "Address (Uncompressed)", found_list, lock)
                if stop_on_find: found_event.set()

        # --- MOVIMENTO ---
        if mode == "GEOMETRIC":
            if multiplier > 1:
                current = current * multiplier
            else:
                current += 1
        elif mode == "LINEAR":
            current += multiplier

        # --- ATUALIZAÇÃO ---
        if current % 1000 == 0:
            with counter.get_lock(): counter.value += 1000
            if core_id == 0:
                try:
                    hex_str = format(current, '064x')
                    shared_key_display.value = hex_str.encode('utf-8')
                except: pass

# --- SISTEMA DE SALVAMENTO (WIF DUPLO) ---
def save_discovery(private_int, public_data, type_found, found_list, lock):
    priv_hex = format(private_int, '064x')
    
    with lock:
        if priv_hex in found_list: return
        found_list.append(priv_hex)
    
    import hashlib, base58
    
    # 1. WIF COMPRESSED (Sufixo 01) - Inicia com K ou L
    extended_comp = bytes.fromhex("80" + priv_hex + "01")
    first_c = hashlib.sha256(extended_comp).digest()
    chk_c = hashlib.sha256(first_c).digest()[:4]
    wif_compressed = base58.b58encode(extended_comp + chk_c).decode()

    # 2. WIF UNCOMPRESSED (Sem Sufixo) - Inicia com 5
    extended_uncomp = bytes.fromhex("80" + priv_hex)
    first_u = hashlib.sha256(extended_uncomp).digest()
    chk_u = hashlib.sha256(first_u).digest()[:4]
    wif_uncompressed = base58.b58encode(extended_uncomp + chk_u).decode()

    print(f"\n{Fore.MAGENTA}{Style.BRIGHT}" + "█"*75)
    print(f"      CRITICAL HIT: ALVO LOCALIZADO")
    print(f"{Fore.MAGENTA}{Style.BRIGHT}" + "█"*75)
    print(f"{Fore.WHITE}[+] TIPO : {type_found}")
    print(f"{Fore.WHITE}[+] ALVO : {Fore.CYAN}{public_data}")
    print(f"{Fore.WHITE}[+] HEX  : {Fore.GREEN}{priv_hex}")
    print(f"{Fore.WHITE}[+] DEC  : {private_int}")
    print(f"{Fore.YELLOW}[+] WIF (Compressed)   : {wif_compressed}")
    print(f"{Fore.YELLOW}[+] WIF (Uncompressed) : {wif_uncompressed}")
    print(f"{Fore.MAGENTA}" + "█"*75 + f"{Style.RESET_ALL}\n")

    with open(FOUND_FILE, "a") as f:
        f.write(f"[{datetime.now()}] TYPE: {type_found}\n")
        f.write(f"ALVO: {public_data}\n")
        f.write(f"HEX : {priv_hex}\n")
        f.write(f"WIF C: {wif_compressed}\n")
        f.write(f"WIF U: {wif_uncompressed}\n")
        f.write("-" * 50 + "\n")

# --- SMART SEEDS ---
def get_smart_seeds(num_cores, multiplier):
    bases = []
    candidate = 1
    while len(bases) < num_cores:
        is_redundant = False
        for b in bases:
            if candidate % b == 0:
                ratio = candidate // b
                temp = ratio
                while temp > 1 and temp % multiplier == 0:
                    temp //= multiplier
                if temp == 1:
                    is_redundant = True
                    break
        if not is_redundant:
            bases.append(candidate)
        candidate += 1
    return bases

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
    if os.name == 'nt': os.system('title BTC GOLD EDITION')

    print(f"{Fore.YELLOW}{Style.BRIGHT}")
    print(r"""
    ██████╗  ██████╗ ██╗     ██████╗ 
   ██╔════╝ ██╔═══██╗██║     ██╔══██╗
   ██║  ███╗██║   ██║██║     ██║  ██║
   ██║   ██║██║   ██║██║     ██║  ██║
   ╚██████╔╝╚██████╔╝███████╗██████╔╝
    ╚═════╝  ╚═════╝ ╚══════╝╚═════╝ 
          GOLD EDITION v5.0
    """)
    
    logical_cores = detect_system_specs()
    print("-" * 60)

    manager = Manager()
    found_list = manager.list()
    lock = manager.Lock()
    shared_key_display = Array('c', 66) 
    shared_key_display.value = b"Carregando..."
    
    found_event = Event()
    stop_event = Event()

    db = TargetDatabase()
    if not db.load():
        with open(TARGET_FILE, 'w') as f: 
            f.write("1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH\n")
            f.write("1Hz96kJKF2HLPGCfHzwnJPwsfJnjZVfXxF\n")
        print(f"{Fore.YELLOW}[AVISO] Arquivo '{TARGET_FILE}' criado.")
        return

    print(f"\n{Fore.YELLOW}[MODO DE OPERAÇÃO]")
    print(f"{Fore.WHITE}1. {Fore.CYAN}GEOMÉTRICO {Fore.WHITE}(Multiplicação Exponencial)")
    print(f"{Fore.WHITE}2. {Fore.CYAN}SEQUENCIAL {Fore.WHITE}(Linear / Range Attack)")
    print(f"{Fore.WHITE}3. {Fore.CYAN}RANDOM {Fore.WHITE}(Aleatório)")
    
    try:
        choice = input(f"\n{Fore.GREEN}>> Selecione: ")
    except KeyboardInterrupt: sys.exit()

    start_num = 1
    mode = "LINEAR"
    multiplier = 1 

    if choice == "1":
        mode = "GEOMETRIC"
        print(f"\n{Fore.YELLOW}[CONFIG GEOMÉTRICA]")
        try: 
            multiplier = int(input(f"{Fore.GREEN}>> Fator Multiplicador (ex: 2, 100): "))
            if multiplier < 2: multiplier = 2
        except: multiplier = 100
    
    elif choice == "2":
        mode = "LINEAR"
        print(f"\n{Fore.YELLOW}[CONFIG SEQUENCIAL]")
        print("Digite o Bit Inicial (ex: 66) OU deixe vazio para usar Checkpoint.")
        bit_input = input(f"{Fore.GREEN}>> Bit Inicial: ")
        
        if bit_input.strip():
            try: start_num = 2 ** (int(bit_input) - 1)
            except: start_num = 1
        else:
            cp = load_checkpoint()
            if cp > 1:
                if input(f"Retomar checkpoint {cp}? (s/n): ").lower() == 's': start_num = cp

        try:
            stride_in = input(f"{Fore.GREEN}>> Pulo/Stride (Padrão 1): ")
            multiplier = int(stride_in) if stride_in else 1
        except: multiplier = 1

    elif choice == "3":
        mode = "RANDOM"
    
    stop_on_find = input(f"\n{Fore.YELLOW}[?] Parar ao encontrar? (s/n): ").lower() == 's'

    counter = Value('L', 0)
    processes = []
    
    print(f"\n{Fore.YELLOW}[*] Iniciando {logical_cores} Workers (WIF Duplo Ativado)...")

    seeds = []
    if mode == "GEOMETRIC":
        seeds = get_smart_seeds(logical_cores, multiplier)
    else:
        for i in range(logical_cores): seeds.append(start_num + (i * multiplier))

    for i in range(logical_cores):
        real_multiplier = multiplier
        if mode == "LINEAR":
            real_multiplier = logical_cores * multiplier

        p = Process(target=worker_engine, args=(
            seeds[i], real_multiplier, mode, db.addresses, db.pubkeys, 
            counter, found_event, stop_event, stop_on_find, found_list, lock, shared_key_display, i
        ))
        p.daemon = True
        p.start()
        processes.append(p)

    start_time = time.time()
    try:
        while True:
            if stop_event.is_set(): break
            if stop_on_find and found_event.is_set():
                time.sleep(1)
                break
            
            time.sleep(0.2)
            elapsed = time.time() - start_time
            total = counter.value
            try: hex_view = shared_key_display.value.decode('utf-8')
            except: hex_view = "SYNC..."

            if elapsed > 0:
                hps = total / elapsed
                sys.stdout.write(
                    f"\r{Fore.YELLOW}[RUNNING] "
                    f"{Fore.WHITE}Speed: {Fore.GREEN}{hps:,.0f} keys/s "
                    f"{Fore.WHITE}| Total: {total:,} "
                    f"{Fore.WHITE}| Mode: {Fore.CYAN}{mode} (x{multiplier})\n"
                    f"{Fore.YELLOW}>> KEY: {Fore.WHITE}{hex_view}\033[F"
                )
                sys.stdout.flush()
                
                if mode == "LINEAR" and int(elapsed) % 30 == 0:
                    save_checkpoint(start_num + (total * multiplier))

    except KeyboardInterrupt:
        print(f"\n\n{Fore.RED}[!] PARANDO SISTEMA...")
        stop_event.set()
        if mode == "LINEAR":
            save_checkpoint(start_num + (counter.value * multiplier))

    finally:
        stop_event.set()
        for p in processes: p.terminate()
        print(f"{Fore.CYAN}[*] Sistema Desligado.")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()