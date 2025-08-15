import subprocess
import sys

# Lista de scripts para rodar na ordem desejada
SCRIPTS = [
    "bling_3m_v2.py",
    "bling_28d_v2.py",
    "bling_custo_v2.py",
    "operacao_v2.py",
    "NOTASQIVEBLING_v2.py"
]

for script in SCRIPTS:
    print(f"\n===== Rodando {script} =====\n")
    try:
        subprocess.run([sys.executable, script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao rodar {script}: {e}")
