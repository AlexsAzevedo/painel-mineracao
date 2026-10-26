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
    saldoBtc:0.0001, saldoUsd:0.0001/0.00001237, placas:[PLACA(placa || {}), CPU], desconhecidos:[], ...o});
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
  /* em que minutos (desde a primeira leitura) o retrato do celular foi gravado */
  window.minutosGravados = async (lista) => {
    const ms = [], s = Storage.prototype.setItem, t0 = Date.now();
    Storage.prototype.setItem = function (k, v) { if (k === "min-kx-app") ms.push(Math.round((Date.now() - t0) / 60e3)); return s.call(this, k, v); };
    try { await simularLeituras(lista); } finally { Storage.prototype.setItem = s; }
    return ms;
  };
  /* como o app da Kryptex de verdade: a conta guarda bitcoin (B); o app manda o saldo em dólar pela cotação do momento
     (rp, bitcoins por dólar, sem arredondar) e a cotação com 8 casas; o painel volta para bitcoin com ela (kryptex-app.js) */
  window.LEIT_KX = (B, rp) => { const r8 = Math.round(rp * 1e8) / 1e8, usd = B / rp;
    return LEIT({cotacoes: {brl: 4.965204, btc: r8}, saldoUsd: usd, saldoBtc: usd * r8}); };
  window.SALDO_NOVO = LEIT_KX(0.0001 * 1.01, 0.00001237);   /* 1% a mais de bitcoin na conta */
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
    # placa AMD com os sensores do driver (sensores-amd.js): o consumo medido é o da placa; a luz conta o PC inteiro na
    # tomada (a placa mais o resto do PC do setup, pela eficiência da fonte)
    wt = pg.evaluate("[wattsNaTomada(373), wattsNaTomada(273)]")
    checa("PC na tomada: a placa medida mais o resto do PC", wt[0] > 373 + 30 and 90 < wt[0] - wt[1] < 125, wt)
    rm = pg.evaluate("""(() => { const l = LEIT({}, {watts: 373, tempMem: 76, tempHot: 77, rpm: 2765}), r = ritmoKxa(l);
      return {lucro: r.lucroDia, esperado: r.brutoDia - wattsNaTomada(373) * 24 / 1000 * tarifaEf()}; })()""")
    checa("com o consumo medido, o ritmo desconta o PC inteiro", abs(rm["lucro"] - rm["esperado"]) < 1e-9, rm)
    am = pg.evaluate("simularLeituras([MIN]).then(() => [kxaHist.amostras.at(-1)[2], wattsNaTomada(286)])")
    checa("a leitura guarda o consumo do PC na tomada", am[0] is not None and abs(am[0] - am[1]) < 1e-9, am)
    tl = pg.evaluate("""(() => { const l = LEIT({}, {watts: 373, tempMem: 76, tempHot: 77, rpm: 2765});
      const r = {...l, estado: 'minerando', hoje: {ganho: 1, luz: 0.5, lucro: 0.5}, linha: [], ritmo: ritmoKxa(l)};
      const d = document.createElement('div'); d.innerHTML = htmlAgoraVivo(r, false);
      const tile = rx => [...d.querySelectorAll('.ag-n')].find(n => rx.test(n.textContent)).innerText.replace(/\\s+/g, ' ');
      return {consumo: tile(/Consumo/i), temp: tile(/Temperatura/i), pc: Math.round(wattsNaTomada(373)), prot: d.querySelector('.ag-prot').textContent}; })()""")
    checa("consumo medido: o PC na tomada e a placa", f"≈ {tl['pc']} W" in tl["consumo"] and "placa 373 W" in tl["consumo"], tl)
    checa("temperatura da memória e do ponto mais quente", "memória 76 °C" in tl["temp"] and "ponto quente 77 °C" in tl["temp"], tl)
    checa("a proteção diz o limite do ponto mais quente", "ponto mais quente a 105 °C" in tl["prot"], tl)
    pq = pg.evaluate("""(() => { const est = {quentes: 0}, c = {...kxaCfg(), protecao: true}, l = LEIT({}, {temp: 50, tempMem: 80, tempHot: 106});
      deveProteger(est, l, c, Date.now()); return deveProteger(est, l, c, Date.now() + 60e3); })()""")
    checa("proteção pelo ponto mais quente", bool(pq) and pq["minutos"] == 15 and "ponto mais quente a 106 °C" in pq["motivo"], pq)
    # "Ler agora" (ou o Atualizar do celular) logo depois de uma leitura: o leitor da AMD dá a temperatura mais alta dos
    # últimos segundos, e a mesma amostra quente não pode valer por duas leituras seguidas
    pr = pg.evaluate("""(() => { const est = {quentes: 0}, c = {...kxaCfg(), protecao: true}, l = LEIT({}, {temp: 50, tempMem: 80, tempHot: 106}), t = Date.now();
      return [deveProteger(est, l, c, t), deveProteger(est, l, c, t + 10e3), deveProteger(est, l, c, t + 60e3)]; })()""")
    checa("a leitura logo depois não conta de novo para a proteção", pr[0] is None and pr[1] is None and bool(pr[2]) and pr[2]["minutos"] == 15, pr)
    # setup com mais de uma máquina: o app da Kryptex é só deste PC (o da RX 9070 XT). O PC na tomada (quadro, ritmo e o
    # celular) é só ele, com a fonte dele, em qualquer ordem das máquinas; a luz de hoje soma as outras pelo estimado
    mm = pg.evaluate("""(async () => {
      const antes = {setup, placas};
      try {
        placas = [...antes.placas, {_id: "l2", modelo: "amd-rx-6600", qtd: 2, preco: 900, data: "2026-10-01"}];
        const PC = maqBase({id: "pc", nome: "PC", fonteW: 850, selo: "Gold", base: 30}), RIG = maqBase({id: "rig", nome: "Rig", fonteW: 650, selo: "Bronze", base: 30});
        const usar = (ms) => { setup = migrarSetup({tensao: 220, maquinas: ms, aloc: {l1: "pc", l2: "rig"}}); };
        const l = LEIT({}, {watts: 370, tempMem: 76, tempHot: 77});
        usar([RIG, PC]);
        const dc = 370 + calcMaq(setup.maquinas[1]).wCpu + 30, esperado = dc / eficiencia("Gold", dc / 850, 220), rig = calcMaq(setup.maquinas[0]).tomada;
        const rigPrimeiro = wattsNaTomada(370, l);
        await simularLeituras([l]);
        const amostra = kxaHist.amostras.at(-1)[2], ret = retratoKxa(Date.now()), rt = ritmoKxa(l);
        usar([PC, RIG]);
        const pcPrimeiro = wattsNaTomada(370, l);
        /* acha este PC pelo modelo das placas, mesmo quando a outra máquina tem menos placas */
        placas = [...antes.placas, {_id: "l2", modelo: "amd-rx-6600", qtd: 2, preco: 900, data: "2026-10-01"}, {_id: "l3", modelo: "amd-rx-6600", qtd: 1, preco: 900, data: "2026-10-01"}];
        setup = migrarSetup({tensao: 220, maquinas: [RIG, PC], aloc: {l1: "pc", l2: "pc", l3: "rig"}});
        const peloModelo = (maqDestePc(l) || {}).id;
        placas = [...antes.placas, {_id: "l2", modelo: "amd-rx-6600", qtd: 2, preco: 900, data: "2026-10-01"}];
        /* uma placa minerando sem medida no mesmo PC: entra pelo consumo do catálogo, não como 0 W */
        usar([PC]);
        const l2 = LEIT({}, {watts: 370});
        l2.placas.splice(1, 0, {...l2.placas[0], id: "gpu-2", nome: "AMD Radeon RX 6600", watts: null, tempMem: null, hash: 2e13, rendimentoUsd: 0.4});
        const w6600 = dados(byId["amd-rx-6600"]).w, r2 = ritmoKxa(l2);
        await simularLeituras([l2]);
        return {esperado, rig, rigPrimeiro, pcPrimeiro, peloModelo, amostra, wattsPc: ret.wattsPc, lucro: rt.lucroDia, lucroEsperado: rt.brutoDia - esperado * 24 / 1000 * tarifaEf(),
          lucro2: r2.lucroDia, lucro2Esperado: r2.brutoDia - wattsNaTomada(370 + w6600, l2) * 24 / 1000 * tarifaEf(), wattsPc2: retratoKxa(Date.now()).wattsPc, pc2: wattsNaTomada(370 + w6600, l2)};
      } finally { setup = antes.setup; placas = antes.placas; }
    })()""")
    perto = lambda a, b: a is not None and b is not None and abs(a - b) < 1e-6
    checa("várias máquinas: o PC na tomada é só este PC, com a fonte dele", perto(mm["rigPrimeiro"], mm["esperado"]) and perto(mm["pcPrimeiro"], mm["esperado"]), mm)
    checa("várias máquinas: acha este PC pelo modelo das placas", mm["peloModelo"] == "pc", mm)
    checa("várias máquinas: o celular e o ritmo usam só este PC", perto(mm["wattsPc"], mm["esperado"]) and perto(mm["lucro"], mm["lucroEsperado"]), mm)
    checa("várias máquinas: a luz de hoje soma as outras pelo estimado", perto(mm["amostra"], mm["esperado"] + mm["rig"]), mm)
    checa("placa sem medida no mesmo PC entra pelo catálogo", perto(mm["lucro2"], mm["lucro2Esperado"]) and perto(mm["wattsPc2"], mm["pc2"]), mm)
    checa("limite do ponto mais quente: 105 °C", pg.evaluate("kxaCfg().limHot") == 105)
    rt = pg.evaluate("""(() => { kxa = novoKxa(); kxaHist = {v: 2, amostras: []}; const l = LEIT({}, {watts: 373, tempHot: 77}); processarLeituraKxa(l, Date.now());
      const r = retratoKxa(); kxaHist = {v: 2, amostras: []}; kxa = novoKxa(); const l2 = LEIT({}, {watts: null}); processarLeituraKxa(l2, Date.now()); const r2 = retratoKxa();
      return {hot: r.placas[0].tempHot, pc: r.wattsPc, medido: r.wattsMedido, esperado: wattsNaTomada(373), pc2: r2.wattsPc, medido2: r2.wattsMedido, est: wattsEstimados()}; })()""")
    checa("retrato: o ponto mais quente e o consumo do PC", rt["hot"] == 77 and abs(rt["pc"] - rt["esperado"]) < 1e-9 and rt["medido"] is True, rt)
    checa("retrato sem consumo medido: o estimado", abs(rt["pc2"] - rt["est"]) < 1e-9 and rt["medido2"] is False, rt)
    ce = pg.evaluate("""(() => { const r = {v: 1, quando: Date.now(), estado: 'minerando', placas: [{nome: 'RX 9070 XT', tipo: 'gpu', minerando: true, watts: 373, temp: 46, tempMem: 76, tempHot: 77}],
      hoje: {ganho: 1, luz: 0.5, lucro: 0.5}, ritmo: {brutoDia: 14, lucroDia: 3}, linha: [], wattsPc: 512, wattsMedido: true};
      const d = document.createElement('div'); d.innerHTML = htmlAgoraVivo(r, false, true);
      return [...d.querySelectorAll('.ag-n')].find(n => /Consumo/i.test(n.textContent)).innerText.replace(/\\s+/g, ' '); })()""")
    checa("no celular, o consumo do PC vem do retrato", "≈ 512 W" in ce and "placa 373 W" in ce, ce)
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
    # dinheiro novo na conta (o saldo em bitcoin subiu): o retrato vai de novo em até 5 minutos (o celular aberto recebe na
    # hora), não a cada leitura. A Kryptex guarda o saldo em bitcoin: o preço do bitcoin mexendo muda o saldo em dólar sem
    # dinheiro novo, e o arredondamento da cotação (8 casas) não pode parecer dinheiro novo
    r = pg.evaluate("minutosGravados([[0, MIN], [1, MIN], [2, SALDO_NOVO], [3, SALDO_NOVO], [4, SALDO_NOVO], [5, SALDO_NOVO], [6, SALDO_NOVO]])")
    checa("retrato: dinheiro novo vai em até 5 min", r == [0, 5], r)
    r = pg.evaluate("minutosGravados(Array.from({length: 60}, (_, i) => [i, LEIT_KX(0.0001 * (1 + 0.005 * i), 0.00001237)]))")
    checa("retrato: dinheiro entrando a cada minuto vai no máximo a cada 5 min", r == list(range(0, 60, 5)), r)
    r = pg.evaluate("minutosGravados(Array.from({length: 60}, (_, i) => [i, LEIT_KX(0.0001, 0.00001237 * (1 + 0.02 * Math.sin(i / 4)))]))")
    checa("retrato: só o preço do bitcoin mexeu (o saldo em dólar muda), não vai antes dos 30 min", r == [0, 30], r)
    r = pg.evaluate("minutosGravados([[0, MIN], [1, MIN], [2, LEIT_KX(0, 0.00001237)], [3, LEIT_KX(0, 0.00001237)], [4, LEIT_KX(0, 0.00001237)], [5, LEIT_KX(0, 0.00001237)]])")
    checa("retrato: saque vai em até 5 min", r == [0, 5], r)
    # saldo vai para os dias da Kryptex (Diário)
    checa("saldo para o Diário", pg.evaluate("simularLeituras([MIN]), kxHist.saldos.length > 0 && kx.saldo && kx.saldo.moeda === 'BRL'"))
    # até a 1.6.1, o saldo do app da Kryptex (que vem em dólar) foi guardado como se fosse bitcoin: US$ 0,005 virava uns
    # R$ 1.990 de ganho. A primeira leitura com cotação converte as leituras guardadas e os saldos que elas puseram nos dias
    # da Kryptex (os do site ficam como estão), e os dias já calculados com eles são calculados de novo
    mig = pg.evaluate("""(() => {
      const agora = Date.now(), d = new Date(agora); d.setHours(0, 0, 0, 0); const ini = d.getTime();
      const ts = [ini - 60 * 60e3, ini - 30 * 60e3, ini + 11 * 3600e3, ini + 11.5 * 3600e3], usd = [0, 0, 0.004862, 0.0050139];
      const preco = 4.965198 / 0.00001251, ontem = isoLocal(new Date(ini - 3600e3));
      kxa = novoKxa();
      kxaHist = {amostras: ts.map((t, i) => [t, usd[i], null, i >= 2 ? 1 : 0, i >= 2 ? 1.1e14 : 0, 46, null])};   // gravado pela 1.6.1 (sem "v")
      kxHist.saldos = [[ini - 2 * 3600e3, 0.00000005, 400000], ...ts.map((t, i) => [t + 7, usd[i], preco])];
      kx.saldo = {btc: 0.0050139, fiat: 0.0050139 * preco, moeda: "BRL", preco, quando: ts[3] + 7};
      kx.dias = {[ontem]: {btc: 0.000211, valor: 84, moeda: "BRL", horas: null, aproximado: true, parcial: "22:00", fonte: "saldo"}};
      const l = LEIT({cotacoes: {brl: 4.965198, btc: 0.00001251}, saldoBtc: 0.0050139 * 0.00001251});
      processarLeituraKxa(l, agora);
      const r = {v: kxaHist.v, guardado: JSON.parse(localStorage.getItem("min-kxa-hist")).v, a3: kxaHist.amostras[3][1], site: kxHist.saldos[0][1],
        s4: kxHist.saldos[4][1], saldo: kx.saldo.btc, fiat: kx.saldo.fiat, ontem: kx.dias[ontem] && kx.dias[ontem].valor,
        ganho: hojeKxa(kxaHist.amostras, agora, 1.0, precoBtcBrl(l)).ganho};
      processarLeituraKxa(l, agora + 60e3);   // a segunda leitura não converte de novo
      r.a3b = kxaHist.amostras[3][1];
      if(typeof carregarKxaHist !== "function") return r;
      localStorage.setItem("min-kxa-hist", JSON.stringify({v: 2, amostras: [[1, 0.5, null, 0, 0, null, null]]}));
      const c2 = carregarKxaHist();
      localStorage.setItem("min-kxa-hist", JSON.stringify({amostras: [[1, 0.5, null, 0, 0, null, null]]}));
      const c1 = carregarKxaHist();
      r.carrega = [c2.v, c2.amostras.length, c1.v || 1, c1.amostras.length];
      return r;
    })()""")
    checa("1.6.1: as leituras guardadas passam para bitcoin (uma vez só)", mig["v"] == 2 and mig["guardado"] == 2 and abs(mig["a3"] - 0.0050139 * 0.00001251) < 1e-15 and mig["a3b"] == mig["a3"], mig)
    checa("1.6.1: o ganho de hoje volta ao certo (R$ 0,02, não R$ 1.990)", 0.02 < mig["ganho"] < 0.03, mig)
    checa("1.6.1: os saldos do app nos dias da Kryptex também (os do site não)", abs(mig["s4"] - 0.0050139 * 0.00001251) < 1e-15 and mig["site"] == 0.00000005, mig)
    checa("1.6.1: o saldo de agora e o dia de ontem refeitos", mig["saldo"] < 1e-6 and mig["fiat"] < 0.03 and mig["ontem"] is not None and mig["ontem"] < 0.01, mig)
    checa("o histórico do app guarda a versão", mig.get("carrega") == [2, 1, 1, 1], mig)
    # o dia anterior ao primeiro saldo do app também é refeito: ele pode ter usado o trecho "último saldo do site → primeiro do
    # app" (o PC desligado na virada do dia). Os dias só com saldos do site ficam como estão
    mig2 = pg.evaluate("""(() => {
      const agora = Date.now(), d = new Date(agora); d.setHours(0, 0, 0, 0); const ini = d.getTime();
      const ontem = isoLocal(new Date(ini - 3600e3)), anteontem = isoLocal(new Date(ini - 25 * 3600e3)), preco = 4.965198 / 0.00001251;
      const ts = [ini + 8 * 3600e3, ini + 8.5 * 3600e3], usd = [0.0030, 0.0031];
      kxa = novoKxa();
      kxaHist = {amostras: ts.map((t, i) => [t, usd[i], null, 1, 1.1e14, 46, null])};   // gravado pela 1.6.1 (sem "v")
      kxHist.saldos = [[ini - 47 * 3600e3, 0.00000004, 396000], [ini - 30 * 60e3, 0.00000006, 396000], ...ts.map((t, i) => [t + 7, usd[i], preco])];
      kx.dias = {[anteontem]: {btc: 0.00000002, valor: 0.0079, moeda: "BRL", horas: null, aproximado: false, parcial: "", fonte: "saldo"},
                 [ontem]: {btc: 0.000176, valor: 70, moeda: "BRL", horas: null, aproximado: true, parcial: "", fonte: "saldo"}};
      const l = LEIT({cotacoes: {brl: 4.965198, btc: 0.00001251}, saldoBtc: 0.0031 * 0.00001251});
      processarLeituraKxa(l, agora);
      return {ontem: kx.dias[ontem] && kx.dias[ontem].valor, anteontem: kx.dias[anteontem] && kx.dias[anteontem].valor};
    })()""")
    checa("1.6.1: o dia antes do primeiro saldo do app também é refeito", mig2["ontem"] is not None and mig2["ontem"] < 0.01, mig2)
    checa("1.6.1: os dias só do site ficam como estavam", mig2["anteontem"] == 0.0079, mig2)
    # a tela Agora ao vivo
    pg.evaluate("simularLeituras([MIN, MIN])"); pg.evaluate("irPara('resumo')")
    t = pg.inner_text("#agora")
    checa("tela ao vivo", all(s in t for s in ["Minerando", "Pearl", "SRBMiner", "286 W", "63 °C", "memória 78 °C", "54%", "113 TH/s", "lucro"]), t[:400])
    checa("proteção na tela", "85 °C" in t and "100 °C" in t, t[-300:])
    checa("ritmo de agora", "ritmo de agora" in t.lower() and "R$ 14,72/dia" in t, t[:500])
    # o saldo total da conta (o mesmo que o app da Kryptex mostra), ao lado do ganho de hoje
    checa("saldo na Kryptex", "saldo na kryptex" in t.lower() and "R$ 40,14" in t and "US$ 8,08" in t, t[:500])
    lado = pg.evaluate("""(() => { const eh = document.querySelector('#agora .ag-hoje:not(.ag-saldo)'), es = document.querySelector('#agora .ag-saldo'); if (!eh || !es) return {ok: false, falta: !eh ? 'hoje' : 'saldo'};
      const h = eh.getBoundingClientRect(), s = es.getBoundingClientRect();
      return {ok: s.left >= h.right - 1 && Math.abs(s.top - h.top) < 4, h: [h.left, h.top, h.right], s: [s.left, s.top, s.right]}; })()""")
    checa("saldo ao lado do hoje no PC", lado["ok"], lado)
    checa("o retrato leva o saldo em dólar", abs((pg.evaluate("retratoKxa().saldoUsd") or 0) - 8.0841) < 0.001)
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
    checa("campo do ponto mais quente", pg.is_visible("#kxa-limhot") and pg.input_value("#kxa-limhot") == "105")
    pg.fill("#kxa-limhot", "100"); pg.dispatch_event("#kxa-limhot", "change")
    checa("limite do ponto mais quente muda", pg.evaluate("kxaCfg().limHot") == 100)
    pg.fill("#kxa-limhot", "300"); pg.dispatch_event("#kxa-limhot", "change")
    checa("limite do ponto mais quente fora da faixa não entra", pg.evaluate("kxaCfg().limHot") == 100 and pg.input_value("#kxa-limhot") == "100")
    checa("limite do ponto mais quente vale na proteção", pg.evaluate("simularLeituras([{...MIN, placas:[{...MIN.placas[0], tempHot:101}, MIN.placas[1]]}, {...MIN, placas:[{...MIN.placas[0], tempHot:101}, MIN.placas[1]]}])")["acoes"] == [["pausar", 15]])
    pg.uncheck("#kxa-protecao")
    checa("desligar a proteção", pg.evaluate("kxaCfg().protecao") is False and pg.is_disabled("#kxa-limtemp") and pg.is_disabled("#kxa-limhot"))
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
    checa("saldo no celular", "saldo na kryptex" in t.lower() and "R$ 48,12" in t, t[:400])
    emb = pgc.evaluate("""(() => { const eh = document.querySelector('#agora .ag-hoje:not(.ag-saldo)'), es = document.querySelector('#agora .ag-saldo'); if (!eh || !es) return {ok: false, falta: !eh ? 'hoje' : 'saldo'};
      const h = eh.getBoundingClientRect(), s = es.getBoundingClientRect();
      return {ok: s.top >= h.bottom - 1, h: [h.top, h.bottom], s: [s.top, s.bottom]}; })()""")
    checa("no celular, o saldo fica embaixo do hoje", emb["ok"], emb)
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify({...RETRATO, saldoBtc: null})); recarregarDados(['min-kx-app'])")
    checa("sem saldo no retrato, sem o quadro do saldo", "saldo na kryptex" not in pgc.inner_text("#agora").lower())
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify(RETRATO)); recarregarDados(['min-kx-app'])")
    checa("estado no topo do celular", "Minerando" in pgc.inner_text("#g-chip"))
    # o botão de atualizar no alto (e puxar a tela para baixo) traz também uma leitura nova do app da Kryptex do PC, mesmo
    # com o retrato de 3 minutos; o Atualizar do quadro Agora faz o mesmo, e os dois esperam 30 s entre um e outro
    leituras = "window.__pedidos.filter(p=>p[0]==='kryptex-agora').length"
    pgc.evaluate("window.__atu = 0; window.__atuOrig = window.desktop.sync.atualizar; window.__atuConta = async () => { window.__atu++; return window.__atuOrig(); }; window.desktop.sync.atualizar = window.__atuConta; atuPc.ultimo = 0; 0")
    n0 = pgc.evaluate(leituras)
    pgc.click("#topo-atu"); pgc.wait_for_timeout(300)
    checa("atualizar no alto: dados e leitura nova da Kryptex", pgc.evaluate(leituras) == n0 + 1 and pgc.evaluate("window.__atu") == 1, [pgc.evaluate(leituras) - n0, pgc.evaluate("window.__atu")])
    checa("atualizar no alto: recado quando chega", "atualizados" in pgc.inner_text("#toast"), pgc.inner_text("#toast"))
    pgc.click("[data-kxa-atualizar]"); pgc.wait_for_timeout(300)
    checa("atualizar do quadro: não repete antes de 30 s", pgc.evaluate(leituras) == n0 + 1 and pgc.evaluate("window.__atu") == 1, [pgc.evaluate(leituras) - n0, pgc.evaluate("window.__atu")])
    pgc.evaluate("atuPc.ultimo = Date.now() - 31e3; 0")
    pgc.click("[data-kxa-atualizar]"); pgc.wait_for_timeout(300)
    checa("atualizar do quadro: dados e leitura nova", pgc.evaluate(leituras) == n0 + 2 and pgc.evaluate("window.__atu") == 2, [pgc.evaluate(leituras) - n0, pgc.evaluate("window.__atu")])
    # o PC não conseguiu ler o app da Kryptex: o recado diz, e os outros dados valem
    pgc.evaluate("""window.__pedirOk0 = window.desktop.pedirAoPc; window.desktop.pedirAoPc = async (nome, args) => { window.__pedidos.push([nome, args || {}]);
      return nome === 'kryptex-agora' ? {ok: false, texto: 'O PC não conseguiu ler o app da Kryptex: o app da Kryptex não respondeu.'} : {ok: true}; }; atuPc.ultimo = 0; 0""")
    pgc.click("#topo-atu"); pgc.wait_for_timeout(300)
    t = pgc.inner_text("#toast")
    checa("atualizar no alto: leitura que falhou aparece no recado", "atualizados" in t and "não conseguiu ler o app da Kryptex" in t, t)
    # PC desligado: os dados não vêm, e o recado sai na hora, sem esperar a leitura (que só desistiria depois de 50 s)
    pgc.evaluate("""window.desktop.sync.atualizar = async () => { throw new Error('O PC não respondeu. Confira se ele está ligado.'); };
      window.desktop.pedirAoPc = (nome, args) => { window.__pedidos.push([nome, args || {}]); return new Promise(() => {}); }; atuPc.ultimo = 0; 0""")
    pgc.click("#topo-atu"); pgc.wait_for_timeout(300)
    t = pgc.inner_text("#toast")
    checa("PC desligado: o recado não espera a leitura", "não respondeu" in t and pgc.evaluate("atuPc.rodando") is False, [t, pgc.evaluate("atuPc.rodando")])
    # tocar de novo enquanto atualiza: diz que ainda está atualizando (e não fica mudo)
    pgc.evaluate("window.desktop.sync.atualizar = () => new Promise(() => {}); window.desktop.pedirAoPc = window.__pedirOk0; atuPc.ultimo = 0; 0")
    pgc.click("#topo-atu"); pgc.wait_for_timeout(200); pgc.click("#topo-atu"); pgc.wait_for_timeout(200)
    checa("tocar de novo enquanto atualiza: avisa", "Ainda atualizando" in pgc.inner_text("#toast"), pgc.inner_text("#toast"))
    pgc.evaluate("atuPc.rodando = false; document.getElementById('topo-atu').removeAttribute('aria-busy'); 0")
    # os dados chegaram e a leitura demora: o recado sai sem esperar mais (a leitura entra no quadro quando chegar)
    pgc.evaluate("""window.desktop.sync.atualizar = window.__atuConta; ESPERA_LEITURA_ATU = 300;
      window.desktop.pedirAoPc = (nome, args) => { window.__pedidos.push([nome, args || {}]); return new Promise(() => {}); }; atuPc.ultimo = 0; 0""")
    pgc.click("#topo-atu"); pgc.wait_for_timeout(700)
    t = pgc.inner_text("#toast")
    checa("leitura demorando: o recado sai mesmo assim", "atualizados" in t and "ainda está vindo" in t and pgc.evaluate("atuPc.rodando") is False, [t, pgc.evaluate("atuPc.rodando")])
    pgc.evaluate("ESPERA_LEITURA_ATU = 20e3; window.desktop.pedirAoPc = window.__pedirOk0; 0")
    # o retrato acabou de chegar (menos de 1 min e meio): o PC lê a cada minuto, então só os dados, sem pedir outra leitura
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify({...RETRATO, quando: AGORA - 30e3})); recarregarDados(['min-kx-app']); atuPc.ultimo = 0; atuPc.rodando = false; 0")
    n1, a1 = pgc.evaluate(leituras), pgc.evaluate("window.__atu")
    pgc.click("#topo-atu"); pgc.wait_for_timeout(300)
    checa("retrato de agora: só os dados", pgc.evaluate(leituras) == n1 and pgc.evaluate("window.__atu") == a1 + 1 and "atualizados" in pgc.inner_text("#toast"), [pgc.evaluate(leituras) - n1, pgc.evaluate("window.__atu") - a1, pgc.inner_text("#toast")])
    pgc.evaluate("localStorage.setItem('min-kx-app', JSON.stringify(RETRATO)); recarregarDados(['min-kx-app']); window.desktop.sync.atualizar = window.__atuOrig; atuPc.ultimo = 0; 0")
    # em dia com o PC (a ponte do app diz "ativo"): só a leitura, sem pedir os dados; se o PC não responde (desligado,
    # dormindo), o recado diz depois que ele não respondeu, e não fica só no "chegam assim que ele responder"
    pgc.evaluate("""window.__infoOrig = window.desktop.sync.info; window.desktop.sync.info = async () => ({ativo: true});
      window.__atu = 0; window.desktop.sync.atualizar = window.__atuConta; ESPERA_LEITURA_ATU = 100;
      window.desktop.pedirAoPc = (nome, args) => { window.__pedidos.push([nome, args || {}]);
        return new Promise((ok, nao) => setTimeout(() => nao(new Error('o PC não respondeu. Confira se ele está ligado, com o painel aberto e com internet')), 400)); };
      atuPc.ultimo = 0; atuPc.rodando = false; 0""")
    n2 = pgc.evaluate(leituras)
    pgc.click("#topo-atu"); pgc.wait_for_timeout(250)
    t = pgc.inner_text("#toast")
    checa("em dia: só a leitura, sem pedir os dados", pgc.evaluate(leituras) == n2 + 1 and pgc.evaluate("window.__atu") == 0 and "Pedi a leitura" in t, [pgc.evaluate(leituras) - n2, pgc.evaluate("window.__atu"), t])
    pgc.wait_for_timeout(500)
    checa("em dia com o PC sem responder: o recado diz", "não respondeu" in pgc.inner_text("#toast"), pgc.inner_text("#toast"))
    # fora de dia: os dados saem antes da leitura (no limite de mensagens, a vaga que sobrar vai para os dados)
    pgc.evaluate("""window.__ordem = []; window.desktop.sync.info = async () => ({ativo: false}); ESPERA_LEITURA_ATU = 20e3;
      window.desktop.sync.atualizar = async () => { window.__ordem.push('dados'); };
      window.desktop.pedirAoPc = async (nome, args) => { window.__ordem.push(nome); window.__pedidos.push([nome, args || {}]); return {ok: true}; };
      atuPc.ultimo = 0; atuPc.rodando = false; 0""")
    pgc.click("#topo-atu"); pgc.wait_for_timeout(300)
    checa("fora de dia: os dados saem antes da leitura", pgc.evaluate("window.__ordem") == ["dados", "kryptex-agora"], pgc.evaluate("window.__ordem"))
    pgc.evaluate("window.desktop.sync.info = window.__infoOrig; window.desktop.sync.atualizar = window.__atuOrig; window.desktop.pedirAoPc = window.__pedirOk0; atuPc.ultimo = 0; 0")
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
