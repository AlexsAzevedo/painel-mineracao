"""App da Kryptex no painel do PC: ganho e luz de hoje, avisos (parou, voltou, fechado), proteção de temperatura,
retrato para o celular e a tela Agora (dados inventados; o app da Kryptex é de mentira).
Uso: python3 testes/kryptex_app.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

FIXTURAS = """(() => {
  const PLACA = (o) => ({id:"gpu-1", tipo:"gpu", nome:"AMD Radeon RX 9070 XT", desativada:false, minerando:true, moeda:"PRL", algoritmo:"pearlhash", minerador:"srbminer",
    hash:1.13e14, rendimentoUsd:2.965, temp:63, tempMem:78, tempHot:null, watts:286, ventoinha:54, rpm:null, erros1h:0, ...o});
  const CPU = {id:"cpu-1", tipo:"cpu", nome:"13th Gen Intel(R) Core(TM) i7-13700", desativada:false, minerando:false, moeda:"", algoritmo:"", minerador:"",
    hash:0, rendimentoUsd:0.31, temp:52, tempMem:null, tempHot:null, watts:null, ventoinha:null, rpm:null, erros1h:0};
  const LEIT = (o, placa) => ({ok:true, quando:Date.now(), pausado:false, pausaAte:null, moeda:"BRL", computador:"PC-TESTE", cotacoes:{brl:4.965204, btc:0.00001237},
    saldoBtc:0.0001, placas:[PLACA(placa || {}), CPU], desconhecidos:[], ...o});
  window.MIN = LEIT();
  window.PARADO = LEIT({}, {minerando:false, hash:0, moeda:"", minerador:"", watts:18});
  window.PAUSADO_COM_HASH = LEIT({pausado:true}, {minerando:false, watts:20});
  window.QUENTE = LEIT({}, {temp:86});
  window.FALHA = {ok:false, erro:"tempo", msg:"o app da Kryptex demorou demais para responder"};
  window.AGORA = Date.now();
  window.AMOSTRAS_SAQUE = [[AGORA-4*3600e3, 0.00010, 286, 1, 1, 63, 78], [AGORA-3*3600e3, 0.00012, 286, 1, 1, 63, 78],
                           [AGORA-2*3600e3, 0.00002, 286, 1, 1, 63, 78], [AGORA-1*3600e3, 0.00003, 286, 1, 1, 63, 78]];
  /* cada item: [minutos desde o início, leitura] ou só a leitura (um minuto depois da anterior) */
  window.simularLeituras = async (lista) => {
    kxa = novoKxa(); kxaHist = {amostras: []}; kxaSnap = null; kx.alertas = []; window.__acoes = [];
    const orig = Date.now, t0 = orig(); let ultimo = -1;
    try {
      for (const item of lista) {
        const [min, l] = Array.isArray(item) ? item : [ultimo + 1, item];
        ultimo = min; const t = t0 + min * 60e3; Date.now = () => t;
        window.__leituras = [l];
        await lerKryptexApp();
      }
    } finally { Date.now = orig; }
    return {estado: kxa.estado, alertas: kx.alertas.map(a => a.tipo).reverse(), acoes: window.__acoes};
  };
  window.contarGravacoes = async (lista) => {
    let n = 0; const s = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k, v) { if (k === "min-kx-app") n++; return s.call(this, k, v); };
    try { await simularLeituras(lista); } finally { Storage.prototype.setItem = s; }
    return n;
  };
})();"""


def kryptex_app(p):
    pg = abrir(p, dados=DADOS, pc=True)
    pg.wait_for_timeout(2000)   # a primeira leitura sozinha (sem app: nada) passa antes dos testes
    pg.evaluate(FIXTURAS)
    # ganho de hoje com saque no meio
    h = pg.evaluate("hojeKxa(AMOSTRAS_SAQUE, AGORA, 1.0, 400000)")
    checa("hoje_com_saque", abs(h["ganho"] - 0.00003 * 400000) < 1e-6 and h["ganho"] > 0, h)
    checa("hoje: luz e lucro", abs(h["kwh"] - 4 * 0.286 * 5 / 60) < 1e-6 and abs(h["lucro"] - (h["ganho"] - h["luz"])) < 1e-9, h)
    # PC dormiu: o contador de parada recomeça e a luz conta no máximo 5 min por leitura
    checa("buraco_nao_avisa", pg.evaluate("simularLeituras([[0, MIN], [360, PARADO], [361, PARADO]])")["alertas"] == [])
    checa("luz do buraco", abs(pg.evaluate("hojeKxa([[AGORA-6*3600e3, 0.0001, 286, 1, 1, 63, 78], [AGORA, 0.0001, 286, 1, 1, 63, 78]], AGORA, 1.0, 400000).kwh") - 0.286 * 5 / 60) < 1e-6)
    checa("sem watts: tomada do setup", pg.evaluate("hojeKxa([[AGORA-60e3, 0.0001, null, 1, 1, 63, 78]], AGORA, 1.0, 400000).kwh > 0"))
    # pausado com o hashrate de antes: não avisa
    checa("pausado_nao_avisa", pg.evaluate("simularLeituras([MIN, PAUSADO_COM_HASH, PAUSADO_COM_HASH, PAUSADO_COM_HASH])") == {"estado": "pausada", "alertas": [], "acoes": []})
    # parou e voltou (com os avisos no celular ligados)
    pg.evaluate("celCfg = {...(celCfg || {}), ligado: true, topico: 'painel-teste', maquinas: true}")
    checa("parou_voltou", pg.evaluate("simularLeituras([MIN, PARADO, PARADO, PARADO, MIN])")["alertas"] == ["parou", "voltou"])
    checa("aviso no Windows e no celular", pg.evaluate("[window.__notificacoes.some(n => /parou de minerar/.test(n.titulo)), window.__celular.some(m => m.tipo === 'maquina')]") == [True, True])
    # proteção de temperatura
    checa("protecao_15", pg.evaluate("simularLeituras([QUENTE, QUENTE])")["acoes"] == [["pausar", 15]])
    checa("protecao: aviso", pg.evaluate("kx.alertas.some(a => a.tipo === 'quente' && /86 °C/.test(a.texto))"))
    checa("protecao_longa", pg.evaluate("simularLeituras([[0, QUENTE], [1, QUENTE], [16, MIN], [76, QUENTE], [77, QUENTE]])")["acoes"] == [["pausar", 15], ["pausar", 44640]])
    checa("uma leitura quente só não pausa", pg.evaluate("simularLeituras([QUENTE, MIN, QUENTE, MIN])")["acoes"] == [])
    # app que respondia e parou de responder: 1 aviso depois de 5 minutos
    checa("fechado", pg.evaluate("simularLeituras([[0, MIN], [1, FALHA], [3, FALHA], [6, FALHA], [7, FALHA]])")["alertas"] == ["fechado"])
    checa("app que nunca respondeu: sem aviso", pg.evaluate("simularLeituras([FALHA, FALHA, FALHA, FALHA, FALHA, FALHA, FALHA])")["alertas"] == [])
    # retrato para o celular: ao mudar de estado e a cada 30 min
    checa("retrato", pg.evaluate("contarGravacoes(Array(60).fill(MIN))") == 2)
    checa("retrato ao parar", pg.evaluate("contarGravacoes([MIN, MIN, PAUSADO_COM_HASH, PAUSADO_COM_HASH])") == 2)
    r = pg.evaluate("JSON.parse(localStorage.getItem('min-kx-app'))")
    checa("retrato tem o que o celular mostra", r and r["v"] == 1 and r["estado"] == "pausada" and r["placas"][0]["temp"] == 63 and "hoje" in r and "linha" in r, r)
    checa("min-kx-app sincroniza", pg.evaluate("SINCRONIZADAS.includes('min-kx-app') && !SINCRONIZADAS.includes('min-kxa-hist')"))
    # saldo vai para os dias da Kryptex (Diário)
    checa("saldo para o Diário", pg.evaluate("simularLeituras([MIN]), kxHist.saldos.length > 0 && kx.saldo && kx.saldo.moeda === 'BRL'"))
    # a tela Agora ao vivo
    pg.evaluate("simularLeituras([MIN, MIN])"); pg.evaluate("irPara('resumo')")
    t = pg.inner_text("#agora")
    checa("tela ao vivo", all(s in t for s in ["Minerando", "Pearl", "SRBMiner", "286 W", "63 °C", "memória 78 °C", "54%", "113 TH/s", "lucro"]), t[:400])
    checa("proteção na tela", "85 °C" in t and "100 °C" in t, t[-300:])
    checa("estado no menu", "Minerando" in pg.inner_text("#vivo"))
    pg.evaluate("window.__acoes = []")
    pg.click("details.pausar summary"); pg.click('[data-pausa="60"]'); pg.wait_for_timeout(200)
    checa("pausar pelo botão", pg.evaluate("window.__acoes") == [["pausar", 60]])
    pg.evaluate("window.__leituras = [{...PAUSADO_COM_HASH, pausaAte: AGORA + 3600e3}]; lerKryptexApp()"); pg.wait_for_timeout(200)
    t = pg.inner_text("#agora")
    checa("pausada até", "Pausada até 15:00" in t and pg.is_visible("[data-voltar]"), t[:200])
    pg.evaluate("window.__acoes = []"); pg.click("[data-voltar]"); pg.wait_for_timeout(200)
    checa("voltar pelo botão", pg.evaluate("window.__acoes") == [["voltar"]])
    pg.evaluate("window.__leituras = [FALHA]; kxa.ultimaOk = Date.now() - 10*60e3; lerKryptexApp()"); pg.wait_for_timeout(200)
    checa("app fechado na tela", "App da Kryptex fechado" in pg.inner_text("#agora"))
    # Premissas › App da Kryptex
    pg.evaluate("irPara('premissas')")
    checa("painel em Premissas", pg.is_visible("#kxa-p") and pg.is_checked("#kxa-ligado") and pg.is_checked("#kxa-protecao") and pg.input_value("#kxa-limtemp") == "85")
    pg.fill("#kxa-limtemp", "80"); pg.dispatch_event("#kxa-limtemp", "change")
    checa("limite da placa", pg.evaluate("kxaCfg().limTemp") == 80)
    checa("limite vale na proteção", pg.evaluate("simularLeituras([{...MIN, placas:[{...MIN.placas[0], temp:81}, MIN.placas[1]]}, {...MIN, placas:[{...MIN.placas[0], temp:81}, MIN.placas[1]]}])")["acoes"] == [["pausar", 15]])
    pg.uncheck("#kxa-protecao")
    checa("desligar a proteção", pg.evaluate("kxaCfg().protecao") is False and pg.is_disabled("#kxa-limtemp"))
    checa("protecao_desligada", pg.evaluate("simularLeituras([QUENTE, QUENTE])")["acoes"] == [])
    pg.evaluate("window.__copiado = null; window.desktop.copiar = async (t) => { window.__copiado = t; return true; }")
    pg.click("#kxa-copiar"); pg.wait_for_timeout(200)
    c = pg.evaluate("window.__copiado") or ""
    checa("copiar o que leu", "srbminer" in c and "PC-TESTE" not in c, c[:200])
    checa("sem erros no console", not erros(pg), erros(pg)[:3])


with sync_playwright() as p:
    kryptex_app(p)
fim()
