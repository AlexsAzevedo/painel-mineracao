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
    # a leitura das marcas de energia falhou uma vez: valem as últimas (a queda continua sendo falta de energia)
    m = pg.evaluate("""(async () => { const orig = Date.now, t0 = orig(); window.__energia = null; window.__leituras = [MIN];
      Date.now = () => t0 + 387 * 60e3; try { await lerKryptexApp(); } finally { Date.now = orig; } return paradas.lista.map(p => p.motivo); })()""")
    checa("as marcas de energia não vieram nesta leitura: valem as últimas", m == ["energia"], m)
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
    # uma queda mais longa que as 36 horas de leituras (o PC ficou 40 h desligado): a leitura de antes dela não se perde
    r = sim(pg, [[0, "MIN"], [1, "MIN"], [2400, "MIN"], [2401, "MIN"]], [[2390, "ligou"]])
    checa("queda mais longa que as 36 horas de leituras", so(r, *C) == [{"ini": 1, "fim": 2400, "ligou": 2390, "motivo": "energia"}], r["paradas"])
    r = sim(pg, [[0, "MIN"], [1, "MIN"], [2400, "FECHADO"], [2401, "FECHADO"], [2405, "MIN"]], [[2390, "ligou"]])
    checa("queda mais longa que as 36 horas, com o app da Kryptex abrindo depois", so(r, *C) == [{"ini": 1, "fim": 2405, "ligou": 2390, "motivo": "energia"}], r["paradas"])
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


P3 = {"ini": ms(21, 3), "fim": ms(21, 5), "ligou": None, "motivo": "semleitura", "aprox": True, "ritmo": 1.03}
P5 = {"ini": ms(20, 10), "fim": ms(20, 10, 30), "ligou": None, "motivo": "pausa", "aprox": False, "ritmo": 1.03}
DADOS_UI = {**DADOS_CONTAS, "min-paradas": {"v": 1, "retro": True, "lista": [P1, P2, P3, P4, P5, {**P6, "fim": ms(25, 13, 50), "ritmo": 1.03}]},
            "min-diario": [DIA("2026-10-24", 18.54, 18, "kryptex", 1), DIA("2026-10-23", 24.72, 24, "", 2),
                           DIA("2026-10-22", 22.66, 22, "kryptex", 3), DIA("2026-10-21", 22.66, 22, "kryptex", 4)]}
LINHA_24 = "Fora do ar 6 h: 02:00–08:00 (Falta de energia?) · deixou de ganhar uns R$ 6,18"
COPIA = """25/10/2026, das 13:40 às 13:50 (10 min): a placa ficou parada
25/10/2026, das 05:00 às 07:10 (2 h 10 min): o PC apagou de repente (falta de energia?) e ligou às 07:00
24/10/2026, das 02:00 às 08:00 (6 h): o PC apagou de repente (falta de energia?) e ligou às 07:50
22/10/2026, das 22:00 de 22/10/2026 às 01:00 de 23/10/2026 (3 h): a placa ficou parada
21/10/2026, das ~03:00 às ~05:00 (2 h): o PC ficou sem leitura (desligado ou sem energia)
20/10/2026, das 10:00 às 10:30 (30 min): a mineração ficou pausada por você"""
# o texto da célula do dia na tabela (ou no cartão, no celular) do Diário
JS_DIA = "(d) => { const tr = [...document.querySelectorAll('#d-tab tbody tr')].find(tr => tr.cells[0] && tr.cells[0].textContent.startsWith(d)); return tr ? tr.cells[0].textContent : ''; }"


def diario_ui(p):
    pg = abrir(p, dados=DADOS_UI, pc=True, hash="diario")
    pg.wait_for_timeout(1500)
    dia = lambda d: pg.evaluate(JS_DIA, d)
    checa("diário: a linha das paradas do dia 24", LINHA_24 in dia("24/10/2026"), dia("24/10/2026"))
    checa("diário: a parada que atravessa a meia-noite, no dia 22 (até 24:00)",
          "Fora do ar 2 h: 22:00–24:00 (Placa parada) · deixou de ganhar uns R$ 2,06" in dia("22/10/2026"), dia("22/10/2026"))
    checa("diário: a parada com o horário aproximado, no dia 21",
          "Fora do ar 2 h: ~03:00–~05:00 (Sem leitura (PC desligado ou sem energia)) · deixou de ganhar uns R$ 2,06" in dia("21/10/2026"), dia("21/10/2026"))
    per = pg.evaluate("(document.getElementById('d-paradas') || {}).textContent || ''").strip()
    checa("diário: as paradas do período", per == "No período, a placa ficou 13 h 50 min parada (6 paradas) e deixou de ganhar uns R$ 14,25", per)
    itens = lambda: pg.evaluate("[...document.querySelectorAll('#paradas-p .pd-it')].map(e => e.textContent)")
    it = itens()
    checa("lista de paradas: as 6 do período, a mais nova primeiro", len(it) == 6 and "13:40" in it[0] and "10:00" in it[5], it)
    if not pg.evaluate("!!document.getElementById('pd-energia') && !!document.getElementById('pd-copiar')"):
        pg.context.close()
        return checa("lista de paradas: o filtro e o botão de copiar existem", False)
    pg.check("#pd-energia")
    it = itens()
    checa("lista de paradas: só falta de energia (e as sem leitura)", len(it) == 3 and "05:00" in it[0] and "02:00" in it[1] and "~03:00" in it[2], it)
    pg.uncheck("#pd-energia")
    pg.evaluate("window.__copiado = null; window.desktop.copiar = async t => { window.__copiado = t; return true; }")
    pg.click("#pd-copiar")
    pg.wait_for_timeout(200)
    c = pg.evaluate("window.__copiado")
    checa("lista de paradas: o texto copiado", c == COPIA, c)
    # a dica do gráfico no dia 24 (o mouse sai de cima, para a rolagem não abrir a dica de outro dia)
    pg.mouse.move(0, 0)
    pg.focus('#d-graf .bar-hit[aria-label^="24/10/2026"]')
    dica = pg.evaluate("document.querySelector('#d-graf .tip').textContent")
    checa("gráfico: a dica do dia 24 diz quanto parou", "parou 6 h" in dica, dica)
    # os ganhos lidos da Kryptex: o 24 esperando para ser anotado
    pg.evaluate("kx.dias['2026-10-24'].horas = 18; diario = diario.filter(e => e.data !== '2026-10-24'); renderSugestoesKx()")
    s = pg.evaluate("document.getElementById('kx-sug').textContent")
    checa("ganhos lidos da Kryptex: as horas minerando e quanto parou", "· 18 h minerando · parou 6 h (Falta de energia?)" in s, s)
    for tema in ("claro", "escuro"):
        t = pg.evaluate("(t) => { document.documentElement.dataset.tema = t; renderDiario(); return document.getElementById('v-diario').innerText; }", tema)
        checa(f"diário ({tema}): sem NaN, Infinity nem undefined", not re.search(r"NaN|Infinity|undefined", t), re.findall(r".{0,30}(?:NaN|Infinity|undefined).{0,30}", t)[:3])
    checa("sem erros (diário)", not erros(pg), erros(pg)[:3])
    pg.context.close()
    # Review Focus 4: o painel online (sem o PC) não mostra a lista
    on = abrir(p, dados=DADOS, hash="diario")
    checa("painel online: sem a lista de paradas", on.evaluate("document.getElementById('paradas-p')?.hidden === true"))
    checa("sem erros (painel online)", not erros(on), erros(on)[:3])
    on.context.close()
    # no celular: sem paradas, e com as paradas que vêm do PC
    c1 = abrir(p, 390, 844, dados={**DADOS, "min-paradas": {"v": 1, "retro": True, "lista": []}}, celular=True, hash="diario")
    t = c1.evaluate("(() => { const e = document.getElementById('paradas-p'); return e && !e.hidden ? e.textContent : ''; })()")
    checa("celular sem paradas: Nenhuma parada neste período", "Nenhuma parada neste período" in t, t)
    c1.context.close()
    c2 = abrir(p, 390, 844, dados=DADOS_UI, celular=True, hash="diario")
    checa("celular: a mesma linha do dia 24", LINHA_24 in c2.evaluate(JS_DIA, "24/10/2026"), c2.evaluate(JS_DIA, "24/10/2026"))
    m = c2.evaluate("({larg: document.documentElement.scrollWidth, bt: document.getElementById('pd-copiar') ? document.getElementById('pd-copiar').getBoundingClientRect().height : 0})")
    checa("celular: sem rolagem para o lado e o botão de copiar com 44 px", m["larg"] <= 390 and m["bt"] >= 44, m)
    checa("sem erros (celular)", not erros(c2), erros(c2)[:3])
    c2.context.close()


QUEDA = [[0, "MIN"], [1, "MIN"], [2, "MIN"], [380, "FECHADO"], [381, "FECHADO"], [384, "PARADO"], [386, "MIN"]]
VOLTOU = "Ficou fora do ar das 14:02 às 20:26 (6 h 24 min): o PC apagou de repente (falta de energia?) e ligou às 20:14. Deixou de ganhar uns R$ 6,59."
HOJE = "parou 2 h 20 min hoje (05:00–07:10, Falta de energia?; 13:40–13:50, Placa parada)"
# o retrato do app da Kryptex que o PC manda para o celular
RETRATO = {"v": 1, "estado": "minerando", "pausaAte": None, "computador": "PC-TESTE", "quando": AGORA_MS - 3 * 60000, "minerandoDesde": AGORA_MS - 10 * 60000,
           "placas": [{"nome": "RX 9070 XT", "tipo": "gpu", "minerando": True, "moeda": "PRL", "minerador": "srbminer", "hash": 1.13e14, "temp": 63, "tempMem": 78,
                       "watts": 286, "ventoinha": 54, "rpm": None}],
           "hoje": {"ganho": 9.62, "luz": 5.09, "lucro": 4.53, "kwh": 5.3, "desde": None}, "ritmo": {"brutoDia": 14.7, "lucroDia": 6.9},
           "saldoBtc": 0.00012, "precoBtc": 401000, "linha": [], "protecao": None, "hash24": 1.12e14}


def resumo_avisos(p):
    pg = abrir(p, dados=DADOS_CONTAS, pc=True)
    pg.wait_for_timeout(1500)
    pg.evaluate(FIX)
    pg.evaluate("celCfg = {...(celCfg || {}), ligado: true, topico: 't', maquinas: true}")   # os avisos das máquinas vão para o celular
    t0 = AGORA_MS
    # queda de energia: um aviso só, quando a mineração volta
    r = sim(pg, QUEDA, [[374, "ligou"]], {"t0": t0})
    checa("queda de energia: um aviso, quando a mineração volta, com o horário, o motivo e quanto deixou de ganhar",
          r["alertas"] == ["voltou"] and r["textos"] == ["RX 9070 XT voltou a minerar. " + VOLTOU], r["textos"])
    checa("queda de energia: o mesmo aviso no celular", r["celular"] == [{"tipo": "voltou", "titulo": "RX 9070 XT voltou a minerar", "corpo": VOLTOU}], r["celular"])
    # Review Focus 1: a página recarregou (o painel abriu de novo, com as leituras e as paradas guardadas)
    pg.evaluate("kxa = novoKxa(); energiaCache = null")
    r = sim(pg, [[387, "MIN"]], [[374, "ligou"]], {"manter": True, "t0": t0})
    checa("página recarregada depois da queda: a parada continua e o aviso não se repete",
          r["alertas"].count("voltou") == 1 and r["celular"] == [] and so(r, "ini", "fim", "ligou", "motivo") == [{"ini": 2, "fim": 386, "ligou": 374, "motivo": "energia"}], r)
    # o PC voltou (o painel abriu de novo) e a placa não: um aviso, 15 min depois de o Windows ligar
    sim(pg, [[0, "MIN"], [1, "MIN"], [2, "MIN"]], [], {"t0": t0})
    pg.evaluate("kxa = novoKxa(); energiaCache = null")
    r = sim(pg, [[m, "FECHADO"] for m in range(380, 396)], [[374, "ligou"]], {"manter": True, "t0": t0})
    checa("o PC voltou e a placa não: um aviso só",
          r["celular"] == [{"tipo": "maquina", "titulo": "O PC voltou, mas a placa ainda não está minerando", "corpo": "Ligou às 20:14; a placa está sem minerar desde 14:02."}], r["celular"])
    r = sim(pg, [[396, "MIN"]], [[374, "ligou"]], {"manter": True, "t0": t0})
    checa("o PC voltou e a placa não: quando ela volta, o aviso de fim", [m["tipo"] for m in r["celular"]] == ["voltou"]
          and r["celular"][0]["corpo"].startswith("Ficou fora do ar das 14:02 às 20:36 (6 h 34 min): o PC apagou de repente"), r["celular"])
    # a placa parada por 13 min; a parada curta (o aviso de antes); a pausa (nenhum)
    r = sim(pg, ["MIN"] + ["PARADO"] * 12 + ["MIN"])
    checa("placa parada 13 min: parou e voltou, com quanto deixou de ganhar",
          r["alertas"] == ["parou", "voltou"] and r["textos"][1].endswith("a placa ficou parada. Deixou de ganhar uns R$ 0,22."), r["textos"])
    r = sim(pg, ["MIN", "PARADO", "PARADO", "PARADO", "MIN"])
    checa("parada curta: o aviso de que voltou, como antes (a moeda e o hashrate)", r["alertas"] == ["parou", "voltou"] and "Pearl (PRL)" in r["textos"][1], r["textos"])
    r = sim(pg, ["MIN"] + ["PAUSADO"] * 15 + ["MIN"])
    checa("pausa: nenhum aviso", r["alertas"] == [] and r["celular"] == [], r)
    # o programa do PC fica sabendo que o painel lê o app da Kryptex (e deixa o "O PC voltou" com ele)
    a = pg.evaluate("""(async () => { let arg = null; window.desktop.segundoPlano = async (o) => { arg = o; return {}; };
      apCfg ||= {ligado: false}; celCfg ||= {ligado: false}; acCfg ||= {ligado: false};
      await simularParadas([MIN]); sincronizarSegundoPlano(); return arg; })()""")
    checa("o programa do PC sabe que o painel lê o app da Kryptex (kxa)", bool(a) and a.get("kxa") is True, a)
    checa("sem erros (avisos)", not erros(pg), erros(pg)[:3])
    pg.context.close()
    # Resumo: as paradas de hoje, no PC e no celular
    pg = abrir(p, dados=DADOS_UI, pc=True)
    pg.wait_for_timeout(1500)
    pg.evaluate(FIX)
    sim(pg, [[0, "MIN"]], [], {"manter": True, "t0": t0})
    t = pg.evaluate("document.getElementById('ag-corpo').textContent")
    checa("Resumo: as paradas de hoje", HOJE in t, t)
    t = pg.evaluate("(() => { paradas.lista.find(x => x.ini === %d).fim = null; renderAgora(); return document.getElementById('ag-corpo').textContent; })()" % P6["ini"])
    checa("Resumo: a parada que não acabou", "parada desde 13:40" in t, t)
    checa("sem erros (Resumo)", not erros(pg), erros(pg)[:3])
    pg.context.close()
    c = abrir(p, 390, 844, dados={**DADOS_UI, "min-kx-app": RETRATO}, celular=True)
    t = c.evaluate("document.getElementById('ag-corpo').textContent")
    checa("Resumo no celular: as paradas de hoje", HOJE in t, t)
    checa("sem erros (Resumo no celular)", not erros(c), erros(c)[:3])
    c.context.close()


def retro(p):
    """os dias que já passaram, na primeira leitura desta versão: as quedas pelas leituras de 36 h e, antes delas, pelos
    saldos guardados da conta (horários em minutos desde agora)"""
    t0, T = AGORA_MS, lambda m: AGORA_MS + m * 60000
    taxa = 1.03 / 400000   # bitcoin por hora: R$ 1,03 por hora com o bitcoin a R$ 400.000
    saldo = lambda m: 0.0001 + taxa * ((m + 5760) / 60 - (4 if m >= -3360 else 0))   # sem crescer nas 4 h de −3600 a −3360
    saldos = [[T(m), saldo(m), 400000] for m in range(-5760, -1199, 15) if not -3600 < m < -3360 and not -2400 < m < -2160]
    leituras = [[T(m), saldo(m), 300 if mina else 18, int(mina), 1.13e14 if mina else 0, 63, 78, None]   # as antigas, sem o estado
                for m in range(-1200, 0) if not -900 < m < -720 for mina in [not -299 <= m <= -271]]
    dados = {**DADOS, "min-kryptex": {"v": 1, "quando": t0 - 600000, "dias": DIAS_KX, "maquinas": [], "alertas": []},
             "min-kx-hist": {"saldos": saldos, "hw": {}}, "min-kxa-hist": {"v": 2, "amostras": leituras}}
    # o PC passou a anotar a energia há 1 minuto, e o app do celular recebe os avisos das máquinas
    extra = FIX + "; window.__energia = {desde: %d, marcas: []};" % (t0 - 60000) \
        + " window.desktop.celular.config = async () => ({ligado: true, topico: 'teste', maquinas: true});"
    pg = abrir(p, dados=dados, pc=True, extra=extra)
    pg.wait_for_timeout(1500)   # a primeira leitura desta versão (com o app da Kryptex fechado)
    abertura = pg.evaluate("({retro: paradas.retro, alertas: kx.alertas.map(a => a.tipo), celular: window.__celular.map(m => m.tipo)})")
    r = sim(pg, [[0, "MIN"]], [], {"manter": True, "t0": t0, "energiaDesde": t0 - 60000})
    checa("dias que já passaram: as quedas pelos saldos (horário aproximado) e pelas leituras de 36 h",
          so(r, "ini", "fim", "motivo", "aprox") == [{"ini": -3600, "fim": -3360, "motivo": "semleitura", "aprox": True},
                                                     {"ini": -900, "fim": -720, "motivo": "semleitura", "aprox": False},
                                                     {"ini": -300, "fim": -270, "motivo": "semminerar", "aprox": False}], r["paradas"])
    checa("dias que já passaram: o buraco nos saldos em que o saldo cresceu não vira parada", all(x["ini"] != -2400 for x in r["paradas"]), r["paradas"])
    rt = pg.evaluate("(paradas.lista.find(p => p.ini === %d) || {}).ritmo" % T(-3600))
    checa("dias que já passaram: a queda dos saldos fica com o ritmo da conta", rt is not None and abs(rt - 1.03) < 1e-9, rt)
    g = pg.evaluate("""(() => { const n = paradas.lista.length; atualizarParadas(%d);
      return {n, depois: paradas.lista.length, retro: paradas.retro, guardado: JSON.parse(localStorage.getItem('min-paradas') || 'null')}; })()""" % t0)
    checa("dias que já passaram: na primeira leitura, uma vez só (fica marcado e guardado)",
          abertura["retro"] is True and g["retro"] is True and (g["guardado"] or {}).get("retro") is True and g["n"] == g["depois"] == 3, [abertura, g])
    sem = lambda tipos: not any(t in ("voltou", "parou", "maquina") for t in tipos)
    checa("dias que já passaram: sem avisos", sem(abertura["alertas"]) and sem(abertura["celular"]) and sem(r["alertas"]) and sem([m["tipo"] for m in r["celular"]]),
          [abertura, r["alertas"], r["celular"]])
    h23 = pg.evaluate("kx.dias['2026-10-23'].horas")
    checa("dias que já passaram: o dia 23 desconta a queda dos saldos (4 h)", h23 == 20, h23)
    # a conta de cada buraco nos saldos
    d = pg.evaluate("""typeof paradasDosSaldos !== 'function' ? null : (() => { const t = %d, h = 3600e3, s = (preco, cresceu) => [[t, 0.001, preco], [t + h, 0.001 + cresceu, preco]];
      return [paradasDosSaldos(s(4e5, 0), Infinity, () => null).length,       // sem o ritmo e sem crescer: parada
              paradasDosSaldos(s(4e5, 1e-6), Infinity, () => null).length,    // sem o ritmo e cresceu: não
              paradasDosSaldos(s(0, 1e-8), Infinity, () => 1.03).length,      // sem a cotação: como sem o ritmo
              paradasDosSaldos(s(4e5, 0), t, () => 1.03).length,              // começa quando as leituras de cada minuto já começaram: não
              paradasDosSaldos([[t, 0.001, 4e5], [t + 45 * 60e3, 0.001, 4e5]], Infinity, () => 1.03).length,   // 45 min: não é buraco
              paradasDosSaldos(s(4e5, 0), t + h / 2, () => 1.03).map(p => p.fim - t)];   // atravessa o começo das leituras: acaba nele
    })()""" % (t0 - 10 * 3600000))
    checa("paradas dos saldos: sem o ritmo (ou a cotação), só quando o saldo não cresceu; só antes das leituras; buraco de mais de 45 min",
          d == [1, 0, 0, 0, 0, [1800000]], d)
    # a queda dos saldos que acabou há menos de 3 minutos (as leituras de cada minuto começando agora) também não vira aviso
    a = pg.evaluate("""(() => { const t = %d; paradas = {v: 1, retro: false, lista: []}; kxaHist = {v: 2, amostras: [[t, 0.001, 300, 1, 1.13e14, 63, 78, null, "m"]]};
      kxHist.saldos = [[t - 61 * 60e3, 0.001, 4e5], [t - 60e3, 0.001, 4e5]];
      const r = atualizarParadas(t); return {acabaram: r.acabaram.length, lista: paradas.lista.length}; })()""" % t0)
    checa("dias que já passaram: a queda dos saldos que acabou agora não vira aviso", a == {"acabaram": 0, "lista": 1}, a)
    checa("sem erros (dias que já passaram)", not erros(pg), erros(pg)[:3])
    pg.context.close()


def correcoes(p):
    """o que a revisão final achou: o dia em que o painel começou a ler a conta (já sem os saldos dele), a parada aberta
    quando a leitura do app é desligada, e as quedas dos dias que já passaram sem o ritmo da conta e no começo das
    leituras de cada minuto"""
    pg = abrir(p, dados=DADOS_CONTAS, pc=True)
    pg.wait_for_timeout(1500)
    pg.evaluate(FIX)
    # o dia parcial, já sem os saldos dele (os saldos ficam 6 dias; os dias da conta, 21): desde a primeira leitura (14:05)
    h = pg.evaluate("""(() => { kx.dias['2026-10-15'] = {...kx.dias['2026-10-15'], parcial: '14:05', aproximado: true};
      kxHist.saldos = [[%d, 0.001, 4e5], [%d, 0.0011, 4e5]]; return horasMinerandoDia('2026-10-15', %d); })()""" % (ms(20, 10), ms(20, 11), AGORA_MS))
    checa("o dia em que o painel começou a ler a conta: as horas desde a primeira leitura, mesmo sem os saldos daquele dia", h == 9.9, h)
    # a leitura do app desligada com uma parada aberta: ela acaba na última leitura (senão cresceria para sempre)
    sim(pg, ["MIN"] + ["PARADO"] * 12, [], {"t0": AGORA_MS})
    f = pg.evaluate("""(() => { const c = document.getElementById('kxa-ligado'); c.checked = false; c.dispatchEvent(new Event('change', {bubbles: true}));
      const g = JSON.parse(localStorage.getItem('min-paradas')); return [paradas.lista.map(p => p.fim), g.lista.map(p => p.fim)]; })()""")
    checa("a leitura do app desligada: a parada aberta acaba na última leitura (e fica guardada)", f == [[AGORA_MS + 12 * 60000]] * 2, f)
    # sem o ritmo da conta (nenhum dia nos 7 antes), vale a estimativa: o saldo que quase não cresceu no buraco é queda
    a = pg.evaluate("""(() => { const t = %d; paradas = {v: 1, retro: false, lista: []}; kx.dias = {};
      kxaHist = {v: 2, amostras: [[t, 0.001, 300, 1, 1.13e14, 63, 78, null, "m"]]};
      kxHist.saldos = [[t - 4 * 3600e3, 0.001, 4e5], [t - 2 * 3600e3, 0.001 + 1e-9, 4e5]];
      atualizarParadas(t); return paradas.lista.map(p => [Math.round((p.ini - t) / 60e3), Math.round((p.fim - t) / 60e3), p.motivo]); })()""" % AGORA_MS)
    checa("dias que já passaram, sem o ritmo da conta: vale a estimativa", a == [[-240, -120, "semleitura"]], a)
    # o buraco nos saldos que acaba na primeira leitura de cada minuto (o saldo dela vem uns milissegundos depois)
    b = pg.evaluate("""(() => { const t = %d, m = 60e3; paradas = {v: 1, retro: false, lista: []};
      kxaHist = {v: 2, amostras: Array.from({length: 61}, (_, i) => [t - (60 - i) * m, 0.002, 300, 1, 1.13e14, 63, 78, null, "m"])};
      kxHist.saldos = [[t - 300 * m, 0.002, 4e5], [t - 285 * m, 0.002, 4e5], [t - 60 * m + 5, 0.002, 4e5]];
      atualizarParadas(t); return paradas.lista.map(p => [Math.round((p.ini - t) / m), Math.round((p.fim - t) / m), p.motivo, p.aprox]); })()""" % AGORA_MS)
    checa("dias que já passaram: a queda que acaba no começo das leituras de cada minuto", b == [[-285, -60, "semleitura", True]], b)
    checa("sem erros (correções)", not erros(pg), erros(pg)[:3])
    pg.context.close()


def fotos(p, pasta):
    """as fotos para conferir a olho: o Diário no PC e no celular (claro e escuro) e o Resumo no PC com a linha de hoje"""
    os.makedirs(pasta, exist_ok=True)
    for tema in ("escuro", "claro"):
        for nome, larg, alt, ponte in (("pc", 1366, 900, {"pc": True}), ("celular", 390, 844, {"celular": True})):
            pg = abrir(p, larg, alt, dados=DADOS_UI, hash="diario", **ponte)
            pg.evaluate("(t) => { document.documentElement.dataset.tema = t; renderDiario(); }", tema)
            pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(pasta, f"diario_{nome}_{tema}.png"), full_page=True)
            checa(f"fotos: Diário no {nome} ({tema}) sem erros", not erros(pg), erros(pg)[:3])
            pg.context.close()
    pg = abrir(p, dados=DADOS_UI, pc=True)
    pg.wait_for_timeout(1500)
    pg.evaluate(FIX)
    sim(pg, [[0, "MIN"]], [], {"manter": True, "t0": AGORA_MS})
    pg.screenshot(path=os.path.join(pasta, "resumo_pc.png"), full_page=True)
    checa("fotos: Resumo no PC sem erros", not erros(pg), erros(pg)[:3])
    pg.context.close()


FOTOS = sys.argv[sys.argv.index("--fotos") + 1] if "--fotos" in sys.argv else ""   # pasta para as fotos
with sync_playwright() as p:
    deteccao(p)
    contas(p)
    retro(p)
    diario_ui(p)
    resumo_avisos(p)
    correcoes(p)
    if FOTOS:
        fotos(p, FOTOS)
fim()
