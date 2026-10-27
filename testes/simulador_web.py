"""Simulador de placas na web: a página própria gerada do mineracao.html por web/gerar-simulador.py (dados inventados).
A página é servida como o artifact a serve (o esqueleto com charset e viewport em volta), sem o banco da página: vale o
localStorage ("sim-web").
Uso: python3 testes/simulador_web.py"""
import functools, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403
import apoio

GERADOR = os.path.join(RAIZ, "web", "gerar-simulador.py")
TMP = tempfile.mkdtemp(prefix="simweb-")
SAIDA = os.path.join(TMP, "simulador.html")
# o esqueleto que o artifact põe em volta da página (charset, viewport e o reset pequeno)
ESQUELETO = ('<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
             '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}'
             'body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>@@PAGINA@@</body></html>')


def rodar_gerador(painel=None, saida=SAIDA):
    args = [sys.executable, GERADOR, "--saida", saida] + (["--painel", painel] if painel else [])
    return subprocess.run(args, capture_output=True, text=True)


def copia_sem(trecho):
    """uma cópia do mineracao.html sem o trecho (para ver o gerador parar)"""
    t = open(PAGINA, encoding="utf-8").read()
    assert trecho in t, trecho
    caminho = os.path.join(TMP, "painel-sem.html")
    open(caminho, "w", encoding="utf-8").write(t.replace(trecho, ""))
    return caminho


class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.split("?")[0] in ("/", "/index.html"):
            corpo = ESQUELETO.replace("@@PAGINA@@", open(SAIDA, encoding="utf-8").read()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        else:
            self.send_error(404)


_srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(_Q, directory=TMP))
_srv.daemon_threads = True
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL_WEB = f"http://127.0.0.1:{_srv.server_address[1]}/index.html"
_nav = [None]


def abrir_web(p, largura=1366, altura=900, estado=None, sem_storage=False, extra=""):
    """A página numa aba nova (localStorage vazio, ou com o estado guardado), com o relógio dos testes."""
    if _nav[0] is None:
        _nav[0] = p.chromium.launch()
    ctx = _nav[0].new_context(viewport={"width": largura, "height": altura}, locale="pt-BR", timezone_id="America/Sao_Paulo")
    pg = ctx.new_page()
    pg.set_default_timeout(5000)
    pg.clock.set_fixed_time(AGORA)
    lista = apoio._erros.setdefault(id(pg), [])
    pg.on("pageerror", lambda e: lista.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and lista.append(m.text))
    pg.route(re.compile(r"^https://fonts\.(googleapis|gstatic)\.com/.*"), lambda r: r.abort())
    if sem_storage:
        pg.add_init_script(apoio._SEM_STORAGE)
    elif estado is not None:
        pg.add_init_script("try{ if(!sessionStorage.getItem('__semeado')){ localStorage.setItem('sim-web', %s); sessionStorage.setItem('__semeado','1'); } }catch(e){}"
                           % json.dumps(json.dumps(estado, ensure_ascii=False)))
    if extra:
        pg.add_init_script(extra)
    pg.goto(URL_WEB)
    pg.wait_for_timeout(400)
    return pg


# os mesmos ajudantes de testes/simulador.py
def js(pg, expr):
    return pg.evaluate("(e) => { try { return (0, eval)(e); } catch (x) { return {erro: String(x)}; } }", expr)


def campo(r, *ks):
    for k in ks:
        try:
            r = r[k]
        except (KeyError, IndexError, TypeError):
            return None
    return r


def perto(v, alvo, tol):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v - alvo) < tol


def texto(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText.trim() : ''; }", sel)


def existe(pg, sel):
    return pg.evaluate("(s) => !!document.querySelector(s)", sel)


def visivel(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'; }", sel)


def clica(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); if(!e) return false; e.click(); return true; }", sel)


def preenche(pg, sel, v):
    return pg.evaluate("([s, v]) => { const e = document.querySelector(s); if(!e) return false; e.value = v; e.dispatchEvent(new Event('input', {bubbles:true})); e.dispatchEvent(new Event('change', {bubbles:true})); return true; }", [sel, v])


def escolhe(pg, sel, v):
    return pg.evaluate("([s, v]) => { const e = document.querySelector(s); if(!e) return false; e.value = v; e.dispatchEvent(new Event('change', {bubbles:true})); return true; }", [sel, v])


def valor(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.value : null; }", sel)


def gerar(p):
    r = rodar_gerador()
    checa("gera a página", r.returncode == 0 and os.path.exists(SAIDA) and "gerado:" in r.stdout, (r.stdout + r.stderr)[-300:])
    if not os.path.exists(SAIDA):
        return
    html = open(SAIDA, encoding="utf-8").read()
    faltam = [x for x in ['id="v-sim"', "function fluxoSim", "const CATALOGO_RAW", "--viz-a", ".sim-op{", "function eficiencia", "const MERCADO"] if x not in html]
    checa("leva o simulador do painel", not faltam, faltam)
    checa("contrato do artifact: sem doctype, html, head nem body, e o título primeiro",
          not re.search(r"<(?:!doctype|html|head|body)\b", html, re.I) and html.lstrip().startswith("<title>Simulador de placas</title>"))
    checa("cores nos três estados do tema", ':root:not([data-theme="light"])' in html and ':root[data-theme="dark"]' in html and "data-tema" not in html.split("<script>")[0])
    pg = abrir_web(p)
    checa("abre sem erros, com o simulador à mostra", visivel(pg, "#v-sim") and visivel(pg, "#sim-ops .sim-op") and not erros(pg), erros(pg)[:3])
    # o painel sem uma das peças: o gerador para e diz o que faltou, sem gerar meia página
    for trecho, nome in (("/* ---------- simulador de compra ----------", "bloco do simulador"), ("function eficiencia(", "eficiencia"),
                         ("/* fim do simulador de compra */", "fim do CSS do simulador")):
        outra = os.path.join(TMP, "outra.html")
        r = rodar_gerador(painel=copia_sem(trecho), saida=outra)
        checa(f"peça faltando ({nome}): para com aviso", r.returncode == 1 and "não achei" in (r.stdout + r.stderr) and not os.path.exists(outra),
              (r.stdout + r.stderr)[-200:])


with sync_playwright() as p:
    gerar(p)
fim()
