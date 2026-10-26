"""O app do celular que se atualiza sozinho, pelo lado da página: a ponte do app (celular/src/ponte-app.js) com um plugin
Atualizador de mentira (a parte Android de verdade é testada no JVM: celular/android, testDebugUnitTest).
A página é a montada por montar-www.py, servida aqui, com um capacitor.js de mentira (nada de celular de verdade).
Uso: python3 testes/atualizador.py"""
import base64, functools, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

CELULAR = os.path.join(RAIZ, "celular")
VERSAO_PC = json.load(open(os.path.join(RAIZ, "desktop", "package.json"), encoding="utf-8"))["version"]
VERSAO_APP = json.load(open(os.path.join(CELULAR, "package.json"), encoding="utf-8"))["version"]
TMP = tempfile.mkdtemp(prefix="atualizador-")
WWW = os.path.join(TMP, "www")


class _Q(http.server.SimpleHTTPRequestHandler):
    """a página montada; o "ntfy" daqui aceita o que o app manda e não tem nada para ler (a sincronia não é o assunto
    deste teste: assim a faixa de "sem conexão" não aparece)"""
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/ntfy"):
            self.send_error(404)
        else:
            super().do_GET()

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        corpo = json.dumps({"id": "t" + str(threading.get_ident()), "time": AGORA_MS // 1000, "event": "message"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(corpo)

    do_PUT = do_POST


_srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(_Q, directory=WWW))
_srv.daemon_threads = True
threading.Thread(target=_srv.serve_forever, daemon=True).start()
PORTA = _srv.server_address[1]
r = subprocess.run([sys.executable, os.path.join(CELULAR, "scripts", "montar-www.py"), "--saida", WWW, "--ntfy", f"http://127.0.0.1:{PORTA}/ntfy"],
                   capture_output=True, text=True)
if r.returncode != 0:
    raise SystemExit("montar-www.py falhou: " + r.stdout + r.stderr)
URL_APP = f"http://127.0.0.1:{PORTA}/index.html"
# a página do teste diz ser a versão 9.8.7 (diferente da do app), para ver qual das duas a ponte usa
VERSAO_PAGINA = "9.8.7"
_ponte = os.path.join(WWW, "ponte-app.js")
_txt = open(_ponte, encoding="utf-8").read()
assert f'const PAINEL = "{VERSAO_PC}";' in _txt
open(_ponte, "w", encoding="utf-8").write(_txt.replace(f'const PAINEL = "{VERSAO_PC}";', f'const PAINEL = "{VERSAO_PAGINA}";'))

ESTADO_BASE = {"app": {"versao": VERSAO_APP, "codigo": 10800}, "painel": {"versao": VERSAO_PC, "origem": "apk", "embutido": VERSAO_PC},
               "procurando": False, "ultimaProcura": AGORA_MS - 1800_000, "instalando": False, "podeInstalar": True, "android": 34}

# o Capacitor de mentira: o Atualizador guarda as chamadas e devolve o estado de __atu (mudar() avisa como o evento "estado")
CAPACITOR = """(() => {
  const base = %s, ouvintes = {}, chamadas = [];
  const copia = (o) => JSON.parse(JSON.stringify(o));
  window.__atu = { chamadas, estado: Object.assign(copia(base), window.__atuInicial || {}),
    mudar(e) { this.estado = Object.assign(copia(base), e); (ouvintes.estado || []).forEach(f => f(copia(this.estado))); } };
  const resp = () => Promise.resolve(copia(window.__atu.estado));
  const Atualizador = {
    estado: () => { chamadas.push(["estado"]); return resp(); },
    procurar: (o) => { chamadas.push(["procurar", o]); return resp(); },
    usarPainel: () => { chamadas.push(["usarPainel"]); return resp(); },
    painelOk: (o) => { chamadas.push(["painelOk", o]); return resp(); },
    instalarApp: () => { chamadas.push(["instalarApp"]); window.__atu.estado.instalando = true; return resp(); },
    visto: (o) => { chamadas.push(["visto", o]); delete window.__atu.estado[o.qual]; return resp(); },
    addListener: (ev, fn) => { (ouvintes[ev] = ouvintes[ev] || []).push(fn); return Promise.resolve({ remove() {} }); }
  };
  const nada = () => Promise.resolve();
  const plugins = { Atualizador,
    App: { addListener: () => Promise.resolve({ remove() {} }), minimizeApp: nada },
    Device: { getInfo: () => Promise.resolve({ name: "Celular de teste" }) },
    SystemBars: { setStyle: nada } };
  window.Capacitor = { isNativePlatform: () => true, getPlatform: () => "android", registerPlugin: (n) => plugins[n] || null };
})();""" % json.dumps(ESTADO_BASE)

CODIGO = "PM1-" + base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
SEMENTE = {"pm-codigo": CODIGO, "pm-aparelho": "aparelho-teste-1", "pm-sinc": json.dumps({"pronto": True, "versao": 1, "ultimaVez": AGORA_MS})}
for k, v in DADOS.items():
    SEMENTE[k] = json.dumps(v)

_pedidos, _erros_app, _nav = [], {}, [None]


def abrir_app(p, inicial=None, quebrar=False, celular_largura=390):
    """abre a página do app (contexto novo) com o Capacitor de mentira; inicial: o estado do Atualizador ao abrir"""
    if _nav[0] is None:
        _nav[0] = p.chromium.launch()
    ctx = _nav[0].new_context(viewport={"width": celular_largura, "height": 844}, locale="pt-BR", timezone_id="America/Sao_Paulo")
    pg = ctx.new_page()
    pg.set_default_timeout(5000)
    pg.clock.set_fixed_time(AGORA)
    lista = _erros_app.setdefault(id(pg), [])
    pg.on("pageerror", lambda e: lista.append(str(e)))
    pg.on("request", lambda req: _pedidos.append(req.url))
    pg.route(re.compile(r".*/capacitor\.js$"), lambda rota: rota.fulfill(status=200, content_type="text/javascript", body=CAPACITOR))
    if quebrar:
        def pagina(rota):
            corpo = rota.fetch().text()
            rota.fulfill(status=200, content_type="text/html", body=corpo.replace("</html>", '<script>throw new Error("teste: o painel quebrou")</script></html>'))
        pg.route(re.compile(r".*/index\.html$"), pagina)
    pg.add_init_script("try{ if(!sessionStorage.getItem('__semeado')){ const d = %s; for (const k in d) localStorage.setItem(k, d[k]); sessionStorage.setItem('__semeado','1'); } }catch(e){}" % json.dumps(SEMENTE))
    if inicial is not None:
        pg.add_init_script("window.__atuInicial = %s;" % json.dumps(inicial))
    pg.goto(URL_APP)
    pg.wait_for_timeout(900)
    return pg


def chamadas(pg):
    return pg.evaluate("__atu.chamadas")


def zerar(pg):
    pg.evaluate("__atu.chamadas.length = 0")


def usou(pg):
    return ["usarPainel"] in chamadas(pg)


def toast(pg):
    return pg.evaluate("(document.getElementById('toast') || {}).textContent || ''")


def mudar(pg, **e):
    pg.evaluate("(e) => __atu.mudar(e)", e)


def ponte(p):
    pg = abrir_app(p)
    checa("confirma que abriu", ["painelOk", {"versao": VERSAO_PAGINA}] in chamadas(pg), chamadas(pg))
    checa("procura ao abrir", ["procurar", {"forcar": False}] in chamadas(pg), chamadas(pg))
    checa("versão da página", pg.evaluate("window.desktop.versao") == VERSAO_PAGINA, pg.evaluate("window.desktop.versao"))
    checa("atualizador para o painel", pg.evaluate("!!window.desktop.atualizador && typeof window.desktop.atualizador.instalarApp === 'function'"))
    checa("estado conhecido", pg.evaluate("((window.desktop.atualizador && window.desktop.atualizador.estado()) || {}).app") == {"versao": VERSAO_APP, "codigo": 10800})
    checa("sem a versão nova pelo GitHub na ponte", pg.evaluate("'versaoNova' in window.desktop.sync.info()") is False)

    zerar(pg)
    mudar(pg, pronta={"versao": "9.9.9"})
    pg.wait_for_timeout(300)
    checa("painel novo na hora", usou(pg), chamadas(pg))

    # com folha aberta: espera; ao fechar, troca
    zerar(pg)
    pg.evaluate("abrirFolha('d-folha')")
    mudar(pg, pronta={"versao": "9.9.9"})
    pg.wait_for_timeout(2500)
    checa("com folha aberta, espera", not usou(pg), chamadas(pg))
    pg.evaluate("fecharFolha()")
    pg.wait_for_timeout(2500)
    checa("ao fechar a folha, troca", usou(pg))

    # com o cursor num campo de texto: espera; ao sair, troca
    zerar(pg)
    pg.evaluate("(() => { const i = document.createElement('input'); i.type = 'text'; i.id = '__campo'; document.querySelector('.main').prepend(i); i.focus(); })()")
    mudar(pg, pronta={"versao": "9.9.9"})
    pg.wait_for_timeout(2500)
    checa("com o cursor num campo, espera", not usou(pg))
    pg.evaluate("document.getElementById('__campo').blur()")
    pg.wait_for_timeout(2500)
    checa("ao sair do campo, troca", usou(pg))
    zerar(pg)
    pg.evaluate("(() => { const c = document.createElement('input'); c.type = 'checkbox'; c.id = '__marca'; document.querySelector('.main').prepend(c); c.focus(); })()")
    mudar(pg, pronta={"versao": "9.9.9"})
    pg.wait_for_timeout(300)
    checa("uma caixa de marcar com o foco não segura a troca", usou(pg))

    # em segundo plano: espera; ao voltar, troca
    zerar(pg)
    pg.evaluate("Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true}); document.dispatchEvent(new Event('visibilitychange'))")
    mudar(pg, pronta={"versao": "9.9.9"})
    pg.wait_for_timeout(2500)
    checa("em segundo plano, espera", not usou(pg))
    pg.evaluate("Object.defineProperty(document, 'visibilityState', {value: 'visible', configurable: true}); document.dispatchEvent(new Event('visibilitychange'))")
    pg.wait_for_timeout(400)
    checa("ao voltar para a frente, troca", usou(pg))

    zerar(pg)
    mudar(pg)
    pg.wait_for_timeout(2500)
    checa("sem pronta, não troca", not usou(pg))
    checa("sem erros na página", not _erros_app[id(pg)], _erros_app[id(pg)])

    pt = abrir_app(p, inicial={"trocou": {"de": "1.8.0", "para": "9.9.9"}})
    checa("aviso de troca", "Painel atualizado: versão 9.9.9" in toast(pt), toast(pt))
    checa("aviso de troca visto", ["visto", {"qual": "trocou"}] in chamadas(pt))
    pv = abrir_app(p, inicial={"voltou": {"de": "9.9.9", "para": "1.8.0"}})
    checa("aviso de volta", "O painel 9.9.9 não abriu direito; voltei para o 1.8.0." in toast(pv), toast(pv))
    checa("aviso de volta visto", ["visto", {"qual": "voltou"}] in chamadas(pv))

    pq = abrir_app(p, quebrar=True)
    checa("o painel quebrado não confirma que abriu", not any(c[0] == "painelOk" for c in chamadas(pq)), chamadas(pq))
    checa("nenhum pedido à API do GitHub", not [u for u in _pedidos if "api.github.com" in u])


def texto(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText.trim() : ''; }", sel)


def visivel(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && !e.hidden && e.getClientRects().length > 0; }", sel)


def clica(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); if(!e) return false; e.click(); return true; }", sel)


def painel(p):
    pg = abrir_app(p)
    pg.evaluate("irPara('premissas'); abrirSecao(document.getElementById('estecel-p'))")   # no celular, os quadros de Premissas abrem pelo título
    pg.wait_for_timeout(200)
    checa("versões no Este celular", texto(pg, "#estecel-versao") == f"painel {VERSAO_PAGINA} · app {VERSAO_APP}", texto(pg, "#estecel-versao"))
    checa("em dia", "em dia, conferido há 30 min" in texto(pg, "#estecel-info"), texto(pg, "#estecel-info"))
    zerar(pg)
    clica(pg, "#estecel-procurar")
    pg.wait_for_timeout(200)
    checa("procurar versão nova força a procura", ["procurar", {"forcar": True}] in chamadas(pg), chamadas(pg))
    checa("sem .apk, sem botão de instalar", not visivel(pg, "#estecel-instalar") and not visivel(pg, "#app-nova"))

    mudar(pg, apk={"versao": "1.9.0"}, podeInstalar=False, android=34)
    pg.wait_for_timeout(200)
    faixa = texto(pg, "#app-nova")
    checa("faixa do app", visivel(pg, "#app-nova") and "Atualização do app pronta (versão 1.9.0)." in faixa and "Na primeira vez, o Android pede" in faixa, faixa)
    checa("botão de instalar no Este celular", visivel(pg, "#estecel-instalar") and texto(pg, "#estecel-instalar") == "Atualizar o app")
    checa("Este celular diz que o app está pronto", "versão 1.9.0 do app pronta" in texto(pg, "#estecel-info"), texto(pg, "#estecel-info"))
    zerar(pg)
    clica(pg, "#app-nova .pri"); clica(pg, "#app-nova .pri")
    pg.wait_for_timeout(300)
    checa("um toque instala uma vez", [c[0] for c in chamadas(pg)].count("instalarApp") == 1, chamadas(pg))
    checa("instalando", "instalando a versão 1.9.0 do app" in texto(pg, "#estecel-info") and pg.evaluate("document.querySelector('#app-nova .pri').disabled"), texto(pg, "#estecel-info"))
    mudar(pg, apk={"versao": "1.9.0"}, podeInstalar=True, android=34)
    pg.wait_for_timeout(200)
    checa("sem a dica quando o Android já deixa", "Na primeira vez" not in texto(pg, "#app-nova"))
    clica(pg, "#app-nova button.link")
    checa("o × fecha a faixa", not visivel(pg, "#app-nova"))

    mudar(pg, falhaApk="a atualização foi cancelada", apk=None)
    pg.wait_for_timeout(200)
    checa("falha com link", visivel(pg, "#estecel-baixar") and "a atualização foi cancelada" in texto(pg, "#estecel-p"), texto(pg, "#estecel-p"))
    checa("link para o .apk", pg.evaluate("document.getElementById('estecel-baixar').href").endswith("/Painel-de-Mineracao.apk"))
    mudar(pg, baixando={"qual": "painel", "versao": "1.8.1", "pct": 40})
    pg.wait_for_timeout(200)
    checa("baixando", "baixando a versão 1.8.1… 40%" in texto(pg, "#estecel-info"), texto(pg, "#estecel-info"))
    mudar(pg, erro={"codigo": "rede", "msg": "sem internet agora"})
    pg.wait_for_timeout(200)
    checa("erro em palavras simples", "não deu para atualizar agora: sem internet agora" in texto(pg, "#estecel-info"), texto(pg, "#estecel-info"))
    mudar(pg, precisaApp={"versao": "2.0.0"})
    pg.wait_for_timeout(200)
    checa("precisa do app novo", "a versão 2.0.0 precisa do app novo" in texto(pg, "#estecel-info"), texto(pg, "#estecel-info"))
    checa("sem erros no painel", not _erros_app[id(pg)], _erros_app[id(pg)])

    # o PC: a lista de celulares com a versão do painel de cada um
    aparelhos = [{"id": "a1", "nome": "Celular A", "app": "1.8.0", "painel": "1.8.0", "visto": AGORA_MS, "ativo": True},
                 {"id": "a2", "nome": "Celular B", "app": "1.7.1", "visto": AGORA_MS - 3600_000, "ativo": False}]
    cfg = {"ligado": True, "aparelhos": aparelhos, "codigo": "PM1-x", "qr": "", "qrApk": "", "urlApk": "", "apk": True, "conectado": True}
    pc = abrir(p, pc=True, dados=DADOS, extra="window.desktop.appCelular.config = async () => (%s);" % json.dumps(cfg))
    pc.evaluate("irPara('premissas')")
    pc.wait_for_timeout(300)
    lista = texto(pc, "#appcel-lista")
    checa("lista do PC", "painel 1.8.0 · app 1.8.0" in lista and "app 1.7.1" in lista and "painel 1.7.1" not in lista, lista)


with sync_playwright() as p:
    ponte(p)
    painel(p)
fim()
