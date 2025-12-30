#!/usr/bin/env python3
"""
BTC GOLD Benchmark Tool
Mede performance real do programa em k/s (keys por segundo)

Uso: python benchmark.py
"""

import time
import hashlib
import os
import sys
from datetime import datetime

try:
    from coincurve import PrivateKey
except ImportError:
    print("[ERROR] Instale: pip install coincurve")
    sys.exit()

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore: RED=GREEN=YELLOW=CYAN=MAGENTA=WHITE=RESET=""
    class Style: BRIGHT=DIM=NORMAL=""

print(f"{Fore.YELLOW}{Style.BRIGHT}")
print(r"""
    ███████╗ ██████╗ ██╗   ██╗███╗   ██╗ ██████╗ 
    ██╔════╝██╔═══██╗██║   ██║████╗  ██║██╔════╝ 
    ███████╗██║   ██║██║   ██║██╔██╗ ██║██║  ███╗
    ╚════██║██║   ██║██║   ██║██║╚██╗██║██║   ██║
    ███████║╚██████╔╝╚██████╔╝██║ ╚████║╚██████╔╝
    ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ 
    BTC GOLD BENCHMARK v1.0
""")

print(f"{Fore.CYAN}[*] Iniciando benchmark...\n")

# Detectar CPU
logical_cores = os.cpu_count()
print(f"{Fore.WHITE}[*] CPU Cores: {logical_cores}")

# Teste 1: Apenas geração de chaves (baseline)
print(f"\n{Fore.YELLOW}[TEST 1] Key Generation Only")
print(f"{Fore.WHITE}  Medindo 100k chaves aleatórias...")

start = time.time()
for i in range(100000):
    pk = PrivateKey(os.urandom(32))
elapsed = time.time() - start
keygen_kps = (100000 / elapsed) / 1000

print(f"{Fore.GREEN}  Result: {keygen_kps:.1f} k/s (keys geradas apenas)")

# Teste 2: Compressed point
print(f"\n{Fore.YELLOW}[TEST 2] Compressed Point Hashing")
print(f"{Fore.WHITE}  Medindo 100k hashes (compressed)...")

start = time.time()
for i in range(100000):
    priv_bytes = os.urandom(32)
    pk = PrivateKey(priv_bytes)
    pub_c = pk.public_key.format(compressed=True)
    sha = hashlib.sha256(pub_c).digest()
    rip = hashlib.new('ripemd160')
    rip.update(sha)
    h160 = rip.digest()
elapsed = time.time() - start
hash_compressed_kps = (100000 / elapsed) / 1000

print(f"{Fore.GREEN}  Result: {hash_compressed_kps:.1f} k/s (keygen + SHA256 + RIPEMD160)")

# Teste 3: Uncompressed point
print(f"\n{Fore.YELLOW}[TEST 3] Uncompressed Point Hashing")
print(f"{Fore.WHITE}  Medindo 100k hashes (uncompressed)...")

start = time.time()
for i in range(100000):
    priv_bytes = os.urandom(32)
    pk = PrivateKey(priv_bytes)
    pub_u = pk.public_key.format(compressed=False)
    sha = hashlib.sha256(pub_u).digest()
    rip = hashlib.new('ripemd160')
    rip.update(sha)
    h160 = rip.digest()
elapsed = time.time() - start
hash_uncompressed_kps = (100000 / elapsed) / 1000

print(f"{Fore.GREEN}  Result: {hash_uncompressed_kps:.1f} k/s (keygen + SHA256 + RIPEMD160)")

# Teste 4: Both (compressed + uncompressed)
print(f"\n{Fore.YELLOW}[TEST 4] Both Formats (Realistic)")
print(f"{Fore.WHITE}  Medindo 50k chaves com ambos os formatos...")

start = time.time()
for i in range(50000):
    priv_bytes = os.urandom(32)
    pk = PrivateKey(priv_bytes)
    
    # Compressed
    pub_c = pk.public_key.format(compressed=True)
    sha = hashlib.sha256(pub_c).digest()
    rip = hashlib.new('ripemd160')
    rip.update(sha)
    h160_c = rip.digest()
    
    # Uncompressed
    pub_u = pk.public_key.format(compressed=False)
    sha = hashlib.sha256(pub_u).digest()
    rip = hashlib.new('ripemd160')
    rip.update(sha)
    h160_u = rip.digest()
elapsed = time.time() - start
hash_both_kps = (100000 / elapsed) / 1000  # 50k * 2 = 100k total

print(f"{Fore.GREEN}  Result: {hash_both_kps:.1f} k/s (AMBOS: C+U)")

# Sumário
print(f"\n{Fore.CYAN}" + "="*60)
print(f"{Fore.CYAN}BENCHMARK SUMMARY")
print(f"{Fore.CYAN}" + "="*60)
print(f"{Fore.WHITE}[1] KeyGen Only             : {Fore.GREEN}{keygen_kps:.1f} k/s")
print(f"{Fore.WHITE}[2] Compressed Hashing      : {Fore.GREEN}{hash_compressed_kps:.1f} k/s")
print(f"{Fore.WHITE}[3] Uncompressed Hashing    : {Fore.GREEN}{hash_uncompressed_kps:.1f} k/s")
print(f"{Fore.WHITE}[4] Both Formats (Realistic): {Fore.GREEN}{hash_both_kps:.1f} k/s")
print(f"{Fore.CYAN}" + "="*60)

print(f"\n{Fore.YELLOW}[*] Analise:")
print(f"{Fore.WHITE}  - Seu programa USA o modo [4] (ambos formatos)")
print(f"{Fore.WHITE}  - Performance esperada: ~{hash_both_kps:.0f} k/s single-thread")
print(f"{Fore.WHITE}  - Com {logical_cores} cores: ~{hash_both_kps * logical_cores:.0f} k/s teorico")
print(f"{Fore.WHITE}  - V2.4 com overhead: ~{hash_both_kps * logical_cores * 0.8:.0f} k/s realista")

if hash_both_kps > 10:
    print(f"\n{Fore.GREEN}[OK] Performance excelente para Python!")
elif hash_both_kps > 5:
    print(f"\n{Fore.YELLOW}[AVISO] Considere Numba: pip install numba")
else:
    print(f"\n{Fore.RED}[PROBLEMA] Performance baixa. Verifique HW.")

print(f"\n{Fore.CYAN}[*] Timestamp: {datetime.now()}")
