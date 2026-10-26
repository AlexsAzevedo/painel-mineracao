"""Mensagens do app do celular para o PC: o app gasta o mínimo de mensagens do ntfy.sh e só mostra o aviso de limite
quando algo que a pessoa pediu não pôde sair. A página é a montada por montar-www.py, com um Capacitor de mentira e um
"ntfy" de mentira que conta o que o app manda (não há PC respondendo).
Uso: python3 testes/mensagens_app.py"""
import base64, functools, http.server, json, os, re, socketserver, subprocess, sys, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

CELULAR = os.path.join(RAIZ, "celular")
VERSAO_APP = json.load(open(os.path.join(CELULAR, "package.json"), encoding="utf-8"))["version"]
TMP = tempfile.mkdtemp(prefix="mensagens-")
WWW = os.path.join(TMP, "www")
MIN = 60_000
ENVIADAS = []   # cada mensagem que o app mandou ao ntfy (o caminho do tópico)


class _Q(http.server.SimpleHTTPRequestHandler):
    """a página montada; o ntfy daqui aceita (e conta) o que o app manda e não tem nada para ler"""
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/ntfy"):
            self.send_error(404)
        else:
            super().do_GET()

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path.startswith("/ntfy"):
            ENVIADAS.append(self.path)
        corpo = json.dumps({"id": "m%d" % len(ENVIADAS), "time": AGORA_MS // 1000, "event": "message"}).encode()
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

ESTADO_ATU = {"app": {"versao": VERSAO_APP, "codigo": 10800}, "painel": {"versao": VERSAO_APP, "origem": "apk", "embutido": VERSAO_APP},
              "procurando": False, "ultimaProcura": AGORA_MS - 1800_000, "instalando": False, "podeInstalar": True, "android": 34}
CAPACITOR = """(() => {
  const estado = %s, nada = () => Promise.resolve(), resp = () => Promise.resolve(JSON.parse(JSON.stringify(estado)));
  const Atualizador = { estado: resp, procurar: resp, usarPainel: resp, painelOk: resp, instalarApp: resp, visto: resp,
    addListener: () => Promise.resolve({ remove() {} }) };
  const plugins = { Atualizador, App: { addListener: () => Promise.resolve({ remove() {} }), minimizeApp: nada },
    Device: { getInfo: () => Promise.resolve({ name: "Celular de teste" }) }, SystemBars: { setStyle: nada } };
  window.Capacitor = { isNativePlatform: () => true, getPlatform: () => "android", registerPlugin: (n) => plugins[n] || null };
})();""" % json.dumps(ESTADO_ATU)

CODIGO = "PM1-" + base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")
# o retrato do app da Kryptex que o PC mandou há 5 minutos (o botão de atualizar pede uma leitura nova)
RETRATO = {"v": 1, "quando": AGORA_MS - 5 * MIN, "estado": "minerando", "pausaAte": None, "computador": "PC-TESTE",
           "placas": [{"nome": "RX 9070 XT", "tipo": "gpu", "minerando": True, "moeda": "PRL", "minerador": "srbminer", "hash": 1.13e14, "temp": 63, "watts": 286}],
           "hoje": {"ganho": 9.62, "luz": 5.09, "lucro": 4.53, "kwh": 5.3, "desde": None}, "ritmo": {"brutoDia": 14.7, "lucroDia": 6.9},
           "saldoBtc": 0.00012, "saldoUsd": 9.7, "precoBtc": 401000, "linha": [], "protecao": None, "minerandoDesde": AGORA_MS - 5 * 3600_000, "hash24": 1.12e14}

_nav, _erros = [None], {}


def abrir_app(p, envios, ultima_ola):
    """o app aberto, já vinculado, com as mensagens que ele mandou antes (envios) e a hora do último "ola" """
    if _nav[0] is None:
        _nav[0] = p.chromium.launch()
    sinc = {"pronto": True, "versao": 1, "ultimaVez": AGORA_MS - MIN, "envios": envios, "ultimaOla": ultima_ola}
    semente = {"pm-codigo": CODIGO, "pm-aparelho": "aparelho-teste-1", "pm-sinc": json.dumps(sinc), "min-kx-app": json.dumps(RETRATO)}
    for k, v in DADOS.items():
        semente[k] = json.dumps(v)
    ctx = _nav[0].new_context(viewport={"width": 390, "height": 844}, locale="pt-BR", timezone_id="America/Sao_Paulo")
    pg = ctx.new_page()
    pg.set_default_timeout(5000)
    pg.clock.set_fixed_time(AGORA)
    lista = _erros.setdefault(id(pg), [])
    pg.on("pageerror", lambda e: lista.append(str(e)))
    pg.route(re.compile(r".*/capacitor\.js$"), lambda rota: rota.fulfill(status=200, content_type="text/javascript", body=CAPACITOR))
    pg.add_init_script("try{ if(!sessionStorage.getItem('__semeado')){ const d = %s; for (const k in d) localStorage.setItem(k, d[k]); sessionStorage.setItem('__semeado','1'); } }catch(e){}" % json.dumps(semente))
    pg.goto(URL_APP)
    pg.wait_for_timeout(900)
    return pg


def texto(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e && !e.hidden ? e.innerText.trim() : ''; }", sel)


def voltar(pg):
    """o app voltou para a frente (o Android tira e põe a tela de volta)"""
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    pg.wait_for_timeout(500)


def mensagens(p):
    # o app falou com o PC há 5 minutos (um pedido; o último "ola" foi há 12): o PC ainda manda sozinho o que muda, então
    # abrir e voltar para o app não gastam mensagem
    n = len(ENVIADAS)
    pg = abrir_app(p, [AGORA_MS - 12 * MIN, AGORA_MS - 5 * MIN], AGORA_MS - 12 * MIN)
    voltar(pg)
    checa("conversa recente: abrir e voltar não mandam nada", len(ENVIADAS) == n, len(ENVIADAS) - n)
    checa("sem erros (conversa recente)", not _erros[id(pg)], _erros[id(pg)])

    # faz 25 minutos: abrir pergunta ao PC o que mudou (1 mensagem); atualizar logo depois só pede a leitura da Kryptex
    n = len(ENVIADAS)
    pg = abrir_app(p, [AGORA_MS - 25 * MIN], AGORA_MS - 25 * MIN)
    checa("faz tempo: abrir pergunta ao PC", len(ENVIADAS) == n + 1, len(ENVIADAS) - n)
    n = len(ENVIADAS)
    pg.click("#topo-atu"); pg.wait_for_timeout(600)
    checa("atualizar com o app em dia: uma mensagem só", len(ENVIADAS) == n + 1, len(ENVIADAS) - n)

    # o teto de 60 mensagens nas últimas 24 horas (a última há 20 minutos): o que o app faz sozinho (perguntar ao abrir)
    # espera em silêncio; atualizar diz a hora em que libera (a mais velha das 60, há 610 minutos, sai da conta às 03:50)
    cheio = [AGORA_MS - 20 * MIN - i * 10 * MIN for i in range(60)]
    n = len(ENVIADAS)
    pg = abrir_app(p, cheio, AGORA_MS - 20 * MIN)
    checa("teto: nada sai", len(ENVIADAS) == n, len(ENVIADAS) - n)
    aviso = texto(pg, "#remoto-aviso")
    checa("teto: o que o app faz sozinho não mostra o aviso", "mensagens" not in aviso.lower(), aviso)
    pg.click("#topo-atu"); pg.wait_for_timeout(600)
    t = texto(pg, "#toast")
    checa("teto: atualizar diz quando libera", "03:50" in t and "mensagens" in t.lower(), t)
    aviso = texto(pg, "#remoto-aviso")
    checa("teto: depois de pedir, o aviso diz quando libera", "03:50" in aviso, aviso)
    checa("sem erros (teto)", not _erros[id(pg)], _erros[id(pg)])


with sync_playwright() as p:
    mensagens(p)
fim()
