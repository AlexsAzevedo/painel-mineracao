"""Paradas e quedas de energia (1.10.0): o painel do PC anota quando a mineração parou e por quê (pelas leituras de cada
minuto do app da Kryptex e pelas marcas de energia do PC), desconta as paradas das horas do dia e mostra quanto deixou de
ganhar (dados inventados; o app da Kryptex e as marcas do PC são de mentira).
Uso: python3 testes/paradas.py"""
import json, os, re, sys
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


with sync_playwright() as p:
    deteccao(p)
fim()
