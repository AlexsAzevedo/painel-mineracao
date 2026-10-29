"use strict";
/* Teste das regras dos ajustes da placa (desktop/placa-regras.js): o ajuste lido, o de fábrica, as comparações, a
   conferência dos valores e as decisões da vigia de cada minuto.
   Uso: node desktop/scripts/teste-placa-regras.js */
const assert = require("assert");
const R = require("../placa-regras.js");

const AGORA = Date.UTC(2026, 9, 28, 20, 0, 0);
const MIN = 60e3, H = 3600e3;
const CURVA_74 = [[30, 74], [50, 74], [61, 74], [72, 74], [80, 74]];
const CURVA_FAB = [[30, 15], [50, 32], [61, 49], [72, 66], [80, 100]];

/* a placa lida (como o leitor devolve), com mudanças por cima: um objeto mexe só nas chaves que traz */
function P(mud = {}) {
  const base = {
    chave: "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&2B6F2D5B&0&00000019", nome: "AMD Radeon RX 9070 XT", bus: 3, indice: 0, deFabrica: false, modo: 3,
    potencia: { suporta: true, min: -30, max: 10, passo: 1, atual: -20, padrao: 0 },
    tensao: { suporta: true, min: -200, max: 0, passo: 1, atual: -75, padrao: 0, offset: true },
    clock: { suporta: true, min: -500, max: 1000, passo: 1, atual: 0, padrao: 0, offset: true },
    memoria: { suporta: true, min: 2518, max: 3000, passo: 1, atual: 2518, padrao: 2518 },
    temporizacao: { suporta: true, atual: 0, padrao: 0, opcoes: [0, 1] },
    ventoinha: { suporta: true, velMin: 15, velMax: 100, tempMin: 25, tempMax: 100, curva: CURVA_74, curvaPadrao: CURVA_FAB, zeroRpm: { suporta: true, atual: 0, padrao: 1 } },
    agora: { clockMHz: 2950, watts: 301, tempC: 44, ventoinhaRpm: 2552, usoPct: 99 }
  };
  const p = {};
  for (const k of Object.keys(base)) {
    const b = base[k], m = mud[k];
    p[k] = m === undefined ? b : (b && typeof b === "object" && !Array.isArray(b) && m && typeof m === "object" && !Array.isArray(m)) ? { ...b, ...m } : m;
  }
  if (mud.ventoinha && mud.ventoinha.zeroRpm) p.ventoinha.zeroRpm = { ...base.ventoinha.zeroRpm, ...mud.ventoinha.zeroRpm };
  return p;
}
const FABRICA = P({ deFabrica: true, potencia: { atual: 0 }, tensao: { atual: 0 }, ventoinha: { curva: CURVA_FAB, zeroRpm: { atual: 1 } } });

const A = { potencia: -20, tensao: -75, clock: 0, memoria: 2518, temporizacao: 0, ventoinha: { modo: "fixa", pct: 74 } };
const E = (o = {}) => ({ salvo: A, bom: A, teste: null, resetes: [], rpm: { referencia: 0, amostras: [] }, ultimaVigia: AGORA - MIN, erroAte: 0, ...o });
const T = (min = 3, ajuste = A) => ({ ajuste, desde: AGORA - 10 * MIN, minutos: min });
const marcas = (...l) => ({ desde: AGORA - 48 * H, marcas: l.map(([dt, tipo]) => ({ t: AGORA + dt, tipo })) });
const decide = (o) => R.decidir({ placa: P(), e: E(), energia: marcas(), saiu: 0, agora: AGORA, ...o });

/* ajusteDaLeitura */
assert.deepStrictEqual(R.ajusteDaLeitura(P()), A);
assert.deepStrictEqual(R.ajusteDaLeitura(P({ ventoinha: { curva: CURVA_FAB, zeroRpm: { atual: 1 } } })).ventoinha, { modo: "auto" });
const outra = [[30, 40], [50, 50], [61, 60], [72, 70], [80, 80]];
assert.deepStrictEqual(R.ajusteDaLeitura(P({ ventoinha: { curva: outra } })).ventoinha, { modo: "curva", curva: outra, zeroRpm: 0 });
assert.deepStrictEqual(R.ajusteDaLeitura(P({ ventoinha: { zeroRpm: { atual: 1 } } })).ventoinha, { modo: "curva", curva: CURVA_74, zeroRpm: 1 }, "reta, mas com o zero rpm ligado, é curva");
assert(!("tensao" in R.ajusteDaLeitura(P({ tensao: { suporta: false } }))), "sem a tensão, sem a chave");
assert(!("ventoinha" in R.ajusteDaLeitura(P({ ventoinha: { suporta: false } }))), "sem a curva, sem a ventoinha");
assert.deepStrictEqual(R.ajusteDaLeitura(P({ ventoinha: { zeroRpm: { suporta: false, atual: null, padrao: null } } })).ventoinha, { modo: "fixa", pct: 74 });

/* ajusteDeFabrica */
assert.deepStrictEqual(R.ajusteDeFabrica(P()), { potencia: 0, tensao: 0, clock: 0, memoria: 2518, temporizacao: 0, ventoinha: { modo: "auto" } });

/* igual e mesmoAjuste */
assert.strictEqual(R.igual(P(), A), true);
assert.strictEqual(R.igual(P(), { ...A, potencia: -21 }), false);
assert.strictEqual(R.igual(P(), { ...A, ventoinha: { modo: "fixa", pct: 70 } }), false);
assert.strictEqual(R.igual(P(), { ...A, ventoinha: { modo: "auto" } }), false);
assert.strictEqual(R.igual(FABRICA, R.ajusteDeFabrica(P())), true, "a placa de fábrica é igual ao ajuste de fábrica");
assert.strictEqual(R.igual(P({ memoria: { atual: 2600 } }), { ...A, memoria: 2600 }), true, "Review Focus 2: a memória lida de volta");
assert.strictEqual(R.igual(P({ ventoinha: { curva: outra } }), { ...A, ventoinha: { modo: "curva", curva: outra, zeroRpm: 0 } }), true);
assert.strictEqual(R.igual(P({ tensao: { suporta: false } }), A), false, "um ajuste que a placa não tem mais não é igual");
assert.strictEqual(R.mesmoAjuste(A, { ventoinha: { pct: 74, modo: "fixa" }, temporizacao: 0, memoria: 2518, clock: 0, tensao: -75, potencia: -20 }), true);
assert.strictEqual(R.mesmoAjuste(A, { ...A, potencia: -21 }), false);
assert.strictEqual(R.mesmoAjuste(A, null), false);

/* validar */
assert.deepStrictEqual(R.validar(P(), A), null);
const v1 = R.validar(P(), { potencia: -40 });
assert(v1 && v1.erro === "fora-da-faixa" && /-40 fora da faixa \(de -30 a 10\)/.test(v1.msg), JSON.stringify(v1));
assert.strictEqual(R.validar(P({ tensao: { suporta: false } }), { tensao: -80 }).erro, "sem-ajuste");
assert.strictEqual(R.validar(P(), { ventoinha: { modo: "curva", curva: [[50, 40], [30, 50], [61, 60], [72, 70], [80, 80]], zeroRpm: 0 } }).erro, "fora-da-faixa");
assert.strictEqual(R.validar(P(), { ventoinha: { modo: "fixa", pct: 101 } }).erro, "fora-da-faixa");
assert.strictEqual(R.validar(P(), { memoria: 2400 }).erro, "fora-da-faixa");
assert.strictEqual(R.validar(P(), { potencia: -20.5 }).erro, "pedido");

/* limparAjuste */
for (const x of [{ potencia: "x" }, { vram: 1 }, { ventoinha: { modo: "turbo" } }, { potencia: -20.5 }, null, "x", [1],
  { ventoinha: { modo: "fixa" } }, { ventoinha: { modo: "curva", curva: [[30, 40]], zeroRpm: 0 } }, { temporizacao: 2.5 }, { ventoinha: { modo: "auto", pct: 3 } }])
  assert.strictEqual(R.limparAjuste(x), null, "limparAjuste(" + JSON.stringify(x) + ")");
const bom = { ...A, ventoinha: { modo: "curva", curva: outra, zeroRpm: 1 } };
const lb = R.limparAjuste(bom);
assert.deepStrictEqual(lb, bom);
assert(lb !== bom && lb.ventoinha.curva !== bom.ventoinha.curva, "uma cópia");
assert.deepStrictEqual(R.limparAjuste({}), {});

/* reiniciou */
const D = AGORA - 10 * MIN;
assert.strictEqual(R.reiniciou(null, D, 0), null);
assert.strictEqual(R.reiniciou(marcas(), D, 0), null);
assert.strictEqual(R.reiniciou(marcas([-6 * MIN, "desligou"], [-5 * MIN, "ligou"]), D, 0), "normal");
assert.strictEqual(R.reiniciou(marcas([-5 * MIN, "ligou"]), D, 0), "repente");
assert.strictEqual(R.reiniciou(marcas([-5 * MIN, "ligou"]), D, AGORA - 7 * MIN), "normal", "Review Focus 1: o painel tinha saído pelo Sair");
assert.strictEqual(R.reiniciou(marcas([-5 * MIN, "ligou"]), D, AGORA - 12 * MIN), "repente", "saiu antes do começo não conta");
assert.strictEqual(R.reiniciou(marcas([-20 * MIN, "ligou"]), D, 0), null);
assert.strictEqual(R.reiniciou(marcas([-12 * MIN, "desligou"], [-5 * MIN, "ligou"]), D, 0), "repente", "o desligou antes do começo não conta");
assert.strictEqual(R.reiniciou(marcas([-5 * MIN, "ligou"], [-4 * MIN, "desligou"], [-3 * MIN, "ligou"]), D, 0), "repente", "vale a primeira ligação");
assert.strictEqual(R.reiniciou(marcas([-6 * MIN, "suspendeu"], [-5 * MIN, "acordou"]), D, 0), "normal", "acordar da suspensão também (a placa pode voltar de fábrica)");
assert.strictEqual(R.reiniciou(marcas([-30 * MIN, "suspendeu"], [-20 * MIN, "acordou"]), D, 0), null, "acordou antes do começo não conta");

/* decidir: com teste */
assert.deepStrictEqual(decide({ e: E({ teste: T() }), energia: marcas([-5 * MIN, "ligou"]) }),
  { acao: "travou", motivo: "o PC desligou de repente durante o teste", volta: "bom" });
assert.deepStrictEqual(decide({ e: E({ teste: T() }), energia: marcas([-6 * MIN, "desligou"], [-5 * MIN, "ligou"]) }), { acao: "aplicar", reiniciarTeste: true });
assert.deepStrictEqual(decide({ e: E({ teste: T() }), energia: marcas([-5 * MIN, "ligou"]), saiu: AGORA - 7 * MIN }), { acao: "aplicar", reiniciarTeste: true });
assert.deepStrictEqual(decide({ e: E({ teste: T() }), placa: FABRICA }), { acao: "travou", motivo: "o driver de vídeo reiniciou durante o teste", volta: "bom" });
assert.deepStrictEqual(decide({ e: E({ teste: T() }), placa: P({ potencia: { atual: -10 } }) }), { acao: "aplicar", aviso: "outro" });
assert.deepStrictEqual(decide({ e: E({ teste: T(13) }), placa: P({ agora: { usoPct: 100 } }) }), { acao: "contar" });
assert.deepStrictEqual(decide({ e: E({ teste: T(14) }), placa: P({ agora: { usoPct: 100 } }) }), { acao: "bom" });
assert.deepStrictEqual(decide({ e: E({ teste: T(14) }), placa: P({ agora: { usoPct: 50 } }) }), { acao: "nada" });
assert.deepStrictEqual(decide({ e: E({ teste: T(3), rpm: { referencia: 2550, amostras: [] } }), placa: P({ agora: { ventoinhaRpm: 2000, usoPct: 100 } }) }), { acao: "aplicar", aviso: "ventoinha" });
const fab = R.ajusteDeFabrica(P());
assert.deepStrictEqual(decide({ e: E({ salvo: fab, teste: T(3, fab) }), placa: FABRICA }), { acao: "contar" }, "teste do de fábrica com a placa de fábrica (minerando): não travou");

/* decidir: sem teste */
assert.deepStrictEqual(decide({}), { acao: "nada" });
assert.deepStrictEqual(decide({ placa: FABRICA, energia: marcas([-6 * MIN, "desligou"], [-0.5 * MIN, "ligou"]) }), { acao: "aplicar" });
assert.deepStrictEqual(decide({ placa: FABRICA }), { acao: "aplicar", contarReset: true });
assert.deepStrictEqual(decide({ placa: FABRICA, e: E({ resetes: [AGORA - 2 * H] }) }),
  { acao: "travou", motivo: "o driver de vídeo reiniciou 2 vezes em 24 horas", volta: "fabrica", contarReset: true });
assert.deepStrictEqual(decide({ placa: FABRICA, e: E({ resetes: [AGORA - 25 * H] }) }), { acao: "aplicar", contarReset: true });
assert.deepStrictEqual(decide({ placa: P({ potencia: { atual: -10 } }) }), { acao: "aplicar", aviso: "outro" });
assert.deepStrictEqual(decide({ e: E({ rpm: { referencia: 2550, amostras: [] } }), placa: P({ agora: { ventoinhaRpm: 2000 } }) }), { acao: "aplicar", aviso: "ventoinha" });
assert.deepStrictEqual(decide({ e: E({ rpm: { referencia: 2550, amostras: [] } }), placa: P({ agora: { ventoinhaRpm: 2400 } }) }), { acao: "nada" });
const auto = { ...A, ventoinha: { modo: "auto" } };
assert.deepStrictEqual(decide({ e: E({ salvo: auto, rpm: { referencia: 2550, amostras: [] } }), placa: P({ ventoinha: { curva: CURVA_FAB, zeroRpm: { atual: 1 } }, agora: { ventoinhaRpm: 1500 } }) }),
  { acao: "nada" }, "na automática, as rotações mudam com a temperatura");
assert.deepStrictEqual(decide({ e: E({ erroAte: AGORA + MIN }), placa: P({ potencia: { atual: -10 } }) }), { acao: "esperar" });
assert.deepStrictEqual(decide({ placa: null }), { acao: "nada" });
assert.deepStrictEqual(decide({ e: E({ salvo: null }) }), { acao: "nada" });

/* decidir: o driver só "reiniciou" se o painel viu a placa com o ajuste desde que abriu (inicio). Com a inicialização
   rápida do Windows (o padrão), desligar e ligar com o painel fechado não deixa marca, e a placa pode voltar de fábrica:
   isso é o normal, não um travamento (nem um reinício do driver para contar) */
const INI = AGORA - 30 * MIN, SUSP = marcas([-4 * MIN, "suspendeu"], [-1 * MIN, "acordou"]);
assert.deepStrictEqual(decide({ inicio: INI, e: E({ teste: T(), vistoOk: AGORA - 40 * MIN }), placa: FABRICA }), { acao: "aplicar", reiniciarTeste: true },
  "teste de antes de abrir, placa de fábrica: aplica de novo e recomeça o teste");
assert.deepStrictEqual(decide({ inicio: INI, e: E({ teste: T() }), placa: FABRICA }), { acao: "aplicar", reiniciarTeste: true }, "sem vistoOk: nunca viu");
assert.deepStrictEqual(decide({ inicio: INI, e: E({ teste: T(), vistoOk: AGORA - 5 * MIN }), placa: FABRICA }),
  { acao: "travou", motivo: "o driver de vídeo reiniciou durante o teste", volta: "bom" }, "viu o ajuste nesta abertura: o driver reiniciou");
assert.deepStrictEqual(decide({ inicio: INI, e: E({ teste: T(), vistoOk: AGORA - 5 * MIN }), placa: FABRICA, energia: SUSP }), { acao: "aplicar", reiniciarTeste: true },
  "o PC suspendeu e acordou no meio do teste: aplica de novo e recomeça");
assert.deepStrictEqual(decide({ inicio: INI, e: E({ vistoOk: AGORA - 40 * MIN }), placa: FABRICA }), { acao: "aplicar" }, "sem teste, sem ter visto nesta abertura: aplica sem contar");
assert.deepStrictEqual(decide({ inicio: INI, e: E({ vistoOk: AGORA - 40 * MIN, resetes: [AGORA - 2 * H] }), placa: FABRICA }), { acao: "aplicar" }, "e não trava");
assert.deepStrictEqual(decide({ inicio: INI, e: E({ vistoOk: AGORA - 5 * MIN }), placa: FABRICA }), { acao: "aplicar", contarReset: true }, "viu nesta abertura: conta");
assert.deepStrictEqual(decide({ inicio: INI, e: E({ vistoOk: AGORA - 5 * MIN }), placa: FABRICA, energia: SUSP }), { acao: "aplicar" }, "acordou depois de ver: o normal");

/* mediana */
assert.strictEqual(R.mediana([2552, 2500, 2600]), 2552);
assert.strictEqual(R.mediana([1, 2, 3, 4]), 2.5);
assert.strictEqual(R.mediana([]), 0);

console.log("ok");
