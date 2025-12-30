#!/usr/bin/env python3
"""
BTC GOLD Diagnostic Tool
Identifica os problemas que estão causando performance baixa

O resultado de 24 k/s é MUITO BAIXO. Esperado: 150-300 k/s
"""

import sys
import time
import hashlib
import platform
import os

print("\n" + "="*70)
print("BTC GOLD DIAGNOSTIC TOOL")
print("="*70 + "\n")

# ============================================================================
print("[TESTE 1] OpenSSL RIPEMD160 Support")
print("-" * 70)

try:
    import ssl
    ssl_version = ssl.OPENSSL_VERSION
    print(f"[+] OpenSSL versao: {ssl_version}")
except:
    print("[!] NAO CONSEGUIU DETECTAR OpenSSL")

# Testar RIPEMD160
try:
    test_hash = hashlib.new('ripemd160')
    test_hash.update(b'test')
    result = test_hash.hexdigest()
    print(f"[OK] RIPEMD160 funciona: {result[:16]}...")
    ripemd_ok = True
except ValueError as e:
    print(f"[ERROR] RIPEMD160 DESABILITADO!")
    print(f"        Mensagem: {e}")
    print(f"\n        SOLUCAO (Linux):")
    print(f"        1. openssl version -d")
    print(f"        2. nano /etc/ssl/openssl.cnf")
    print(f"        3. Adicione ao final:")
    print(f"")
    print(f"           [openssl_init]")
    print(f"           providers = provider_sect")
    print(f"")
    print(f"           [provider_sect]")
    print(f"           default = default_sect")
    print(f"           legacy = legacy_sect")
    print(f"")
    print(f"           [default_sect]")
    print(f"           activate = 1")
    print(f"")
    print(f"           [legacy_sect]")
    print(f"           activate = 1")
    print(f"")
    ripemd_ok = False

if ripemd_ok:
    # Benchmark RIPEMD160
    print("\n[TEST] Benchmark RIPEMD160 puro...")
    start = time.time()
    for i in range(10000):
        h = hashlib.new('ripemd160')
        h.update(os.urandom(32))
        _ = h.digest()
    elapsed = time.time() - start
    ripemd_kps = (10000 / elapsed) / 1000
    print(f"[+] RIPEMD160: {ripemd_kps:.1f} k/s (esperado: 50+ k/s)")
    
    if ripemd_kps < 20:
        print(f"[WARNING] RIPEMD160 LENTO! (< 20 k/s)")
else:
    print(f"[CRITICAL] RIPEMD160 nao funciona - isso explica 50% da lentidao!")

# ============================================================================
print("\n[TESTE 2] coincurve Binding (C vs Python)")
print("-" * 70)

try:
    from coincurve import PrivateKey
    import coincurve
    
    # Verificar se eh CFFI (C binding)
    try:
        import _libsecp256k1
        print("[OK] coincurve usando CFFI C bindings")
        cffi_ok = True
    except ImportError:
        print("[WARNING] coincurve usando FALLBACK PYTHON!")
        print("          Isso eh MUITO LENTO!")
        print("          Solucao: pip install --force-reinstall coincurve")
        cffi_ok = False
    
    # Benchmark keygen
    print("\n[TEST] Benchmark coincurve keygen...")
    start = time.time()
    for i in range(10000):
        pk = PrivateKey(os.urandom(32))
    elapsed = time.time() - start
    keygen_kps = (10000 / elapsed) / 1000
    print(f"[+] KeyGen: {keygen_kps:.1f} k/s (esperado: 15+ k/s)")
    
    # Benchmark point format
    print("\n[TEST] Benchmark public key formatting...")
    pk = PrivateKey(os.urandom(32))
    start = time.time()
    for i in range(10000):
        pub_c = pk.public_key.format(compressed=True)
        pub_u = pk.public_key.format(compressed=False)
    elapsed = time.time() - start
    format_kps = (20000 / elapsed) / 1000  # 2 formatacoes por iteracao
    print(f"[+] Point format: {format_kps:.1f} k/s (esperado: 50+ k/s)")
    
except ImportError as e:
    print(f"[ERROR] coincurve nao instalado: {e}")
    cffi_ok = False

# ============================================================================
print("\n[TESTE 3] Python GIL Impact")
print("-" * 70)

print(f"[*] Versao Python: {platform.python_version()}")
print(f"[*] Implementacao: {platform.python_implementation()}")

if platform.python_implementation() == "CPython":
    print("[!] CPython tem GIL (Global Interpreter Lock)")
    print("    Multiprocessing eh OBRIGATORIO para ganho real")
    print("    V2.4 usa multiprocessing (certo)")
elif platform.python_implementation() == "PyPy":
    print("[OK] PyPy tem JIT compiler (mais rapido)")
elif platform.python_implementation() == "Jython":
    print("[OK] Jython rodando em JVM (pode ser mais rapido)")

# ============================================================================
print("\n[TESTE 4] Hash Puro (SHA256)")
print("-" * 70)

print("[TEST] Benchmark SHA256...")
start = time.time()
for i in range(100000):
    h = hashlib.sha256(os.urandom(32))
    _ = h.digest()
elapsed = time.time() - start
sha256_kps = (100000 / elapsed) / 1000
print(f"[+] SHA256: {sha256_kps:.1f} k/s (esperado: 500+ k/s)")

if sha256_kps < 100:
    print(f"[WARNING] SHA256 LENTO! Pode indicar CPU limitada ou problema no OpenSSL")

# ============================================================================
print("\n[TESTE 5] Combined Hash160 (SHA256 + RIPEMD160)")
print("-" * 70)

if ripemd_ok:
    print("[TEST] Benchmark combined hash160...")
    start = time.time()
    for i in range(10000):
        data = os.urandom(33)  # Compressed public key
        sha = hashlib.sha256(data).digest()
        rip = hashlib.new('ripemd160')
        rip.update(sha)
        h160 = rip.digest()
    elapsed = time.time() - start
    combined_kps = (10000 / elapsed) / 1000
    print(f"[+] SHA256+RIPEMD160: {combined_kps:.1f} k/s (esperado: 50+ k/s)")
else:
    print("[SKIP] RIPEMD160 nao funciona")

# ============================================================================
print("\n[TESTE 6] Full Benchmark (Realista)")
print("-" * 70)

print("[TEST] Full key generation + hash160...")
start = time.time()
for i in range(5000):
    pk = PrivateKey(os.urandom(32))
    pub_c = pk.public_key.format(compressed=True)
    sha = hashlib.sha256(pub_c).digest()
    rip = hashlib.new('ripemd160')
    rip.update(sha)
    h160 = rip.digest()
elapsed = time.time() - start
full_kps = (5000 / elapsed) / 1000
print(f"[+] Full (KeyGen+Hash160): {full_kps:.1f} k/s")
print(f"    Esperado: 100+ k/s")
print(f"    Seu benchmark: 24.2 k/s")
print(f"    Diferenca: {24.2 / full_kps:.1f}x (BEM ERRADO!)")

# ============================================================================
print("\n[ANALISE] Diagnostico Final")
print("=" * 70)

problems = []

if not ripemd_ok:
    problems.append("CRITICO: RIPEMD160 desabilitado no OpenSSL 3.0+")
if keygen_kps < 10:
    problems.append("CRITICO: coincurve usando fallback Python puro")
if sha256_kps < 100:
    problems.append("ALERTA: SHA256 muito lento (pode ser CPU limitada)")

if problems:
    print("\n[!] PROBLEMAS ENCONTRADOS:\n")
    for i, p in enumerate(problems, 1):
        print(f"    {i}. {p}")
else:
    print("\n[OK] Hardware/bibliotecas parecem OK")
    print("\n[POSSIVEL PROBLEMA] Benchmark.py pode estar medindo errado")
    print("                    ou seu V2.4 ainda tem overhead\n")

print("\n" + "=" * 70)
print("[RECOMENDACOES]")
print("=" * 70)
print("""
1. Se RIPEMD160 está desabilitado:
   Linux: Editar /etc/ssl/openssl.cnf e ativar legacy provider
   
2. Se coincurve está em fallback Python:
   pip install --force-reinstall --no-cache-dir coincurve
   
3. Se SHA256 está lento:
   - Verificar CPU: cat /proc/cpuinfo (Linux)
   - Possivelmente limitado por VM ou cloud
   
4. Rodar novamente DEPOIS das correcoes:
   python diagnostic.py
   python benchmark.py
   
5. Compartilhar output completo comigo para C++ otimizado

""")

print("=" * 70)
print("\n")
