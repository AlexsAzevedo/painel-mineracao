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


def contas(p):
    """As peças da casca nos valores iniciais: os PCs (ligado, desligado e novo), a correção, a revenda, o preço sugerido
    e os números e PCs estranhos."""
    pg = abrir_web(p)
    ef = lambda selo, carga: js(pg, f"eficiencia('{selo}', {carga}, 220)")
    r = js(pg, "calcMaq(maqsReais()[0], {extra:[{tipo:'plano', c:byId['rtx-5070'], q:2, preco:5159}]})")
    checa("PC ligado: soma as placas ao que já gasta", campo(r, "dc") == 680 and perto(campo(r, "luz"), 680/ef("Platinum", 0.68)*24*30/1000*0.96, 1e-9), r)
    r = js(pg, "calcMaq(maqsReais()[1], {extra:[{tipo:'plano', c:byId['rtx-5060'], q:2, preco:2600}]})")
    checa("PC desligado: placas + 40 W", campo(r, "dc") == 240 and campo(r, "ligada") is True, r)
    checa("desligado e sem placas: não gasta", js(pg, "calcMaq(maqsReais()[1]).luz") == 0)
    r = js(pg, "calcMaq(maqNovaSim(), {extra:[{tipo:'plano', c:byId['rtx-5060'], q:3, preco:2600}]})")
    checa("Um PC novo: placas + 40 W, fonte de 650 W Gold", campo(r, "dc") == 340 and campo(r, "fonte") == {"w": 650, "selo": "Gold"}
          and perto(campo(r, "luz"), 340/ef("Gold", 340/650)*24*30/1000*0.96, 1e-9), r)
    checa("bruto das placas novas (sem margem)",
          perto(js(pg, "calcMaq(maqsReais()[0], {extra:[{tipo:'plano', c:byId['rtx-5070'], q:2, preco:5159}]}).brutoGpu"), 2*1564*30/365*5.42, 1e-9))
    checa("correção pelo real digitado", js(pg, "fatorSim()") == {"f": 0.74, "fonte": "real", "placas": []}, js(pg, "fatorSim()"))
    checa("revenda com 25% ao ano", js(pg, "deprecModelo('rtx-5060').d") == 0.25)
    checa("preço sugerido: o menor da pesquisa (usada ou nova)", js(pg, "[melhorPreco(byId['rtx-5060']), melhorPreco(byId['rtx-5070'])]")
          == [{"v": 2600, "fonte": "usado"}, {"v": 5159, "fonte": "novo"}])
    r = js(pg, "numerosOk({dolar:'abc', luz:-1, real:500, horas:30, cdi:'', pctCdi:120})")
    checa("números estranhos: limita ou guarda o anterior", campo(r, "dolar") == 5.42 and campo(r, "luz") == 0 and campo(r, "real") == 200
          and campo(r, "horas") == 24 and campo(r, "cdi") == 13.65 and campo(r, "pctCdi") == 120 and campo(r, "deprec") == 25, r)
    checa("número com vírgula vale", campo(js(pg, "numerosOk({dolar:'5,6'})"), "dolar") == 5.6)
    r = js(pg, "pcsOk([{id:'pc-pessoal', nome:'  Gamer  ', fonteW:'abc', selo:'Titânio', jaGasta:-5}, {id:'pc-pessoal', nome:'repetido'},"
               " {id:'novo', nome:'x'}, {id:'pc-x', nome:'%s', fonteW:50, selo:'Gold', jaGasta:'250'}, null, 7, {nome:'sem id'}])" % ("N"*50))
    checa("PCs estranhos: arruma, limita e tira os repetidos", r == [{"id": "pc-pessoal", "nome": "Gamer", "fonteW": 1000, "selo": "Platinum", "jaGasta": 0},
                                                                   {"id": "pc-x", "nome": "N"*40, "fonteW": 100, "selo": "Gold", "jaGasta": 250}], r)
    checa("sem PC: lista vazia", js(pg, "pcsOk([])") == [])
    checa("sem erros nas contas", not erros(pg), erros(pg)[:3])


# a comparação com o programa: as mesmas opções, os mesmos números e os mesmos PCs
NOMES_PAR = {"m-pc": "PC pessoal", "m-ext": "PC extra"}
SIM_PAR = {"prazo": 0, "cenarioGrafico": "estavel", "opcoes": [
    {"nome": "A", "placas": [{"modelo": "rtx-5070", "qtd": 2, "preco": 5159, "maq": "m-pc"}], "pcNovo": {"custo": 0},
     "pagamento": {"tipo": "cartao", "parcelas": 12}, "dinheiro": {"tipo": "emprestimo", "valor": 10000, "parcelas": 20, "parcela": 674.65}},
    {"nome": "B", "placas": [{"modelo": "rtx-5060", "qtd": 3, "preco": None, "maq": "novo"}], "pcNovo": {"custo": 1500},
     "pagamento": {"tipo": "avista", "parcelas": 12}, "dinheiro": {"tipo": "meu", "valor": 0, "parcelas": 12, "parcela": 0}},
    {"nome": "C", "placas": [{"modelo": "rtx-5060", "qtd": 4, "preco": 2600, "maq": "m-ext"}], "pcNovo": {"custo": 0},
     "pagamento": {"tipo": "avista", "parcelas": 12}, "dinheiro": {"tipo": "meu", "valor": 0, "parcelas": 12, "parcela": 0}}]}
SETUP_PAR = {"v": 1, "tensao": 220, "parcelas": 12, "aloc": {"l1": "m-pc"}, "maquinas": [
    {"id": "m-pc", "nome": NOMES_PAR["m-pc"], "cpu": "outro", "minerarCpu": False, "x16": 1, "x1": 3, "base": 30, "fonteW": 1000, "selo": "Platinum",
     "gpus": [], "extras": [], "nova": False},
    {"id": "m-ext", "nome": NOMES_PAR["m-ext"], "cpu": "outro", "minerarCpu": False, "x16": 1, "x1": 3, "base": 30, "fonteW": 500, "selo": "Bronze",
     "gpus": [], "extras": [], "nova": False}]}
DADOS_PAR = {**DADOS, "min-setup": SETUP_PAR,
             "min-cfg": {**CFG, "dolar": 5.42, "tarifa": 0.96, "bandeira": 0, "horas": 24, "margem": 26, "cdi": 13.65, "pctCdi": 120, "deprec": 25, "sim": SIM_PAR}}
PCS_PAR = [{"id": "m-pc", "nome": NOMES_PAR["m-pc"], "fonteW": 1000, "selo": "Platinum", "jaGasta": 360},
           {"id": "m-ext", "nome": NOMES_PAR["m-ext"], "fonteW": 500, "selo": "Bronze", "jaGasta": 0}]
# o que se compara de cada opção (o texto do aviso de PC que sumiu fala do lugar onde ficam os PCs, que muda de nome)
RESUMO_SIM = """(() => { const T = simularTudo();
  return {prazo: T.prazo, f: T.F.f, ops: T.ops.map(r => ({nome: r.nome, ok: r.ok, texto: r.texto || "", preco: r.ok ? r.preco : null,
    bruto1: r.ok ? r.bruto1 : null, luz: r.ok ? r.min.luz : null, avisos: r.avisos.map(a => a.t.replace("em Montar setup", "em Seus PCs")),
    juros: r.ok ? r.juros : null,
    cen: r.ok ? Object.fromEntries(Object.entries(r.cen).map(([k, f]) => [k, {sePaga: f.sePaga, resultado: f.fim.resultado,
      comRevenda: f.fim.comRevenda, piorM: f.pior.m, piorConta: f.pior.conta}])) : null}))}; })()"""


def diferencas(a, b, tol=1e-6, onde=""):
    """onde a e b diferem (números com diferença de até tol valem como iguais)"""
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        return [] if a == b else [f"{onde}: {a!r} × {b!r}"]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return [] if abs(a - b) <= tol else [f"{onde}: {a!r} × {b!r}"]
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [f"{onde}: chaves {sorted(a)} × {sorted(b)}"]
        return [d for k in a for d in diferencas(a[k], b[k], tol, f"{onde}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{onde}: {len(a)} itens × {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diferencas(x, y, tol, f"{onde}[{i}]")]
    return [f"{onde}: {a!r} × {b!r}"]


def paridade(p):
    prog = js(abrir(p, dados=DADOS_PAR), RESUMO_SIM)
    pg = abrir_web(p)
    js(pg, "pcs = pcsOk(%s); cfg.sim = %s; aplicarNumeros(); 1" % (json.dumps(PCS_PAR), json.dumps(SIM_PAR)))
    web = js(pg, RESUMO_SIM)
    ops = campo(prog, "ops") or []
    # a comparação tem de ter o que comparar: as três opções com contas, o aviso da fonte, os juros e o prazo do empréstimo
    checa("programa: as três opções com contas, o aviso da fonte e os juros",
          len(ops) == 3 and all(o.get("ok") for o in ops) and any("80%" in t for o in ops for t in o.get("avisos", []))
          and campo(ops, 0, "juros", "i") is not None and campo(prog, "prazo") == 20 and perto(campo(prog, "f"), 0.74, 1e-12), prog)
    d = diferencas(prog, web)
    checa("página e programa dão os mesmos resultados", not d, d[:6])
    checa("sem erros na comparação", not erros(pg), erros(pg)[:3])


with sync_playwright() as p:
    gerar(p)
    contas(p)
    paridade(p)
fim()
