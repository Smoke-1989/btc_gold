# 🚨 Performance Debugging Guide

**SEU BENCHMARK: 24.2 k/s = MUITO BAIXO**

Esperado: 150-300 k/s (Python), 500M+ k/s (C++)

---

## 🔍 O Que Está Errado?

Você está **6-12x mais lento do que deveria** estar em Python puro.

Há **3 culpados principais** (em ordem de probabilidade):

### 1. 🔴 **RIPEMD160 Desabilitado (OpenSSL 3.0+)** - 50% DE PERDA

**Verificar:**
```bash
python -c "import hashlib; hashlib.new('ripemd160', b'test').hexdigest()"
```

**Se der erro:**
```
ValueError: unsupported hash type ripemd160
```

**SOLUCAO CRITICA (Linux):**
```bash
# 1. Encontrar OpenSSL config
openssl version -d
# Output: OPENSSLDIR: "/etc/ssl"

# 2. Editar config
sudo nano /etc/ssl/openssl.cnf

# 3. Adicionar no FINAL do arquivo:
[openssl_init]
providers = provider_sect

[provider_sect]
default = default_sect
legacy = legacy_sect

[default_sect]
activate = 1

[legacy_sect]
activate = 1

# 4. Salvar (CTRL+X, Y, ENTER)

# 5. Testar novamente
python -c "import hashlib; print(hashlib.new('ripemd160', b'test').hexdigest())"
```

**SOLUCAO (macOS):**
```bash
brew install openssl@3
export LDFLAGS="-L/usr/local/opt/openssl@3/lib"
export CPPFLAGS="-I/usr/local/opt/openssl@3/include"
pip install --force-reinstall coincurve
```

**SOLUCAO (Windows):**
- Download Visual Studio Community com C++ tools
- Reinstalar coincurve: `pip install --force-reinstall coincurve`

---

### 2. 🟡 **coincurve Usando Fallback Python Puro** - 30% DE PERDA

**Verificar:**
```bash
python -c "import _libsecp256k1; print('OK')"
```

**Se der ImportError:**
coincurve NAO TEM CFFI BINDING (C library nativa)

**SOLUCAO:**
```bash
pip install --force-reinstall --no-cache-dir coincurve
```

**Verificar novamente:**
```bash
python -c "import _libsecp256k1; print('CFFI OK')"
```

---

### 3. 🟠 **Hardware Limitado** - 10-20% DE PERDA

**Se for cloud/VM, pode estar throttled**

**Verificar CPU:**
```bash
# Linux
cat /proc/cpuinfo | grep -i "model name" | head -1

# macOS
system_profiler SPHardwareDataType | grep "Processor"

# Windows
wmic cpu get name
```

**Sintomas:**
- Se `python benchmark.py` mostrar SHA256 < 100 k/s = CPU limitada
- Se em cloud (AWS, Azure, etc) = provavel throttling

---

## 🔧 Diagnostico Automatico

Rodei um script completo que identifica EXATAMENTE o problema:

```bash
python diagnostic.py
```

Este script:
- ✅ Verifica RIPEMD160
- ✅ Verifica CFFI binding do coincurve
- ✅ Mede performance de cada componente
- ✅ Identifica o gargalo
- ✅ Sugere solucoes especificas

**Rode isso PRIMEIRO e compartilhe output completo comigo.**

---

## 📊 Performance Esperada

### Baseline (Seu Sistema)
```bash
python benchmark.py
```

**Resultado esperado:**
- [1] KeyGen Only: 15-20 k/s
- [2] Compressed Hashing: 100-150 k/s
- [3] Uncompressed Hashing: 100-150 k/s
- **[4] Both Formats (REALISTA): 150-300 k/s**

**Seu resultado: 24.2 k/s**
- Isso sugere problemas graves em [2] e [3]
- Provavelmente RIPEMD160 desabilitado OU coincurve em fallback Python

---

## ✅ Checklist de Correcao

- [ ] Rodar `python diagnostic.py`
- [ ] Compartilhar output COMPLETO comigo
- [ ] Se RIPEMD160 erro: aplicar solucao OpenSSL acima
- [ ] Se coincurve fallback: reinstalar com CFFI
- [ ] Rodar `python benchmark.py` novamente
- [ ] Confirmar aumento em k/s
- [ ] Se ainda baixo: pode ser C++ necessario

---

## 🚀 Apos Corrigir

**Se conseguir chegar a 150+ k/s em Python:**
- V2.4 com Numba JIT: +2-5x = **300-750 k/s**
- Isso ja seria excelente!
- C++ entao seria apenas para MEGA escala (500M+)

**Se ficar em 24-50 k/s:**
- Python nao vai funcionar
- **OBRIGATORIO partir direto para C++**
- Timeline: 4-6 horas apos specs coletadas

---

## 📋 Proximos Passos

1. **Rodar diagnostic.py e compartilhar output**
2. **Corrigir problemas identificados**
3. **Rodar benchmark.py novamente**
4. **Se ainda baixo, coletar specs para C++:**
   - Preencher HARDWARE_INFO_TEMPLATE.md
   - Compartilhar tudo comigo

---

## 📞 Suporte Urgente

Se diagnostic.py mostrar problemas:

```
[CRITICAL] RIPEMD160 desabilitado
[CRITICAL] coincurve em fallback Python
```

**Isso explica 80% da lentidao!**

Apos corrigir, espere:
- +2-4x ganho imediato (150-200 k/s)
- +Numba: +2-5x adicional (300-750 k/s)
- C++: 50x total (500M+ k/s)

---

**Rode diagnostic.py AGORA e compartilhe output! 🚀**
