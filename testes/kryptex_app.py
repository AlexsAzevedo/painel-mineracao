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
  window.LEIT = LEIT;
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
    # placa AMD de verdade: o app da Kryptex não manda o consumo; o ritmo de agora desconta a luz estimada (setup na tomada)
    rt = pg.evaluate("""(() => { const l = LEIT({}, {watts: null, tempMem: null}), r = ritmoKxa(l), w = wattsEstimados();
      return {bruto: r.brutoDia, lucro: r.lucroDia, w, esperado: r.brutoDia - w * 24 / 1000 * tarifaEf()}; })()""")
    checa("sem watts: o ritmo desconta a luz estimada", rt["w"] > 0 and abs(rt["lucro"] - rt["esperado"]) < 1e-9 and rt["lucro"] < rt["bruto"], rt)
    cons = pg.evaluate("(() => { const l = LEIT({}, {watts: null, tempMem: null}); const r = {...l, estado: 'minerando', hoje: {ganho: 1, luz: 0.5, lucro: 0.5}, linha: [], ritmo: ritmoKxa(l)}; const d = document.createElement('div'); d.innerHTML = htmlAgoraVivo(r, false); return [...d.querySelectorAll('.ag-n')].find(n => /Consumo/i.test(n.textContent)).innerText.replace(/\\s+/g, ' '); })()")
    checa("sem watts: o consumo aparece estimado", "≈ 320 W" in cons and "estimado" in cons, cons)
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
    # o PC dormiu 6 h e o app da Kryptex ainda não respondeu na primeira leitura: avisa só depois de 5 min de falhas
    checa("acordou: sem aviso na hora", pg.evaluate("simularLeituras([[0, MIN], [360, FALHA]])")["alertas"] == [])
    checa("acordou: avisa depois de 5 min sem resposta", pg.evaluate("simularLeituras([[0, MIN], [360, FALHA], [362, FALHA], [366, FALHA]])")["alertas"] == ["fechado"])
    # a proteção pede a pausa e o app da Kryptex não aceita: não diz que pausou, tenta de novo com 15 min e avisa uma vez
    pg.evaluate("window.__pausarOk = window.desktop.kryptexApp.pausar; window.desktop.kryptexApp.pausar = async (m) => { window.__acoes.push(['pausar', m]); return {ok:false, feito:false, erro:'tempo', msg:'o app da Kryptex demorou demais para responder'}; }")
    r = pg.evaluate("simularLeituras([QUENTE, QUENTE, QUENTE, QUENTE])")
    textos = pg.evaluate("kx.alertas.map(a => a.texto)")
    checa("protecao_falhou: não diz que pausou", not any("Pausei" in x for x in textos) and any("não consegui pausar" in x.lower() for x in textos) and pg.evaluate("kxa.protecao") is None, textos)
    checa("protecao_falhou: tenta de novo com 15 min e avisa uma vez", r["acoes"] == [["pausar", 15], ["pausar", 15]] and len([x for x in textos if "não consegui pausar" in x.lower()]) == 1, [r, textos])
    pg.evaluate("window.desktop.kryptexApp.pausar = window.__pausarOk")
    # retrato para o celular: ao mudar de estado e a cada 30 min
    checa("retrato", pg.evaluate("contarGravacoes(Array(60).fill(MIN))") == 2)
    checa("app que nunca respondeu: não grava retrato", pg.evaluate("contarGravacoes(Array(40).fill(FALHA))") == 0)
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
    checa("ritmo de agora", "ritmo de agora" in t.lower() and "R$ 14,72/dia" in t, t[:500])
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
    checa("recado velho some quando o estado muda", pg.inner_text("#ag-status").strip() == "", pg.inner_text("#ag-status"))
    t = pg.inner_text("#agora")
    checa("app fechado: o menu não diz 'agora'", "App da Kryptex fechado" in pg.inner_text("#vivo") and "hoje até agora" not in pg.inner_text("#vivo"), pg.inner_text("#vivo"))
    checa("app fechado: números da última leitura", pg.evaluate("!!document.querySelector('#agora .ag-nums.velho')") and "última leitura" in t and "Hoje até agora" not in t, t[:300])
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
    pg.evaluate("status2('ag-status', 'Pronto: o app da Kryptex voltou a minerar.', 'ok')")
    pg.uncheck("#kxa-ligado")
    checa("desligar a leitura: estimativa, sem recado velho", pg.evaluate("kxaCfg().ligado") is False and pg.inner_text("#ag-status").strip() == "" and "Sem leitura ao vivo" in pg.inner_text("#agora"),
          [pg.inner_text("#ag-status"), pg.inner_text("#agora")[:120]])
    checa("sem erros no console", not erros(pg), erros(pg)[:3])


RETRATOS = """(() => {
  window.AGORA = Date.now();
  const placa = {nome:"RX 9070 XT", tipo:"gpu", minerando:true, moeda:"PRL", minerador:"srbminer", hash:1.13e14, temp:63, tempMem:78, watts:286, ventoinha:54, rpm:null};
  const base = {v:1, estado:"minerando", pausaAte:null, computador:"PC-TESTE", placas:[placa], hoje:{ganho:9.62, luz:5.09, lucro:4.53, kwh:5.3, desde:null},
    ritmo:{brutoDia:14.7, lucroDia:6.9}, saldoBtc:0.00012, precoBtc:401000, linha:[], protecao:null, hash24:1.12e14};
  window.RETRATO_DE_ONTEM = {...base, quando: AGORA - 21*3600e3, minerandoDesde: AGORA - 30*3600e3};
  window.RETRATO = {...base, quando: AGORA - 3*60e3, minerandoDesde: AGORA - 5*3600e3};
  window.RETRATO_PAUSADO = {...base, quando: AGORA - 60e3, estado:"pausada", pausaAte: AGORA + 3*3600e3, placas:[{...placa, minerando:false}], minerandoDesde: 0};
})();"""


def celular(p):
    pgc = abrir(p, largura=390, altura=844, dados=DADOS, celular=True)
    pgc.evaluate(RETRATOS)
    checa("pede o retrato ao abrir o Resumo", pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length") == 1)
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify(RETRATO_DE_ONTEM)); recarregarDados(['min-kx-app'])")
    t = pgc.inner_text("#agora")
    checa("retrato_velho", "Última leitura há" in t and "Minerando" not in t, t[:200])
    checa("retrato velho: dia da leitura", "24/10" in t, t[:300])
    checa("retrato velho: números apagados", pgc.evaluate("!!document.querySelector('#agora .ag-nums.velho')"))
    pgc.evaluate("irPara('diario'); irPara('resumo')")
    checa("não repete antes de 10 min", pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length") == 1)
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify(RETRATO)); recarregarDados(['min-kx-app'])")
    t = pgc.inner_text("#agora")
    checa("retrato novo", all(s in t for s in ["Minerando", "R$ 9,62", "lucro de R$ 4,53", "286 W", "63 °C", "lido há 3 min"]), t[:400])
    checa("estado no topo do celular", "Minerando" in pgc.inner_text("#g-chip"))
    pgc.click("[data-kxa-atualizar]"); pgc.wait_for_timeout(200)
    checa("atualizar pelo botão", pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length") == 2)
    pgc.click("[data-kxa-atualizar]"); pgc.wait_for_timeout(200)
    checa("atualizar: no máximo 1 a cada 2 min", pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length") == 2)
    pgc.click("details.pausar summary"); pgc.click('[data-pausa="180"]'); pgc.wait_for_timeout(200)
    checa("pausar pelo PC", pgc.evaluate("window.__pedidos.at(-1)") == ["kryptex-pausar", {"minutos": 180}])
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify(RETRATO_PAUSADO)); recarregarDados(['min-kx-app'])")
    checa("pausada no celular", "Pausada até 17:00" in pgc.inner_text("#agora"))
    checa("recado some quando o retrato muda de estado", pgc.inner_text("#ag-status").strip() == "", pgc.inner_text("#ag-status"))
    pgc.click("[data-voltar]"); pgc.wait_for_timeout(200)
    checa("voltar pelo PC", pgc.evaluate("window.__pedidos.at(-1)") == ["kryptex-voltar", {}])
    # o PC grava o retrato a cada 30 min quando nada muda: com 20 min ele ainda vale (estado, botões e topo)
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify({...RETRATO, quando: AGORA - 20*60e3})); recarregarDados(['min-kx-app'])")
    t = pgc.inner_text("#agora")
    checa("retrato de 20 min ainda vale", "Minerando" in t and "Última leitura" not in t and pgc.is_visible("details.pausar") and "Minerando" in pgc.inner_text("#g-chip"), t[:200])
    # retrato vazio (de um PC em que o app da Kryptex nunca respondeu): o celular mostra a estimativa
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify({...RETRATO, estado:'', placas:[]})); recarregarDados(['min-kx-app'])")
    checa("retrato vazio: estimativa", "O PC ainda não mandou" in pgc.inner_text("#agora") and "fechado" not in pgc.inner_text("#agora").lower() and "R$ 0,00" not in pgc.inner_text("#g-chip"), [pgc.inner_text("#agora")[:160], pgc.inner_text("#g-chip")])
    # ao abrir o app, a ponte ainda não tem canal: o pedido automático falha sem gastar os 10 min e sai quando a ponte fica pronta
    pgc.evaluate("""(() => { localStorage.setItem('min-kx-app', JSON.stringify(RETRATO_DE_ONTEM)); recarregarDados(['min-kx-app']); kxaPedido.auto = 0; window.__falhas = 0;
      const orig = window.desktop.pedirAoPc; window.__pedirOk = orig;
      window.desktop.pedirAoPc = async (nome, args) => { if (!window.__pronto) { window.__falhas++; throw new Error('este celular ainda não está ligado ao PC'); } return orig(nome, args); }; })()""")
    n0 = pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length")
    pgc.evaluate("irPara('diario'); irPara('resumo')"); pgc.wait_for_timeout(200)
    checa("ponte sem canal: não gasta o pedido automático", pgc.evaluate("window.__falhas") == 1 and pgc.evaluate("kxaPedido.auto") == 0, pgc.evaluate("[window.__falhas, kxaPedido.auto]"))
    pgc.evaluate("window.__pronto = true; remotoInfo = {ok:false}; remotoEstado({ok:true, texto:'Ligado ao PC'})"); pgc.wait_for_timeout(300)
    checa("ponte pronta: pede o retrato", pgc.evaluate("window.__pedidos.filter(p=>p[0]==='kryptex-agora').length") == n0 + 1)
    pgc.evaluate("window.desktop.pedirAoPc = window.__pedirOk")
    checa("sem erros no celular", not erros(pgc), erros(pgc)[:3])
    # no PC: os três pedidos do celular
    pg = abrir(p, dados=DADOS, pc=True)
    pg.wait_for_timeout(1800); pg.evaluate(FIXTURAS); pg.evaluate("window.__leituras = [MIN]")
    r = pg.evaluate("executarPedidoRemoto({nome:'kryptex-agora'})")
    checa("pedido: ler agora", r["ok"] is True and pg.evaluate("JSON.parse(localStorage.getItem('min-kx-app')).estado") == "minerando", r)
    checa("minutos inválidos", pg.evaluate("executarPedidoRemoto({nome:'kryptex-pausar', args:{minutos:7}})")["ok"] is False and pg.evaluate("window.__acoes.length") == 0)
    checa("pausar pelo pedido", pg.evaluate("executarPedidoRemoto({nome:'kryptex-pausar', args:{minutos:180}})")["ok"] is True and pg.evaluate("window.__acoes.at(-1)") == ["pausar", 180])
    checa("atende mesmo ocupado", pg.evaluate("ofEst.rodando = true, executarPedidoRemoto({nome:'kryptex-voltar'})")["ok"] is True and pg.evaluate("window.__acoes.at(-1)") == ["voltar"])
    checa("sem erros no PC", not erros(pg), erros(pg)[:3])


with sync_playwright() as p:
    kryptex_app(p)
    celular(p)
fim()
