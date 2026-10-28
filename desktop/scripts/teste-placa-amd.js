"use strict";
/* Teste do processo do leitor da placa (desktop/placa-amd.js) com o leitor de mentira (placa-falsa.js): a fila, os prazos,
   as quedas, o sem AMD, o ocioso e a limpeza das respostas.
   Uso: node desktop/scripts/teste-placa-amd.js */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const pasta = fs.mkdtempSync(path.join(os.tmpdir(), "placa-amd-"));
const arq = (n) => path.join(pasta, n);
Object.assign(process.env, {
  PAINEL_PLACA_CMD: path.join(__dirname, "placa-falsa.js"), PAINEL_PLACA_PRAZO_MS: "300", PAINEL_PLACA_ESPERA_MS: "200",
  PAINEL_PLACA_OCIOSO_MS: "300", PAINEL_PLACA_FALSA_PID: arq("pid"), PAINEL_PLACA_LOG: arq("log"),
  PAINEL_PLACA_FALSA_ESTADO: arq("estado.json"), PAINEL_PLACA_JSON: arq("placa.json")
});
const A = require("../placa-amd.js");
const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
const vivo = (pid) => { try { process.kill(pid, 0); return true; } catch (e) { return false; } };
const pid = () => Number(fs.readFileSync(arq("pid"), "utf8"));
const registro = () => { try { return fs.readFileSync(arq("log"), "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l)); } catch (e) { return []; } };
async function ate(cond, ms = 3000) { const t0 = Date.now(); while (!cond()) { if (Date.now() - t0 > ms) return false; await esperar(20); } return true; }
function novo(modo, extra) {
  A._zerar();
  for (const k of ["PAINEL_PLACA_FALSA", "PAINEL_PLACA_FALSA_DEMORA"]) delete process.env[k];
  if (modo) process.env.PAINEL_PLACA_FALSA = modo;
  Object.assign(process.env, extra || {});
  try { fs.unlinkSync(arq("log")); } catch (e) {}
  try { fs.unlinkSync(arq("pid")); } catch (e) {}
}
const CHAVE = "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&2B6F2D5B&0&00000019";

(async () => {
  try {
    /* ler: a placa, e um processo só para dois pedidos */
    novo();
    const r1 = await A.pedir("ler");
    assert(r1.ok === true && r1.placas.length === 1 && r1.placas[0].chave === CHAVE && r1.placas[0].potencia.atual === -20, JSON.stringify(r1).slice(0, 300));
    const p1 = pid();
    const r2 = await A.pedir("ler");
    assert(r2.ok === true && pid() === p1 && A.estado().rodando, "o mesmo processo atende o segundo pedido");

    /* fila: dois pedidos ao mesmo tempo; o segundo só sai depois da resposta do primeiro */
    novo(null, { PAINEL_PLACA_FALSA_DEMORA: "120" });
    const [a, b] = await Promise.all([A.pedir("ler"), A.pedir("aplicar", { chave: CHAVE, ajuste: { potencia: -21 } })]);
    assert(a.ok && b.ok && b.itens.potencia.lido === -21, JSON.stringify([a, b]).slice(0, 300));
    const reg = registro();
    const i1 = reg.findIndex((x) => x.op === "ler"), r1i = reg.findIndex((x) => x.respondeu != null), i2 = reg.findIndex((x) => x.op === "aplicar");
    assert(i1 >= 0 && r1i > i1 && i2 > r1i, "o segundo pedido chegou antes da resposta do primeiro: " + JSON.stringify(reg));
    assert(reg[i2].id > reg[i1].id, "id crescente");
    fs.unlinkSync(arq("estado.json"));

    /* mudo: o prazo, o processo encerrado, a espera e um processo novo depois dela */
    novo("mudo");
    const m1 = await A.pedir("ler");
    assert(m1.ok === false && m1.erro === "prazo", JSON.stringify(m1));
    const pm = pid();
    assert(await ate(() => !vivo(pm), 1500), "o processo mudo foi encerrado");
    const m2 = await A.pedir("ler");
    assert(m2.ok === false && m2.erro === "espera" && /volta a tentar às \d\d:\d\d/.test(m2.msg), JSON.stringify(m2));
    await esperar(260);
    delete process.env.PAINEL_PLACA_FALSA;
    const m3 = await A.pedir("ler");
    assert(m3.ok === true && pid() !== pm, "depois da espera, um processo novo responde: " + JSON.stringify(m3).slice(0, 200));

    /* cai: o processo sai no meio do pedido */
    novo("cai");
    const c1 = await A.pedir("ler");
    assert(c1.ok === false && c1.erro === "caiu", JSON.stringify(c1));

    /* sem AMD: a resposta passa, o processo é encerrado e a próxima tentativa espera 4 vezes mais */
    novo("sem-amd");
    const s1 = await A.pedir("ler");
    assert(s1.ok === false && s1.erro === "sem-amd", JSON.stringify(s1));
    const ps = pid();
    assert(await ate(() => !vivo(ps), 1500), "o processo sem AMD foi encerrado");
    await esperar(300);
    const s2 = await A.pedir("ler");
    assert(s2.erro === "espera", "ainda esperando (4 x 200 ms): " + JSON.stringify(s2));
    await esperar(600);
    delete process.env.PAINEL_PLACA_FALSA;
    const s3 = await A.pedir("ler");
    assert(s3.ok === true, "depois da espera longa, responde: " + JSON.stringify(s3).slice(0, 200));

    /* ocioso: sem pedidos, o processo encerra */
    novo();
    await A.pedir("ler");
    const po = pid();
    assert(A.estado().rodando);
    await esperar(450);
    assert(!A.estado().rodando && await ate(() => !vivo(po), 1500), "o processo ocioso foi encerrado");

    /* lixo: números estragados, textos enormes e chaves estranhas não passam */
    novo("lixo");
    const l = await A.pedir("ler");
    assert(l.ok === true && l.afterburner === false && !("estranho" in l) && l.msg.length <= 300, JSON.stringify(l).slice(0, 300));
    assert(l.placas.length === 8, "no máximo 8 placas: " + l.placas.length);
    const p = l.placas[0];
    assert(p.chave.length <= 300 && p.nome === "" && p.deFabrica === false && !("estranho" in p), JSON.stringify(p).slice(0, 300));
    assert(p.potencia.min === null && p.potencia.max === null && p.potencia.atual === null && p.potencia.padrao === 0 && !("extra" in p.potencia), JSON.stringify(p.potencia));
    assert(JSON.stringify(p.temporizacao.opcoes) === "[0]", JSON.stringify(p.temporizacao));
    assert(JSON.stringify(p.ventoinha.curva) === "[[30,74]]" && JSON.stringify(p.ventoinha.zeroRpm) === '{"suporta":false,"atual":null,"padrao":null}', JSON.stringify(p.ventoinha));
    assert(p.agora.clockMHz === null && p.agora.watts === 301 && p.agora.tempC === null && !("outro" in p.agora), JSON.stringify(p.agora));

    /* parar: encerra o processo */
    novo();
    await A.pedir("ler");
    const pp = pid();
    A.parar();
    assert(!A.estado().rodando && await ate(() => !vivo(pp), 1500), "parar encerrou o processo");

    console.log("ok");
  } catch (e) {
    console.error("FALHOU:", e && e.stack || e);
    process.exitCode = 1;
  } finally {
    A.parar();
    fs.rmSync(pasta, { recursive: true, force: true });
  }
})();
