"use strict";
/* Teste das marcas de energia do PC (desktop/energia.js): a hora em que o Windows ligou, o desligamento normal, a
   suspensão e a volta dela, guardadas num arquivo da pasta de dados, com um relógio de mentira.
   Uso: node desktop/scripts/teste-energia.js */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const pasta = fs.mkdtempSync(path.join(os.tmpdir(), "energia-"));
const arquivo = path.join(pasta, "energia.json");
let t = 1.8e12, up = 3600;
const relogio = { agora: () => t, uptime: () => up };
const noDisco = () => JSON.parse(fs.readFileSync(arquivo, "utf8"));
const tipos = (E) => E.estado().marcas.map((m) => m.tipo);

try {
  const { criar } = require("../energia.js");
  let E = criar({ arquivo, ...relogio });
  /* a primeira vez: o painel começa a anotar agora (e o arquivo já guarda isso) */
  assert.strictEqual(E.estado().desde, 1.8e12);
  assert.strictEqual(noDisco().desde, 1.8e12);

  /* ligou: agora menos o tempo desde que o Windows ligou; abrir o painel de novo na mesma ligação não repete */
  assert.strictEqual(E.registrarLigou(), 1.8e12 - 3600e3);
  t += 60e3; up += 60;
  assert.strictEqual(E.registrarLigou(), 1.8e12 - 3600e3);
  assert.deepStrictEqual(tipos(E), ["ligou"]);

  /* a marca vai para o disco na hora (o desligamento do Windows não espera) */
  E.marcar("desligou");
  assert.deepStrictEqual(noDisco().marcas.map((m) => [m.t, m.tipo]), [[1.8e12 - 3600e3, "ligou"], [1.8e12 + 60e3, "desligou"]]);

  /* outra abertura do painel no mesmo arquivo: o começo e as marcas continuam */
  E = criar({ arquivo, ...relogio });
  assert.strictEqual(E.estado().desde, 1.8e12);
  assert.deepStrictEqual(tipos(E), ["ligou", "desligou"]);

  /* o PC ligou de novo 2 horas depois: outra marca, com a hora dessa ligação */
  t += 7200e3; up = 120;
  assert.strictEqual(E.registrarLigou(), t - 120e3);
  assert.deepStrictEqual(E.estado().marcas.map((m) => [m.t, m.tipo]).slice(-1), [[t - 120e3, "ligou"]]);

  /* suspensão e volta */
  E.marcar("suspendeu"); t += 60e3; E.marcar("acordou");
  assert.deepStrictEqual(tipos(E), ["ligou", "desligou", "ligou", "suspendeu", "acordou"]);

  /* só os três tipos de marca (a ligação só vem de registrarLigou, com a hora em que o Windows ligou) */
  E.marcar("x"); E.marcar("ligou"); E.marcar("");
  assert.deepStrictEqual(tipos(E), ["ligou", "desligou", "ligou", "suspendeu", "acordou"]);

  /* 30 dias depois, as marcas antigas saem */
  t += 31 * 864e5;
  assert.deepStrictEqual(E.estado().marcas, []);
  E.marcar("desligou");
  assert.deepStrictEqual(tipos(E), ["desligou"]);

  /* no máximo 300, ficando as mais novas */
  for (let i = 0; i < 400; i++) { t += 1000; E.marcar(i % 2 ? "acordou" : "suspendeu"); }
  const ms = E.estado().marcas;
  assert.strictEqual(ms.length, 300);
  assert.strictEqual(ms[299].t, t);
  assert.strictEqual(ms[0].t, t - 299 * 1000);
  assert.strictEqual(noDisco().marcas.length, 300);

  /* arquivo estragado: começa de novo, sem erro */
  fs.writeFileSync(arquivo, "{");
  assert.deepStrictEqual(criar({ arquivo, ...relogio }).estado(), { desde: t, marcas: [] });

  /* sem conseguir gravar (o "arquivo" é uma pasta): não lança, e a marca fica na memória */
  const E3 = criar({ arquivo: pasta, ...relogio });
  E3.marcar("desligou");
  assert.deepStrictEqual(E3.estado().marcas.map((m) => m.tipo), ["desligou"]);

  console.log("ok");
} catch (e) {
  console.error("FALHOU:", e && e.stack || e);
  process.exitCode = 1;
} finally {
  try { fs.rmSync(pasta, { recursive: true, force: true }); } catch (e) {}
}
