"""Busca do Marketplace no navegador escondido: a função paginaBuscaFb (de desktop/main.js) rola a página para o
Facebook carregar mais anúncios. Aqui ela roda no Chromium contra uma página que carrega mais anúncios como a do
teste do aplicativo (um sentinela no fim da lista, IntersectionObserver e 300 ms de espera), na janela do mesmo
tamanho do navegador escondido (1280 x 900). Cada rodada tem que achar todos os anúncios.
Uso: python3 testes/rolagem_fb.py"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import RAIZ, checa, sync_playwright  # noqa: F401
from apoio import _ok, _falhas  # noqa: F401

FONTE = open(os.path.join(RAIZ, "desktop", "main.js"), encoding="utf-8").read()
FUNCAO = re.search(r"^async function paginaBuscaFb\(rolar\) \{.*?^\}", FONTE, re.S | re.M).group(0)

def pagina(primeiros, resto):
    card = lambda i: (f'<a href="/marketplace/item/{1000000000000000 + i}/?ref=search" style="display:block;height:150px">'
                      f'<img src="data:," alt="" width="1" height="1"><div>R$1.{i:03d}</div><div>RTX 3070 8GB</div><div>Itajaí, SC</div></a>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Facebook</title></head><body style="margin:0">
    <div role="banner">menu do topo</div><div aria-label="Localização: Itajaí, No raio de 150 km">Itajaí · 150 km</div>
    <div role="main" id="lista">{"".join(card(i) for i in range(primeiros))}</div><div id="fim" style="height:20px"></div>
    <script>const resto = {json.dumps([card(primeiros + i) for i in range(resto)])}; let i = 0;
      new IntersectionObserver((es) => {{ if (es.some((e) => e.isIntersecting) && i < resto.length) {{ const b = resto.slice(i, i + 4); i += 4;
        setTimeout(() => document.getElementById("lista").insertAdjacentHTML("beforeend", b.join("")), 300); }} }}).observe(document.getElementById("fim"));</script>
    </body></html>"""

with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 1280, "height": 900})
    for primeiros, resto in ((9, 8), (9, 5), (11, 8), (6, 12)):
        achados = []
        for rodada in range(4):   # uma página nova por busca, como o navegador escondido abrindo cada endereço
            pg = ctx.new_page()
            pg.route("http://marketplace.teste/**", lambda rota: rota.fulfill(status=200, body=pagina(primeiros, resto), headers={"Content-Type": "text/html; charset=utf-8"}))
            pg.goto("http://marketplace.teste/marketplace/category/search/?query=rtx%203070")
            r = pg.evaluate(f"({FUNCAO})(3)")
            achados.append(len(r["itens"]))
            pg.close()
        checa(f"rolagem acha todos os anúncios ({primeiros} + {resto})", all(n == min(primeiros + resto, primeiros + 12) for n in achados), achados)
    nav.close()
print(json.dumps({"ok": len(_ok), "falhas": _falhas}, ensure_ascii=False, indent=1))
sys.exit(1 if _falhas else 0)
