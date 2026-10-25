"use strict";
/* Teste do módulo do app da Kryptex (desktop/kryptex-app.js) contra o app de mentira (kryptex-falso.js).
   Uso: node desktop/scripts/teste-kryptex-app.js */
const assert = require("assert");
const http = require("http");
const falso = require("./kryptex-falso.js")();

const srv = http.createServer((req, res) => falso.tratar(req, res, new URL(req.url, "http://x").pathname));
srv.listen(0, "127.0.0.1", async () => {
  process.env.PAINEL_KRYPTEX_LOCAL = `http://127.0.0.1:${srv.address().port}`;
  const K = require("../kryptex-app.js");
  try {
    /* leitura minerando */
    const l = await K.ler();
    assert(l.ok, JSON.stringify(l));
    assert.equal(l.placas.length, 2);
    const g = l.placas[0];
    assert(g.tipo === "gpu" && g.minerando && !g.desativada, JSON.stringify(g));
    assert.equal(g.nome, "AMD Radeon RX 9070 XT");
    assert.equal(g.temp, 63); assert.equal(g.tempMem, 78); assert.equal(g.tempHot, null); assert.equal(g.watts, 286);
    assert.equal(g.ventoinha, 54); assert.equal(g.rpm, null);
    assert.equal(g.moeda, "PRL"); assert.equal(g.algoritmo, "pearlhash"); assert.equal(g.minerador, "srbminer");
    assert.equal(g.hash, 1.13e14); assert.equal(g.rendimentoUsd, 2.965);
    const c = l.placas[1];
    assert(c.tipo === "cpu" && !c.minerando && c.hash === 0 && c.rendimentoUsd === 0.31, JSON.stringify(c));   /* parado: o rendimento esperado */
    assert.equal(l.moeda, "BRL"); assert.equal(l.computador, "PC-TESTE");
    assert.deepEqual(l.cotacoes, { brl: 4.965204, btc: 0.00001237 });
    assert.equal(l.saldoBtc, 0.0001); assert.equal(l.pausado, false); assert.equal(l.pausaAte, null);
    assert(typeof l.quando === "number" && Math.abs(l.quando - Date.now()) < 10000);
    /* nada de e-mail, código ou nome de usuário; nunca pede /user */
    const txt = JSON.stringify(l);
    assert(!txt.includes("alex.teste@example.com") && !txt.includes("7f3a9c2e1b4d5f60718293a4b5c6d7e8"), txt);
    assert(!falso.pedidos.some((p) => p.caminho === "/user"));
    assert(l.desconhecidos.includes("campo_novo_qualquer") && !l.desconhecidos.includes("dono"), JSON.stringify(l.desconhecidos));
    /* pausar: só os tempos permitidos */
    await assert.rejects(K.pausar(7), /não permitido/);
    await assert.rejects(K.pausar("60; rm"), /não permitido/);
    assert.equal(falso.pedidos.filter((p) => p.metodo === "PUT").length, 0);
    const ultimoPut = () => JSON.parse(falso.pedidos.filter((p) => p.metodo === "PUT").at(-1).corpo);
    const p = await K.pausar(60);
    assert(p.ok && p.pausado && !p.placas[0].minerando, JSON.stringify(p));
    assert.deepEqual(ultimoPut(), { pause_for: 3600000 });
    assert(p.pausaAte > Date.now() + 3500e3 && p.pausaAte < Date.now() + 3700e3, String(p.pausaAte));
    assert.equal(p.feito, true, "pausar: o app aceitou");
    const v = await K.voltar();
    assert(v.ok && !v.pausado && v.placas[0].minerando);
    assert.equal(v.feito, true, "voltar: o app aceitou");
    assert.deepEqual(ultimoPut(), { pause: false });
    await K.pausar(15); assert.deepEqual(ultimoPut(), { pause_for: 900000 });
    await K.pausar(44640); assert.deepEqual(ultimoPut(), { pause_for: 44640 * 60000 });
    await K.voltar();
    assert(falso.pedidos.every((q) => q.metodo === "GET" || (q.metodo === "PUT" && q.caminho === "/pause")), "só GET e PUT /pause");
    /* pausado com o hashrate de antes: não está minerando */
    falso.estado.modo = "pausado";
    const lp = await K.ler();
    assert(lp.pausado && !lp.placas[0].minerando && lp.placas[0].hash > 0);
    /* o GET /pause do app de verdade ainda não foi visto com a placa pausada: aceita só a hora de voltar e "pause" como objeto */
    for (const f of ["so-ate", "objeto"]) {
      falso.estado.formatoPausa = f; falso.estado.pausaAte = new Date(Date.now() + 3600e3).toISOString();
      const x = await K.ler();
      assert(x.pausado && !x.placas[0].minerando && x.pausaAte > Date.now(), f + " " + JSON.stringify({ pausado: x.pausado, ate: x.pausaAte }));
    }
    falso.estado.formatoPausa = "padrao";
    /* para acertar a leitura com o app de verdade: os nomes das chaves de cada resposta (só os nomes, nunca os valores) */
    const fm = (await K.ler()).formato || {};
    assert((fm.pause || []).includes("pause") && (fm.balance || []).includes("total") && (fm.cotacoes || []).includes("brl") && (fm.config || []).includes("currency"), JSON.stringify(fm));
    assert(!JSON.stringify(fm).includes("PC-TESTE"), "só nomes");
    /* parado sem pausa */
    falso.estado.modo = "parado";
    const lz = await K.ler();
    assert(lz.ok && !lz.pausado && !lz.placas[0].minerando && lz.placas[0].hash === 0 && lz.placas[0].rendimentoUsd === 2.965);
    /* quente */
    falso.estado.modo = "quente";
    assert.equal((await K.ler()).placas[0].temp, 86);
    /* app sem responder: desiste em uns 4 segundos */
    falso.estado.modo = "fechado";
    const t0 = Date.now(), f = await K.ler();
    assert(!f.ok && f.erro === "tempo", JSON.stringify(f));
    assert(Date.now() - t0 < 6000, "demorou " + (Date.now() - t0) + " ms");
    const pf = await K.pausar(60);   /* o app não aceitou a pausa: o painel precisa saber que não pausou */
    assert(!pf.ok && pf.feito === false, JSON.stringify(pf));
    /* app fechado (nada na porta) */
    process.env.PAINEL_KRYPTEX_LOCAL = "http://127.0.0.1:1";
    const fe = await K.ler();
    assert(!fe.ok && fe.erro === "fechado", JSON.stringify(fe));
    console.log("ok");
  } catch (e) {
    console.error("FALHOU:", e && e.message || e);
    process.exitCode = 1;
  } finally {
    srv.closeAllConnections(); srv.close();
  }
});
