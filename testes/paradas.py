"""Paradas e quedas de energia (1.10.0): o painel do PC anota quando a mineração parou e por quê (pelas leituras de cada
minuto do app da Kryptex e pelas marcas de energia do PC), desconta as paradas das horas do dia e mostra quanto deixou de
ganhar (dados inventados; o app da Kryptex e as marcas do PC são de mentira).
Uso: python3 testes/paradas.py"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

FIX = """(() => {
  window.__energia = {desde: 0, marcas: []};
  window.desktop.energia = async () => JSON.parse(JSON.stringify(window.__energia));
  const PLACA = (o) => ({id:"gpu-1", tipo:"gpu", nome:"AMD Radeon RX 9070 XT", desativada:false, minerando:true, moeda:"PRL", algoritmo:"pearlhash", minerador:"srbminer",
    hash:1.13e14, rendimentoUsd:2.965, temp:63, tempMem:78, tempHot:null, watts:286, ventoinha:54, rpm:null, erros1h:0, ...o});
  const CPU = {id:"cpu-1", tipo:"cpu", nome:"13th Gen Intel(R) Core(TM) i7-13700", desativada:false, minerando:false, moeda:"", algoritmo:"", minerador:"",
    hash:0, rendimentoUsd:0.31, temp:52, tempMem:null, tempHot:null, watts:null, ventoinha:null, rpm:null, erros1h:0};
  const LEIT = (o, placa) => ({ok:true, quando:Date.now(), pausado:false, pausaAte:null, moeda:"BRL", computador:"PC-TESTE", cotacoes:{brl:4.965204, btc:0.00001237},
    saldoBtc:0.0001, saldoUsd:0.0001/0.00001237, placas:[PLACA(placa || {}), CPU], desconhecidos:[], ...o});
  window.LEIT = LEIT;
  window.MIN = LEIT();
  window.PARADO = LEIT({}, {minerando:false, hash:0, moeda:"", minerador:"", watts:18});
  window.PAUSADO = LEIT({pausado:true}, {minerando:false, watts:20});
  window.QUENTE = LEIT({}, {temp:86});
  window.FECHADO = {ok:false, erro:"fechado", msg:""};
  /* cada item: [minutos desde t0, leitura] ou só a leitura (um minuto depois da anterior); marcas: [[minutos, tipo]] */
  window.simularParadas = async (lista, marcas = [], op = {}) => {
    if (!op.manter) { kxa = novoKxa(); kxaHist = {v: 2, amostras: []}; kxaSnap = null; kx.alertas = []; paradas = {v: 1, retro: true, lista: []}; }
    window.__celular = []; window.__acoes = [];
    const orig = Date.now, t0 = op.t0 || orig(); let ultimo = op.desde ?? -1;
    window.__energia = {desde: op.energiaDesde ?? (t0 - 864e5), marcas: marcas.map(([m, tipo]) => ({t: t0 + m * 60e3, tipo}))};
    try {
      for (const item of lista) {
        const [min, l] = Array.isArray(item) ? item : [ultimo + 1, item];
        ultimo = min; const t = t0 + min * 60e3; Date.now = () => t;
        window.__leituras = [l];
        await lerKryptexApp();
      }
    } finally { Date.now = orig; }
    const m = (x) => x == null ? null : Math.round((x - t0) / 60e3);
    return {paradas: paradas.lista.map(p => ({ini: m(p.ini), fim: m(p.fim), ligou: m(p.ligou), motivo: p.motivo, aprox: !!p.aprox})),
      alertas: kx.alertas.map(a => a.tipo).reverse(), textos: kx.alertas.map(a => a.texto).reverse(), celular: window.__celular.slice(), t0};
  };
})();"""


def sim(pg, lista, marcas=None, op=None):
    """simularParadas com a lista no formato do JS (as leituras pelo nome: "MIN", "PARADO"...)"""
    def item(x):
        return f"[{x[0]}, {x[1]}]" if isinstance(x, (list, tuple)) else x
    return pg.evaluate(f"simularParadas([{', '.join(item(x) for x in lista)}], {json.dumps(marcas or [])}, {json.dumps(op or {})})")


def so(r, *chaves):
    """as paradas só com as chaves pedidas"""
    return [{k: p[k] for k in chaves} for p in r["paradas"]]


def deteccao(p):
    pg = abrir(p, dados=DADOS, pc=True)
    pg.wait_for_timeout(1500)   # a primeira leitura sozinha (sem app) passa antes dos testes
    pg.evaluate(FIX)
    if not pg.evaluate("typeof paradas !== 'undefined' && typeof paradasDasAmostras === 'function'"):
        return checa("paradas: as paradas existem na página", False)
    C = ("ini", "fim", "ligou", "motivo")
    r = sim(pg, [[0, "MIN"], [1, "MIN"], [2, "MIN"], [380, "FECHADO"], [381, "FECHADO"], [384, "PARADO"], [386, "MIN"]], [[374, "ligou"]])
    checa("queda de energia: do último minuto minerando até minerar de novo, com a hora em que ligou", so(r, *C) == [{"ini": 2, "fim": 386, "ligou": 374, "motivo": "energia"}], r["paradas"])
    r = sim(pg, [[0, "MIN"], [1, "MIN"], [6, "FECHADO"], [7, "MIN"]], [[4, "ligou"]])
    checa("queda curta (religou em 4 min): conta mesmo com menos de 10 min", so(r, *C) == [{"ini": 1, "fim": 7, "ligou": 4, "motivo": "energia"}], r["paradas"])
    r = sim(pg, [[0, "MIN"], [1, "MIN"], [2, "MIN"], [64, "MIN"]], [[3, "desligou"], [60, "ligou"]])
    checa("PC desligado normalmente", so(r, *C) == [{"ini": 2, "fim": 64, "ligou": 60, "motivo": "desligado"}], r["paradas"])
    r = sim(pg, [[0, "MIN"], [4, "MIN"], [91, "MIN"]], [[5, "suspendeu"], [90, "acordou"]])
    checa("PC em suspensão", so(r, *C) == [{"ini": 4, "fim": 91, "ligou": None, "motivo": "suspensao"}], r["paradas"])
    r = sim(pg, [[0, "MIN"], [1, "MIN"], [120, "MIN"]])
    checa("painel fechado com o PC ligado: não vira parada", r["paradas"] == [], r["paradas"])
    r = sim(pg, ["MIN"] + ["FECHADO"] * 12 + ["MIN"])
    checa("app da Kryptex fechado", so(r, "ini", "fim", "motivo") == [{"ini": 0, "fim": 13, "motivo": "fechado"}], r["paradas"])
    r = sim(pg, ["MIN"] + ["PARADO"] * 12 + ["MIN"])
    checa("placa parada", so(r, "ini", "fim", "motivo") == [{"ini": 0, "fim": 13, "motivo": "parada"}], r["paradas"])
    r = sim(pg, ["MIN"] + ["PARADO"] * 5 + ["MIN"])
    checa("parada curta (menos de 10 min): fica de fora", r["paradas"] == [], r["paradas"])
    r = sim(pg, ["MIN"] + ["PAUSADO"] * 15 + ["MIN"])
    checa("pausada por você", so(r, "ini", "fim", "motivo") == [{"ini": 0, "fim": 16, "motivo": "pausa"}], r["paradas"])
    r = sim(pg, [[0, "QUENTE"], [1, "QUENTE"]] + [[m, "PAUSADO"] for m in range(2, 18)] + [[18, "MIN"]])
    checa("pausada pela proteção de temperatura", so(r, "ini", "fim", "motivo") == [{"ini": 1, "fim": 18, "motivo": "protecao"}], r["paradas"])
    r = sim(pg, [[0, "MIN"], [1, "PAUSADO"], [2, "PAUSADO"], [3, "PAUSADO"], [200, "MIN"]], [[150, "ligou"]])
    checa("falta de energia no meio de uma pausa: vale a falta de energia", so(r, *C) == [{"ini": 0, "fim": 200, "ligou": 150, "motivo": "energia"}], r["paradas"])
    r = sim(pg, ["MIN"] + ["PARADO"] * 12)
    checa("parada que não acabou (10 min ou mais)", so(r, "ini", "fim", "motivo") == [{"ini": 0, "fim": None, "motivo": "parada"}], r["paradas"])
    r = sim(pg, ["MIN"] + ["PARADO"] * 5)
    checa("parada que não acabou, com menos de 10 min: ainda não aparece", r["paradas"] == [], r["paradas"])
    # Review Focus 2: duas quedas nas mesmas 36 horas, cada uma com a sua ligação
    r = sim(pg, [[0, "MIN"], [1, "MIN"], [120, "MIN"], [121, "MIN"], [300, "MIN"], [450, "MIN"]], [[110, "ligou"], [440, "ligou"]])
    checa("duas quedas nas mesmas 36 horas", so(r, *C) == [{"ini": 1, "fim": 120, "ligou": 110, "motivo": "energia"}, {"ini": 300, "fim": 450, "ligou": 440, "motivo": "energia"}], r["paradas"])
    # Review Focus 5: leituras repetidas no mesmo minuto
    r = sim(pg, [[0, "MIN"], [0, "MIN"], [1, "PARADO"], [1, "PARADO"]] + [[m, "PARADO"] for m in range(2, 13)] + [[13, "MIN"]])
    checa("leituras repetidas no mesmo minuto", so(r, "ini", "fim", "motivo") == [{"ini": 0, "fim": 13, "motivo": "parada"}], r["paradas"])
    # Review Focus 3: parada mais longa que as 36 horas de leituras
    r = pg.evaluate("""(async () => {
      kxa = novoKxa(); kx.alertas = []; const t0 = Date.now();
      kxaHist = {v: 2, amostras: Array.from({length: 2101}, (_, i) => [t0 + (i - 2100) * 60e3, 0.0001, 18, 0, 0, 63, 78, null, "p"])};
      paradas = {v: 1, retro: true, lista: [{ini: t0 - 40 * 3600e3, fim: null, ligou: null, motivo: "parada", aprox: false, ritmo: null}]};
      return simularParadas([[1, MIN]], [], {manter: true, t0});
    })()""")
    checa("parada mais longa que as 36 horas de leituras: o início guardado fica", so(r, "ini", "fim", "motivo") == [{"ini": -2400, "fim": 1, "motivo": "parada"}], r["paradas"])
    # o estado em cada leitura de minuto
    pg.evaluate("simularParadas([MIN, PAUSADO, PARADO, FECHADO])")
    checa("o estado nas leituras de minuto", pg.evaluate("kxaHist.amostras.map(a => a[8])") == ["m", "u", "p", "f"], pg.evaluate("kxaHist.amostras.map(a => a[8])"))
    # grava pouco: quando a parada chega a 10 min e quando ela acaba
    n = pg.evaluate("""(async () => {
      let n = 0; const s = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'min-paradas') n++; return s.call(this, k, v); };
      try { await simularParadas([MIN, ...Array(15).fill(PARADO), MIN]); } finally { Storage.prototype.setItem = s; }
      return n; })()""")
    checa("grava a lista só quando ela muda (2 vezes numa parada)", n == 2, n)
    checa("sem erros (detecção)", not erros(pg), erros(pg)[:3])
    # as duas listas de chaves que o PC e o celular dividem
    lista = lambda arq, pad: re.findall(r'"(min-[\w-]+)"', re.search(pad, open(os.path.join(RAIZ, arq), encoding="utf-8").read()).group(1))
    a = lista("mineracao.html", r"const SINCRONIZADAS = \[([^\]]*)\]")
    b = lista(os.path.join("desktop", "sincronia.js"), r"const SINCRONIZADAS = \[([^\]]*)\]")
    checa("min-paradas nas duas listas de chaves do PC e do celular (iguais)", a == b and "min-paradas" in a, [a, b])
    # no celular: a lista vem do PC e é recarregada quando muda
    um = {"ini": AGORA_MS - 3 * 3600e3, "fim": AGORA_MS - 2 * 3600e3, "ligou": AGORA_MS - 2 * 3600e3 - 5 * 60e3, "motivo": "energia", "aprox": False, "ritmo": 1.03}
    pc = abrir(p, dados={**DADOS, "min-paradas": {"v": 1, "retro": True, "lista": [um]}}, celular=True)
    antes = pc.evaluate("paradas.lista.length")
    pc.evaluate("(p) => { localStorage.setItem('min-paradas', JSON.stringify({v: 1, retro: true, lista: [p, {...p, ini: p.ini - 864e5, fim: p.fim - 864e5}]})); recarregarDados(['min-paradas']); }", um)
    checa("no celular, a lista vem do PC e recarrega", [antes, pc.evaluate("paradas.lista.length")] == [1, 2], [antes, pc.evaluate("paradas.lista.length")])
    checa("sem erros (celular)", not erros(pc), erros(pc)[:3])
    pc.context.close()   # as fotos das ofertas ainda carregando não ficam para o fim do teste
    pg.context.close()


def ms(dia, h=0, m=0):
    """a hora de Brasília de um dia de outubro de 2026, em ms"""
    return int(datetime.datetime(2026, 10, dia, h, m, tzinfo=BRT).timestamp() * 1000)


# a conta da Kryptex: R$ 24,72 por dia de 24 h (R$ 1,03 por hora), menos o 23 (aproximado) e o 22 (em US$)
DIAS_KX = {f"2026-10-{d:02d}": {"btc": 0.0000618, "valor": 24.72, "moeda": "BRL", "horas": 24, "aproximado": False, "parcial": ""} for d in range(14, 25)}
DIAS_KX["2026-10-23"] = {**DIAS_KX["2026-10-23"], "aproximado": True, "valor": 100}
DIAS_KX["2026-10-22"] = {**DIAS_KX["2026-10-22"], "moeda": "USD", "valor": 24.72 / 5.04}
P1 = {"ini": ms(24, 2), "fim": ms(24, 8), "ligou": ms(24, 7, 50), "motivo": "energia", "aprox": False, "ritmo": 1.03}
P2 = {"ini": ms(22, 22), "fim": ms(23, 1), "ligou": None, "motivo": "parada", "aprox": False, "ritmo": 1.03}
P4 = {"ini": ms(25, 5), "fim": ms(25, 7, 10), "ligou": ms(25, 7), "motivo": "energia", "aprox": False, "ritmo": 1.03}
P6 = {"ini": ms(25, 13, 40), "fim": None, "ligou": None, "motivo": "parada", "aprox": False, "ritmo": None}
DIA = lambda data, valor, horas, fonte="", n=1: {"_id": data, "data": data, "valor": valor, "moeda": "BRL", "dolar": 5.04, "horas": horas, "obs": "Kryptex" if fonte else "",
                                                 "criado": n, **({"fonte": fonte} if fonte else {})}
DADOS_CONTAS = {**DADOS, "min-kryptex": {"v": 1, "quando": AGORA_MS - 600000, "dias": DIAS_KX, "maquinas": [], "alertas": []},
                "min-paradas": {"v": 1, "retro": True, "lista": [P1, P2, P4, P6]},
                "min-diario": [DIA("2026-10-24", 18.54, 24, "kryptex", 1), DIA("2026-10-23", 24.72, 24, "", 2)]}
achar = lambda p: f"paradas.lista.find(x => x.ini === {p['ini']})"


def contas(p):
    pg = abrir(p, dados=DADOS_CONTAS, pc=True)
    pg.wait_for_timeout(1500)
    pg.evaluate(FIX)
    if not pg.evaluate("typeof ritmoConta === 'function'"):
        return checa("contas: as contas das paradas existem", False)
    # o ritmo da conta: os 7 dias antes, sem os aproximados, com o dia em US$ em reais
    checa("ritmo da conta nos 7 dias antes (sem os aproximados, com US$ em reais)", abs(pg.evaluate("ritmoConta('2026-10-25')") - 1.03) < 1e-9, pg.evaluate("ritmoConta('2026-10-25')"))
    checa("ritmo da conta sem dias antes: nenhum", pg.evaluate("ritmoConta('2026-10-14')") is None)
    e = pg.evaluate("[ritmoEstimado(), totaisSetup({horas: 24}).recUsd / 365 / 24 * cfg.dolar * fatorSim().f]")
    checa("ritmo estimado: a estimativa da Kryptex por hora, com a correção pelo real", e[0] > 0 and abs(e[0] - e[1]) < 1e-9, e)
    # horas minerando de cada dia: 24 h menos as paradas, cortadas na meia-noite; hoje, até agora
    h = pg.evaluate("['2026-10-24', '2026-10-22', '2026-10-23', '2026-10-25'].map(d => horasMinerandoDia(d, %d))" % AGORA_MS)
    checa("horas minerando: 24 h menos as paradas do dia (e hoje, até agora)", h == [18, 22, 23, 11.5], h)
    # quanto deixou de ganhar
    v = pg.evaluate(f"[perdaParada({achar(P1)}), perdaParada({achar(P2)}, '2026-10-22'), perdaParada({achar(P6)}, undefined, {AGORA_MS})]")
    checa("deixou de ganhar: as horas paradas vezes o ritmo", abs(v[0] - 6.18) < 1e-9 and abs(v[1] - 2.06) < 1e-9 and abs(v[2] - 20 / 60 * 1.03) < 1e-9, v)
    # os dias que vieram da Kryptex ficam com as horas certas; os digitados, não mudam
    r = pg.evaluate("""(() => { const mudou = aplicarParadasNosDias(%d), d = Object.fromEntries(diario.map(e => [e.data, e.horas]));
      const kxg = JSON.parse(localStorage.getItem('min-kryptex')).dias, l = linhaDia(diario.find(e => e.data === '2026-10-24'));
      return {mudou, d24: d['2026-10-24'], d23: d['2026-10-23'], kx24: kxg['2026-10-24'].horas, kx22: kxg['2026-10-22'].horas,
        guardado: JSON.parse(localStorage.getItem('min-diario')).find(e => e.data === '2026-10-24').horas,
        est: [l.eUsd, estDia('2026-10-24', 18).usd, estDia('2026-10-24', 24).usd]}; })()""" % AGORA_MS)
    checa("o dia da Kryptex fica com 18 h; o digitado continua com 24", [r["mudou"], r["d24"], r["d23"], r["guardado"]] == [True, 18, 24, 18], r)
    checa("os dias da conta da Kryptex ficam com as horas certas (e vão para o celular)", [r["kx24"], r["kx22"]] == [18, 22], r)
    checa("o estimado do dia usa as horas minerando", abs(r["est"][0] - r["est"][1]) < 1e-12 and r["est"][1] < r["est"][2], r["est"])
    # o ritmo fica guardado quando a parada acaba: o da conta nos 7 dias antes. A simulação começa sem as paradas guardadas
    # (o 24 volta a ter 24 h); com o 24 rendendo R$ 31,20: (5 × 24,72 + 31,20) / 144 h
    pg.evaluate("kx.dias['2026-10-24'].valor = 31.2; simularParadas([MIN, ...Array(12).fill(PARADO), MIN])")
    rt = pg.evaluate("paradas.lista.map(p => p.ritmo)")
    checa("o ritmo fica guardado quando a parada acaba", len(rt) == 1 and abs(rt[0] - 154.8 / 144) < 1e-9, rt)
    checa("sem erros (contas)", not erros(pg), erros(pg)[:3])
    pg.context.close()


with sync_playwright() as p:
    deteccao(p)
    contas(p)
fim()
