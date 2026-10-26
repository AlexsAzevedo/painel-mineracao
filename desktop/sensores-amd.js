"use strict";
/* Sensores das placas de vídeo AMD (Windows). O leitor sensores-amd.ps1 (PowerShell escondido, pela biblioteca ADL que
   vem com o driver da AMD) fica rodando e manda uma leitura a cada 10 segundos; aqui ficam as dos últimos 50 segundos
   (menos que o minuto entre as leituras do painel: a mesma amostra não entra em duas leituras seguidas). Só lê.
   juntar(leitura) completa a leitura do app da Kryptex (kryptex-app.js) com o que ela não traz nas placas AMD: a
   temperatura da memória e do ponto mais quente, o consumo da placa e as rotações da ventoinha.
   O leitor começa na primeira pergunta (a leitura do app da Kryptex, a cada minuto) e para depois de 5 minutos sem
   ninguém perguntar. Se ele cair, ou ficar 2 minutos sem mandar leitura boa (o ADL parou de responder depois de uma
   atualização do driver, ou ele travou), liga de novo depois de 1, 5 e 30 minutos; sem placa AMD ou sem o driver, só
   confere de novo depois de 1 hora.
   No teste: PAINEL_SENSORES_CMD (um script de Node que imprime as linhas) no lugar do PowerShell, e
   PAINEL_SENSORES_INTERVALO_MS, PAINEL_SENSORES_ESPERA_MS, PAINEL_SENSORES_OCIOSO_MS e PAINEL_SENSORES_MUDO_MS para os
   tempos. */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const INTERVALO_S = 10, JANELA = 50e3;
const num = (v, d) => (Number(process.env[v]) > 0 ? Number(process.env[v]) : d);
const ESPERAS = () => { const t = num("PAINEL_SENSORES_ESPERA_MS", 0); return t ? [t, t, t] : [60e3, 5 * 60e3, 30 * 60e3]; };
const ESPERA_SEM_AMD = () => num("PAINEL_SENSORES_ESPERA_MS", 0) * 4 || 60 * 60e3;
const OCIOSO = () => num("PAINEL_SENSORES_OCIOSO_MS", 5 * 60e3);
const MUDO = () => num("PAINEL_SENSORES_MUDO_MS", 2 * 60e3);
/* o que é possível numa placa de vídeo; fora disso, o número é lixo (consumo 0 é sensor sem valor, não medida) */
const FAIXAS = { borda: [-20, 150], memoria: [-20, 150], quente: [-20, 150], placaW: [1, 1500], rpm: [0, 10000], vent: [0, 100], uso: [0, 100] };

let proc = null, buffer = "", leituras = [], falhas = 0, proximaTentativa = 0, ultimoPedido = 0, timerOcioso = null, inicio = 0, ultimaBoa = 0;
let estado = { erro: "", msg: "", metodo: "" };

function comando() {
  const teste = process.env.PAINEL_SENSORES_CMD;
  if (teste) return { cmd: process.execPath, args: [teste], env: { ...process.env, ELECTRON_RUN_AS_NODE: "1" } };
  if (process.platform !== "win32") return null;
  const ps1 = [process.resourcesPath && path.join(process.resourcesPath, "sensores-amd.ps1"), path.join(__dirname, "sensores-amd.ps1")]
    .find((p) => { try { return !!p && fs.existsSync(p); } catch (e) { return false; } });
  if (!ps1) return null;
  const ps = path.join(process.env.SystemRoot || "C:\\Windows", "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
  return { cmd: ps, args: ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", ps1, "-Intervalo", String(INTERVALO_S), "-Pai", String(process.pid)], env: process.env };
}

function limpo(p) {
  const o = { bus: Number.isInteger(p.bus) ? p.bus : null, nome: String(p.nome || "").slice(0, 80), metodo: String(p.metodo || "").slice(0, 16) };
  for (const [k, [min, max]] of Object.entries(FAIXAS)) { const v = Number(p[k]); o[k] = p[k] != null && Number.isFinite(v) && v >= min && v <= max ? v : null; }
  return o;
}

function receber(linha) {
  let o; try { o = JSON.parse(linha); } catch (e) { return; }
  if (!o || typeof o !== "object") return;
  if (o.ok === true && Array.isArray(o.placas)) {
    const placas = o.placas.slice(0, 8).map(limpo);
    leituras.push({ t: Date.now(), placas });
    const lim = Date.now() - JANELA; leituras = leituras.filter((l) => l.t >= lim);
    falhas = 0; ultimaBoa = Date.now(); estado = { erro: "", msg: "", metodo: (placas.find((p) => p.metodo) || {}).metodo || "" };
    return;
  }
  if (o.ok === false) {
    const erro = String(o.erro || "falhou").slice(0, 24);
    estado = { erro, msg: String(o.msg || "").slice(0, 160), metodo: "" };
    /* sem placa AMD ou sem o driver: não adianta continuar perguntando */
    if (erro === "sem-amd" || erro === "sem-adl" || erro === "falhou") { proximaTentativa = Date.now() + ESPERA_SEM_AMD(); encerrar(); }
  }
}

function encerrar() {
  const p = proc; proc = null; buffer = "";
  if (p) { try { p.kill(); } catch (e) {} }
}

function iniciar() {
  if (proc || Date.now() < proximaTentativa) return;
  const c = comando();
  if (!c) { estado = { erro: "indisponivel", msg: "sem leitor de sensores neste computador", metodo: "" }; return; }
  let p;
  try { p = spawn(c.cmd, c.args, { env: c.env, windowsHide: true, stdio: ["ignore", "pipe", "ignore"] }); }
  catch (e) { caiu(String(e && e.message || e)); return; }
  proc = p; buffer = ""; inicio = Date.now(); ultimaBoa = 0;
  p.stdout.setEncoding("utf8");
  p.stdout.on("data", (d) => {
    if (proc !== p) return;
    buffer += d;
    let i;
    while ((i = buffer.indexOf("\n")) >= 0) { const linha = buffer.slice(0, i).trim(); buffer = buffer.slice(i + 1); if (linha) receber(linha); if (proc !== p) return; }
    if (buffer.length > 1e6) buffer = "";
  });
  p.on("error", (e) => { if (proc === p) { proc = null; caiu(String(e && e.message || e)); } });
  p.on("exit", (codigo) => { if (proc === p) { proc = null; caiu(`o leitor parou (${codigo})`); } });
}

/* o leitor parou sem ninguém pedir: liga de novo depois de 1, 5 e 30 minutos */
function caiu(msg) {
  const e = ESPERAS(); proximaTentativa = Date.now() + e[Math.min(falhas, e.length - 1)]; falhas++;
  if (!estado.erro) estado = { erro: "parou", msg: String(msg).slice(0, 160), metodo: "" };
}

function armarOcioso() {
  if (timerOcioso) return;
  timerOcioso = setInterval(() => {
    if (Date.now() - ultimoPedido >= OCIOSO()) { encerrar(); clearInterval(timerOcioso); timerOcioso = null; }
  }, Math.min(60e3, Math.max(50, OCIOSO() / 4)));
  if (timerOcioso.unref) timerOcioso.unref();
}

/* as leituras dos últimos 50 s de cada placa: a temperatura mais alta, o consumo médio, a ventoinha da última */
function ultima() {
  ultimoPedido = Date.now();
  /* vivo, mas sem leitura boa há um tempo: encerra e liga de novo depois da espera (o ADL volta a responder num leitor novo) */
  if (proc && Date.now() - Math.max(inicio, ultimaBoa) > MUDO()) { encerrar(); caiu("o leitor parou de mandar leituras"); }
  iniciar(); armarOcioso();
  const lim = Date.now() - JANELA, rec = leituras.filter((l) => l.t >= lim);
  if (!rec.length) return { ok: false, erro: estado.erro || "esperando", msg: estado.msg };
  const porBus = new Map();
  for (const l of rec) for (const p of l.placas) { const k = p.bus != null ? "b" + p.bus : "n" + p.nome; if (!porBus.has(k)) porBus.set(k, []); porBus.get(k).push(p); }
  const placas = [...porBus.values()].map((ps) => {
    const vals = (k) => ps.map((x) => x[k]).filter((v) => v != null);
    const max = (k) => { const v = vals(k); return v.length ? Math.max(...v) : null; };
    const media = (k) => { const v = vals(k); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
    const ultimo = (k) => { const v = vals(k); return v.length ? v[v.length - 1] : null; };
    const u = ps[ps.length - 1];
    return { bus: u.bus, nome: u.nome, borda: max("borda"), memoria: max("memoria"), quente: max("quente"), placaW: media("placaW"),
      rpm: ultimo("rpm"), vent: ultimo("vent"), uso: media("uso"), n: ps.length };
  });
  return { ok: true, quando: rec[rec.length - 1].t, metodo: estado.metodo, placas };
}

/* completa a leitura do app da Kryptex nas placas AMD (pelo barramento PCI; sem ele, pelo nome, se só houver uma) */
function juntar(l) {
  if (!l || !l.ok || !Array.isArray(l.placas)) return l;
  const amd = l.placas.filter((p) => p && p.tipo === "gpu" && p.fabricante === "amd");
  if (!amd.length) return l;
  const s = ultima();
  l.sensores = { ok: !!s.ok, erro: s.ok ? "" : s.erro || "", metodo: s.ok ? s.metodo || "" : "" };
  if (!s.ok) return l;
  for (const p of amd) {
    const mesmoNome = s.placas.filter((x) => x.nome && x.nome === p.nome);
    const x = (p.bus != null && s.placas.find((q) => q.bus === p.bus)) || (mesmoNome.length === 1 ? mesmoNome[0] : null);
    if (!x) continue;
    if (p.temp == null && x.borda != null) p.temp = x.borda;
    if (p.tempMem == null && x.memoria != null) p.tempMem = x.memoria;
    if (p.tempHot == null && x.quente != null) p.tempHot = x.quente;
    if (p.watts == null && x.placaW != null) p.watts = Math.round(x.placaW);
    if (p.rpm == null && x.rpm != null) p.rpm = x.rpm;
  }
  return l;
}

function parar() { encerrar(); if (timerOcioso) { clearInterval(timerOcioso); timerOcioso = null; } }
function estadoLeitor() { return { rodando: !!proc, ...estado }; }
/* só para o teste: esquece as leituras e as esperas */
function _zerar() { parar(); leituras = []; falhas = 0; proximaTentativa = 0; inicio = ultimaBoa = 0; estado = { erro: "", msg: "", metodo: "" }; }

module.exports = { ultima, juntar, parar, estado: estadoLeitor, _zerar };
