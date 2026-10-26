"""Monta o pacote da página do app do celular que vai em cada release (a partir da 1.8.0, o app troca a página sozinho).

Saída (em --saida):
- painel-celular.zip: a página (a pasta montada por montar-www.py), com os arquivos em ordem, data fixa e as mesmas
  permissões, para a mesma página dar sempre o mesmo zip;
- manifesto.json: o texto que AssinarPainel.java assina: a versão da página e a do app para que ela foi feita (appMin,
  de painel.json), o SHA-256 e o tamanho do zip e os do .apk da mesma release (versão e código do celular/package.json).

Uso: python3 celular/scripts/montar-pacote.py --www <pasta da página> --apk <arquivo .apk> --saida <pasta>
"""
import hashlib, json, pathlib, re, sys, zipfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent          # celular/
MAX_ZIP, MAX_APK = 20 << 20, 100 << 20                         # os mesmos limites do app (Manifesto.java)

args = sys.argv[1:]
def opcao(nome):
    if nome not in args:
        sys.exit(f"falta {nome}. Uso: montar-pacote.py --www <pasta> --apk <arquivo.apk> --saida <pasta>")
    i = args.index(nome); v = args[i + 1]; del args[i:i + 2]; return v
www, apk, saida = pathlib.Path(opcao("--www")), pathlib.Path(opcao("--apk")), pathlib.Path(opcao("--saida"))
if args:
    sys.exit("opção desconhecida: " + " ".join(args))
if not (www / "index.html").is_file() or not (www / "painel.json").is_file():
    sys.exit(f"{www} não tem a página montada (index.html e painel.json): rode montar-www.py antes")
if not apk.is_file():
    sys.exit(f"não achei o .apk em {apk}")

painel = json.loads((www / "painel.json").read_text(encoding="utf-8"))
app = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))["version"]
for nome, v in (("da página", painel.get("versao")), ("do app (appMin)", painel.get("app")), ("do app", app)):
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(v)):
        sys.exit(f"a versão {nome} ({v}) não é do tipo X.Y.Z")
x, y, z = (int(n) for n in app.split("."))


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


saida.mkdir(parents=True, exist_ok=True)
zip_ = saida / "painel-celular.zip"
arquivos = sorted((p.relative_to(www).as_posix(), p) for p in www.rglob("*") if p.is_file())
with zipfile.ZipFile(zip_, "w") as zf:
    for rel, p in arquivos:
        info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, p.read_bytes(), compresslevel=9)

if zip_.stat().st_size > MAX_ZIP or apk.stat().st_size > MAX_APK:
    sys.exit(f"pacote grande demais para o app (zip até {MAX_ZIP >> 20} MB, .apk até {MAX_APK >> 20} MB)")

manifesto = {"formato": 1, "tipo": "painel-mineracao/painel-celular", "versao": painel["versao"], "appMin": painel["app"],
             "painel": {"sha256": sha256(zip_), "tamanho": zip_.stat().st_size},
             "app": {"versao": app, "codigo": x * 10000 + y * 100 + z, "sha256": sha256(apk), "tamanho": apk.stat().st_size}}
(saida / "manifesto.json").write_text(json.dumps(manifesto, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(f"{zip_}: página {painel['versao']} (app {painel['app']} ou mais novo), {zip_.stat().st_size // 1024} KB, {len(arquivos)} arquivos")
