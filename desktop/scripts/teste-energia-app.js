"use strict";
/* Teste da energia no aplicativo de verdade (Electron, sem mostrar janela): o programa anota quando o Windows ligou, o
   desligamento normal e a suspensão; a página lê isso pela ponte; e o "O PC voltou" do programa fica para o painel
   quando ele lê o app da Kryptex. Grava teste-energia-app.json em PAINEL_SAIDA e sai com 1 se algo falhar.
   Uso, dentro de desktop/:
   PAINEL_TESTE=1 PAINEL_TESTE_ROTEIRO=teste-energia-app.js PAINEL_DADOS=<pasta vazia> PAINEL_SAIDA=<pasta>
   PAINEL_NTFY=http://127.0.0.1:9 xvfb-run -a ./node_modules/.bin/electron . --no-sandbox */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { powerMonitor } = require("electron");

module.exports = async (principal, x) => {
  const ok = [], falhas = [];
  const checa = (nome, cond, extra) => { (cond ? ok : falhas).push(nome + (!cond && extra !== undefined ? " [" + JSON.stringify(extra) + "]" : "")); };
  const dados = x.app.getPath("userData");
  const ler = (n) => { try { return JSON.parse(fs.readFileSync(path.join(dados, n), "utf8")); } catch (e) { return null; } };
  const js = (c) => principal.webContents.executeJavaScript(c);
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  try {
    /* a página carregou, com a ponte; depois, espera o painel terminar de abrir (ele também chama o segundo plano) */
    for (let i = 0; i < 150; i++) { if (await js("!!(window.desktop && window.desktop.segundoPlano)").catch(() => false)) break; await esperar(100); }
    await esperar(3000);

    /* ligou: anotado ao abrir, com a hora em que o Windows ligou */
    const ligou = Date.now() - os.uptime() * 1000, a0 = ler("energia.json");
    const ls = a0 ? a0.marcas.filter((m) => m.tipo === "ligou") : [];
    checa("ligou: anotado ao abrir o programa", ls.length === 1 && Math.abs(ls[0].t - ligou) < 5000, a0);

    /* suspensão, volta e o Windows desligando: vão para o arquivo na hora */
    powerMonitor.emit("suspend"); powerMonitor.emit("resume");
    principal.emit("session-end");
    const a1 = ler("energia.json"), seq = a1 ? a1.marcas.map((m) => m.tipo).join() : "";
    checa("suspensão, volta e desligamento normal no arquivo", seq === "ligou,suspendeu,acordou,desligou", a1);

    /* a página lê as marcas pela ponte */
    const e = await js("window.desktop.energia()");
    checa("a página lê as marcas pela ponte", !!e && !!a1 && e.desde === a1.desde && e.marcas.map((m) => m.tipo).join() === seq, e);

    /* com o painel lendo o app da Kryptex (kxa), o aviso "O PC voltou" é dele, e o programa não manda o seu */
    await js("window.desktop.segundoPlano({bandeja: false, iniciar: false, kxa: true})");
    const sp = ler("segundo-plano.json");
    checa("o segundo plano guarda kxa", x.segundoPlano().kxa === true && !!sp && sp.kxa === true, sp);
    x.celular.mudar({ ligado: true, sinal: true, topico: "teste-energia", ultimoSinal: Date.now() - 2 * 3600e3, saiuAMao: false });
    checa("com kxa, o programa não manda o \"O PC voltou\"", (await x.celular.verificarVolta()) === false);
    await js("window.desktop.segundoPlano({bandeja: false, iniciar: false, kxa: false})");
    checa("sem kxa, o programa manda o \"O PC voltou\"", (await x.celular.verificarVolta()) === true);
  } catch (err) {
    falhas.push("erro: " + ((err && err.stack) || err));
  }
  const r = { ok: ok.length, falhas };
  fs.writeFileSync(path.join(process.env.PAINEL_SAIDA || os.tmpdir(), "teste-energia-app.json"), JSON.stringify(r, null, 1));
  console.log(JSON.stringify(r));
  x.app.exit(falhas.length ? 1 : 0);
};
