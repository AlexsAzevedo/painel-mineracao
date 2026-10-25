"""Monta celular/www (a página do app do celular) a partir do painel (mineracao.html).

- troca as fontes do Google por cópias locais (o app abre sem internet, com os dados guardados);
- põe uma política de segurança: a página só fala com o ntfy.sh (sincronia) e com a API do GitHub (versão nova do app);
- carrega, antes do painel, o Capacitor (ponte com o Android), a sincronia (a mesma do PC: desktop/sincronia.js) e a ponte
  do app (src/ponte-app.js), que liga o painel aos dados do PC e mostra a tela de vincular;
- copia o leitor de QR code (jsQR), o ícone e as fontes.

Uso: python3 scripts/montar-www.py [--saida <pasta>] [--ntfy <endereço>]
  --ntfy: só para teste (ntfy de mentira, por exemplo http://127.0.0.1:1234/ntfy); a página aceita esse endereço também.
"""
import json, pathlib, re, shutil, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent          # celular/
REPO = RAIZ.parent
args = sys.argv[1:]
def opcao(nome):
    if nome in args:
        i = args.index(nome); v = args[i + 1]; del args[i:i + 2]; return v
    return None
saida = pathlib.Path(opcao("--saida") or RAIZ / "www")
ntfy_teste = opcao("--ntfy")
# a versão do app é a dele (celular/package.json), que só sobe quando o app muda; não precisa ser a do PC
versao = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))["version"]
assert re.fullmatch(r"\d+\.\d+\.\d+", versao), f"a versão do app ({versao}) não é do tipo X.Y.Z"

html = (REPO / "mineracao.html").read_text(encoding="utf-8")
if saida.exists():
    shutil.rmtree(saida)
(saida / "fonts").mkdir(parents=True)

# ---------- fontes locais ----------
FONTES = [("Sora", "sora", [600, 700]),
          ("Inter", "inter", [400, 500, 600, 700]),
          ("JetBrains Mono", "jetbrains-mono", [400])]
css = []
for familia, pacote, pesos in FONTES:
    for p in pesos:
        nome = f"{pacote}-latin-{p}-normal.woff2"
        shutil.copy(RAIZ / "node_modules" / "@fontsource" / pacote / "files" / nome, saida / "fonts" / nome)
        css.append(f'@font-face{{font-family:"{familia}";font-style:normal;font-weight:{p};font-display:swap;src:url(fonts/{nome}) format("woff2")}}')
antes = len(html)
html = re.sub(r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">',
              "<style>" + "".join(css) + "</style>", html, count=1)
assert len(html) != antes, "não achei o link das fontes do Google"

# ---------- scripts do app, antes do painel ----------
teste = f"<script>window.__NTFY__={json.dumps(ntfy_teste)};</script>" if ntfy_teste else ""
ponte = ('<script src="capacitor.js"></script><script src="sincronia.js"></script>' + teste + '<script src="ponte-app.js"></script>\n')
i = html.index("<script>")
html = html[:i] + ponte + html[i:]

conexoes = "https://ntfy.sh https://api.github.com" + (" " + re.match(r"https?://[^/]+", ntfy_teste).group(0) if ntfy_teste else "")
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self'; "
       f"img-src 'self' data: blob: https://*.fbcdn.net https://*.olx.com.br; media-src 'self' blob: mediastream:; connect-src {conexoes}; "
       "object-src 'none'; base-uri 'none'; form-action 'none'")
pagina = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<meta name="theme-color" content="#0C1016">'
          '<meta name="format-detection" content="telephone=no">'
          f'<meta http-equiv="Content-Security-Policy" content="{CSP}">' + html + "</html>")
(saida / "index.html").write_text(pagina, encoding="utf-8")

# ---------- arquivos de apoio ----------
ponte_js = (RAIZ / "src" / "ponte-app.js").read_text(encoding="utf-8")
assert ponte_js.count("__VERSAO__") == 1
(saida / "ponte-app.js").write_text(ponte_js.replace("__VERSAO__", versao), encoding="utf-8")
shutil.copy(REPO / "desktop" / "sincronia.js", saida / "sincronia.js")
shutil.copy(RAIZ / "node_modules" / "@capacitor" / "core" / "dist" / "capacitor.js", saida / "capacitor.js")
shutil.copy(RAIZ / "node_modules" / "jsqr" / "dist" / "jsQR.js", saida / "jsQR.js")
shutil.copy(REPO / "desktop" / "app" / "icone.png", saida / "icone.png")
total = sum(f.stat().st_size for f in saida.rglob("*") if f.is_file())
print(f"{saida}: versão {versao}, {len(pagina)//1024} KB de página, {total//1024} KB no total" + (f" · ntfy de teste: {ntfy_teste}" if ntfy_teste else ""))
