"use strict";
/* Teste do módulo dos sensores AMD (desktop/sensores-amd.js) com o leitor de mentira (sensores-falso.js).
   Uso: node desktop/scripts/teste-sensores-amd.js */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const pasta = fs.mkdtempSync(path.join(os.tmpdir(), "sensores-amd-"));
const arqPid = path.join(pasta, "pid");
Object.assign(process.env, {
  PAINEL_SENSORES_CMD: path.join(__dirname, "sensores-falso.js"), PAINEL_SENSORES_INTERVALO_MS: "40",
  PAINEL_SENSORES_ESPERA_MS: "300", PAINEL_SENSORES_OCIOSO_MS: "600", PAINEL_SENSORES_MUDO_MS: "400", SENSORES_FALSO_PID: arqPid
});
const S = require("../sensores-amd.js");
const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
const vivo = (pid) => { try { process.kill(pid, 0); return true; } catch (e) { return false; } };
const pidAtual = () => Number(fs.readFileSync(arqPid, "utf8"));
async function ate(cond, ms = 3000) { const t0 = Date.now(); while (!cond()) { if (Date.now() - t0 > ms) return false; await esperar(20); } return true; }

/* a leitura do app da Kryptex, como kryptex-app.js devolve (só o que importa aqui) */
const leituraKx = () => ({ ok: true, placas: [
  { id: "2", tipo: "gpu", fabricante: "amd", bus: 3, nome: "AMD Radeon RX 9070 XT", minerando: true, temp: 45, tempMem: null, tempHot: null, watts: null, ventoinha: 81, rpm: null },
  { id: "9", tipo: "gpu", fabricante: "nvidia", bus: 1, nome: "NVIDIA GeForce RTX 3070", minerando: true, temp: 60, tempMem: 80, tempHot: null, watts: 120, ventoinha: 60, rpm: null },
  { id: "1", tipo: "cpu", fabricante: "intel", bus: null, nome: "13th Gen Intel(R) Core(TM) i7-13700", minerando: false, temp: null, tempMem: null, tempHot: null, watts: null, ventoinha: null, rpm: null }] });

(async () => {
  try {
    /* a primeira pergunta liga o leitor; enquanto não chega leitura, não completa nada */
    const u0 = S.ultima();
    assert.equal(u0.ok, false);
    assert(S.estado().rodando, "o leitor começou");
    assert(await ate(() => S.ultima().ok), "chegou leitura");
    await esperar(200);
    const u = S.ultima();
    assert.equal(u.placas.length, 1);
    const p = u.placas[0];
    assert(p.bus === 3 && p.nome === "AMD Radeon RX 9070 XT" && p.memoria === 76 && p.quente === 77 && p.borda === 46 && p.rpm === 2765, JSON.stringify(p));
    assert(p.placaW > 372 && p.placaW < 402 && p.n >= 3, "o consumo é a média do último minuto: " + JSON.stringify(p));

    /* juntar: completa só a placa AMD, só o que o app da Kryptex não trouxe */
    const j = S.juntar(leituraKx());
    const [amd, nv, cpu] = j.placas;
    assert(amd.tempMem === 76 && amd.tempHot === 77 && amd.rpm === 2765 && amd.temp === 45, JSON.stringify(amd));
    assert(amd.watts > 372 && amd.watts < 402 && Number.isInteger(amd.watts), "consumo da placa: " + amd.watts);
    assert.deepEqual(nv, leituraKx().placas[1], "a NVIDIA fica como veio");
    assert.deepEqual(cpu, leituraKx().placas[2], "o processador fica como veio");
    assert(j.sensores && j.sensores.ok === true && j.sensores.metodo === "pmlog", JSON.stringify(j.sensores));
    /* sem o barramento, acha pelo nome */
    const semBus = leituraKx(); semBus.placas[0].bus = null;
    assert.equal(S.juntar(semBus).placas[0].tempHot, 77);
    /* o que o app da Kryptex trouxe vale mais */
    const comMem = leituraKx(); comMem.placas[0].tempMem = 70; comMem.placas[0].watts = 300;
    const jm = S.juntar(comMem).placas[0];
    assert(jm.tempMem === 70 && jm.watts === 300 && jm.tempHot === 77, JSON.stringify(jm));
    /* leitura que falhou ou sem placa AMD: fica como está */
    assert.deepEqual(S.juntar({ ok: false, erro: "fechado" }), { ok: false, erro: "fechado" });
    const soNv = { ok: true, placas: [leituraKx().placas[1]] };
    assert.deepEqual(S.juntar(soNv), { ok: true, placas: [leituraKx().placas[1]] });

    /* cada amostra vale para uma leitura do painel só (ele lê de minuto em minuto e conta duas leituras quentes seguidas
       para pausar): 55 s depois, ela já não entra, senão a mesma amostra quente valeria por duas leituras */
    S.parar();
    const relogio = Date.now;
    try {
      const t0 = relogio();
      Date.now = () => t0 + 55e3;
      const velha = S.ultima();
      assert(!velha.ok, "a amostra de 55 s atrás não conta mais: " + JSON.stringify(velha));
    } finally { Date.now = relogio; S.parar(); }

    /* consumo 0 não é medida (o sensor veio marcado como lido, mas sem valor): a placa fica sem consumo medido */
    process.env.SENSORES_FALSO_PLACAS = JSON.stringify([{ bus: 3, nome: "AMD Radeon RX 9070 XT", borda: 46, placaW: -30 }]);   // o falso alterna −30 e 0
    S._zerar();
    S.ultima(); assert(await ate(() => { const x = S.ultima(); return x.ok && x.placas[0].n >= 2; }), "leituras com consumo 0");
    assert.equal(S.ultima().placas[0].placaW, null, "consumo 0 não conta");
    assert.equal(S.juntar(leituraKx()).placas[0].watts, null, "a placa fica sem consumo medido");
    delete process.env.SENSORES_FALSO_PLACAS;

    /* valores fora do possível não entram */
    S.parar();
    process.env.SENSORES_FALSO_PLACAS = JSON.stringify([{ bus: 3, nome: "AMD Radeon RX 9070 XT", borda: 46, memoria: 300, quente: -50, placaW: 9000, rpm: 2700 }]);
    S._zerar();
    S.ultima(); assert(await ate(() => S.ultima().ok), "leitura com valores estranhos");
    const pe = S.ultima().placas[0];
    assert(pe.memoria === null && pe.quente === null && pe.placaW === null && pe.borda === 46, JSON.stringify(pe));
    delete process.env.SENSORES_FALSO_PLACAS;

    /* parar encerra o leitor */
    const pid1 = pidAtual();
    assert(vivo(pid1));
    S.parar();
    assert(await ate(() => !vivo(pid1)), "o leitor foi encerrado");
    assert(!S.estado().rodando);

    /* o leitor caiu: liga de novo depois da espera */
    S._zerar();
    process.env.SENSORES_FALSO_MODO = "cai";
    S.ultima();
    assert(await ate(() => !S.estado().rodando), "caiu");
    S.ultima(); assert(!S.estado().rodando, "não liga de novo antes da espera");
    await esperar(350);
    S.ultima(); assert(S.estado().rodando, "ligou de novo depois da espera");
    S.parar();

    /* o leitor continua vivo, mas parou de mandar leituras boas (o ADL deixou de responder depois de uma atualização do
       driver, ou o leitor travou): depois de um tempo sem leitura boa, ele é encerrado e liga de novo depois da espera */
    for (const modo of ["sem-sensores", "mudo"]) {
      S._zerar();
      process.env.SENSORES_FALSO_MODO = modo;
      S.ultima();
      assert(await ate(() => { try { return vivo(pidAtual()) && S.estado().rodando; } catch (e) { return false; } }), "começou: " + modo);
      const pidM = pidAtual();
      assert(await ate(() => { S.ultima(); return !S.estado().rodando; }, 2000), "encerrou o leitor sem leituras: " + modo);
      assert(await ate(() => !vivo(pidM)), "o processo acabou: " + modo);
      if (modo === "sem-sensores") assert.equal(S.estado().erro, "sem-sensores");
      S.ultima(); assert(!S.estado().rodando, "espera antes de ligar de novo: " + modo);
      await esperar(350);
      S.ultima(); assert(S.estado().rodando, "ligou de novo depois da espera: " + modo);
      S.parar();
    }
    delete process.env.SENSORES_FALSO_MODO;

    /* sem placa AMD (ou sem o driver): para e só confere de novo bem depois */
    S._zerar();
    process.env.SENSORES_FALSO_MODO = "sem-amd";
    S.ultima();
    assert(await ate(() => S.estado().erro === "sem-amd"), "erro sem-amd");
    assert(await ate(() => !S.estado().rodando), "parou o leitor");
    await esperar(350);
    const us = S.ultima();
    assert(!us.ok && us.erro === "sem-amd" && !S.estado().rodando, "não liga de novo logo: " + JSON.stringify(us));
    const js = S.juntar(leituraKx());
    assert(js.sensores && js.sensores.ok === false && js.sensores.erro === "sem-amd" && js.placas[0].tempHot === null, JSON.stringify(js.sensores));
    delete process.env.SENSORES_FALSO_MODO;

    /* ninguém pergunta por um tempo: o leitor para sozinho */
    S._zerar();
    S.ultima(); assert(await ate(() => S.ultima().ok));
    const pid2 = pidAtual();
    assert(await ate(() => !S.estado().rodando, 3000), "parou por falta de uso");
    assert(await ate(() => !vivo(pid2)), "processo encerrado");

    /* fora do Windows e sem o leitor de teste: não liga nada */
    S._zerar();
    const cmd = process.env.PAINEL_SENSORES_CMD; delete process.env.PAINEL_SENSORES_CMD;
    const ui = S.ultima();
    assert(!ui.ok && ui.erro === "indisponivel" && !S.estado().rodando, JSON.stringify(ui));
    process.env.PAINEL_SENSORES_CMD = cmd;
    console.log("ok");
  } catch (e) {
    console.error("FALHOU:", e && e.stack || e);
    process.exitCode = 1;
  } finally {
    try { S.parar(); } catch (e) {}
    setTimeout(() => process.exit(), 100);
  }
})();
