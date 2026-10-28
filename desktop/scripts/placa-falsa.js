"use strict";
/* Leitor da placa de mentira para os testes (no lugar do placa-amd.ps1): lê os pedidos em linhas de JSON e responde
   no mesmo formato do leitor de verdade, com uma RX 9070 XT como a do Alex (28/10/2026).
   - PAINEL_PLACA_FALSA: "normal" (padrão), "mudo" (não responde), "cai" (sai ao receber o primeiro pedido),
     "sem-amd" (responde sem-amd a tudo) ou "lixo" (responde o ler com números e textos estragados);
   - PAINEL_PLACA_FALSA_ESTADO: arquivo com a placa (os valores de agora), que o aplicar muda e o teste pode mudar.
     Além dos valores: deFabrica (a placa lê como de fábrica), rpm (a ventoinha caiu para esse rpm), potenciaOutro (outro
     programa pôs essa potência), uso (o uso de agora) e recusar (o aplicar devolve esse código do driver). O aplicar
     limpa deFabrica, rpm e potenciaOutro, como o leitor de verdade, que grava tudo numa chamada só;
   - PAINEL_PLACA_LOG: cada pedido vira uma linha {t, id, op, chave, ajuste, placaJson} (placaJson = o conteúdo de
     PAINEL_PLACA_JSON naquele instante) e cada resposta, {t, respondeu: id};
   - PAINEL_PLACA_FALSA_DEMORA: espera antes de cada resposta (ms); PAINEL_PLACA_FALSA_PID: arquivo com o número do processo. */
const fs = require("fs");
const readline = require("readline");

const modo = process.env.PAINEL_PLACA_FALSA || "normal";
const demora = Number(process.env.PAINEL_PLACA_FALSA_DEMORA) || 0;
const arqEstado = process.env.PAINEL_PLACA_FALSA_ESTADO || "";
if (process.env.PAINEL_PLACA_FALSA_PID) fs.writeFileSync(process.env.PAINEL_PLACA_FALSA_PID, String(process.pid));

const CHAVE = "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&2B6F2D5B&0&00000019";
const PADRAO = { potencia: 0, tensao: 0, clock: 0, memoria: 2518, temporizacao: 0, curva: [[30, 15], [50, 32], [61, 49], [72, 66], [80, 100]], zeroRpm: 1 };
const INICIO = { potencia: -20, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, curva: [[30, 74], [50, 74], [61, 74], [72, 74], [80, 74]], zeroRpm: 0 };
const FAIXA = { potencia: [-30, 10], tensao: [-200, 0], clock: [-500, 1000], memoria: [2518, 3000], temporizacao: [0, 1] };

function lerEstado() {
  try { return { ...INICIO, ...JSON.parse(fs.readFileSync(arqEstado, "utf8")) }; } catch (e) { return { ...INICIO }; }
}
function gravarEstado(e) { if (arqEstado) fs.writeFileSync(arqEstado, JSON.stringify(e)); }
function anotar(o) {
  if (!process.env.PAINEL_PLACA_LOG) return;
  fs.appendFileSync(process.env.PAINEL_PLACA_LOG, JSON.stringify({ t: Date.now(), ...o }) + "\n");
}

const num = (atual, [min, max], padrao, offset) => ({ suporta: true, min, max, passo: 1, atual, padrao, ...(offset ? { offset: true } : {}) });
function placa(e) {
  const v = e.deFabrica ? { ...e, ...PADRAO } : { ...e };
  if (e.potenciaOutro != null) v.potencia = e.potenciaOutro;
  const igual = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const deFabrica = ["potencia", "tensao", "clock", "memoria", "temporizacao", "zeroRpm"].every((k) => v[k] === PADRAO[k]) && igual(v.curva, PADRAO.curva);
  return {
    chave: CHAVE, nome: "AMD Radeon RX 9070 XT", bus: 3, indice: 0, deFabrica, modo: 3,
    potencia: num(v.potencia, FAIXA.potencia, 0), tensao: num(v.tensao, FAIXA.tensao, 0, true), clock: num(v.clock, FAIXA.clock, 0, true),
    memoria: num(v.memoria, FAIXA.memoria, 2518), temporizacao: { suporta: true, atual: v.temporizacao, padrao: 0, opcoes: [0, 1] },
    ventoinha: { suporta: true, velMin: 15, velMax: 100, tempMin: 25, tempMax: 100, curva: v.curva, curvaPadrao: PADRAO.curva,
      zeroRpm: { suporta: true, atual: v.zeroRpm, padrao: 1 } },
    agora: { clockMHz: 2950, memoriaMHz: 2518, tensaoMv: 850, watts: 301, tempC: 44, quenteC: 61, memoriaC: 60,
      ventoinhaRpm: e.rpm != null ? e.rpm : 2552, ventoinhaPct: 74, usoPct: e.uso != null ? e.uso : 99 }
  };
}

function aplicar(p, fabrica) {
  const e = lerEstado();
  if (p.chave !== CHAVE) return { id: p.id, ok: false, erro: "sem-placa", msg: "a placa " + p.chave + " não foi encontrada" };
  if (e.recusar) return { id: p.id, ok: false, erro: "recusou", msg: "o driver recusou a gravação (" + e.recusar + ": precisa de administrador)" };
  const atual = e.deFabrica ? { ...e, ...PADRAO } : { ...e };
  if (e.potenciaOutro != null) atual.potencia = e.potenciaOutro;
  const alvo = fabrica ? { ...PADRAO } : { potencia: atual.potencia, tensao: atual.tensao, clock: atual.clock, memoria: atual.memoria,
    temporizacao: atual.temporizacao, curva: atual.curva, zeroRpm: atual.zeroRpm };
  for (const [k, v] of Object.entries(fabrica ? {} : p.ajuste || {})) {
    if (FAIXA[k]) {
      if (!Number.isInteger(v)) return { id: p.id, ok: false, erro: "pedido", msg: "valor que não é inteiro em " + k };
      if (v < FAIXA[k][0] || v > FAIXA[k][1]) return { id: p.id, ok: false, erro: "fora-da-faixa", msg: `${k} ${v} fora da faixa (de ${FAIXA[k][0]} a ${FAIXA[k][1]})` };
      alvo[k] = k === "memoria" && v % 2 ? v - 1 : v;   /* a memória vai de 2 em 2: o driver arredonda */
    } else if (k === "ventoinha") {
      if (v.modo === "auto") { alvo.curva = PADRAO.curva; alvo.zeroRpm = 1; }
      else if (v.modo === "fixa") { alvo.curva = atual.curva.map(([c]) => [c, v.pct]); alvo.zeroRpm = 0; }
      else if (v.modo === "curva") { alvo.curva = v.curva; alvo.zeroRpm = v.zeroRpm; }
      else return { id: p.id, ok: false, erro: "pedido", msg: "modo da ventoinha desconhecido" };
    } else return { id: p.id, ok: false, erro: "pedido", msg: "campo desconhecido: " + k };
  }
  const novo = { ...e, ...alvo };
  delete novo.deFabrica; delete novo.rpm; delete novo.potenciaOutro;
  gravarEstado(novo);
  const lida = placa(novo);
  const itens = {};
  for (const k of ["potencia", "tensao", "clock", "memoria", "temporizacao"]) itens[k] = { pedido: alvo[k], lido: lida[k].atual };
  itens.curva = { pedido: alvo.curva, lido: lida.ventoinha.curva };
  itens.zeroRpm = { pedido: alvo.zeroRpm, lido: lida.ventoinha.zeroRpm.atual };
  return { id: p.id, ok: true, itens, placa: lida };
}

function lixo(id) {
  const ruim = { suporta: true, min: "abc", max: 1e308, passo: 1, atual: -999999, padrao: 0, extra: "x" };
  const p = { chave: "x".repeat(5000), nome: 5, bus: 3, indice: 0, deFabrica: "sim", modo: 3, estranho: { a: 1 },
    potencia: ruim, tensao: ruim, clock: ruim, memoria: ruim, temporizacao: { suporta: true, atual: 0, padrao: 0, opcoes: [0, "1", 2e9] },
    ventoinha: { suporta: true, velMin: 15, velMax: 100, tempMin: 25, tempMax: 100, curva: [[30, 74], ["a", 74], [50]], curvaPadrao: [], zeroRpm: {} },
    agora: { clockMHz: 1e9, watts: 301, tempC: "quente", outro: 5 } };
  return { id, ok: true, afterburner: "sim", estranho: 1, msg: "y".repeat(5000), placas: Array.from({ length: 12 }, () => p) };
}

function responder(p) {
  if (modo === "sem-amd") return { id: p.id, ok: false, erro: "sem-amd", msg: "nenhuma placa AMD" };
  if (p.op === "ler") return modo === "lixo" ? lixo(p.id) : { id: p.id, ok: true, afterburner: false, placas: [placa(lerEstado())] };
  if (p.op === "aplicar") return aplicar(p, false);
  if (p.op === "fabrica") return aplicar(p, true);
  return { id: p.id, ok: false, erro: "pedido", msg: "pedido desconhecido: " + p.op };
}

const rl = readline.createInterface({ input: process.stdin });
let fila = Promise.resolve();
rl.on("line", (linha) => {
  let p = null;
  try { p = JSON.parse(linha); } catch (e) { p = null; }
  let placaJson = null;
  try { placaJson = process.env.PAINEL_PLACA_JSON ? fs.readFileSync(process.env.PAINEL_PLACA_JSON, "utf8") : null; } catch (e) { placaJson = null; }
  anotar({ id: p && p.id, op: p && p.op, chave: p && p.chave, ajuste: p && p.ajuste, placaJson });
  if (modo === "cai") process.exit(3);
  if (modo === "mudo") return;
  fila = fila.then(async () => {
    if (demora) await new Promise((ok) => setTimeout(ok, demora));
    const r = p ? responder(p) : { id: null, ok: false, erro: "pedido", msg: "o pedido não é JSON" };
    anotar({ respondeu: r.id });
    process.stdout.write(JSON.stringify(r) + "\r\n");
  });
});
rl.on("close", () => process.exit(0));
/* como o -Pai do leitor de verdade: sai quando quem o abriu acabou */
const pai = process.ppid;
setInterval(() => { if (process.ppid !== pai) process.exit(0); }, 500).unref();
