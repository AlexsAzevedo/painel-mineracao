"use strict";
/* Teste do estado e da vigia dos ajustes da placa (desktop/placa.js) com um leitor de mentira em JS, um relógio e marcas de
   energia de mentira: assumir, aplicar, o teste de 15 minutos, travou, de fábrica, outro programa, a ventoinha, os erros
   do leitor e a fiação no programa (main.js, preload.js, package.json).
   Uso: node desktop/scripts/teste-placa.js */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const Placa = require("../placa.js");
const R = require("../placa-regras.js");

const pasta = fs.mkdtempSync(path.join(os.tmpdir(), "placa-"));
const CHAVE = "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&2B6F2D5B&0&00000019";
const NOME = "AMD Radeon RX 9070 XT";
const MIN = 60e3, H = 3600e3;
const CURVA_FAB = [[30, 15], [50, 32], [61, 49], [72, 66], [80, 100]];
const A = { potencia: -20, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, ventoinha: { modo: "fixa", pct: 74 } };
const FAB = { potencia: 0, tensao: 0, clock: 0, memoria: 2518, temporizacao: 0, curva: CURVA_FAB, zeroRpm: 1 };

/* o leitor de mentira: uma RX 9070 XT que muda com o aplicar, como o leitor de verdade */
function leitorFalso(arquivo) {
  const c = { potencia: -20, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, curva: [[30, 74], [50, 74], [61, 74], [72, 74], [80, 74]], zeroRpm: 0, rpm: 2552, uso: 99 };
  const num = (atual, min, max, padrao, offset) => ({ suporta: true, min, max, passo: 1, atual, padrao, ...(offset ? { offset: true } : {}) });
  const lida = () => ({
    chave: CHAVE, nome: NOME, bus: 3, indice: 0, modo: 3,
    deFabrica: Object.keys(FAB).every((k) => JSON.stringify(c[k]) === JSON.stringify(FAB[k])),
    potencia: num(c.potencia, -30, 10, 0), tensao: num(c.tensao, -200, 0, 0, true), clock: num(c.clock, -500, 1000, 0, true),
    memoria: num(c.memoria, 2518, 3000, 2518), temporizacao: { suporta: true, atual: c.temporizacao, padrao: 0, opcoes: [0, 1] },
    ventoinha: { suporta: true, velMin: 15, velMax: 100, tempMin: 25, tempMax: 100, curva: c.curva, curvaPadrao: CURVA_FAB, zeroRpm: { suporta: true, atual: c.zeroRpm, padrao: 1 } },
    agora: { clockMHz: 2950, watts: 301, tempC: 44, ventoinhaRpm: c.rpm, usoPct: c.uso }
  });
  const f = { c, pedidos: [], jsonNoAplicar: [], sobrepos: false, falha: {}, semPlacas: false };
  let ocupado = false;
  f.reiniciarDriver = () => Object.assign(c, JSON.parse(JSON.stringify(FAB)));
  f.pedir = async (op, d) => {
    if (ocupado) f.sobrepos = true;
    ocupado = true;
    f.pedidos.push({ op, ...(d || {}) });
    if (op === "aplicar" && arquivo) { try { f.jsonNoAplicar.push(fs.readFileSync(arquivo, "utf8")); } catch (e) { f.jsonNoAplicar.push(null); } }
    await new Promise((ok) => setTimeout(ok, 3));
    ocupado = false;
    if (f.falha[op]) return f.falha[op];
    if (op === "ler") return { ok: true, afterburner: false, placas: f.semPlacas ? [] : [lida()] };
    if (op === "fabrica") { Object.assign(c, JSON.parse(JSON.stringify(FAB))); c.rpm = 2552; return { ok: true, itens: {}, placa: lida() }; }
    if (op === "aplicar") {
      const a = d.ajuste;
      for (const k of ["potencia", "tensao", "clock", "temporizacao"]) if (k in a) c[k] = a[k];
      if ("memoria" in a) c.memoria = a.memoria % 2 ? a.memoria - 1 : a.memoria;   /* o driver arredonda a memória */
      if (a.ventoinha && a.ventoinha.modo === "fixa") { c.curva = c.curva.map(([t]) => [t, a.ventoinha.pct]); c.zeroRpm = 0; }
      if (a.ventoinha && a.ventoinha.modo === "auto") { c.curva = CURVA_FAB; c.zeroRpm = 1; }
      if (a.ventoinha && a.ventoinha.modo === "curva") { c.curva = a.ventoinha.curva; c.zeroRpm = a.ventoinha.zeroRpm; }
      c.rpm = 2552;
      return { ok: true, itens: { potencia: { pedido: a.potencia, lido: c.potencia } }, placa: lida() };
    }
    return { ok: false, erro: "pedido", msg: "?" };
  };
  return f;
}

let n = 0;
function novo(op = {}) {
  const arquivo = path.join(pasta, `placa-${++n}.json`);
  if (op.conteudo != null) fs.writeFileSync(arquivo, op.conteudo);
  const amd = leitorFalso(arquivo);
  const x = { arquivo, amd, T: Date.UTC(2026, 9, 28, 20, 0, 0), en: { desde: 0, marcas: [] }, mudou: 0 };
  x.placa = Placa.criar({ arquivo, amd, energia: () => x.en, agora: () => x.T, aoMudar: () => { x.mudou++; } });
  x.ler = () => JSON.parse(fs.readFileSync(arquivo, "utf8"));
  x.aplicados = () => amd.pedidos.filter((p) => p.op === "aplicar" || p.op === "fabrica");
  x.vigiar = async (vezes = 1, passo = MIN) => { for (let i = 0; i < vezes; i++) { x.T += passo; await x.placa.vigiar(); } };
  return x;
}
/* o painel aberto de novo (outro processo): o mesmo arquivo, o mesmo leitor e as mesmas marcas, com o relógio seguindo */
function reabrir(x) {
  const y = { ...x, mudou: 0 };
  y.placa = Placa.criar({ arquivo: x.arquivo, amd: x.amd, energia: () => y.en, agora: () => y.T, aoMudar: () => { y.mudou++; } });
  y.vigiar = async (vezes = 1, passo = MIN) => { for (let i = 0; i < vezes; i++) { y.T += passo; await y.placa.vigiar(); } };
  return y;
}

(async () => {
  try {
    /* sem cuidar: nada é aplicado */
    let x = novo();
    let r = await x.placa.aplicar(CHAVE, A);
    assert(r.ok === false && r.erro === "pedido", JSON.stringify(r));
    assert.strictEqual(x.aplicados().length, 0);

    /* assumir: guarda o que a placa tem, sem gravar nada */
    r = await x.placa.cuidar(true);
    assert(r.assumiu === true && r.cuidar === true, JSON.stringify(r).slice(0, 200));
    let est = await x.placa.estado();
    assert.deepStrictEqual(est.placas[CHAVE].salvo, A);
    assert.strictEqual(est.placas[CHAVE].situacao, "bom");
    assert.strictEqual(x.aplicados().length, 0, "assumir não grava nada na placa");
    assert.strictEqual(x.ler().cuidar, true);
    assert(est.leitura && est.leitura.placas.length === 1 && est.leitura.afterburner === false);

    /* aplicar: o arquivo já tem o teste quando o leitor recebe o pedido */
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -21 });
    assert(r.ok === true && r.leitura.potencia.atual === -21, JSON.stringify(r).slice(0, 200));
    const noAplicar = JSON.parse(x.amd.jsonNoAplicar[0]);
    assert.strictEqual(noAplicar.placas[CHAVE].teste.ajuste.potencia, -21, "gravado antes de aplicar");
    est = await x.placa.estado();
    assert(est.placas[CHAVE].situacao === "teste" && est.placas[CHAVE].faltam === 15, JSON.stringify(est.placas[CHAVE]));

    /* Review Focus 2: a memória que o driver arredonda vira o salvo, e a vigia não aplica de novo */
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -21, memoria: 2601 });
    est = await x.placa.estado();
    assert.strictEqual(est.placas[CHAVE].salvo.memoria, 2600);
    assert.strictEqual(est.placas[CHAVE].teste.ajuste.memoria, 2600);
    let antes = x.aplicados().length;
    await x.vigiar();
    assert.strictEqual(x.aplicados().length, antes, "a memória arredondada não faz aplicar de novo");

    /* o leitor recusa: o salvo volta ao de antes */
    const salvoAntes = (await x.placa.estado()).placas[CHAVE].salvo;
    x.amd.falha.aplicar = { ok: false, erro: "fora-da-faixa", msg: "potência -40 fora da faixa (de -30 a 10)" };
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -25 });
    assert(r.ok === false && r.erro === "fora-da-faixa", JSON.stringify(r));
    assert.deepStrictEqual((await x.placa.estado()).placas[CHAVE].salvo, salvoAntes);
    delete x.amd.falha.aplicar;

    /* 15 minutos minerando: o ajuste vira bom (um aplicar novo começa o teste do zero) */
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -21, memoria: 2600 });
    assert(r.ok, JSON.stringify(r));
    x.amd.c.uso = 100;
    await x.vigiar(14);
    assert.strictEqual((await x.placa.estado()).placas[CHAVE].faltam, 1, "com 14 minutos, falta 1");
    await x.vigiar(1);
    est = await x.placa.estado();
    assert(est.placas[CHAVE].situacao === "bom" && est.placas[CHAVE].bomDesde === x.T && est.placas[CHAVE].bom.potencia === -21, JSON.stringify(est.placas[CHAVE]));

    /* travou: o PC ligou sem o desligamento normal durante o teste */
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -22, memoria: 2600 });
    assert(r.ok, JSON.stringify(r));
    x.T += 5 * MIN;
    x.en.marcas.push({ t: x.T - 2 * MIN, tipo: "ligou" });
    await x.vigiar();
    est = await x.placa.estado();
    assert.deepStrictEqual(est.eventos.map((e) => [e.tipo, e.titulo, e.corpo]), [["travou", "O ajuste da placa travou",
      "AMD Radeon RX 9070 XT: o PC desligou de repente durante o teste. O painel voltou para o ajuste anterior."]]);
    const ultimo = x.aplicados().slice(-1)[0];
    assert(ultimo.op === "aplicar" && ultimo.ajuste.potencia === -21, "voltou para o bom: " + JSON.stringify(ultimo));
    assert.strictEqual(est.placas[CHAVE].situacao, "travou");
    assert.deepStrictEqual((await x.placa.estado()).eventos, [], "Review Focus 4: o aviso sai uma vez só");

    /* o mesmo ajuste de novo: pede confirmação; confirmado, aplica */
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -22, memoria: 2600 });
    assert(r.ok === false && r.precisaConfirmar === true && r.travou.motivo === "o PC desligou de repente durante o teste", JSON.stringify(r));
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -22, memoria: 2600 }, { mesmoQueTravou: true });
    assert(r.ok === true, JSON.stringify(r));

    /* Review Focus 1: o painel saiu pelo Sair antes de o PC ligar de novo: não é travou, o teste recomeça */
    x.T += 2 * MIN;
    x.placa.saiu();
    assert.strictEqual(x.ler().saiu, x.T, "o saiu vai para o arquivo na hora");
    x.T += 3 * MIN;
    x.en.marcas.push({ t: x.T - MIN, tipo: "ligou" });
    antes = x.aplicados().length;
    await x.vigiar();
    est = await x.placa.estado();
    assert.deepStrictEqual(est.eventos, [], "sem aviso de travou");
    assert(x.aplicados().length === antes + 1 && est.placas[CHAVE].teste && est.placas[CHAVE].teste.minutos === 0 && est.placas[CHAVE].teste.desde === x.T,
      JSON.stringify(est.placas[CHAVE].teste));

    /* o driver reiniciou 2 vezes em 24 horas, sem teste: o ajuste trava e a placa volta ao de fábrica */
    x = novo();
    await x.placa.cuidar(true);
    x.amd.reiniciarDriver();
    await x.vigiar();
    assert.strictEqual(x.aplicados().slice(-1)[0].op, "aplicar", "a primeira vez, aplica de novo");
    assert.deepStrictEqual((await x.placa.estado()).eventos, []);
    x.T += H;
    x.amd.reiniciarDriver();
    await x.vigiar();
    est = await x.placa.estado();
    assert.strictEqual(x.aplicados().slice(-1)[0].op, "fabrica");
    assert.deepStrictEqual(est.placas[CHAVE].salvo, R.ajusteDeFabrica({ potencia: { suporta: true, padrao: 0 }, tensao: { suporta: true, padrao: 0 },
      clock: { suporta: true, padrao: 0 }, memoria: { suporta: true, padrao: 2518 }, temporizacao: { suporta: true, padrao: 0 }, ventoinha: { suporta: true } }));
    assert.deepStrictEqual(est.eventos.map((e) => e.corpo), ["AMD Radeon RX 9070 XT: o driver de vídeo reiniciou 2 vezes em 24 horas. O painel voltou a placa para o de fábrica."]);
    assert.strictEqual(est.placas[CHAVE].travou[0].ajuste.potencia, -20);

    /* a inicialização rápida do Windows (o padrão): Sair, desligar e ligar não deixa marca, e a placa volta de fábrica.
       Sem ter visto o ajuste desde que abriu, o painel não conclui que o driver reiniciou */
    x = novo();
    await x.placa.cuidar(true);
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -21 });
    assert(r.ok, JSON.stringify(r));
    x.amd.c.uso = 100;
    await x.vigiar(3);
    x.placa.saiu();
    x.T += 10 * H;
    x.amd.reiniciarDriver();
    x = reabrir(x);
    await x.vigiar();
    est = await x.placa.estado();
    assert.deepStrictEqual(est.eventos, [], "teste de antes de abrir, placa de fábrica sem marca: sem travou");
    assert(x.amd.c.potencia === -21 && est.placas[CHAVE].teste && est.placas[CHAVE].teste.minutos === 0, "aplica de novo e recomeça o teste: " + JSON.stringify(est.placas[CHAVE].teste));
    /* sem teste: duas voltas assim em 24 horas não travam o ajuste (nem contam como o driver reiniciando) */
    x = novo();
    await x.placa.cuidar(true);
    for (let i = 0; i < 2; i++) {
      x.placa.saiu();
      x.T += 3 * H;
      x.amd.reiniciarDriver();
      x = reabrir(x);
      await x.vigiar();
    }
    est = await x.placa.estado();
    assert.deepStrictEqual(est.eventos, [], "duas voltas sem marca: sem aviso");
    assert.deepStrictEqual(est.placas[CHAVE].salvo, A, "o ajuste continua o mesmo");
    assert.strictEqual(x.amd.c.potencia, -20, "aplicado de novo");
    /* o PC suspendeu no meio do teste e a placa acordou de fábrica; a primeira gravação falha: depois da espera, o painel
       aplica de novo, sem travou (a marca da suspensão não se perde com a falha) */
    x = novo();
    await x.placa.cuidar(true);
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -21 });
    assert(r.ok, JSON.stringify(r));
    x.amd.c.uso = 100;
    await x.vigiar(2);
    x.en.marcas.push({ t: x.T + 10e3, tipo: "suspendeu" }, { t: x.T + 50e3, tipo: "acordou" });
    x.amd.reiniciarDriver();
    x.amd.falha.aplicar = { ok: false, erro: "prazo", msg: "o leitor da placa não respondeu" };
    await x.vigiar();
    delete x.amd.falha.aplicar;
    await x.vigiar(1, 11 * MIN);
    est = await x.placa.estado();
    assert(!est.eventos.some((e) => e.tipo === "travou"), "sem travou: " + JSON.stringify(est.eventos.map((e) => e.tipo)));
    assert(x.amd.c.potencia === -21 && est.placas[CHAVE].teste && est.placas[CHAVE].teste.minutos === 0, "aplicou o ajuste em teste de novo: " + JSON.stringify(est.placas[CHAVE].teste));
    /* com o painel aberto e o ajuste visto, o driver reiniciando no meio do teste ainda é travou */
    x = novo();
    await x.placa.cuidar(true);
    r = await x.placa.aplicar(CHAVE, { ...A, potencia: -21 });
    x.amd.c.uso = 100;
    await x.vigiar(2);
    x.amd.reiniciarDriver();
    await x.vigiar();
    est = await x.placa.estado();
    assert.deepStrictEqual(est.eventos.map((e) => e.corpo), ["AMD Radeon RX 9070 XT: o driver de vídeo reiniciou durante o teste. O painel voltou para o ajuste anterior."]);

    /* outro programa: aplica de novo e avisa no máximo uma vez por hora */
    x = novo();
    await x.placa.cuidar(true);
    x.amd.c.potencia = -10;
    await x.vigiar();
    est = await x.placa.estado();
    assert.deepStrictEqual(est.eventos.map((e) => [e.tipo, e.titulo]), [["outro", "Outro programa mudou o ajuste da placa"]]);
    assert(est.eventos[0].corpo.includes('desligue nele o "Aplicar overclock ao iniciar o sistema"'), est.eventos[0].corpo);
    assert.strictEqual(x.amd.c.potencia, -20, "aplicou de novo");
    x.amd.c.potencia = -10;
    await x.vigiar(1, 2 * MIN);
    assert(x.amd.c.potencia === -20 && (await x.placa.estado()).eventos.length === 0, "aplica, mas sem aviso dentro da hora");
    x.amd.c.potencia = -10;
    await x.vigiar(1, 61 * MIN);
    assert.strictEqual((await x.placa.estado()).eventos.length, 1, "depois de uma hora, avisa de novo");

    /* a ventoinha: a referência das 3 primeiras leituras; com a queda, grava de novo e avisa */
    x = novo();
    await x.placa.cuidar(true);
    await x.vigiar(3);
    assert.strictEqual(x.ler().placas[CHAVE].rpm.referencia, 2552);
    x.amd.c.rpm = 1500;
    antes = x.aplicados().length;
    await x.vigiar();
    est = await x.placa.estado();
    assert.strictEqual(x.aplicados().length, antes + 1);
    assert.deepStrictEqual(est.eventos.map((e) => [e.tipo, e.corpo]), [["ventoinha", "AMD Radeon RX 9070 XT: as rotações caíram de 2.552 para 1.500 rpm. O painel gravou a ventoinha de novo."]]);

    /* a gravação falha na vigia (Review Focus 5): avisa uma vez e espera 10 minutos */
    for (const falha of [{ ok: false, erro: "recusou", msg: "o driver recusou a gravação (-23: precisa de administrador)" },
      { ok: false, erro: "prazo", msg: "o leitor da placa não respondeu" }]) {
      x = novo();
      await x.placa.cuidar(true);
      x.amd.c.potencia = -10;
      x.amd.falha.aplicar = falha;
      await x.vigiar();
      est = await x.placa.estado();
      assert.deepStrictEqual(est.eventos.map((e) => [e.tipo, e.titulo, e.corpo]),
        [["parou", "O painel não conseguiu aplicar o ajuste da placa", `AMD Radeon RX 9070 XT: ${falha.msg}. Ele tenta de novo em 10 minutos.`]]);
      antes = x.aplicados().length;
      await x.vigiar(1, 5 * MIN);
      assert.strictEqual(x.aplicados().length, antes, "nada de aplicar na espera");
      delete x.amd.falha.aplicar;
      await x.vigiar(1, 6 * MIN);
      assert(x.aplicados().length === antes + 1 && x.amd.c.potencia === -20, "depois da espera, aplica");
      assert.deepStrictEqual((await x.placa.estado()).eventos.filter((e) => e.tipo === "parou"), []);
    }
    /* a leitura falha na vigia: nada muda, sem exceção nem aviso */
    x.amd.falha.ler = { ok: false, erro: "prazo", msg: "o leitor da placa não respondeu" };
    antes = x.aplicados().length;
    await x.vigiar();
    est = await x.placa.estado();
    assert(x.aplicados().length === antes && est.eventos.length === 0 && est.erro && est.erro.erro === "prazo", JSON.stringify(est.erro));
    delete x.amd.falha.ler;

    /* robustez: a placa sumiu; o arquivo estragado; vigia e aplicar ao mesmo tempo */
    x = novo();
    await x.placa.cuidar(true);
    x.amd.semPlacas = true;
    await x.vigiar();
    assert.deepStrictEqual((await x.placa.estado()).placas[CHAVE].salvo, A, "a placa que sumiu continua guardada");
    x.amd.semPlacas = false;
    x = novo({ conteudo: "{" });
    est = await x.placa.estado();
    assert(est.cuidar === false && Object.keys(est.placas).length === 0, JSON.stringify(est));
    await x.placa.cuidar(true);
    await Promise.all([x.placa.vigiar(), x.placa.aplicar(CHAVE, { ...A, potencia: -21 }), x.placa.vigiar(), x.placa.ler()]);
    assert.strictEqual(x.amd.sobrepos, false, "o leitor nunca recebe dois pedidos ao mesmo tempo");
    assert(x.mudou > 0, "aoMudar foi chamado");

    /* a fiação no programa */
    const main = fs.readFileSync(path.join(__dirname, "..", "main.js"), "utf8");
    const preload = fs.readFileSync(path.join(__dirname, "..", "preload.js"), "utf8");
    const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "package.json"), "utf8"));
    assert(main.includes('ipcMain.handle("placa"'), "main.js: o IPC placa");
    assert(/try\s*\{[^}]*require\("\.\/placa\.js"\)/.test(main), "main.js: o require do placa.js dentro de try");
    assert(/before-quit[\s\S]{0,200}placa\.saiu\(\)/.test(main), "main.js: placa.saiu() no before-quit");
    assert(main.includes("PAINEL_PLACA_VIGIA_MS"), "main.js: PAINEL_PLACA_VIGIA_MS");
    assert(/will-quit[\s\S]{0,200}placaAmd\.parar\(\)/.test(main), "main.js: o leitor para no will-quit");
    for (const f of ["estado:", "ler:", "cuidar:", "aplicar:", "fabrica:", "aoMudar:"]) assert(preload.includes("placa: {") && preload.includes(f), "preload.js: " + f);
    for (const f of ["placa.js", "placa-amd.js", "placa-regras.js"]) assert(pkg.build.files.includes(f), "build.files: " + f);
    assert(pkg.build.extraResources.some((r) => r.from === "placa-amd.ps1" && r.to === "placa-amd.ps1"), "extraResources: placa-amd.ps1");

    console.log("ok");
  } catch (e) {
    console.error("FALHOU:", (e && e.stack) || e);
    process.exitCode = 1;
  } finally {
    fs.rmSync(pasta, { recursive: true, force: true });
  }
})();
