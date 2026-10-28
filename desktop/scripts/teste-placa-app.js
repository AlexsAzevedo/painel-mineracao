"use strict";
/* Teste dos ajustes da placa no aplicativo de verdade (Electron, sem mostrar janela), com o leitor de mentira
   (placa-falsa.js no lugar do placa-amd.ps1): a página mostra a placa; marcar "O painel cuida dos ajustes da placa" assume
   o que ela tem sem gravar nada; aplicar grava o estado (com o teste) antes de pedir ao leitor; 15 vigias com a placa
   minerando fazem o ajuste virar bom; o PC ligando sem o desligamento normal no meio de um teste faz o ajuste travar e
   voltar para o anterior, com um aviso só (nem recarregando a página ele sai de novo); outro programa mudando a potência e
   a ventoinha fixa que cai fazem gravar de novo e avisar; a min-placa fica no localStorage da janela; e o Sair marca o
   "saiu" no placa.json. Grava teste-placa-app.json em PAINEL_SAIDA e sai com 1 se algo falhar.
   O roteiro põe sozinho PAINEL_PLACA_FALSA_ESTADO, PAINEL_PLACA_LOG e PAINEL_PLACA_JSON, antes de o leitor ligar.
   Uso, dentro de desktop/:
   PAINEL_TESTE=1 PAINEL_TESTE_ROTEIRO=teste-placa-app.js PAINEL_DADOS=<pasta vazia> PAINEL_SAIDA=<pasta>
   PAINEL_NTFY=http://127.0.0.1:9 PAINEL_PLACA_CMD=scripts/placa-falsa.js PAINEL_PLACA_VIGIA_MS=1000
   xvfb-run -a ./node_modules/.bin/electron . --no-sandbox
   Com PAINEL_PLACA_FALSA=cai, o leitor cai no primeiro pedido, e o teste tem de falhar (a começar pela seção sem placa). */
const fs = require("fs");
const os = require("os");
const path = require("path");

const TRAVOU = "O ajuste da placa travou", OUTRO = "Outro programa mudou o ajuste da placa", VENTOINHA = "A ventoinha da placa foi para o automático";
const canon = (v) => JSON.stringify(v, (k, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.keys(x).sort().map((kk) => [kk, x[kk]])) : x));

module.exports = async (principal, x) => {
  const ok = [], falhas = [];
  const checa = (nome, cond, extra) => { (cond ? ok : falhas).push(nome + (!cond && extra !== undefined ? " [" + String(JSON.stringify(extra)).slice(0, 600) + "]" : "")); return !!cond; };
  const saida = process.env.PAINEL_SAIDA || os.tmpdir();
  const arqEstado = path.join(saida, "placa-falsa-estado.json"), arqLog = path.join(saida, "placa-falsa.log");
  const arqPlaca = path.join(x.app.getPath("userData"), "placa.json");
  /* antes de o leitor ligar: o primeiro pedido vem da página, que ainda está carregando */
  for (const a of [arqEstado, arqLog]) try { fs.unlinkSync(a); } catch (e) {}
  fs.writeFileSync(arqEstado, JSON.stringify({ uso: 100 }));
  Object.assign(process.env, { PAINEL_PLACA_FALSA_ESTADO: arqEstado, PAINEL_PLACA_LOG: arqLog, PAINEL_PLACA_JSON: arqPlaca });
  /* os erros da página que falam da placa */
  const errosPagina = [];
  principal.webContents.on("console-message", (e, nivel, msg) => {
    const lv = e && e.level !== undefined ? e.level : nivel, m = String(e && e.message !== undefined ? e.message : msg);
    if ((lv === "error" || lv === 3) && /placa/i.test(m)) errosPagina.push(m);
  });

  const js = (c) => principal.webContents.executeJavaScript(c);
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  const aguardar = async (fn, ms = 20000) => {
    const fim = Date.now() + ms;
    for (;;) {
      let v = false;
      try { v = await fn(); } catch (e) { v = false; }
      if (v) return v;
      if (Date.now() > fim) return false;
      await esperar(200);
    }
  };
  const registro = () => { try { return fs.readFileSync(arqLog, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)); } catch (e) { return []; } };
  const aplicacoes = () => registro().filter((r) => r.op === "aplicar");
  const mudarFalsa = (o) => { let e = {}; try { e = JSON.parse(fs.readFileSync(arqEstado, "utf8")); } catch (err) {} fs.writeFileSync(arqEstado, JSON.stringify({ ...e, ...o })); };
  const avisos = (titulo) => x.testeSegundoPlano.notificacoes.filter((n) => n.titulo === titulo);
  const estadoArq = () => { try { return JSON.parse(fs.readFileSync(arqPlaca, "utf8")); } catch (e) { return null; } };
  const entradaArq = () => { const s = estadoArq(); return s && s.placas ? Object.values(s.placas)[0] || null : null; };
  const situacao = () => js("(() => { const s = document.querySelector('#placa-lista .placa-sit'); return s ? s.textContent : ''; })()");
  const minPlaca = async () => { try { return JSON.parse(await js("localStorage.getItem('min-placa')")); } catch (e) { return null; } };
  const comCartao = () => js("!document.getElementById('placa-p').hidden && document.querySelectorAll('#placa-lista .placa-c').length === 1");
  const aplicarPela = (pot) => js(`(() => { const c = document.querySelector('#placa-lista .placa-c'), i = c.querySelector('[data-campo="potencia"]');
    i.value = '${pot}'; i.dispatchEvent(new Event('input', {bubbles: true})); c.querySelector('[data-acao="aplicar"]').click(); })()`);
  const AJ = { potencia: -21, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, ventoinha: { modo: "fixa", pct: 74 } };

  try {
    /* 1. abrir: a página mostra a placa do leitor de mentira */
    if (!checa("abrir: a seção mostra a placa", await aguardar(comCartao, 30000))) throw new Error("sem a placa na seção, o resto não tem como rodar");

    /* 2. cuidar: assume o que a placa tem, sem gravar nada nela */
    await js("document.getElementById('placa-cuidar').click()");
    checa("cuidar: o texto de assumir", await aguardar(() => js("document.getElementById('placa-status').textContent.startsWith('O painel guardou o ajuste que a placa já tem')")));
    checa("cuidar: nada gravado na placa", aplicacoes().length === 0, aplicacoes());
    const s0 = estadoArq();
    checa("cuidar: o placa.json com a placa assumida", !!s0 && s0.cuidar === true && Object.keys(s0.placas || {}).length === 1, s0);

    /* 3. aplicar −21 pela página: o estado vai para o disco antes do pedido ao leitor */
    await aplicarPela(-21);
    const ap = await aguardar(() => aplicacoes()[0]);
    checa("aplicar: o leitor recebeu o ajuste completo", !!ap && canon(ap.ajuste) === canon(AJ), ap);
    let pj = null; try { pj = JSON.parse(ap.placaJson); } catch (e) {}
    const e3 = pj && pj.placas ? Object.values(pj.placas)[0] : null;
    checa("aplicar: o placa.json já tinha o teste quando o leitor recebeu o pedido", !!e3 && !!e3.teste && canon(e3.teste.ajuste) === canon(AJ), e3);
    checa("aplicar: a seção diz em teste", await aguardar(async () => (await situacao()).startsWith("Em teste")), await situacao());

    /* 4. 15 vigias com a placa minerando: o ajuste vira bom (e a min-placa leva isso para o celular) */
    checa("teste bom: a seção diz ajuste bom", await aguardar(async () => (await situacao()).startsWith("Ajuste bom desde"), 45000), await situacao());
    const m4 = await aguardar(async () => { const m = await minPlaca(); return m && m.placas && m.placas[0] && m.placas[0].situacao === "bom" ? m : false; });
    checa("min-placa: no localStorage, com a situação bom e o ajuste", !!m4 && m4.cuidar === true && canon(m4.placas[0].ajuste) === canon(AJ), m4);

    /* 5. travou: outro ajuste (−22) e o PC ligando sem o desligamento normal no meio do teste */
    await aplicarPela(-22);
    checa("travou: o −22 chegou ao leitor", !!(await aguardar(() => aplicacoes().find((a) => a.ajuste && a.ajuste.potencia === -22))));
    await aguardar(async () => (await situacao()).startsWith("Em teste"));
    const n5 = aplicacoes().length;
    x.placaTeste.energia = { desde: 0, marcas: [{ tipo: "ligou", t: Date.now() }] };
    checa("travou: o aviso no Windows", !!(await aguardar(() => avisos(TRAVOU).length >= 1)), x.testeSegundoPlano.notificacoes);
    const corpo = (avisos(TRAVOU)[0] || {}).corpo;
    checa("travou: o motivo no aviso", corpo === "AMD Radeon RX 9070 XT: o PC desligou de repente durante o teste. O painel voltou para o ajuste anterior.", corpo);
    checa("travou: o leitor recebeu o anterior (−21)", aplicacoes().slice(n5).some((a) => a.ajuste && a.ajuste.potencia === -21), aplicacoes().slice(n5));
    checa("travou: a seção diz que travou", await aguardar(async () => (await situacao()).includes("travou a placa (o PC desligou de repente durante o teste)")), await situacao());
    x.placaTeste.energia = null;
    const m5 = await aguardar(async () => { const m = await minPlaca(); return m && m.placas && m.placas[0] && m.placas[0].situacao === "travou" ? m : false; });
    checa("min-placa: travou, com o motivo e o ajuste anterior", !!m5 && m5.placas[0].travou && m5.placas[0].travou.motivo === "o PC desligou de repente durante o teste"
      && canon(m5.placas[0].ajuste) === canon(AJ), m5);
    /* recarregar a página (como na atualização do painel) não faz o aviso sair de novo */
    principal.webContents.reload();
    await esperar(1500);
    await aguardar(comCartao, 30000);
    await esperar(3000);
    checa("travou: o aviso saiu uma vez só, mesmo recarregando a página", avisos(TRAVOU).length === 1, avisos(TRAVOU));

    /* 6. outro programa mudou a potência: o painel aplica de novo e avisa uma vez */
    const n6 = aplicacoes().length;
    mudarFalsa({ potenciaOutro: -10 });
    checa("outro programa: o aviso", !!(await aguardar(() => avisos(OUTRO).length >= 1)), x.testeSegundoPlano.notificacoes);
    checa("outro programa: o painel aplicou o ajuste de novo", aplicacoes().slice(n6).some((a) => a.ajuste && a.ajuste.potencia === -21), aplicacoes().slice(n6));
    await esperar(3000);
    checa("outro programa: um aviso só", avisos(OUTRO).length === 1, avisos(OUTRO));

    /* 7. a ventoinha fixa caiu (foi para o automático): com a referência (3 leituras), grava de novo e avisa */
    checa("ventoinha: a referência das rotações", !!(await aguardar(() => { const e = entradaArq(); return e && e.rpm && e.rpm.referencia > 0; })), entradaArq());
    const n7 = aplicacoes().length;
    mudarFalsa({ rpm: 1500 });
    checa("ventoinha: o aviso", !!(await aguardar(() => avisos(VENTOINHA).length >= 1)), x.testeSegundoPlano.notificacoes);
    const cv = (avisos(VENTOINHA)[0] || {}).corpo;
    checa("ventoinha: as rotações no aviso", cv === "AMD Radeon RX 9070 XT: as rotações caíram de 2.552 para 1.500 rpm. O painel gravou a ventoinha de novo.", cv);
    checa("ventoinha: o painel gravou de novo", aplicacoes().length > n7, aplicacoes().slice(n7));

    /* 8. o Sair marca o "saiu" (um PC que liga depois disso não vira travamento) */
    x.app.emit("before-quit");
    const s8 = estadoArq();
    checa("sair: o placa.json marca o saiu", !!s8 && s8.saiu > 0, s8 && s8.saiu);
    checa("sem erros da placa na página", errosPagina.length === 0, errosPagina);
  } catch (err) {
    falhas.push("erro: " + ((err && err.stack) || err));
  }
  const r = { ok: ok.length, falhas };
  fs.writeFileSync(path.join(saida, "teste-placa-app.json"), JSON.stringify(r, null, 1));
  console.log(JSON.stringify(r));
  x.app.exit(falhas.length ? 1 : 0);
};
