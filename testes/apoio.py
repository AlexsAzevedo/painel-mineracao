"""Apoio dos testes de navegador do painel (mineracao.html).

Os testes abrem a página do repositório num servidor local, com dados inventados (nada do Alex). Uso:
    from apoio import *
    with sync_playwright() as p:
        pg = abrir(p, dados=DADOS)
        checa("alguma coisa", pg.evaluate("1+1") == 2)
    fim()
"""
import datetime, functools, http.server, json, os, re, socketserver, struct, sys, tempfile, threading, zlib
from playwright.sync_api import sync_playwright  # noqa: F401  (os testes importam daqui)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGINA = os.path.join(RAIZ, "mineracao.html")
BRT = datetime.timezone(datetime.timedelta(hours=-3))
AGORA = datetime.datetime(2026, 10, 25, 14, 0, tzinfo=BRT)      # relógio dos testes (horário de Brasília)
AGORA_MS = int(AGORA.timestamp() * 1000)


def _png1():
    """Uma imagem PNG de 1 pixel (a "foto" que carrega nos testes)."""
    def bloco(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(b"\x00\xf5\xa5\x24\xff")) + bloco(b"IEND", b""))

# ---------- página e servidor ----------
_pasta = tempfile.mkdtemp(prefix="painel-teste-")
with open(PAGINA, encoding="utf-8") as f:
    _html = f.read()
with open(os.path.join(_pasta, "pagina.html"), "w", encoding="utf-8") as f:
    f.write('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + _html + "</html>")


class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


_srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(_Q, directory=_pasta))
threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{_srv.server_address[1]}/pagina.html"

# ---------- dados inventados ----------
PERFIL = {"nome": "Teste", "cidade": "Itajaí", "uf": "SC", "la": -26.9078, "lo": -48.6619, "raio": 100, "quando": 1761300000000}
CFG = {"dolar": 5.04, "tarifa": 0.96, "bandeira": 0, "horas": 24, "meses": 12, "margem": 20, "cdi": 13.65, "pctCdi": 100,
       "revenda": False, "deprec": 25, "cotacoes": {}, "overrides": {}, "perfil": PERFIL}
PLACAS = [{"_id": "l1", "modelo": "amd-rx-9070-xt", "qtd": 1, "preco": 5000, "pagamento": "avista", "parcelas": 1, "data": "2026-10-11", "criado": 1760180000000}]
_VALORES = [14.12, 14.81, 13.25, 15.34, 14.62, 11.08, 14.93, 15.21, 14.44, 13.87, 15.06, 14.71, 12.64, 14.18]
DIARIO = [{"_id": f"2026-10-{11 + i:02d}", "data": f"2026-10-{11 + i:02d}", "valor": v, "moeda": "BRL", "dolar": 5.04, "horas": 24, "obs": "", "criado": 1760200000000 + i}
          for i, v in enumerate(_VALORES)]

FB = "https://scontent.teste.fbcdn.net/v/t45/"
OLX = "https://img.olx.com.br/thumbs500x360/"
def _of(n, site, modelo, preco, titulo, cidade, km, foto="", antigo=0, novo=False, caiu=0):
    return {"site": site, "id": str(1000 + n), "k": f"{site}:{1000 + n}", "url": f"https://www.facebook.com/marketplace/item/{1000 + n}/" if site == "fb" else f"https://sc.olx.com.br/anuncio-{1000000 + n}",
            "titulo": titulo, "preco": preco, "antigo": antigo, "cidade": cidade, "uf": "SC", "modelo": modelo, "km": km, "flags": [],
            "achado": 1761390000000 - n * 60000, "novo": novo, "caiu": caiu, "foto": foto}
# 6 que compensam, 3 apertadas e 3 que não compensam com as premissas de CFG; 8 com foto e 4 sem
OFERTAS_ITENS = [
    _of(1, "fb", "rtx-3070", 1650, "RTX 3070 Gigabyte Gaming OC 8 GB", "Itajaí", 0, FB + "of1.jpg", antigo=1800, caiu=1800),
    _of(2, "olx", "rtx-4060", 1480, "RTX 4060 MSI Ventus 2X 8 GB", "Balneário Camboriú", 15, OLX + "of2.jpg", novo=True),
    _of(3, "fb", "rtx-3080", 2900, "RTX 3080 EVGA FTW3 10 GB", "Navegantes", 10, FB + "of3.jpg"),
    _of(4, "fb", "rtx-3070", 2200, "RTX 3070 Asus Dual", "Brusque", 35),
    _of(5, "fb", "rtx-4060", 1900, "RTX 4060 Galax 1-Click", "Itajaí", 0, FB + "of5.jpg"),
    _of(6, "olx", "rtx-3060-ti", 1700, "RTX 3060 Ti Zotac Twin Edge", "Blumenau", 55),
    _of(7, "fb", "rtx-3060-ti", 2050, "RTX 3060 Ti EVGA XC", "Brusque", 35, FB + "of7.jpg"),
    _of(8, "olx", "rtx-3070", 2600, "RTX 3070 Ti Palit", "Joinville", 90, OLX + "of8.jpg"),
    _of(9, "fb", "rtx-4060", 2700, "RTX 4060 Asus ROG Strix", "Itapema", 25),
    _of(10, "fb", "rtx-3080", 4300, "RTX 3080 Asus TUF 12 GB", "Florianópolis", 95, FB + "of10.jpg"),
    _of(11, "olx", "rtx-3060-ti", 2400, "RTX 3060 Ti Gigabyte Eagle", "Gaspar", 45, OLX + "of11.jpg"),
    _of(12, "fb", "amd-rx-6700-xt", 1250, "RX 6700 XT Sapphire Pulse 12 GB", "Navegantes", 10),
]
OFERTAS = {"quando": 1761397200000, "cidade": "Itajaí", "uf": "SC", "raio": 100, "sites": ["fb", "olx"], "itens": OFERTAS_ITENS,
           "avisos": [], "fbLocal": "", "fora": {}, "brutos": 12, "parado": False}
DADOS = {"min-cfg": CFG, "min-placas": PLACAS, "min-diario": DIARIO, "min-ofertas": OFERTAS}
DADOS_ESPERADO = {
    "recebido_mes": round(sum(_VALORES), 2),     # 198,26
    "dias_grafico_diario": 6,                     # período padrão do Diário: 7 dias (19 a 25/10; anotados 19 a 24)
    "ofertas_filtradas": 9,                       # "Só os que compensam" mostra compensa + apertado
    "ofertas_sem_foto_visiveis": 3,
}

# ---------- window.desktop de mentira ----------
_CELULAR = """(() => {
  window.__pedidos = [];
  const nada = () => {};
  window.desktop = {remoto: true,
    sync: {aoReceber: nada, aoEstado: nada, mudou: nada, info: async () => ({}), atualizar: async () => ({ok: true})},
    pedirAoPc: async (nome, args) => { window.__pedidos.push([nome, args || {}]); return {ok: true}; }};
})();"""
_PC = """(() => {
  window.__acoes = []; window.__leituras = []; window.__notificacoes = []; window.__celular = [];
  const nada = () => {}, vazio = async () => null;
  const leitura = () => window.__leituras.length > 1 ? window.__leituras.shift() : (window.__leituras[0] || {ok: false, erro: "fechado", msg: ""});
  const base = {versao: "1.6.0-teste",
    notificar: async (n) => { window.__notificacoes.push(n); return true; },
    celular: {config: async () => ({ligado: false}), enviar: async (m) => { window.__celular.push(m); return true; }, aoMudar: nada, aoPedir: nada},
    kryptex: {ler: async () => ({erro: "teste"}), entrar: async () => true},
    kryptexApp: {ler: async () => leitura(),
      pausar: async (m) => { window.__acoes.push(["pausar", m]); return leitura(); },
      voltar: async () => { window.__acoes.push(["voltar"]); return leitura(); }},
    acesso: {config: async () => ({ligado: false, enderecos: []}), aoMudar: nada},
    appCelular: {config: async () => null, aoMudar: nada},
    atualizacao: {estado: async () => ({estado: "atual"}), procurar: vazio, instalar: vazio, aoMudar: nada},
    backup: {info: async () => null, salvar: vazio, escolherPasta: vazio, abrirPasta: vazio},
    segundoPlano: async () => ({bandeja: false, iniciar: false, temBandeja: false}),
    inicioWindows: async () => ({comWindows: false, escolheu: false, minimizado: true, bandeja: false, precisa: false}),
    janelaVisivel: async () => true, aoAbrir: nada, dadosMudaram: nada, copiar: async () => true};
  window.desktop = new Proxy(base, {get: (t, k) => (k in t || typeof k === "symbol" || k === "remoto" || k === "app" || k === "sync") ? t[k] : vazio});
})();"""
_SEM_STORAGE = """(() => { const erro = () => { throw new Error("armazenamento bloqueado"); };
  for (const m of ["getItem", "setItem", "removeItem", "key", "clear"]) Storage.prototype[m] = erro; })();"""

_navegador = None
_erros = {}


def abrir(p, largura=1366, altura=900, dados=None, celular=False, pc=False, sem_storage=False, hash="resumo", rotas_fotos=True):
    """Abre a página numa aba nova (contexto novo: localStorage vazio) e devolve a Page."""
    global _navegador
    if _navegador is None:
        _navegador = p.chromium.launch()
    ctx = _navegador.new_context(viewport={"width": largura, "height": altura}, locale="pt-BR", timezone_id="America/Sao_Paulo")
    pg = ctx.new_page()
    pg.set_default_timeout(5000)
    pg.clock.set_fixed_time(AGORA)
    lista = _erros.setdefault(id(pg), [])
    pg.on("pageerror", lambda e: lista.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and lista.append(m.text))
    if rotas_fotos:
        # as fotos de mentira não saem para a internet: "ok.jpg" volta uma imagem de 1 pixel; o resto falha
        png = _png1()
        def foto(rota):
            if rota.request.url.endswith("/ok.jpg"):
                rota.fulfill(status=200, content_type="image/png", body=png)
            else:
                rota.abort()
        pg.route(re.compile(r"^https://[^/]*(fbcdn\.net|olx\.com\.br)/.*"), foto)
    pg.route(re.compile(r"^https://fonts\.(googleapis|gstatic)\.com/.*"), lambda r: r.abort())
    if sem_storage:
        pg.add_init_script(_SEM_STORAGE)
    elif dados:
        semente = "try{ if(!sessionStorage.getItem('__semeado')){ const d = %s; for(const k in d) localStorage.setItem(k, JSON.stringify(d[k])); sessionStorage.setItem('__semeado','1'); } }catch(e){}" % json.dumps(dados, ensure_ascii=False)
        pg.add_init_script(semente)
    if celular:
        pg.add_init_script(_CELULAR)
    if pc:
        pg.add_init_script(_PC)
    pg.goto(URL + "#" + hash)
    pg.wait_for_timeout(500)
    return pg


def erros(pg):
    """Erros da página e do console desde que ela abriu (fora as fontes, que os testes bloqueiam)."""
    return [e for e in _erros.get(id(pg), []) if "fonts.g" not in e and "ERR_FAILED" not in e and "net::" not in e]


# ---------- contraste ----------
_JS_CORES = """(tema) => { const r = document.documentElement, antes = r.dataset.tema; r.dataset.tema = tema;
  const s = getComputedStyle(r), v = n => s.getPropertyValue(n).trim();
  const o = {}; for (const n of ["--bg","--surface","--sunk","--fg","--muted","--accent","--onaccent","--good","--warn","--bad","--side-bg","--side-fg","--side-muted"]) o[n] = v(n);
  r.dataset.tema = antes; return o; }"""
PARES = [("--fg", "--bg"), ("--fg", "--surface"), ("--muted", "--surface"), ("--muted", "--bg"), ("--accent", "--bg"), ("--accent", "--surface"),
         ("--onaccent", "--accent"), ("--good", "--surface"), ("--warn", "--surface"), ("--bad", "--surface"),
         ("--side-fg", "--side-bg"), ("--side-muted", "--side-bg")]


def _rgb(c):
    c = c.strip()
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(x * 2 for x in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.findall(r"[\d.]+", c)
    return tuple(int(float(x)) for x in m[:3])


def _lum(c):
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(x) for x in _rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razao(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def contrastes(pg, tema):
    cores = pg.evaluate(_JS_CORES, tema)
    return {f"{a} sobre {b}": razao(cores[a], cores[b]) for a, b in PARES if cores.get(a) and cores.get(b)}


# ---------- resultado ----------
_ok, _falhas = [], []


def checa(nome, cond, extra=""):
    (_ok if cond else _falhas).append(nome + (f" [{extra}]" if extra not in ("", None) and not cond else ""))


def fim():
    global _navegador
    if _navegador is not None:
        try:
            _navegador.close()
        except Exception:
            pass   # o Playwright já fechou tudo ao sair do "with"
        _navegador = None
    print(json.dumps({"ok": len(_ok), "falhas": _falhas}, ensure_ascii=False, indent=1))
    sys.exit(1 if _falhas else 0)
