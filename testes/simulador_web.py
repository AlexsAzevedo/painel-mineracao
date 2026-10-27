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


def copia_com(antes, depois, todas=False):
    """uma cópia do mineracao.html com o trecho trocado (para ver o gerador parar quando o painel muda)"""
    t = open(PAGINA, encoding="utf-8").read()
    assert antes in t, antes
    caminho = os.path.join(TMP, "painel-mudado.html")
    open(caminho, "w", encoding="utf-8").write(t.replace(antes, depois) if todas else t.replace(antes, depois, 1))
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
    faltam = [x for x in ['id="v-sim"', "function fluxoSim", "const CATALOGO_RAW", "--viz-a", ".sim-op{", "function eficiencia", "const MERCADO",
                          "const OFERTAS", "function lojasBusca", "const urlBuscaFb", "const UF_NOMES", "const semAcento", "const NOTEBOOK"] if x not in html]
    checa("leva o simulador do painel", not faltam, faltam)
    checa("contrato do artifact: sem doctype, html, head nem body, e o título primeiro",
          not re.search(r"<(?:!doctype|html|head|body)\b", html, re.I) and html.lstrip().startswith("<title>Simulador de placas</title>"))
    checa("cores nos três estados do tema", ':root:not([data-theme="light"])' in html and ':root[data-theme="dark"]' in html and "data-tema" not in html.split("<script>")[0])
    pg = abrir_web(p)
    checa("abre sem erros, com o simulador à mostra", visivel(pg, "#v-sim") and visivel(pg, "#sim-ops .sim-op") and not erros(pg), erros(pg)[:3])
    # o painel sem uma das peças: o gerador para e diz o que faltou, sem gerar meia página
    for trecho, nome in (("/* ---------- simulador de compra ----------", "bloco do simulador"), ("function eficiencia(", "eficiencia"),
                         ("/* fim do simulador de compra */", "fim do CSS do simulador"), ("function lojasBusca(", "lojasBusca"),
                         ("const urlBuscaFb =", "urlBuscaFb")):
        outra = os.path.join(TMP, "outra.html")
        if os.path.exists(outra):
            os.remove(outra)
        r = rodar_gerador(painel=copia_sem(trecho), saida=outra)
        checa(f"peça faltando ({nome}): para com aviso", r.returncode == 1 and "não achei" in (r.stdout + r.stderr) and not os.path.exists(outra),
              (r.stdout + r.stderr)[-200:])
    # o painel mudado de jeitos que deixariam a página quebrada: o gerador também para
    for (antes, depois, todas), nome in (
            (('const SELOS = {"Sem selo"', 'const SELOS = {\n  "Sem selo"', False), "const em várias linhas"),
            (('<section class="view" id="v-sim" aria-labelledby="t-sim" hidden>',
              '<section class="view" id="v-sim" aria-labelledby="t-sim" hidden>\n<section class="extra"></section>', False), "seção dentro da seção"),
            (("calcMaq(", "calcularMaq(", True), "calcMaq com outro nome"),
            (("[0] || null;\n}\n/* fonte à venda mais barata", "[0] || null;\n} // fim\n/* fonte à venda mais barata", False), "função fechada com comentário"),
            (("0.175 : 0.15; }", "0.175 : 0.15; ", False), "erro de sintaxe no bloco")):
        outra = os.path.join(TMP, "outra.html")
        if os.path.exists(outra):
            os.remove(outra)
        r = rodar_gerador(painel=copia_com(antes, depois, todas), saida=outra)
        checa(f"painel mudado ({nome}): para com aviso", r.returncode == 1 and "não achei" in (r.stdout + r.stderr) and not os.path.exists(outra),
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


NUM = '#web-numeros [data-num="%s"]'
PC = '#web-pcs [data-pc="%s"][data-campo="%s"]'
A = '.sim-op[data-op="A"] '
NOMES_PCS = "[...document.querySelectorAll('#web-pcs [data-campo=nome]')].map(i => i.value)"


def lista_pcs(pg, L="A"):
    """os nomes da lista "Em qual PC" da primeira placa da opção L"""
    return js(pg, "[...document.querySelectorAll('.sim-op[data-op=\"%s\"] [data-campo=\"maq\"] option')].map(o => o.textContent)" % L)


def montar_a(pg, modelo="rtx-5070", qtd="2"):
    escolhe(pg, A + '[data-campo="modelo"]', modelo)
    preenche(pg, A + '[data-campo="qtd"]', qtd)


def tela(p):
    pg = abrir_web(p)
    checa("cabeçalho da página, sem o título da tela do programa", texto(pg, ".web-topo h1") == "Simulador de placas" and visivel(pg, ".web-topo h1")
          and not visivel(pg, "#v-sim > .vh"))
    vals = [valor(pg, NUM % k) for k in ("dolar", "luz", "horas", "real", "cdi", "pctCdi", "deprec")]
    checa("Seus números com os valores iniciais", vals == ["5,42", "0,96", "24", "74", "13,65", "120", "25"], vals)
    nomes = js(pg, NOMES_PCS)
    checa("Seus PCs com os 3 PCs", nomes == ["PC pessoal", "PC extra (i5-13400)", "PC extra (i7-8700)"], nomes)
    r = [valor(pg, PC % ("pc-pessoal", c)) for c in ("fonteW", "selo", "jaGasta")]
    checa("o PC pessoal: 1000 W Platinum, 360 W hoje", r == ["1000", "Platinum", "360"], r)
    checa("a dica do PC desligado", "0 W = desligado" in texto(pg, "#web-pcs"))
    checa("Em qual PC: os 3 PCs e Um PC novo", lista_pcs(pg) == nomes + ["Um PC novo"], lista_pcs(pg))
    montar_a(pg)
    res0 = texto(pg, A + ".sim-res")
    checa("a opção A faz a conta", "Lucro da mineração no 1º mês" in res0, res0[:200])
    b0, l0 = js(pg, "simularTudo().ops[0].bruto1"), js(pg, "simularTudo().ops[0].min.luz")
    preenche(pg, NUM % "real", "50")
    checa("rendimento real 50%: o ganho cai para 50/74", perto(js(pg, "simularTudo().ops[0].bruto1"), b0 * 50 / 74, 1e-9) and "50%" in texto(pg, "#sim-fator"),
          [b0, js(pg, "simularTudo().ops[0].bruto1"), texto(pg, "#sim-fator")])
    preenche(pg, NUM % "luz", "1,2")
    checa("luz a R$ 1,20: a luz sobe 1,2/0,96", perto(js(pg, "simularTudo().ops[0].min.luz"), l0 * 1.2 / 0.96, 1e-9))
    checa("o resultado na tela acompanha os números", texto(pg, A + ".sim-res") != res0)
    # números e PCs estranhos: ao sair do campo, ele mostra o valor que vale
    preenche(pg, NUM % "dolar", "abc")
    preenche(pg, PC % ("pc-i5", "fonteW"), "")
    preenche(pg, PC % ("pc-i5", "jaGasta"), "-20")
    r = [valor(pg, NUM % "dolar"), valor(pg, PC % ("pc-i5", "fonteW")), valor(pg, PC % ("pc-i5", "jaGasta"))]
    checa("campo com letras, vazio ou negativo: mostra o valor que vale", r == ["5,42", "500", "0"], r)
    clica(pg, "#aba-dados")
    preenche(pg, PC % ("pc-pessoal", "nome"), "Gamer")
    checa("PC renomeado: o nome novo na lista da opção", "Gamer" in lista_pcs(pg) and valor(pg, A + '[data-campo="maq"]') == "pc-pessoal", lista_pcs(pg))
    clica(pg, '[data-pc-del="pc-pessoal"]')
    av = texto(pg, A + ".sim-avisos")
    checa("PC removido: a opção avisa e usa Um PC novo", "não existe mais em Seus PCs" in av and valor(pg, A + '[data-campo="maq"]') == "novo"
          and js(pg, NOMES_PCS) == ["PC extra (i5-13400)", "PC extra (i7-8700)"], av)
    clica(pg, "#web-pc-add")
    nomes = js(pg, NOMES_PCS)
    checa("+ PC: uma linha nova, na lista da opção, com o cursor no nome", len(nomes) == 3 and nomes[-1] in lista_pcs(pg)
          and js(pg, "document.activeElement.dataset.campo") == "nome", [nomes, lista_pcs(pg)])
    t = js(pg, "document.body.innerText")
    checa("sem NaN, Infinity nem undefined", not any(x in t for x in ("NaN", "Infinity", "undefined")))
    checa("guardado só neste navegador (sem o banco da página)", "só neste navegador" in texto(pg, "#web-guardado"), texto(pg, "#web-guardado"))
    checa("sem erros na tela", not erros(pg), erros(pg)[:3])


def abas(p):
    pg = abrir_web(p)
    r = js(pg, "[...document.querySelectorAll('.web-abas [role=tab]')].map(t => [t.id, t.getAttribute('aria-selected'), t.getAttribute('aria-controls'), t.tabIndex])")
    checa("três abas, Simular aberta", r == [["aba-simular", "true", "painel-simular", 0], ["aba-placas", "false", "painel-placas", -1], ["aba-dados", "false", "painel-dados", -1]], r)
    r = js(pg, "['painel-simular', 'painel-placas', 'painel-dados'].map(i => { const e = document.getElementById(i); return e ? [e.getAttribute('role'), e.getAttribute('aria-labelledby')] : null; })")
    checa("os painéis das abas", r == [["tabpanel", "aba-simular"], ["tabpanel", "aba-placas"], ["tabpanel", "aba-dados"]], r)
    checa("só o painel da aba aberta aparece", visivel(pg, "#v-sim") and not visivel(pg, "#painel-placas") and not visivel(pg, "#web-numeros"))
    if not existe(pg, "#aba-simular"):
        return checa("abas: as abas existem", False)
    pg.focus("#aba-simular"); pg.keyboard.press("ArrowRight")
    r = [js(pg, "document.activeElement.id"), visivel(pg, "#painel-placas"), visivel(pg, "#v-sim")]
    checa("seta para a direita: Placas", r == ["aba-placas", True, False], r)
    pg.keyboard.press("End")
    pg.keyboard.press("ArrowRight")
    checa("End e a seta voltam ao começo", js(pg, "document.activeElement.id") == "aba-simular" and visivel(pg, "#v-sim"))
    pg.keyboard.press("ArrowLeft")
    checa("seta para a esquerda no começo: Meus dados", js(pg, "document.activeElement.id") == "aba-dados" and visivel(pg, "#web-numeros") and visivel(pg, "#web-pcs"))
    pg.keyboard.press("Home")
    checa("Home: Simular", js(pg, "document.activeElement.id") == "aba-simular" and visivel(pg, "#v-sim"))
    clica(pg, "#aba-dados")
    checa("a aba fica guardada neste aparelho", js(pg, "localStorage.getItem('sim-web-aba')") == "dados")
    checa("barra das abas presa no alto", js(pg, "getComputedStyle(document.querySelector('.web-abas')).position") == "sticky")
    pg2 = abrir_web(p, extra="try{ if(!sessionStorage.getItem('__aba')){ localStorage.setItem('sim-web-aba', 'placas'); sessionStorage.setItem('__aba', '1'); } }catch(e){}")
    checa("abre na aba guardada", visivel(pg2, "#painel-placas") and js(pg2, "document.getElementById('aba-placas').getAttribute('aria-selected')") == "true")
    pg3 = abrir_web(p, extra="try{ if(!sessionStorage.getItem('__aba')){ localStorage.setItem('sim-web-aba', 'outra'); sessionStorage.setItem('__aba', '1'); } }catch(e){}")
    checa("aba guardada que não existe: Simular", visivel(pg3, "#v-sim"))
    pg4 = abrir_web(p, sem_storage=True)
    clica(pg4, "#aba-placas")
    checa("sem armazenamento: abre em Simular e troca de aba sem erro", visivel(pg4, "#painel-placas") and not erros(pg4), erros(pg4)[:3])
    checa("sem erros (abas)", not any(erros(x) for x in (pg, pg2, pg3)), [e for x in (pg, pg2, pg3) for e in erros(x)][:3])


# o que o resumo tem de dizer de cada opção, calculado na página pelo simulador: [letra, placas, resposta, fim, lucro]
ESPERADO_RESUMO = """(() => { const T = simularTudo(), k = T.s.cenarioGrafico; return T.ops.map(r => { if(!r.ok) return [r.nome, r.texto]; const f = r.cen[k];
  return [r.nome, placasSimTxt(r), f.sePaga != null ? `Se paga em ${mesSim(f.sePaga)} (mês ${f.sePaga})` : `Não se paga em ${T.prazo} meses`,
    `No fim (${T.prazo} meses): ${f.fim.resultado >= 0 ? 'sobram' : 'faltam'} ${brl0(Math.abs(f.fim.resultado))}`, `Lucro no 1º mês: ${sinal(r.bruto1 - r.min.luz)}`]; }); })()"""
# as etiquetas que cada opção tem de ter: a que se paga primeiro e a que sobra mais no fim (todas as empatadas)
ETIQUETAS = """(() => { const T = simularTudo(), k = T.s.cenarioGrafico, ok = T.ops.filter(r => r.ok); if(ok.length < 2) return T.ops.map(r => [r.nome, []]);
  const pagas = ok.map(r => r.cen[k].sePaga).filter(m => m != null), cedo = pagas.length ? Math.min(...pagas) : null, mais = Math.max(...ok.map(r => r.cen[k].fim.resultado));
  return T.ops.map(r => [r.nome, !r.ok ? [] : [...(cedo != null && r.cen[k].sePaga === cedo ? ['Se paga primeiro'] : []), ...(r.cen[k].fim.resultado === mais ? ['Sobra mais no fim'] : [])]]); })()"""
QUADROS = "[...document.querySelectorAll('#web-quadros .web-quadro')].map(e => [e.dataset.op, e.innerText, [...e.querySelectorAll('.web-etq')].map(x => x.textContent.trim())])"


def confere_resumo(pg, nome):
    esperado, etq, quadros = js(pg, ESPERADO_RESUMO), js(pg, ETIQUETAS), js(pg, QUADROS)
    ok = isinstance(quadros, list) and [q[0] for q in quadros] == [e[0] for e in esperado] \
        and all(all(x in q[1] for x in e[1:]) for q, e in zip(quadros, esperado)) and [[q[0], q[2]] for q in quadros] == etq
    checa(nome, ok, [quadros, esperado, etq])


def resumo(p):
    pg = abrir_web(p, estado={"v": 1, "t": 1, "pcs": PCS_PAR, "sim": SIM_PAR})
    if not existe(pg, "#web-quadros"):
        return checa("resumo: os quadros existem", False)
    confere_resumo(pg, "resumo: um quadro por opção, com a resposta do simulador e as etiquetas")
    checa("resumo: as três opções têm conta (o teste compara de verdade)", all(len(e) == 5 for e in js(pg, ESPERADO_RESUMO)))
    # cenário: os botões mudam o mesmo cenário do gráfico, e ele fica guardado
    checa("resumo: os três botões de cenário, Estável marcado", js(pg, "[...document.querySelectorAll('[data-cen-res]')].map(b => [b.dataset.cenRes, b.getAttribute('aria-pressed')])")
          == [["estavel", "true"], ["devagar", "false"], ["rapido", "false"]])
    clica(pg, '[data-cen-res="rapido"]')
    r = [js(pg, "cfg.sim.cenarioGrafico"), js(pg, "document.querySelector('[data-cen-res=rapido]').getAttribute('aria-pressed')"), valor(pg, "#sim-cen")]
    checa("resumo: Caindo rápido muda o cenário do gráfico", r == ["rapido", "true", "rapido"], r)
    confere_resumo(pg, "resumo: os quadros no cenário Caindo rápido")
    pg.wait_for_timeout(2500)
    checa("resumo: o cenário fica guardado", campo(js(pg, "JSON.parse(localStorage.getItem('sim-web'))"), "sim", "cenarioGrafico") == "rapido")
    # mudar o rendimento real muda o lucro do quadro
    antes = js(pg, QUADROS)[0][1]
    preenche(pg, NUM % "real", "50")
    confere_resumo(pg, "resumo: acompanha os seus números")
    checa("resumo: o quadro A mudou com o rendimento real", js(pg, QUADROS)[0][1] != antes)
    t = texto(pg, "#web-resumo")
    checa("resumo: sem NaN, Infinity nem undefined", t and not any(x in t for x in ("NaN", "Infinity", "undefined")), t[:200])
    # tocar num quadro abre o Simular naquela opção
    clica(pg, "#aba-placas")
    clica(pg, '#web-quadros .web-quadro[data-op="B"]')
    r = [visivel(pg, "#v-sim"), js(pg, "document.activeElement.matches('.sim-op[data-op=\"B\"] [data-campo=\"modelo\"][data-i=\"0\"]')")]
    checa("resumo: tocar no quadro B abre o Simular na primeira placa de B", r == [True, True], r)
    # empate: A e B iguais levam as duas etiquetas
    a = SIM_PAR["opcoes"][0]
    pg2 = abrir_web(p, estado={"v": 1, "t": 1, "pcs": PCS_PAR, "sim": {"opcoes": [a, {**a, "nome": "B"}]}})
    confere_resumo(pg2, "resumo: no empate, as etiquetas vão para as duas")
    checa("resumo: no empate, as duas com as duas etiquetas", [q[2] for q in js(pg2, QUADROS)] == [["Se paga primeiro", "Sobra mais no fim"]] * 2, js(pg2, QUADROS))
    # uma opção só com conta: sem etiquetas; a sem placa diz o que falta; o quadro "+ Opção"
    pg3 = abrir_web(p, estado={"v": 1, "t": 1, "pcs": PCS_PAR, "sim": {"opcoes": [a, {"nome": "B", "placas": [{"modelo": "", "qtd": 1, "preco": None, "maq": "m-pc"}]}]}})
    confere_resumo(pg3, "resumo: uma opção só com conta, sem etiquetas")
    checa("resumo: a opção sem placa diz o que falta", "Escolha uma placa para ver as contas." in js(pg3, QUADROS)[1][1])
    checa("resumo: com 2 opções, o quadro + Opção", existe(pg3, "#web-quadros .web-quadro-mais") and "+ Opção" in texto(pg3, "#web-quadros .web-quadro-mais"))
    clica(pg3, "#web-quadros .web-quadro-mais")
    r = [js(pg3, "simCfg().opcoes.map(o => o.nome)"), visivel(pg3, "#v-sim"), js(pg3, "document.activeElement.matches('.sim-op[data-op=\"C\"] [data-campo=\"modelo\"]')")]
    checa("resumo: + Opção cria a C e abre o Simular nela", r == [["A", "B", "C"], True, True], r)
    checa("resumo: com 3 opções, sem o + Opção", not existe(pg3, "#web-quadros .web-quadro-mais"))
    checa("sem erros (resumo)", not any(erros(x) for x in (pg, pg2, pg3)), [e for x in (pg, pg2, pg3) for e in erros(x)][:3])


LINKS_5070 = ["https://www.facebook.com/marketplace/category/search/?query=RTX%205070&exact=false&radius=100", "https://www.olx.com.br/estado-sc?q=RTX%205070",
              "https://www.kabum.com.br/busca/rtx-5070", "https://www.pichau.com.br/search?q=RTX%205070", "https://www.terabyteshop.com.br/busca?str=RTX+5070",
              "https://lista.mercadolivre.com.br/rtx-5070", "https://www.google.com/search?tbm=shop&q=placa%20de%20v%C3%ADdeo%20RTX%205070",
              "https://promotech.app.br/comparar/placa-de-video/rtx-5070-vs-rtx-5090"]
LINKS = "(id => [...document.querySelectorAll(`#web-lista .web-placa[data-id=\"${id}\"] details.web-procurar a`)].map(a => [a.href, a.target, a.rel]))"
IDS_LISTA = "[...document.querySelectorAll('#web-lista .web-placa')].map(e => e.dataset.id)"
MARCA_TODAS = "(e => { e.checked = %s; e.dispatchEvent(new Event('change', {bubbles: true})); return 1; })(document.querySelector('#pl-todas'))"


def sem_acento(s):
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn").lower()


def placas(p):
    pg = abrir_web(p)
    if not (existe(pg, "#web-lista") and existe(pg, "#web-melhores")):
        return checa("placas: a lista e as Melhores compras existem", False)
    clica(pg, "#aba-placas")
    g, l = 1564/365*30*5.42*24/24*74/100, 160*24*30/1000*0.96
    c = js(pg, "contaPlaca(byId['rtx-5070'])")
    checa("placas: a conta da RTX 5070", perto(campo(c, "ganho"), g, 1e-9) and perto(campo(c, "luz"), l, 1e-9) and perto(campo(c, "lucro"), g - l, 1e-9)
          and campo(c, "usado") == 5600 and campo(c, "n") == 2 and campo(c, "novo") == 5159 and campo(c, "loja") == "Guerra Digital" and campo(c, "menor") == 5159
          and perto(campo(c, "meses", "menor"), 5159/(g - l), 1e-9) and perto(campo(c, "meses", "usado"), 5600/(g - l), 1e-9), c)
    dados = js(pg, "CATALOGO.map(c => [c.id, c.nome, c.marca, c.w, c.rec, (MERCADO.precos[c.id] || {}).usado || 0, (MERCADO.precos[c.id] || {}).novo || 0, soMineracao(c) || deNotebook(c)])")

    def contas(luz=0.96):
        r = []
        for i, nome, marca, w, rec, usado, novo, especial in dados:
            lucro = rec/365*30*5.42*24/24*74/100 - w*24*30/1000*luz
            ps = [v for v in (usado, novo) if v > 0]
            menor = min(ps) if ps else None
            r.append({"id": i, "nome": nome, "marca": marca, "w": w, "lucro": lucro, "menor": menor, "especial": especial,
                      "meses": menor/lucro if menor and lucro > 0 else None})
        return r
    todas = contas()
    padrao = [x for x in todas if x["menor"] and not x["especial"]]
    por_retorno = lambda lst: [x["id"] for x in sorted(lst, key=lambda x: (x["meses"] is None, x["meses"] or 0))]
    melhores = [x["id"] for x in sorted([x for x in padrao if x["meses"] is not None], key=lambda x: x["meses"])[:5]]
    checa("placas: as Melhores compras", js(pg, "[...document.querySelectorAll('#web-melhores li')].map(e => e.dataset.id)") == melhores,
          [js(pg, "[...document.querySelectorAll('#web-melhores li')].map(e => e.dataset.id)"), melhores])
    checa("placas: a lista no padrão (com preço no Brasil), se paga mais rápido primeiro", js(pg, IDS_LISTA) == por_retorno(padrao), [len(js(pg, IDS_LISTA)), len(padrao)])
    t = texto(pg, '#web-lista .web-placa[data-id="rtx-5070"]')
    m = js(pg, "n1(contaPlaca(byId['rtx-5070']).meses.novo)")
    checa("placas: os preços e os meses da RTX 5070", all(x in t for x in ("Usada R$ 5.600 (2 anúncios)", "Nova R$ 5.159 (Guerra Digital)", f"se paga em {m} meses")), t)
    checa("placas: os links da RTX 5070, numa aba nova", js(pg, LINKS + "('rtx-5070')") == [[u, "_blank", "noopener noreferrer"] for u in LINKS_5070], js(pg, LINKS + "('rtx-5070')"))
    checa("placas: o termo da busca sem a marca na frente", js(pg, "termoBusca(byId['amd-rx-9070-xt'])") == "RX 9070 XT")
    # filtros e ordem
    preenche(pg, "#pl-busca", "5070")
    checa("placas: busca pelo nome", js(pg, IDS_LISTA) == por_retorno([x for x in padrao if "5070" in sem_acento(x["nome"])]), js(pg, IDS_LISTA))
    preenche(pg, "#pl-busca", "")
    escolhe(pg, "#pl-marca", "AMD")
    checa("placas: só AMD", js(pg, IDS_LISTA) == por_retorno([x for x in padrao if x["marca"] == "AMD"]), js(pg, IDS_LISTA))
    escolhe(pg, "#pl-marca", "")
    preenche(pg, "#pl-teto", "3000")
    checa("placas: preço até R$ 3.000", js(pg, IDS_LISTA) == por_retorno([x for x in padrao if x["menor"] <= 3000]), js(pg, IDS_LISTA))
    preenche(pg, "#pl-teto", "")
    for ordem, chave in (("lucro", lambda x: -x["lucro"]), ("preco", lambda x: (x["menor"] is None, x["menor"] or 0)), ("consumo", lambda x: x["w"])):
        escolhe(pg, "#pl-ordem", ordem)
        checa(f"placas: ordem {ordem}", js(pg, IDS_LISTA) == [x["id"] for x in sorted(padrao, key=chave)], js(pg, IDS_LISTA)[:6])
    escolhe(pg, "#pl-ordem", "retorno")
    js(pg, MARCA_TODAS % "true")
    checa("placas: Mostrar todas", js(pg, IDS_LISTA) == por_retorno(todas), len(js(pg, IDS_LISTA)))
    # o catálogo de hoje não tem placa só de mineração (as CMP ficaram só no LEGADO): a etiqueta vai conferida numa inventada
    cmp = js(pg, "(c => htmlPlaca({c, r: contaPlaca(c)}))({...byId['rtx-5070'], id: 'cmp-teste', nome: 'NVIDIA CMP Teste', curto: 'CMP Teste'})")
    checa("placas: as etiquetas notebook e só mineração", "notebook" in texto(pg, '#web-lista .web-placa[data-id="rtx-4050"]') and "só mineração" in cmp, cmp[:200])
    checa("placas: sem preço no Brasil", "Sem preço no Brasil na pesquisa" in texto(pg, '#web-lista .web-placa[data-id="gtx-1650-super"]'))
    # a luz cara: a lista diz quando a luz come o lucro
    clica(pg, "#aba-dados"); preenche(pg, NUM % "luz", "5"); clica(pg, "#aba-placas")
    negativa = next(x["id"] for x in contas(5) if x["lucro"] <= 0)
    checa("placas: a luz come o lucro", "A luz come o lucro" in texto(pg, f'#web-lista .web-placa[data-id="{negativa}"]'), negativa)
    js(pg, MARCA_TODAS % "false")
    nota = texto(pg, "#web-placas")
    checa("placas: a nota dos preços e da conta", "22/10/2026" in nota and "no Simular entram a fonte e o resto do PC" in nota)
    t = texto(pg, "#painel-placas")
    checa("placas: sem NaN, Infinity nem undefined", not any(x in t for x in ("NaN", "Infinity", "undefined")))
    # a busca de usadas, em Meus dados
    clica(pg, "#aba-dados")
    BUSCA = '#web-busca [data-busca="%s"]'
    checa("busca de usadas: SC e 100 km", [valor(pg, BUSCA % "uf"), valor(pg, BUSCA % "raio")] == ["SC", "100"])
    escolhe(pg, BUSCA % "uf", "PR"); preenche(pg, BUSCA % "raio", "50")
    links = [x[0] for x in js(pg, LINKS + "('rtx-5070')")]
    checa("busca de usadas: os links acompanham", links[:2] == ["https://www.facebook.com/marketplace/category/search/?query=RTX%205070&exact=false&radius=50",
                                                             "https://www.olx.com.br/estado-pr?q=RTX%205070"], links[:2])
    pg.wait_for_timeout(2500)
    checa("busca de usadas: fica guardada", campo(js(pg, "JSON.parse(localStorage.getItem('sim-web'))"), "busca") == {"uf": "PR", "raio": 50})
    r = []
    for v in ("abc", "5", "9999"):
        preenche(pg, BUSCA % "raio", v); r.append(valor(pg, BUSCA % "raio"))
    checa("busca de usadas: raio estranho fica no anterior ou no limite", r == ["50", "10", "500"], r)
    checa("busca de usadas: estado que não existe fica no anterior", js(pg, "buscaOk({uf: 'XX'}).uf") == "PR")
    pg2 = abrir_web(p, estado={"v": 1, "t": 1})
    checa("busca de usadas: estado guardado sem ela abre com SC e 100", js(pg2, "busca") == {"uf": "SC", "raio": 100})
    checa("sem erros (placas)", not erros(pg) and not erros(pg2), (erros(pg) + erros(pg2))[:3])


PL = '#web-lista .web-placa[data-id="%s"] '
OPCOES = "simCfg().opcoes.map(o => [o.nome, o.placas.map(x => [x.modelo, x.qtd, x.preco, x.maq])])"
RADIOS = "(s => [...document.querySelectorAll(s + '.web-escolha [data-esc-preco]')].map(r => [r.value, r.checked, r.closest('label').innerText.trim()]))"
BOTOES = "(s => [...document.querySelectorAll(s + '.web-escolha [data-esc-op]')].map(b => [b.dataset.escOp, b.innerText.trim()]))"
FOCO = "(s => document.activeElement && document.activeElement.matches(s))"
ESCOLHAS_ABERTAS = "[...document.querySelectorAll('.web-escolha')].filter(e => !e.hidden).length"


def simular_pela_lista(pg, card, onde, preco=None, lugar=PL):
    """Simular numa placa da lista (ou das Melhores compras), com o preço escolhido, e onde colocar"""
    clica(pg, "#aba-placas")
    clica(pg, lugar % card + "[data-simular]")
    if preco is not None:
        clica(pg, lugar % card + '.web-escolha [data-esc-preco][value="%s"]' % preco)
    return clica(pg, lugar % card + '.web-escolha [data-esc-op="%s"]' % onde)


def simular_lista(p):
    pg = abrir_web(p)
    if not existe(pg, PL % "rtx-5060" + "[data-simular]"):
        return checa("simular pela lista: o botão Simular de cada placa existe", False)
    clica(pg, "#aba-placas")
    clica(pg, PL % "rtx-5060" + "[data-simular]")
    radios, botoes = js(pg, RADIOS + "('%s')" % (PL % "rtx-5060")), js(pg, BOTOES + "('%s')" % (PL % "rtx-5060"))
    checa("simular pela lista: a escolha abre na placa, com o menor preço marcado", visivel(pg, PL % "rtx-5060" + ".web-escolha")
          and radios == [["2600", True, "Usada R$ 2.600"], ["2665", False, "Nova R$ 2.665"]], radios)
    checa("simular pela lista: onde colocar, Opção A ou Nova opção, e Cancelar", [b[0] for b in botoes] == ["A", "nova"] and botoes[0][1].startswith("Opção A")
          and botoes[1][1] == "Nova opção" and existe(pg, PL % "rtx-5060" + ".web-escolha [data-esc-cancelar]"), botoes)
    checa("simular pela lista: o Simular diz que a escolha está aberta", js(pg, "document.querySelector('%s[data-simular]').getAttribute('aria-expanded')" % (PL % "rtx-5060")) == "true")
    # a nova, na Opção A que só tem a linha vazia: entra nela, e o Simular abre com o cursor na quantidade
    clica(pg, PL % "rtx-5060" + '.web-escolha [data-esc-preco][value="2665"]')
    clica(pg, PL % "rtx-5060" + '.web-escolha [data-esc-op="A"]')
    r = [js(pg, OPCOES), js(pg, "document.querySelector('#aba-simular').getAttribute('aria-selected')"), visivel(pg, "#v-sim"),
         js(pg, FOCO + "('.sim-op[data-op=\"A\"] [data-campo=\"qtd\"][data-i=\"0\"]')"), js(pg, ESCOLHAS_ABERTAS)]
    checa("simular pela lista: na linha vazia da Opção A, com o preço escolhido, e o Simular aberto nela",
          r == [[["A", [["rtx-5060", 1, 2665, "pc-pessoal"]]]], "true", True, True, 0], r)
    # numa opção com placa: mais uma linha, no PC da última
    escolhe(pg, A + '[data-campo="maq"][data-i="0"]', "pc-i5")
    simular_pela_lista(pg, "rtx-5070", "A")
    r = [js(pg, OPCOES), js(pg, FOCO + "('.sim-op[data-op=\"A\"] [data-campo=\"qtd\"][data-i=\"1\"]')")]
    checa("simular pela lista: numa opção com placa, entra como mais uma linha, com 1 placa e o PC da última",
          r == [[["A", [["rtx-5060", 1, 2665, "pc-i5"], ["rtx-5070", 1, 5159, "pc-i5"]]]], True], r)
    # uma linha vazia no fim (do + Placa) recebe a placa, em vez de ficar sobrando
    clica(pg, "[data-sim='add-linha'][data-op='A']")
    simular_pela_lista(pg, "rtx-3070-ti", "A")
    r = js(pg, OPCOES)
    checa("simular pela lista: a linha vazia que sobrou recebe a placa", r == [["A", [["rtx-5060", 1, 2665, "pc-i5"], ["rtx-5070", 1, 5159, "pc-i5"],
                                                                                    ["rtx-3070-ti", 1, 2250, "pc-i5"]]]], r)
    # Nova opção: a B, com a placa
    simular_pela_lista(pg, "rtx-3080-ti", "nova")
    r = [js(pg, OPCOES)[1:], js(pg, FOCO + "('.sim-op[data-op=\"B\"] [data-campo=\"qtd\"][data-i=\"0\"]')")]
    checa("simular pela lista: Nova opção cria a B com a placa", r == [[["B", [["rtx-3080-ti", 1, 3500, "pc-pessoal"]]]], True], r)
    # das Melhores compras também, e uma escolha aberta de cada vez
    clica(pg, "#aba-placas")
    melhor = js(pg, "document.querySelector('#web-melhores li[data-id]').dataset.id")
    clica(pg, PL % "rtx-5060" + "[data-simular]")
    clica(pg, '#web-melhores li[data-id="%s"] [data-simular]' % melhor)
    checa("simular pela lista: das Melhores compras, a escolha abre no item (e a outra fecha)",
          visivel(pg, '#web-melhores li[data-id="%s"] .web-escolha' % melhor) and js(pg, ESCOLHAS_ABERTAS) == 1
          and js(pg, "document.querySelector('%s[data-simular]').getAttribute('aria-expanded')" % (PL % "rtx-5060")) == "false")
    clica(pg, '#web-melhores li[data-id="%s"] .web-escolha [data-esc-op="nova"]' % melhor)
    r = [x[0] for x in js(pg, OPCOES)] + [campo(js(pg, OPCOES), 2, 1, 0, 0)]
    checa("simular pela lista: das Melhores compras, numa Nova opção (a C)", r == ["A", "B", "C", melhor], r)
    # com 3 opções: sem Nova opção
    clica(pg, "#aba-placas")
    clica(pg, PL % "rtx-5060-ti" + "[data-simular]")
    checa("simular pela lista: com 3 opções, sem Nova opção", [b[0] for b in js(pg, BOTOES + "('%s')" % (PL % "rtx-5060-ti"))] == ["A", "B", "C"])
    checa("simular pela lista: com 3 opções, simularPlaca não cria a quarta", js(pg, "(() => { const a = JSON.stringify(cfg.sim); return [simularPlaca('rtx-5060', 'nova', 2600), JSON.stringify(cfg.sim) === a]; })()") == [None, True])
    # Cancelar e Esc: fecham sem mudar nada, com o cursor de volta no Simular
    antes = js(pg, "JSON.stringify(cfg.sim)")
    clica(pg, PL % "rtx-5060-ti" + ".web-escolha [data-esc-cancelar]")
    r = [js(pg, "JSON.stringify(cfg.sim)") == antes, js(pg, ESCOLHAS_ABERTAS), js(pg, "document.querySelector('#aba-placas').getAttribute('aria-selected')"),
         js(pg, FOCO + "('%s[data-simular]')" % (PL % "rtx-5060-ti"))]
    checa("simular pela lista: Cancelar fecha sem mudar nada", r == [True, 0, "true", True], r)
    pg.locator(PL % "rtx-5060-ti" + "[data-simular]").click()
    dentro = js(pg, "!!document.activeElement.closest('.web-escolha')")
    pg.keyboard.press("Escape")
    r = [dentro, js(pg, "JSON.stringify(cfg.sim)") == antes, js(pg, ESCOLHAS_ABERTAS), js(pg, FOCO + "('%s[data-simular]')" % (PL % "rtx-5060-ti"))]
    checa("simular pela lista: o cursor entra na escolha, e Esc fecha sem mudar nada", r == [True, True, 0, True], r)
    # uma escolha aberta fecha ao trocar de aba (as opções podem mudar lá)
    clica(pg, PL % "rtx-5060-ti" + "[data-simular]")
    clica(pg, "#aba-dados"); clica(pg, "#aba-placas")
    checa("simular pela lista: trocar de aba fecha a escolha", js(pg, ESCOLHAS_ABERTAS) == 0)
    # sem preço no Brasil (com Mostrar todas): entra sem preço
    js(pg, MARCA_TODAS % "true")
    clica(pg, PL % "gtx-1650-super" + "[data-simular]")
    radios = js(pg, RADIOS + "('%s')" % (PL % "gtx-1650-super"))
    clica(pg, PL % "gtx-1650-super" + '.web-escolha [data-esc-op="B"]')
    r = [radios, campo(js(pg, OPCOES), 1, 1, 1)]
    checa("simular pela lista: placa sem preço entra sem preço, para digitar no Simular",
          r == [[["", True, "Sem preço: você digita no Simular"]], ["gtx-1650-super", 1, None, "pc-pessoal"]], r)
    checa("simular pela lista: o Simular pede o preço que falta", "Falta o preço da GTX 1650 Super" in texto(pg, '#web-quadros .web-quadro[data-op="B"]'), texto(pg, '#web-quadros .web-quadro[data-op="B"]'))
    js(pg, MARCA_TODAS % "false")
    # sem PCs (todos removidos em Meus dados): a linha nova vai para Um PC novo
    clica(pg, "#aba-dados")
    for _ in range(3):
        clica(pg, "#web-pcs [data-pc-del]")
    simular_pela_lista(pg, "rtx-5060", "A")
    r = [js(pg, "pcs.length"), campo(js(pg, OPCOES), 0, 1, 3)]
    checa("simular pela lista: sem PCs, a linha nova vai para Um PC novo", r == [0, ["rtx-5060", 1, 2600, "novo"]], r)
    pg.wait_for_timeout(2500)
    g = js(pg, "JSON.parse(localStorage.getItem('sim-web')).sim.opcoes.map(o => [o.nome, o.placas.map(x => x.modelo)])")
    checa("simular pela lista: fica guardado", g == [["A", ["rtx-5060", "rtx-5070", "rtx-3070-ti", "rtx-5060"]], ["B", ["rtx-3080-ti", "gtx-1650-super"]], ["C", [melhor]]], g)
    # a linha vazia guardada com um PC que não existe mais recebe a placa em Um PC novo; uma opção sem linhas, no primeiro PC
    vazia = {"nome": "A", "placas": [{"modelo": "", "qtd": 1, "preco": None, "maq": "pc-pessoal"}], "pcNovo": {"custo": 0},
             "pagamento": {"tipo": "avista", "parcelas": 12}, "dinheiro": {"tipo": "meu", "valor": 0, "parcelas": 12, "parcela": 0}}
    pg2 = abrir_web(p, estado={"v": 1, "t": 1, "pcs": [], "sim": {"prazo": 0, "cenarioGrafico": "estavel", "opcoes": [vazia, {**vazia, "nome": "B", "placas": []}]}})
    simular_pela_lista(pg2, "rtx-5060", "A")
    js(pg2, "pcs = pcsOk(%s); renderPcs(); 1" % json.dumps(PCS_PAR))
    simular_pela_lista(pg2, "rtx-5070", "B")
    r = [campo(js(pg2, OPCOES), 0, 1), campo(js(pg2, OPCOES), 1, 1)]
    checa("simular pela lista: linha vazia com PC que sumiu vai para Um PC novo; opção sem linhas, no primeiro PC",
          r == [[["rtx-5060", 1, 2600, "novo"]], [["rtx-5070", 1, 5159, "m-pc"]]], r)
    # no celular: a escolha e o Simular sem rolar para o lado, com o gráfico na largura da tela e botões de 44 px
    pg3 = abrir_web(p, largura=390, altura=844)
    clica(pg3, "#aba-placas")
    clica(pg3, PL % "rtx-5070" + "[data-simular]")
    aberta = [js(pg3, "document.documentElement.scrollWidth"),
              js(pg3, "[...document.querySelectorAll('.web-escolha:not([hidden]) button, .web-escolha:not([hidden]) label')].map(e => Math.round(e.getBoundingClientRect().height))")]
    clica(pg3, PL % "rtx-5070" + '.web-escolha [data-esc-op="A"]')
    r = js(pg3, "[document.documentElement.scrollWidth, innerWidth, (e => e && e.getBoundingClientRect().width)(document.querySelector('#sim-graf svg')), document.querySelector('#sim-graf').clientWidth]")
    checa("celular: Simular pela lista sem rolar para o lado, com o gráfico na largura da tela",
          aberta[0] <= 390 and r[0] <= r[1] and r[2] is not None and r[2] <= r[3] + 0.5, [aberta[0], r])
    checa("celular: os botões e os preços da escolha com 44 px", aberta[1] and min(aberta[1]) >= 44, aberta[1])
    checa("sem erros (simular pela lista)", not any(erros(x) for x in (pg, pg2, pg3)), [e for x in (pg, pg2, pg3) for e in erros(x)][:3])


def foco_real(p):
    """Com cliques e teclas de verdade: depois de digitar num campo, o clique ou o Tab seguinte chega aonde a pessoa quis."""
    pg = abrir_web(p)
    if not (existe(pg, NUM % "dolar") and existe(pg, PC % ("pc-i5", "jaGasta")) and existe(pg, "#aba-dados")):
        return checa("foco de verdade: os campos de Seus números e Seus PCs e as abas existem", False)
    clica(pg, "#aba-dados")
    pg.click(NUM % "dolar"); pg.keyboard.press("Control+A"); pg.keyboard.type("5,6")
    pg.click(NUM % "luz")
    r = [js(pg, "document.activeElement.dataset.num"), js(pg, "numeros.dolar"), valor(pg, NUM % "dolar")]
    checa("dólar com vírgula e clique na luz: o foco vai para a luz", r == ["luz", 5.6, "5,6"], r)
    pg.keyboard.press("Control+A"); pg.keyboard.type("-3"); pg.keyboard.press("Tab")
    r = [valor(pg, NUM % "luz"), js(pg, "numeros.luz"), js(pg, "document.activeElement.dataset.num")]
    checa("luz negativa e Tab: o campo mostra 0 e o foco segue", r == ["0", 0, "horas"], r)
    pg.click(PC % ("pc-i5", "jaGasta")); pg.keyboard.press("Control+A"); pg.keyboard.type("120")
    pg.click("#aba-simular")
    r = [js(pg, "document.activeElement.id"), js(pg, "pcs[1].jaGasta"), visivel(pg, "#v-sim")]
    checa("já gasta e clique na aba Simular: o foco vai para a aba e o valor fica", r == ["aba-simular", 120, True], r)
    pg.click(A + '[data-campo="modelo"]')
    checa("e a placa da opção A recebe o clique", js(pg, "document.activeElement.matches('.sim-op[data-op=\"A\"] [data-campo=\"modelo\"]')") is True)
    pg.keyboard.press("Escape")
    pg.click("#aba-dados")
    pg.click(PC % ("pc-i7", "nome")); pg.keyboard.press("Control+A"); pg.keyboard.type("Rig da garagem")
    pg.click(NUM % "real")
    r = [js(pg, "document.activeElement.dataset.num"), lista_pcs(pg)[2]]
    checa("nome do PC e clique noutro campo: o foco vai para ele, com o nome na lista", r == ["real", "Rig da garagem"], r)
    checa("sem erros (foco de verdade)", not erros(pg), erros(pg)[:3])


def guardar(p):
    pg = abrir_web(p)
    montar_a(pg)
    preenche(pg, NUM % "real", "60")
    preenche(pg, PC % ("pc-i7", "jaGasta"), "200")
    checa("mexer não grava na hora", js(pg, "localStorage.getItem('sim-web')") is None)
    pg.wait_for_timeout(2500)
    salvo = js(pg, "JSON.parse(localStorage.getItem('sim-web'))")
    checa("grava 2 s depois da última mudança, com a hora dela", campo(salvo, "v") == 1 and campo(salvo, "t") == AGORA_MS
          and campo(salvo, "numeros", "real") == 60 and campo(salvo, "pcs", 2, "jaGasta") == 200
          and campo(salvo, "sim", "opcoes", 0, "placas", 0, "modelo") == "rtx-5070", salvo)
    pg2 = abrir_web(p, estado=salvo)
    r = [valor(pg2, NUM % "real"), valor(pg2, PC % ("pc-i7", "jaGasta")), valor(pg2, A + '[data-campo="modelo"]'), valor(pg2, A + '[data-campo="qtd"]')]
    checa("abre de novo igual", r == ["60", "200", "rtx-5070", "2"], r)
    checa("e com a mesma conta", perto(js(pg2, "simularTudo().ops[0].bruto1"), js(pg, "simularTudo().ops[0].bruto1"), 1e-9))
    # esconder a página grava já o que esperava
    preenche(pg2, PC % ("pc-pessoal", "nome"), "Gamer")
    preenche(pg2, NUM % "horas", "20")
    pg2.evaluate("Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true}); document.dispatchEvent(new Event('visibilitychange'))")
    salvo = js(pg2, "JSON.parse(localStorage.getItem('sim-web'))")
    checa("esconder a página grava na hora", campo(salvo, "pcs", 0, "nome") == "Gamer" and campo(salvo, "numeros", "horas") == 20, salvo)
    checa("sem erros (guardar)", not erros(pg) and not erros(pg2), (erros(pg) + erros(pg2))[:3])


def celular(p):
    pg = abrir_web(p, largura=390, altura=844)
    montar_a(pg)
    clica(pg, "[data-sim='add-op']")
    caixa = "(s => { const e = document.querySelector(s); if(!e) return null; const r = e.getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom]; })"
    largura = {}
    for aba in ("simular", "placas", "dados"):
        clica(pg, f"#aba-{aba}")
        largura[aba] = js(pg, "document.documentElement.scrollWidth")
    checa("celular: as três abas", js(pg, "document.querySelectorAll('.web-abas [role=tab]').length") == 3)
    checa("celular: nenhuma aba rola para o lado", all(v is not None and v <= 390 for v in largura.values()), largura)
    clica(pg, "#aba-dados")
    cx = js(pg, f"['#web-numeros', '#web-pcs'].map({caixa})")
    checa("celular: Seus números em cima de Seus PCs", isinstance(cx, list) and all(cx) and all(c[0] >= 0 and c[1] <= 390 for c in cx) and cx[1][2] >= cx[0][3], cx)
    altos = js(pg, "[...document.querySelectorAll('#web-numeros input, #web-pcs input, #web-pcs select, #web-pcs button, .web-abas [role=tab]')].filter(e => e.getClientRects().length).map(e => Math.round(e.getBoundingClientRect().height))")
    checa("celular: campos, botões e abas com 44 px de altura", altos and min(altos) >= 44, altos)
    clica(pg, "#aba-simular")
    cx = js(pg, f"['.sim-op[data-op=\"A\"]', '.sim-op[data-op=\"B\"]'].map({caixa})")
    checa("celular: as opções uma embaixo da outra", isinstance(cx, list) and all(cx) and all(c[0] >= 0 and c[1] <= 390 for c in cx) and cx[1][2] >= cx[0][3], cx)
    checa("sem erros (celular)", not erros(pg), erros(pg)[:3])


def sem_armazenamento(p):
    pg = abrir_web(p, sem_storage=True)
    checa("sem onde guardar: abre com os valores iniciais, em Simular", valor(pg, NUM % "dolar") == "5,42" and len(js(pg, NOMES_PCS)) == 3 and visivel(pg, "#v-sim"))
    montar_a(pg)
    preenche(pg, NUM % "real", "80")
    pg.wait_for_timeout(2500)
    checa("sem onde guardar: a conta funciona", "Lucro da mineração no 1º mês" in texto(pg, A + ".sim-res") and "80%" in texto(pg, "#sim-fator"))
    checa("sem onde guardar: avisa que vale até fechar", "não deixa guardar" in texto(pg, "#web-guardado"), texto(pg, "#web-guardado"))
    checa("sem onde guardar: sem erros", not erros(pg), erros(pg)[:3])


# o banco da página de mentira (a mesma interface de window.claude.use("db") e use("user")); cada resposta demora ms
BANCO = """(() => { const B = window.__banco = {docs: %s, sets: 0, nulo: %s, ms: %d};
  const copia = o => JSON.parse(JSON.stringify(o)), espera = () => new Promise(r => setTimeout(r, B.ms));
  const db = {doc: path => ({path, id: path.split('/').pop(),
    get: async () => { await espera(); const d = B.docs[path]; return {id: path.split('/').pop(), exists: !!d, data: () => d ? copia(d) : undefined, metadata: {fromCache: false, hasPendingWrites: false}}; },
    set: async o => { await espera(); B.sets++; B.docs[path] = copia(o); }})};
  window.claude = {use: async n => { await espera(); return B.nulo ? null : n === 'db' ? db : n === 'user' ? {id: async () => 'u1'} : null; }};
})();"""
DOC = "data/users/u1/simulador"
HORA = 3600 * 1000


def banco_falso(docs, nulo=False, ms=300):
    return BANCO % (json.dumps(docs), "true" if nulo else "false", ms)


def banco(p):
    no_banco = {"v": 1, "t": AGORA_MS - HORA, "numeros": {"dolar": 5.42, "luz": 0.96, "horas": 24, "real": 61, "cdi": 13.65, "pctCdi": 120, "deprec": 25},
                "pcs": [{"id": "pc-b", "nome": "Do banco", "fonteW": 750, "selo": "Gold", "jaGasta": 300}],
                "sim": {"opcoes": [{"nome": "A", "placas": [{"modelo": "rtx-5060", "qtd": 3, "preco": 2500, "maq": "pc-b"}]}]}}
    no_navegador = {**no_banco, "t": AGORA_MS - 2 * HORA, "numeros": {**no_banco["numeros"], "real": 70},
                    "pcs": [{"id": "pc-n", "nome": "Do navegador", "fonteW": 500, "selo": "Bronze", "jaGasta": 0}]}
    # o banco tem o mais novo: abre o do banco (PC e celular iguais)
    pg = abrir_web(p, estado=no_navegador, extra=banco_falso({DOC: no_banco}))
    pg.wait_for_timeout(1200)
    if not existe(pg, NUM % "real"):
        return checa("banco da página: os campos de Seus números existem", False)
    r = [valor(pg, NUM % "real"), js(pg, NOMES_PCS), valor(pg, A + '[data-campo="qtd"]')]
    checa("banco da página: abre o que está guardado lá (PC e celular iguais)", r == ["61", ["Do banco"], "3"], r)
    checa("banco da página: diz que abre igual no PC e no celular", "abre igual no PC e no celular" in texto(pg, "#web-guardado"), texto(pg, "#web-guardado"))
    checa("banco da página: só abrir não grava", js(pg, "__banco.sets") == 0)
    checa("banco da página: o navegador fica com o do banco", campo(js(pg, "JSON.parse(localStorage.getItem('sim-web'))"), "numeros", "real") == 61)
    clica(pg, "#aba-dados")
    pg.click(NUM % "real"); pg.keyboard.press("Control+A"); pg.keyboard.type("65")
    pg.wait_for_timeout(2800)
    r = [js(pg, f"__banco.docs['{DOC}'].numeros.real"), js(pg, f"__banco.docs['{DOC}'].t"), js(pg, "__banco.sets")]
    checa("banco da página: grava uma vez depois de digitar, com a hora", r == [65, AGORA_MS, 1], r)
    # mudou noutro aparelho (mais novo): ao voltar para a página, ela pega o que está no banco, sem gravar de novo
    js(pg, f"Object.assign(__banco.docs['{DOC}'], {{t: {AGORA_MS + 60000}}}); __banco.docs['{DOC}'].numeros.real = 66; document.dispatchEvent(new Event('visibilitychange')); 1")
    pg.wait_for_timeout(1000)
    checa("banco da página: ao voltar para a página, pega o que mudou noutro aparelho", valor(pg, NUM % "real") == "66" and js(pg, "numeros.real") == 66,
          [valor(pg, NUM % "real"), js(pg, "numeros.real")])
    checa("banco da página: pegar do banco não grava de novo", js(pg, "__banco.sets") == 1, js(pg, "__banco.sets"))
    # o banco ficou para trás (uma gravação não chegou lá): ao voltar, a página manda o daqui, sem voltar atrás
    js(pg, f"Object.assign(__banco.docs['{DOC}'], {{t: {AGORA_MS - HORA}}}); __banco.docs['{DOC}'].numeros.real = 50; document.dispatchEvent(new Event('visibilitychange')); 1")
    pg.wait_for_timeout(1500)
    r = [valor(pg, NUM % "real"), js(pg, f"__banco.docs['{DOC}'].numeros.real")]
    checa("banco da página: banco mais velho ao voltar: fica o daqui e vai para o banco", r == ["66", 66], r)
    # este navegador tem o mais novo ao abrir (a última gravação não chegou ao banco): fica o daqui e vai para o banco
    pg2 = abrir_web(p, estado={**no_navegador, "t": AGORA_MS - 1000, "numeros": {**no_navegador["numeros"], "real": 99}}, extra=banco_falso({DOC: no_banco}))
    pg2.wait_for_timeout(2000)
    r = [valor(pg2, NUM % "real"), js(pg2, NOMES_PCS), js(pg2, f"__banco.docs['{DOC}'].numeros.real")]
    checa("banco da página: o navegador mais novo que o banco: fica o daqui e vai para o banco", r == ["99", ["Do navegador"], 99], r)
    # com uma cópia neste navegador, mexer antes de o banco responder vale e vai para o banco
    pg3 = abrir_web(p, estado=no_navegador, extra=banco_falso({DOC: no_banco}, ms=500))
    preenche(pg3, NUM % "real", "90")
    pg3.wait_for_timeout(3000)
    r = [valor(pg3, NUM % "real"), js(pg3, f"__banco.docs['{DOC}'].numeros.real")]
    checa("banco da página: com cópia neste navegador, mexer antes de ele responder vale", r == ["90", 90], r)
    # aparelho novo (nada neste navegador): mexer antes de o banco responder não apaga o que está guardado
    pg4 = abrir_web(p, extra=banco_falso({DOC: no_banco}, ms=500))
    preenche(pg4, NUM % "dolar", "6")
    pg4.wait_for_timeout(2500)
    r = [valor(pg4, NUM % "real"), js(pg4, NOMES_PCS), valor(pg4, A + '[data-campo="qtd"]'), js(pg4, f"__banco.docs['{DOC}'].pcs[0].nome"),
         js(pg4, f"__banco.docs['{DOC}'].sim.opcoes[0].placas[0].qtd")]
    checa("banco da página: aparelho novo, mexer antes de o banco responder não apaga o guardado", r == ["61", ["Do banco"], "3", "Do banco", 3], r)
    checa("banco da página: e avisa que o que mudou antes ficou de fora", "ficou de fora" in texto(pg4, "#web-guardado"), texto(pg4, "#web-guardado"))
    # enquanto o banco não responde, a página não deixa mexer (e diz por quê)
    pg5 = abrir_web(p, estado=no_navegador, extra=banco_falso({DOC: no_banco}, ms=700))
    r = [js(pg5, "document.querySelector('main.web').inert"), texto(pg5, "#web-guardado")]
    checa("banco da página: abrindo, a página espera o banco", r[0] is True and "Abrindo" in r[1], r)
    pg5.wait_for_timeout(2500)
    checa("banco da página: com a resposta, dá para mexer", js(pg5, "document.querySelector('main.web').inert") is False and valor(pg5, NUM % "real") == "61")
    # sem o banco (fora do claude.ai): fica o do navegador, sem esperar
    pg6 = abrir_web(p, estado=no_navegador, extra=banco_falso({}, nulo=True))
    pg6.wait_for_timeout(800)
    r = [valor(pg6, NUM % "real"), js(pg6, NOMES_PCS), js(pg6, "document.querySelector('main.web').inert")]
    checa("sem o banco: abre o deste navegador", r == ["70", ["Do navegador"], False], r)
    pgs = [pg, pg2, pg3, pg4, pg5, pg6]
    checa("banco da página: sem erros", not any(erros(x) for x in pgs), [e for x in pgs for e in erros(x)][:3])


with sync_playwright() as p:
    gerar(p)
    contas(p)
    paridade(p)
    abas(p)
    resumo(p)
    placas(p)
    simular_lista(p)
    tela(p)
    foco_real(p)
    guardar(p)
    celular(p)
    sem_armazenamento(p)
    banco(p)
fim()
