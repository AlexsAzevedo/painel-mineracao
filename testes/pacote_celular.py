"""A página do app do celular e o pacote que vai em cada release: a versão do painel dentro da página (painel.json e
ponte-app.js) e a política de segurança.
Uso: python3 testes/pacote_celular.py"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import RAIZ, checa, fim

CELULAR = os.path.join(RAIZ, "celular")
VERSAO_PC = json.load(open(os.path.join(RAIZ, "desktop", "package.json"), encoding="utf-8"))["version"]
VERSAO_APP = json.load(open(os.path.join(CELULAR, "package.json"), encoding="utf-8"))["version"]
TMP = tempfile.mkdtemp(prefix="pacote-celular-")


def montar_www(saida):
    r = subprocess.run([sys.executable, os.path.join(CELULAR, "scripts", "montar-www.py"), "--saida", saida], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("montar-www.py falhou: " + r.stdout + r.stderr)
    return saida


def ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def montagem():
    www = montar_www(os.path.join(TMP, "www"))
    painel = os.path.join(www, "painel.json")
    checa("painel.json com as duas versões", os.path.exists(painel) and json.load(open(painel)) == {"versao": VERSAO_PC, "app": VERSAO_APP},
          ler(painel) if os.path.exists(painel) else "sem painel.json")
    ponte = ler(os.path.join(www, "ponte-app.js"))
    checa("a ponte sabe a versão do painel", f'const PAINEL = "{VERSAO_PC}";' in ponte)
    checa("sem marcador sobrando", "__PAINEL__" not in ponte and "__VERSAO__" not in ponte)
    pagina = ler(os.path.join(www, "index.html"))
    checa("a página não fala com a API do GitHub", "api.github.com" not in pagina)
    checa("a página fala com o ntfy.sh", "connect-src https://ntfy.sh" in pagina)
    return www


montagem()
fim()
