"""Conferência da parte Android do app (celular/scripts/conferir-nativo.py): falha quando a parte Android muda sem subir a
versão do app, ou quando a versão sobe sem gravar o resumo. Roda num repositório git mínimo, numa pasta temporária.
Uso: python3 testes/conferir_nativo.py"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import RAIZ, checa, fim

SCRIPT = os.path.join(RAIZ, "celular", "scripts", "conferir-nativo.py")
tmp = tempfile.mkdtemp(prefix="nativo-")
nativo = os.path.join(tmp, "celular", "nativo.json")


def escrever(rel, texto):
    caminho = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)


def git(*args):
    subprocess.run(["git", "-C", tmp, *args], check=True, capture_output=True)


def pacote(versao, jsqr="1.4.0"):
    escrever("celular/package.json", json.dumps({"name": "x", "version": versao,
                                                  "dependencies": {"@capacitor/core": "8.5.3", "@capacitor/android": "8.5.3", "jsqr": jsqr},
                                                  "devDependencies": {"@capacitor/cli": "8.5.3", "@fontsource/inter": "5.3.0"}}, indent=2))


def rodar(*args):
    return subprocess.run([sys.executable, SCRIPT, "--raiz", tmp, *args], capture_output=True, text=True)


git("init", "-q")
escrever("celular/android/app/build.gradle", "apply plugin: 'com.android.application'\n")
escrever("celular/capacitor.config.json", '{"appId": "x"}\n')
pacote("1.0.0")
git("add", "-A")

r = rodar("--gravar")
checa("grava o resumo", r.returncode == 0 and json.load(open(nativo))["app"] == "1.0.0", r.stdout + r.stderr)
r = rodar()
checa("confere sem mudança", r.returncode == 0 and "parte Android conferida: app 1.0.0" in r.stdout, r.stdout + r.stderr)

escrever("celular/android/app/build.gradle", "mudou\n"); git("add", "-A")
r = rodar()
checa("parte Android mudou sem subir a versão: falha", r.returncode == 1 and "suba a versão do app" in r.stdout.lower(), r.stdout + r.stderr)

pacote("1.1.0")
r = rodar()
checa("versão subiu sem gravar: falha", r.returncode == 1 and "--gravar" in r.stdout and "1.1.0" in r.stdout, r.stdout + r.stderr)
checa("depois de gravar, passa", rodar("--gravar").returncode == 0 and rodar().returncode == 0)

escrever("celular/capacitor.config.json", '{"appId": "y"}\n')
r = rodar()
checa("configuração do Capacitor conta", r.returncode == 1, r.stdout)
escrever("celular/capacitor.config.json", '{"appId": "x"}\n')

pacote("1.1.0", jsqr="1.4.1")
checa("pacote que não é @capacitor não conta", rodar().returncode == 0)
pacote("1.1.0")
j = json.load(open(os.path.join(tmp, "celular", "package.json"))); j["dependencies"]["@capacitor/android"] = "8.6.0"
escrever("celular/package.json", json.dumps(j))
checa("versão de um @capacitor conta", rodar().returncode == 1)
pacote("1.1.0")

escrever("celular/src/ponte-app.js", "x"); git("add", "-A")
checa("página não conta", rodar().returncode == 0)
escrever("celular/android/app/src/main/java/A.java", "class A {}\n")
checa("arquivo fora do git não conta", rodar().returncode == 0)
git("add", "-A")
checa("arquivo novo da parte Android conta", rodar().returncode == 1)

fim()
