"use strict";
/* O processo do leitor da placa (placa-amd.ps1, PowerShell escondido, pela biblioteca ADL que vem com o driver da AMD).
   pedir(op, dados) manda um pedido ("ler", "aplicar" com {chave, ajuste}, "fabrica" com {chave}) e devolve a resposta,
   limpa (só as chaves do protocolo, números finitos de até 100000, textos de até 300 caracteres, até 8 placas). Nunca
   rejeita: um problema vira {ok: false, erro, msg}, com o erro do leitor ou um destes:
   - indisponivel: sem leitor neste computador (fora do Windows, ou sem o placa-amd.ps1);
   - prazo: o leitor não respondeu a tempo (60 s no primeiro pedido, que compila o C#; 20 s nos outros; 30 s no de
     fábrica) e foi encerrado;
   - caiu: o leitor parou no meio do pedido;
   - espera: depois de uma queda, o leitor só volta depois de 1, 5 e 30 minutos; sem placa AMD ou sem o driver, 1 hora.
   Um pedido de cada vez, numa fila. Sem pedidos por 5 minutos, o leitor encerra.
   No teste: PAINEL_PLACA_CMD (um script de Node no lugar do PowerShell), PAINEL_PLACA_PRAZO_MS (todos os prazos),
   PAINEL_PLACA_ESPERA_MS (as esperas; a do sem AMD é 4 vezes isso) e PAINEL_PLACA_OCIOSO_MS. */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const num = (v, d) => (Number(process.env[v]) > 0 ? Number(process.env[v]) : d);
const PRAZO_PRIMEIRO = () => num("PAINEL_PLACA_PRAZO_MS", 60e3);
const PRAZO = () => num("PAINEL_PLACA_PRAZO_MS", 20e3);
const PRAZO_FABRICA = () => num("PAINEL_PLACA_PRAZO_MS", 30e3);
const ESPERAS = () => { const t = num("PAINEL_PLACA_ESPERA_MS", 0); return t ? [t, t, t] : [60e3, 5 * 60e3, 30 * 60e3]; };
const ESPERA_SEM_AMD = () => num("PAINEL_PLACA_ESPERA_MS", 0) * 4 || 60 * 60e3;
const OCIOSO = () => num("PAINEL_PLACA_OCIOSO_MS", 5 * 60e3);

let proc = null, buffer = "", pendente = null, proximoId = 1, respondeu = false;
let falhas = 0, proxima = 0, ultimoPedido = 0, timerOcioso = null, fila = Promise.resolve();
let estado = { erro: "", msg: "" };

/* ---------- a limpeza das respostas ---------- */
const LIM = 100000;
const n = (v) => (typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= LIM ? v : null);
const t = (v) => (typeof v === "string" ? v.slice(0, 300) : "");
const sim = (v) => v === true;
const obj = (v) => (v && typeof v === "object" && !Array.isArray(v) ? v : null);
const numeros = (l) => (Array.isArray(l) ? l.map(n).filter((x) => x !== null).slice(0, 16) : []);
const pares = (l) => (Array.isArray(l) ? l.filter((p) => Array.isArray(p) && p.length === 2 && n(p[0]) !== null && n(p[1]) !== null).slice(0, 5).map((p) => [p[0], p[1]]) : []);
function item(o) {
  o = obj(o);
  if (!o || o.suporta !== true) return { suporta: false };
  const r = { suporta: true, min: n(o.min), max: n(o.max), passo: n(o.passo), atual: n(o.atual), padrao: n(o.padrao) };
  if (typeof o.offset === "boolean") r.offset = o.offset;
  return r;
}
function temporizacao(o) {
  o = obj(o);
  return !o || o.suporta !== true ? { suporta: false } : { suporta: true, atual: n(o.atual), padrao: n(o.padrao), opcoes: numeros(o.opcoes) };
}
function ventoinha(o) {
  o = obj(o);
  if (!o || o.suporta !== true) return { suporta: false };
  const z = obj(o.zeroRpm) || {};
  return { suporta: true, velMin: n(o.velMin), velMax: n(o.velMax), tempMin: n(o.tempMin), tempMax: n(o.tempMax),
    curva: pares(o.curva), curvaPadrao: pares(o.curvaPadrao), zeroRpm: { suporta: sim(z.suporta), atual: n(z.atual), padrao: n(z.padrao) } };
}
const AGORA = ["clockMHz", "memoriaMHz", "tensaoMv", "watts", "tempC", "quenteC", "memoriaC", "ventoinhaRpm", "ventoinhaPct", "usoPct"];
function agora(o) {
  const r = {};
  o = obj(o);
  if (o) for (const k of AGORA) if (k in o) r[k] = n(o[k]);
  return r;
}
function placa(p) {
  p = obj(p);
  if (!p) return null;
  return { chave: t(p.chave), nome: t(p.nome), bus: n(p.bus), indice: n(p.indice), deFabrica: sim(p.deFabrica), modo: n(p.modo),
    potencia: item(p.potencia), tensao: item(p.tensao), clock: item(p.clock), memoria: item(p.memoria),
    temporizacao: temporizacao(p.temporizacao), ventoinha: ventoinha(p.ventoinha), agora: agora(p.agora) };
}
function itens(o) {
  const r = {};
  o = obj(o);
  if (!o) return r;
  for (const k of ["potencia", "tensao", "clock", "memoria", "temporizacao", "zeroRpm"]) {
    const x = obj(o[k]);
    if (x) r[k] = { pedido: n(x.pedido), lido: n(x.lido) };
  }
  const c = obj(o.curva);
  if (c) r.curva = { pedido: pares(c.pedido), lido: pares(c.lido) };
  return r;
}
function limpar(o) {
  o = obj(o);
  if (!o) return { ok: false, erro: "falhou", msg: "resposta estranha do leitor da placa" };
  if (o.ok !== true) return { ok: false, erro: t(o.erro) || "falhou", msg: t(o.msg) };
  const r = { ok: true };
  if (Array.isArray(o.placas)) { r.afterburner = sim(o.afterburner); r.placas = o.placas.slice(0, 8).map(placa).filter(Boolean); }
  if (o.itens !== undefined) r.itens = itens(o.itens);
  if (o.placa !== undefined) r.placa = placa(o.placa);
  if (typeof o.msg === "string") r.msg = t(o.msg);
  return r;
}

/* ---------- o processo ---------- */
function comando() {
  const teste = process.env.PAINEL_PLACA_CMD;
  if (teste) return { cmd: process.execPath, args: [teste], env: { ...process.env, ELECTRON_RUN_AS_NODE: "1" } };
  if (process.platform !== "win32") return null;
  const ps1 = [process.resourcesPath && path.join(process.resourcesPath, "placa-amd.ps1"), path.join(__dirname, "placa-amd.ps1")]
    .find((p) => { try { return !!p && fs.existsSync(p); } catch (e) { return false; } });
  if (!ps1) return null;
  const ps = path.join(process.env.SystemRoot || "C:\\Windows", "System32", "WindowsPowerShell", "v1.0", "powershell.exe");
  return { cmd: ps, args: ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", ps1, "-Pai", String(process.pid)], env: process.env };
}

function encerrar() {
  const p = proc; proc = null; buffer = ""; respondeu = false;
  if (p) { try { p.kill(); } catch (e) {} }
}

function terminarPendente(r) {
  if (!pendente) return;
  const x = pendente; pendente = null;
  clearTimeout(x.timer);
  x.resolve(r);
}

/* o leitor parou sem querer: só volta depois de 1, 5 e 30 minutos */
function caiu(msg) {
  const e = ESPERAS();
  proxima = Date.now() + e[Math.min(falhas, e.length - 1)];
  falhas++;
  estado = { erro: "caiu", msg: String(msg).slice(0, 160) };
}

function receber(linha) {
  let o;
  try { o = JSON.parse(linha); } catch (e) { return; }
  if (!o || typeof o !== "object" || !pendente || o.id !== pendente.id) return;
  respondeu = true;
  const r = limpar(o);
  if (!r.ok && (r.erro === "sem-amd" || r.erro === "sem-adl")) {
    /* sem placa AMD ou sem o driver: não adianta continuar perguntando */
    proxima = Date.now() + ESPERA_SEM_AMD();
    estado = { erro: r.erro, msg: r.msg };
    encerrar();
  } else { falhas = 0; estado = { erro: "", msg: "" }; }
  terminarPendente(r);
}

function iniciar() {
  const c = comando();
  if (!c) { estado = { erro: "indisponivel", msg: "sem leitor da placa neste computador" }; return false; }
  let p;
  try { p = spawn(c.cmd, c.args, { env: c.env, windowsHide: true, stdio: ["pipe", "pipe", "ignore"] }); }
  catch (e) { caiu(String((e && e.message) || e)); return false; }
  proc = p; buffer = ""; respondeu = false;
  p.stdout.setEncoding("utf8");
  p.stdout.on("data", (d) => {
    if (proc !== p) return;
    buffer += d;
    let i;
    while ((i = buffer.indexOf("\n")) >= 0) {
      const linha = buffer.slice(0, i).trim();
      buffer = buffer.slice(i + 1);
      if (linha) receber(linha);
      if (proc !== p) return;
    }
    if (buffer.length > 4e6) buffer = "";
  });
  p.stdin.on("error", () => {});   /* escrever num leitor que acabou de cair */
  const parou = (msg) => {
    if (proc !== p) return;
    proc = null; buffer = "";
    caiu(msg);
    terminarPendente({ ok: false, erro: "caiu", msg: "o leitor da placa parou" });
  };
  p.on("error", (e) => parou(String((e && e.message) || e)));
  p.on("exit", (codigo) => parou(`o leitor da placa parou (${codigo})`));
  return true;
}

function armarOcioso() {
  if (timerOcioso) return;
  timerOcioso = setInterval(() => {
    if (!pendente && Date.now() - ultimoPedido >= OCIOSO()) { encerrar(); clearInterval(timerOcioso); timerOcioso = null; }
  }, Math.min(60e3, Math.max(50, OCIOSO() / 4)));
  if (timerOcioso.unref) timerOcioso.unref();
}

const hhmm = (ms) => new Date(ms).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

function executar(op, dados) {
  ultimoPedido = Date.now();
  armarOcioso();
  if (Date.now() < proxima) return Promise.resolve({ ok: false, erro: "espera", msg: "o leitor da placa volta a tentar às " + hhmm(proxima) });
  if (!proc && !iniciar()) return Promise.resolve({ ok: false, erro: estado.erro || "indisponivel", msg: estado.msg || "" });
  const p = proc, id = proximoId++;
  const prazo = !respondeu ? PRAZO_PRIMEIRO() : op === "fabrica" ? PRAZO_FABRICA() : PRAZO();
  return new Promise((resolve) => {
    pendente = { id, resolve, timer: setTimeout(() => {
      if (!pendente || pendente.id !== id) return;
      encerrar();
      caiu("o leitor da placa não respondeu");
      terminarPendente({ ok: false, erro: "prazo", msg: "o leitor da placa não respondeu" });
    }, prazo) };
    try { p.stdin.write(JSON.stringify({ ...(dados || {}), id, op }) + "\n"); }
    catch (e) { encerrar(); caiu(String((e && e.message) || e)); terminarPendente({ ok: false, erro: "caiu", msg: "o leitor da placa parou" }); }
  });
}

/* um pedido de cada vez; nunca rejeita */
function pedir(op, dados) {
  const r = fila.then(() => executar(String(op || ""), dados))
    .catch((e) => ({ ok: false, erro: "falhou", msg: String((e && e.message) || e).slice(0, 160) }));
  fila = r.then(() => {}, () => {});
  return r;
}

function parar() {
  encerrar();
  terminarPendente({ ok: false, erro: "caiu", msg: "o leitor da placa foi encerrado" });
  if (timerOcioso) { clearInterval(timerOcioso); timerOcioso = null; }
}
function estadoLeitor() { return { rodando: !!proc, erro: estado.erro, msg: estado.msg, proxima }; }
/* só para o teste: esquece as quedas e as esperas */
function _zerar() { parar(); falhas = 0; proxima = 0; estado = { erro: "", msg: "" }; fila = Promise.resolve(); }

module.exports = { pedir, estado: estadoLeitor, parar, _zerar };
