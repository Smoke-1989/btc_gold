import os
import sys
import time
import json
import secrets
import platform
import hashlib
import binascii
from multiprocessing import Process, Value, cpu_count, Event, Manager, Array
from datetime import datetime

# --- CONFIGURAÇÃO DE ALTA PERFORMANCE ---
import gc

# --- VERIFICAÇÃO DE DEPENDÊNCIAS CRÍTICAS ---
try:
    from coincurve import PrivateKey, PublicKey
    BACKEND = "COINCURVE"
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

# --- LOADERS UNIVERSAIS ---
def load_targets(file_path, input_type):
    targets = set()
    raw_count = 0
    if not os.path.exists(file_path):
        return targets, 0

    print(f"{Fore.YELLOW}[*] Processando Database ({input_type})...")
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                h160_bytes = None
                
                try:
                    # TIPO 1: ENDEREÇOS (1A1z...)
                    if input_type == "ADDRESS":
                        if line.startswith("1"):
                            full_payload = base58.b58decode_check(line)
                            h160_bytes = full_payload[1:]

                    # TIPO 2: HASH160 (Hex string: a1z2...)
                    elif input_type == "HASH160":
                        if len(line) == 40: # 20 bytes em hex
                            h160_bytes = bytes.fromhex(line)

                    # TIPO 3: PUBKEYS (Hex string: 02/03/04...)
                    elif input_type == "PUBKEY":
                        if len(line) > 60: # Simples check de comprimento
                            pub_bytes = bytes.fromhex(line)
                            # Converte PubKey -> SHA256 -> RIPEMD160
                            sha = hashlib.sha256(pub_bytes).digest()
                            rip = hashlib.new('ripemd160')
                            rip.update(sha)
                            h160_bytes = rip.digest()

                    if h160_bytes:
                        targets.add(h160_bytes)
                        raw_count += 1
                        
                except: continue

        print(f"{Fore.GREEN}[OK] Database Carregada: {len(targets)} Alvos Únicos (Normalizados para HASH160)")
        return targets, raw_count
    except Exception as e:
        print(f"{Fore.RED}[!] Erro ao processar alvos: {e}")
        return set(), 0

# --- ENGINE OTIMIZADA (V2.3 - ENTERPRISE SYNC) ---
def worker_engine(core_id, num_cores, start_val, stride, mode, multiplier, target_set, counter, found_event, stop_event, stop_on_find, found_list, lock, shared_key_display, scan_mode, range_start=None, range_end=None):
    """
    Worker sincronizado corretamente para todos os modos:
    
    LINEAR (Sequencial):
        Core i comeca em: start_val + i
        Pulo por iteração: stride (igual para todos)
        Resultado: cobertura sem colisao em: C0={start + 0, start + stride, start + 2*stride, ...}
                                            C1={start + 1, start + stride+1, start + 2*stride+1, ...}
    
    RANDOM:
        Cada core gera aleatorio dentro de [range_start, range_end]
        Distribuição uniforme garantida
    
    GEOMETRIC:
        Core i comeca em: start_val + i
        Operação: current *= multiplier a cada passo
        Resultado: C0={start, start*mult, start*mult^2, ...}
                  C1={start+1, (start+1)*mult, (start+1)*mult^2, ...}
    """
    import hashlib
    
    sha256 = hashlib.sha256
    new_ripemd = lambda: hashlib.new('ripemd160')
    
    check_compressed = (scan_mode in [1, 3])
    check_uncompressed = (scan_mode in [2, 3])
    
    BATCH_SIZE = 10000
    
    # INICIALIZAÇÃO: Cada core começa em seu ponto unico
    if mode == "LINEAR":
        current = start_val + core_id  # Offset único por core
    elif mode == "GEOMETRIC":
        current = start_val + core_id  # Offset único por core
    elif mode == "RANDOM":
        current = None  # Gerado aleatoriamente a cada iteração
    
    local_targets = target_set
    gc.disable()

    while not stop_event.is_set():
        if stop_on_find and found_event.is_set(): break

        for _ in range(BATCH_SIZE):
            
            # --- GERÃO DA CHAVE ---
            if mode == "LINEAR":
                # Já inicializada, apenas pula
                pass
            elif mode == "GEOMETRIC":
                # Já inicializada, apenas multiplica
                pass
            elif mode == "RANDOM":
                # Gera dentro do range
                if range_end:
                    current = secrets.randbelow(range_end - range_start) + range_start
                else:
                    current = int.from_bytes(secrets.token_bytes(32), 'big') % MAX_KEY_LIMIT
            
            try:
                priv_bytes = current.to_bytes(32, 'big')
                pk = PrivateKey(priv_bytes)
            except:
                # Se falhar, avança para próximo em modo LINEAR, ou gera novo em RANDOM
                if mode in ["LINEAR", "GEOMETRIC"]:
                    if mode == "LINEAR": current += stride
                    elif mode == "GEOMETRIC": current *= multiplier
                continue

            # --- HASHING E VERIFICAÇÃO ---
            if check_compressed:
                pub_c = pk.public_key.format(compressed=True)
                r = new_ripemd()
                r.update(sha256(pub_c).digest())
                h160_c = r.digest()
                
                if h160_c in local_targets:
                    found_event.set()
                    save_discovery_v2(current, h160_c, "Compressed", found_list, lock)
                    if stop_on_find: return

            if check_uncompressed:
                pub_u = pk.public_key.format(compressed=False)
                r = new_ripemd()
                r.update(sha256(pub_u).digest())
                h160_u = r.digest()
                
                if h160_u in local_targets:
                    found_event.set()
                    save_discovery_v2(current, h160_u, "Uncompressed", found_list, lock)
                    if stop_on_find: return
            
            # --- MOVIMENTO MATEMÁTICO (Após verificação) ---
            if mode == "LINEAR":
                current += stride
            elif mode == "GEOMETRIC":
                current *= multiplier
            # RANDOM: regera na próxima iteração
        
        # --- UPDATE GLOBAL (A CADA BATCH) ---
        with counter.get_lock():
            counter.value += BATCH_SIZE
        
        # Display atualizado
        if core_id == 0:
            try:
                hex_str = format(current, '064x')
                shared_key_display.value = hex_str.encode('utf-8')
            except: pass

# --- SISTEMA DE SALVAMENTO ---
def save_discovery_v2(private_int, h160_bytes, type_found, found_list, lock):
    priv_hex = format(private_int, '064x')
    with lock:
        if priv_hex in found_list: return
        found_list.append(priv_hex)
    
    version_byte = b'\x00'
    payload = version_byte + h160_bytes
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    address_str = base58.b58encode(payload + checksum).decode()
    
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
    suffix = "01" if compressed else ""
    extended = bytes.fromhex("80" + priv_hex + suffix)
    first = hashlib.sha256(extended).digest()
    chk = hashlib.sha256(first).digest()[:4]
    return base58.b58encode(extended + chk).decode()

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

def get_bit_range_input():
    print(f"\n{Fore.YELLOW}[CONFIGURAÇÃO DE RANGE (Aleatório)]")
    print("Ex: '66' (bit 66) | '1:256' (Full) | '10:20' (Intervalo)")
    val = input(f"{Fore.GREEN}>> Range: ").strip()
    
    start = 1
    end = MAX_KEY_LIMIT
    
    if not val: return start, end
        
    if ":" in val:
        try:
            parts = val.split(":")
            bit_min = int(parts[0])
            bit_max = int(parts[1])
            start = 2**(bit_min-1)
            end = 2**bit_max
        except: pass
    else:
        try:
            bit = int(val)
            start = 2**(bit-1)
            end = 2**bit
        except: pass
    return start, end

# --- MAIN ---
def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    if os.name == 'nt': os.system('title BTC GOLD PROFESSIONAL v2.3')

    print(f"{Fore.YELLOW}{Style.BRIGHT}")
    print(r"""
    ██████╗ ████████╗██╗██████╗ ███████╗
    ██╔══██╗╚══██╔══╝██║██╔══██╗██╔════╝
    ██████╔╝   ██║   ██║██║  ██║█████╗  
    ██╔══██╗   ██║   ██║██║  ██║██╔══╝  
    ██████╔╝   ██║   ██║██████╔╝███████╗
    ╚═════╝    ╚═╝   ╚═╝╚═════╝ ╚══════╝
    PROFESSIONAL EDITION v2.3 (ENTERPRISE SYNC)
    """)
    
    cores = detect_system_specs()
    
    # --- SELETOR DE INPUT DA DATABASE ---
    print(f"\n{Fore.YELLOW}[DATABASE INPUT FORMAT]")
    print(f"Qual o formato dos dados em '{os.path.basename(TARGET_FILE)}'?")
    print(f"[1] Endereços Bitcoin (1A1z...)")
    print(f"[2] HASH160 (Hexadecimal - 40 chars)")
    print(f"[3] Public Keys (Hexadecimal - 02/03/04...)")
    
    try: in_sel = input(f"{Fore.GREEN}>> Opção [1]: ").strip() or "1"
    except: in_sel = "1"
    
    input_type = "ADDRESS"
    if in_sel == "2": input_type = "HASH160"
    elif in_sel == "3": input_type = "PUBKEY"

    target_set, count = load_targets(TARGET_FILE, input_type)
    if count == 0:
        print(f"{Fore.RED}[!] Database vazia ou formato incorreto. Verifique '{TARGET_FILE}'")
        sys.exit()

    # 1. SCAN MODE
    print(f"\n{Fore.YELLOW}[ALVO - TIPO DE ENDEREÇO]")
    print(f"[1] Apenas Comprimidos (Recomendado/Rápido)")
    print(f"[2] Apenas Descomprimidos")
    print(f"[3] AMBOS")
    try: s_in = input(f"{Fore.GREEN}>> Opção [1]: ").strip() or "1"
    except: s_in = "1"
    scan_mode = int(s_in) if s_in in ['1','2','3'] else 1

    # 2. STOP ON FIND
    print(f"\n{Fore.YELLOW}[PARADA AUTOMÁTICA]")
    print(f"[S] Parar ao encontrar primeiro resultado")
    print(f"[N] Continuar minerando infinitamente (Padrão)")
    stop_choice = input(f"{Fore.GREEN}>> Opção [N]: ").strip().upper()
    stop_on_find = (stop_choice == 'S')

    # 3. OPERATION MODE
    print(f"\n{Fore.YELLOW}[MODO DE OPERAÇÃO]")
    print(f"1. SEQUENCIAL {Fore.CYAN}(Range Attack)")
    print(f"2. RANDOM {Fore.CYAN}(Range Aleatório)")
    print(f"3. GEOMÉTRICO {Fore.CYAN}(Multiplicação)")
    try: m_in = input(f"{Fore.GREEN}>> Selecione: ").strip()
    except: sys.exit()

    start_num = 1
    mode = "LINEAR"
    stride = 1
    multiplier = 1
    range_start = 1
    range_end = None

    if m_in == "1": # SEQUENCIAL
        mode = "LINEAR"
        print(f"\n{Fore.YELLOW}[CONFIG SEQUENCIAL]")
        print("Digite o BIT inicial (ex: 66) ou ENTER para Checkpoint")
        bit_in = input(f"{Fore.GREEN}>> Bit Inicial: ").strip()
        
        if bit_in:
            start_num = 2**(int(bit_in)-1)
        else:
            start_num = load_checkpoint()
            print(f"{Fore.CYAN}[INFO] Retomando de: {start_num}")

        print(f"\nPulo Padrão = {cores} (Para não repetir chaves entre cores)")
        try:
            stride_in = input(f"{Fore.GREEN}>> Stride/Pulo [Enter = {cores}]: ").strip()
            stride = int(stride_in) if stride_in else cores
        except: stride = cores
        
        print(f"{Fore.CYAN}[INFO] Cores 0-{cores-1} irão gerar chaves sem colisao")

    elif m_in == "2": # RANDOM
        mode = "RANDOM"
        range_start, range_end = get_bit_range_input()
        
    elif m_in == "3": # GEOMETRICO
        mode = "GEOMETRIC"
        print(f"\n{Fore.YELLOW}[CONFIG GEOMÉTRICA]")
        print("Digite BIT inicial (ex: 1) e o Fator Multiplicador")
        bit_in = input(f"{Fore.GREEN}>> Bit Inicial [1]: ").strip()
        start_num = 2**(int(bit_in)-1) if bit_in else 1
        
        try:
            mult_in = input(f"{Fore.GREEN}>> Fator Multiplicador [2]: ").strip()
            multiplier = int(mult_in) if mult_in else 2
        except: multiplier = 2
        
        print(f"{Fore.CYAN}[INFO] Sequence: C0={{start, start*{multiplier}, start*{multiplier}^2, ...}}")
        print(f"{Fore.CYAN}       C1={{start+1, (start+1)*{multiplier}, (start+1)*{multiplier}^2, ...}}")

    # --- EXECUÇÃO ---
    manager = Manager()
    found_list = manager.list()
    lock = manager.Lock()
    found_event = Event()
    stop_event = Event()
    counter = Value('L', 0)
    shared_key_display = Array('c', 66)
    shared_key_display.value = b"Starting..."

    print(f"\n{Fore.YELLOW}[*] INICIANDO ENGINE V2.3 EM {cores} CORES...")
    
    processes = []
    
    for i in range(cores):
        p = Process(target=worker_engine, args=(
            i, cores, start_num, stride, mode, multiplier, target_set, counter, 
            found_event, stop_event, stop_on_find, found_list, lock, shared_key_display, scan_mode, range_start, range_end
        ))
        p.daemon = True
        p.start()
        processes.append(p)

    start_time = time.time()
    
    try:
        while True:
            time.sleep(0.5)
            if stop_on_find and found_event.is_set():
                time.sleep(1)
                break
                
            elapsed = time.time() - start_time
            total = counter.value
            
            if elapsed > 0:
                hps = total / elapsed
                try: hex_view = shared_key_display.value.decode('utf-8')
                except: hex_view = "SYNC"
                
                sys.stdout.write(
                    f"\r{Fore.BLUE}[RUNNING] "
                    f"Speed: {Fore.GREEN}{hps:,.0f} k/s "
                    f"{Fore.WHITE}| Found: {len(found_list)} "
                    f"| {hex_view[-16:]}..."
                )
                sys.stdout.flush()
                
                if mode == "LINEAR" and int(elapsed) % 30 == 0:
                    # Checkpoint correto para LINEAR com múltiplos cores
                    # Estimamos em qual iteração estamos (batches processados)
                    iterations = total // 10000
                    checkpoint_val = start_num + (iterations * stride)
                    save_checkpoint(checkpoint_val)

    except KeyboardInterrupt:
        print(f"\n\n{Fore.RED}[!] Parando...")
        if mode == "LINEAR":
            iterations = counter.value // 10000
            checkpoint_val = start_num + (iterations * stride)
            save_checkpoint(checkpoint_val)
            
    finally:
        stop_event.set()
        for p in processes: p.terminate()
        print(f"{Fore.YELLOW}\n[*] Engine parado. Resultados salvos em '{FOUND_FILE}'")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
