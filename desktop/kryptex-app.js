"use strict";
/* App da Kryptex deste PC. O app da Kryptex do Windows tem um serviço (KryptexService.exe) que responde em
   http://localhost:8107, sem senha e só dentro do computador: é o que o próprio app usa para desenhar a janela dele.
   O painel usa só estas 5 leituras e estas 2 ações (pausar por um tempo e voltar a minerar). Daqui só sai o que o painel
   usa: nada de nome de usuário, e-mail ou códigos. No teste, o endereço vem de PAINEL_KRYPTEX_LOCAL. */
const http = require("http");

const LEITURAS = ["/devices", "/balance", "/pause", "/currency-rates", "/configuration"];
/* 15 minutos (proteção de temperatura), 1, 3 e 8 horas e "até eu voltar" (31 dias, como no menu do app da Kryptex) */
const PAUSAS = [15, 60, 180, 480, 44640];
const LIMITE_MS = 4000, LIMITE_BYTES = 2 * 1024 * 1024;
const base = () => String(process.env.PAINEL_KRYPTEX_LOCAL || "http://127.0.0.1:8107").replace(/\/+$/, "");
const erro = (tipo, msg) => Object.assign(new Error(msg), { tipo });

function pedir(metodo, caminho, corpo) {
  return new Promise((ok, nao) => {
    let u;
    try { u = new URL(base() + caminho); } catch (e) { nao(erro("fechado", "endereço do app da Kryptex inválido")); return; }
    const dados = corpo == null ? null : Buffer.from(JSON.stringify(corpo));
    const cab = { Accept: "application/json" };
    if (dados) { cab["Content-Type"] = "application/json"; cab["Content-Length"] = dados.length; }
    let fim = false;
    const terminar = (f, v) => { if (fim) return; fim = true; clearTimeout(prazo); f(v); };
    const req = http.request(u, { method: metodo, headers: cab }, (res) => {
      const partes = []; let n = 0;
      res.on("data", (c) => {
        n += c.length;
        if (n > LIMITE_BYTES) { terminar(nao, erro("formato", "resposta grande demais")); req.destroy(); return; }
        partes.push(c);
      });
      res.on("end", () => {
        if (res.statusCode < 200 || res.statusCode >= 300) { terminar(nao, erro("formato", `o app da Kryptex respondeu ${res.statusCode}`)); return; }
        const txt = Buffer.concat(partes).toString("utf8");
        if (!txt.trim()) { terminar(ok, null); return; }
        try { terminar(ok, JSON.parse(txt)); } catch (e) { terminar(nao, erro("formato", "resposta do app da Kryptex que não é JSON")); }
      });
      res.on("error", () => terminar(nao, erro("fechado", "a conexão com o app da Kryptex caiu")));
    });
    const prazo = setTimeout(() => { terminar(nao, erro("tempo", "o app da Kryptex demorou demais para responder")); req.destroy(); }, LIMITE_MS);
    req.on("error", (e) => terminar(nao, erro("fechado", e && e.code === "ECONNREFUSED" ? "o app da Kryptex não está aberto neste PC" : "não deu para falar com o app da Kryptex")));
    if (dados) req.write(dados);
    req.end();
  });
}

/* ---------- campos ---------- */
const num = (v) => { const x = typeof v === "number" ? v : (typeof v === "string" && v.trim() !== "" ? Number(v) : NaN); return Number.isFinite(x) ? x : null; };
const pos = (v) => { const x = num(v); return x != null && x > 0 ? x : null; };
const CAMPOS = {
  temp: ["core_temperature", "temperature", "gpu_temperature", "temperature_gpu"],
  tempMem: ["memory_temperature", "temperature_memory", "mem_temperature", "vram_temperature"],
  tempHot: ["hotspot_temperature", "junction_temperature", "temperature_hotspot"],
  watts: ["power_usage", "power_draw", "power", "watts", "board_power", "power_consumption"]
};
const CONHECIDOS = new Set([...Object.values(CAMPOS).flat(), "id", "pci_address", "core_clock", "memory_clock", "fan_speed", "fan_speed_percent", "fan_speed_rpm", "rebar", "driver_version"]);
const primeiro = (o, nomes) => { for (const k of nomes) { const x = pos(o[k]); if (x != null) return x; } return null; };
/* hora em ms: número em segundos ou ms, ou data escrita */
function ms(v) {
  if (v == null || v === "" || v === false) return null;
  if (typeof v === "number") return v > 1e12 ? v : v > 1e9 ? v * 1000 : null;
  const t = Date.parse(String(v));
  return Number.isFinite(t) ? t : null;
}

function placaDe(d, pausado, desconhecidos) {
  const dev = (d && d.device) || {}, rd = (d && d.reading) || {};
  const tipo = String(dev.type || "").toLowerCase() === "cpu" ? "cpu" : "gpu";
  const desativada = !!(dev.configuration && dev.configuration.disabled);
  let ativo = null, melhor = 0;
  for (const comb of Array.isArray(d && d.algorithm_combinations) ? d.algorithm_combinations : []) {
    const alg = (comb && Array.isArray(comb.algorithms) && comb.algorithms[0]) || {};
    for (const m of (comb && Array.isArray(comb.miners) ? comb.miners : [])) {
      const st = (m && m.stats) || {}, cas = Array.isArray(st.coin_algorithms) ? st.coin_algorithms : [];
      const hash = cas.reduce((a, c) => a + (pos(c && c.local_hashrate) || pos(c && c.hashrate) || 0), 0);
      const rend = pos(st.profitability) ?? cas.reduce((a, c) => a + (pos(c && c.profitability) || 0), 0);
      if (rend > melhor) melhor = rend;
      if (!(hash > 0 || (num(st.process_count) || 0) > 0)) continue;
      if (!ativo || hash > ativo.hash) ativo = { hash, rend, moeda: String(alg.coin || "").toUpperCase().slice(0, 12), algoritmo: String(alg.algorithm || "").slice(0, 32),
        minerador: String((m && m.name) || "").slice(0, 32), erros1h: num(st.error_count_1h) || 0 };
    }
  }
  for (const [k, v] of Object.entries(rd)) if (!CONHECIDOS.has(k) && num(v) != null && desconhecidos.size < 30) desconhecidos.add(String(k).slice(0, 40));
  const fan = num(rd.fan_speed);
  return {
    id: String(dev.id || (d && d.id) || "").slice(0, 64), tipo, nome: String(dev.name || "").slice(0, 80), desativada,
    minerando: !!ativo && !pausado && !desativada,
    moeda: ativo ? ativo.moeda : "", algoritmo: ativo ? ativo.algoritmo : "", minerador: ativo ? ativo.minerador : "",
    hash: ativo ? ativo.hash : 0, rendimentoUsd: ativo ? ativo.rend : melhor,
    temp: primeiro(rd, CAMPOS.temp), tempMem: primeiro(rd, CAMPOS.tempMem), tempHot: primeiro(rd, CAMPOS.tempHot), watts: primeiro(rd, CAMPOS.watts),
    ventoinha: pos(rd.fan_speed_percent) ?? (fan != null && fan > 0 && fan <= 100 ? fan : null),
    rpm: pos(rd.fan_speed_rpm) ?? (fan != null && fan > 100 ? fan : null),
    erros1h: ativo ? ativo.erros1h : 0
  };
}

const chaves = (o) => (o && typeof o === "object" && !Array.isArray(o) ? Object.keys(o).slice(0, 30).map((k) => String(k).slice(0, 40)) : []);

/* ---------- o que o painel chama ---------- */
async function ler() {
  const quando = Date.now();
  const r = await Promise.allSettled(LEITURAS.map((c) => pedir("GET", c)));
  const [devices, balance, pause, rates, conf] = r.map((x) => (x.status === "fulfilled" ? x.value : null));
  if (r[0].status === "rejected") { const e = r[0].reason || {}; return { ok: false, erro: e.tipo || "fechado", msg: String(e.message || e).slice(0, 160) }; }
  if (!Array.isArray(devices)) return { ok: false, erro: "formato", msg: "o app da Kryptex não mandou a lista de placas" };
  /* o formato do GET /pause com a placa pausada ainda não foi visto no app de verdade: aceita pause/paused/is_paused,
     "pause" como objeto e a hora de voltar no futuro */
  const po = pause && typeof pause === "object" ? pause : {}, sub = po.pause && typeof po.pause === "object" ? po.pause : {};
  const pa = [po, sub].flatMap((o) => ["pause_until", "paused_until", "until", "resume_at"].map((k) => ms(o[k]))).find((x) => x != null) ?? null;
  const pausado = [po.pause, po.paused, po.is_paused, sub.paused].some((v) => v === true) || (pa != null && pa > quando);
  const tx = (rates && typeof rates.rates === "object" && rates.rates) || rates || {};
  const desconhecidos = new Set();
  return {
    ok: true, quando, pausado, pausaAte: pausado ? (pa ?? null) : null,
    moeda: String((conf && conf.currency) || "").toUpperCase().slice(0, 8), computador: String((conf && conf.computer_name) || "").slice(0, 60),
    cotacoes: { brl: pos(tx.brl), btc: pos(tx.btc) },
    saldoBtc: balance && num(balance.total) != null && num(balance.total) >= 0 ? num(balance.total) : null,
    placas: devices.slice(0, 16).map((d) => placaDe(d, pausado, desconhecidos)),
    desconhecidos: [...desconhecidos],
    /* para acertar a leitura com o app de verdade: só os nomes das chaves de cada resposta, nunca os valores */
    formato: { pause: chaves(pause), balance: chaves(balance), cotacoes: chaves(tx), config: chaves(conf) }
  };
}
async function pausar(minutos) {
  const m = Number(minutos);
  if (typeof minutos !== "number" || !PAUSAS.includes(m)) throw new Error("tempo de pausa não permitido");
  try { await pedir("PUT", "/pause", { pause_for: m * 60000 }); }
  catch (e) { return { ok: false, feito: false, erro: e.tipo || "fechado", msg: String(e.message || e).slice(0, 160) }; }
  return { ...(await ler()), feito: true };   /* feito: o app aceitou a pausa (mesmo se a leitura logo depois falhar) */
}
async function voltar() {
  try { await pedir("PUT", "/pause", { pause: false }); }
  catch (e) { return { ok: false, feito: false, erro: e.tipo || "fechado", msg: String(e.message || e).slice(0, 160) }; }
  return { ...(await ler()), feito: true };
}

module.exports = { ler, pausar, voltar, PAUSAS };
