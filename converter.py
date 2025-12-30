import os
import sys
import hashlib
import binascii

try:
    import base58
except ImportError:
    print("Instale: pip install base58")
    sys.exit()

def pubkey_to_hash160(pubkey_hex):
    try:
        pub_bytes = bytes.fromhex(pubkey_hex)
        sha = hashlib.sha256(pub_bytes).digest()
        rip = hashlib.new('ripemd160')
        rip.update(sha)
        return rip.hexdigest()
    except: return None

def address_to_hash160(address):
    try:
        decoded = base58.b58decode_check(address)
        return decoded[1:].hex()
    except: return None

def main():
    print("=== CONVERSOR UNIVERSAL PARA HASH160 ===")
    print("Transforma seus arquivos (PubKeys ou Endereços) em HASH160 puro para máxima velocidade.")
    
    file_path = input("\nArquivo de entrada: ").strip()
    if not os.path.exists(file_path):
        print("Arquivo não encontrado!")
        return

    print("\n[1] Entrada são ENDEREÇOS (1A1z...)")
    print("[2] Entrada são PUBKEYS (02/03/04...)")
    mode = input(">> Opção: ").strip()
    
    output_file = file_path + "_converted.txt"
    
    print(f"\nConvertendo... Aguarde.")
    count = 0
    with open(file_path, 'r') as fin, open(output_file, 'w') as fout:
        for line in fin:
            line = line.strip()
            if not line: continue
            
            result = None
            if mode == "1":
                result = address_to_hash160(line)
            elif mode == "2":
                result = pubkey_to_hash160(line)
            
            if result:
                fout.write(result + "\n")
                count += 1
                if count % 10000 == 0: print(f"Processados: {count}", end='\r')

    print(f"\n\n[SUCESSO] {count} linhas convertidas.")
    print(f"Salvo em: {output_file}")
    print("Use este arquivo no btc_gold.py escolhendo a opção HASH160!")

if __name__ == "__main__":
    main()
