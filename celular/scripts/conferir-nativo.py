"""Confere se a parte Android do app mudou sem subir a versão do app.

Desde a 1.8.0, o app do celular troca a página (o painel) sozinho, e a versão do app (celular/package.json) só sobe
quando a parte Android muda: uma página nova só exige app novo quando a versão do app subiu (appMin). Se a parte
Android mudasse sem a versão subir, um celular com o app velho receberia uma página feita para o app novo.

A parte Android: os arquivos de celular/android que estão no git, celular/capacitor.config.json e as versões dos
pacotes @capacitor/* de celular/package.json. O resumo (SHA-256) fica em celular/nativo.json, junto com a versão do app.

Uso: python3 celular/scripts/conferir-nativo.py [--gravar] [--raiz <pasta do repositório>]
  --gravar: grava o resumo de agora para a versão de agora (depois de subir a versão do app).
"""
import hashlib, json, pathlib, subprocess, sys

args = sys.argv[1:]
gravar = "--gravar" in args
if gravar:
    args.remove("--gravar")
raiz = pathlib.Path(__file__).resolve().parent.parent.parent
if "--raiz" in args:
    i = args.index("--raiz"); raiz = pathlib.Path(args[i + 1]).resolve(); del args[i:i + 2]
if args:
    sys.exit("uso: conferir-nativo.py [--gravar] [--raiz <pasta>]")

celular = raiz / "celular"
pacote = json.loads((celular / "package.json").read_text(encoding="utf-8"))
versao = pacote["version"]


def resumo():
    h = hashlib.sha256()
    lista = subprocess.run(["git", "-C", str(raiz), "ls-files", "-z", "celular/android"], check=True, capture_output=True).stdout
    caminhos = sorted(p for p in lista.decode("utf-8").split("\0") if p) + ["celular/capacitor.config.json"]
    for rel in caminhos:
        arq = raiz / rel
        h.update(rel.encode("utf-8") + b"\0" + (arq.read_bytes() if arq.is_file() else b"<sem arquivo>") + b"\0")
    cap = {secao: {k: v for k, v in sorted(pacote.get(secao, {}).items()) if k.startswith("@capacitor/")}
           for secao in ("dependencies", "devDependencies")}
    h.update(json.dumps(cap, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


atual = resumo()
arquivo = celular / "nativo.json"
if gravar:
    arquivo.write_text(json.dumps({"app": versao, "resumo": atual}, indent=2) + "\n", encoding="utf-8")
    print(f"resumo da parte Android gravado: app {versao}")
    sys.exit(0)

gravado = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
if gravado.get("app") != versao:
    print(f"A versão do app subiu para {versao}: rode celular/scripts/conferir-nativo.py --gravar.")
    sys.exit(1)
if gravado.get("resumo") != atual:
    print(f"A parte Android do app mudou (código em celular/android, celular/capacitor.config.json ou a versão de um pacote "
          f"@capacitor), mas a versão do app continua {versao}. Suba a versão do app em celular/package.json e rode "
          f"conferir-nativo.py --gravar.")
    sys.exit(1)
print(f"parte Android conferida: app {versao}")
