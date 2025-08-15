import subprocess

scripts = [
    "bling_3m_v2.py",
    "bling_28d_v2.py",
    "bling_custo_v2.py",
    "NOTASQIVEBLING_v2.py",
    "operacao_v2.py"
]

for script in scripts:
    print(f"🚀 Executando {script}...")
    result = subprocess.run(["python", script], capture_output=True, text=True)
    
    print(f"📄 Saída de {script}:\n{result.stdout}")
    
    if result.stderr:
        print(f"⚠️ Erros em {script}:\n{result.stderr}")

print("✅ Todos os scripts foram executados.")
