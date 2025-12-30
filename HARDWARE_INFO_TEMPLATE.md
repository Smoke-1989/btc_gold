# Hardware Information Template

Preencha todas as informacoes abaixo para que eu construa o C++ `btc_gold_cpp` otimizado para seu sistema.

## 1. Sistema Operacional

```bash
uname -a
# ou no Windows:
systeminfo | findstr /C:"OS"
```

**Resultado:**
- [ ] Linux (qual distro?) ________________
- [ ] Windows (qual versao?) ________________
- [ ] macOS (qual version?) ________________

**Passe aqui o output completo:**
```

```

---

## 2. CPU (Processador)

### Linux:
```bash
lscpu
```

### macOS:
```bash
system_profiler SPHardwareDataType
```

### Windows:
```cmd
wmic cpu get name,cores,threads,maxclockspeed
```

**Resultado:**

**Marca/Modelo:**
```

```

**Numero de cores:**
```

```

**Velocidade (GHz):**
```

```

**Geração (ex: Intel 10th Gen, AMD Ryzen 5000 Series):**
```

```

---

## 3. Instrucoes SIMD Disponiveis

### Linux:
```bash
grep -o 'avx[^ ]*' /proc/cpuinfo | sort -u
# Procure por: avx, avx2, avx512f, sse4_1, sse4_2
```

### macOS:
```bash
sysctl -a | grep -i simd
```

### Windows:
```powershell
Get-WmiObject Win32_Processor | Select-Object -ExpandProperty Description
```

**Instrucoes disponíveis (verificar):**
- [ ] SSE4.1
- [ ] SSE4.2
- [ ] AVX
- [ ] AVX2 ✅ (Recomendado minimo)
- [ ] AVX512F (Excelente, se disponivel)

**Output:**
```

```

---

## 4. Memoria RAM

### Linux:
```bash
free -h
```

### macOS:
```bash
sysctl hw.memsize
```

### Windows:
```cmd
wmic OS get totalvisiblememoryx64
```

**Total RAM:**
```

```

**RAM Disponivel (atual):**
```

```

---

## 5. GPU (Opcional, para futura aceleracao CUDA)

### NVIDIA:
```bash
nvidia-smi
```

### AMD:
```bash
rocm-smi
```

### Intel:
```bash
clinfo
```

**GPU (se tiver):**
- [ ] NVIDIA (qual modelo?) ________________
- [ ] AMD (qual modelo?) ________________
- [ ] Intel (qual modelo?) ________________
- [ ] Nenhuma

**Output (se aplicavel):**
```

```

---

## 6. Compilador Disponivel

### Linux (check gcc/clang):
```bash
gcc --version
clang --version
```

### macOS:
```bash
clang --version
gcc --version
```

### Windows (check MSVC):
```cmd
cl.exe /?  # MSVC (Visual Studio)
g++ --version  # MinGW
```

**Compiladores encontrados:**
- [ ] GCC (versao) ________________
- [ ] Clang (versao) ________________
- [ ] MSVC (versao) ________________

**Output:**
```

```

---

## 7. CMake (Build System)

```bash
cmake --version
```

**CMake instalado?**
- [ ] Sim (versao: ____________)
- [ ] Nao (vou instalar)

---

## 8. Bibliotecas Criptograficas Disponiveis

### Linux:
```bash
pkg-config --list-all | grep -i 'openssl\|secp256k1'
libsecp256k1-dev  # Verificar se instalado
```

### macOS (Homebrew):
```bash
brew list | grep -i 'openssl\|secp256k1'
```

### Windows:
```cmd
where openssl.exe
```

**Bibliotecas encontradas:**
- [ ] OpenSSL (versao) ________________
- [ ] libsecp256k1 (instalado?) Sim/Nao

**Output:**
```

```

---

## 9. Resumo Final

```markdown
| Item | Valor |
|------|-------|
| SO | ________________ |
| CPU | ________________ |
| Cores | ________________ |
| RAM | ________________ |
| SIMD | ________________ |
| Compilador | ________________ |
| GPU | ________________ |
```

---

## 10. Benchmark Python V2.4

Antes de passar para C++, rode o benchmark para baseLine:

```bash
python benchmark.py
```

**Resultado (copie aqui):**
```
[1] KeyGen Only             : ___ k/s
[2] Compressed Hashing      : ___ k/s
[3] Uncompressed Hashing    : ___ k/s
[4] Both Formats (Realistic): ___ k/s
```

---

## ENVIE TUDO ACIMA

Após preencher, compartilhe comigo para que eu construa o `btc_gold_cpp` otimizado exatamente para seu hardware.

**Timeline C++:**
- Coleta de info: Hoje
- Build system setup: 30 min
- Core implementation: 2-3 horas
- Testing e otimizacao: 1-2 horas
- **Total: 4-6 horas para C++ pronto**

🚀 Pronto para o proximo nivel?
