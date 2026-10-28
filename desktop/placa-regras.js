"use strict";
/* As regras dos ajustes da placa, em funções puras (sem Electron, sem arquivo, sem relógio próprio): o ajuste que a placa
   tem, o de fábrica, as comparações, a conferência dos valores e as decisões da vigia de cada minuto (placa.js).
   O ajuste: {potencia, tensao, clock, memoria, temporizacao, ventoinha: {modo: "auto"} | {modo: "fixa", pct} |
   {modo: "curva", curva: [[°C, %] x 5], zeroRpm}}, só com os ajustes que a placa tem. */

const CAMPOS = ["potencia", "tensao", "clock", "memoria", "temporizacao"];
const NOMES = { potencia: "potência", tensao: "tensão", clock: "clock máximo", memoria: "memória", temporizacao: "temporização" };
const TESTE_MIN = 15;     /* minutos minerando para um ajuste novo virar bom */
const USO_MIN = 80;       /* uso da placa (%) para o minuto contar */
const QUEDA = 0.85;       /* a ventoinha fixa abaixo disso da referência foi para o automático */
const DIA = 24 * 3600e3;

const tem = (x) => !!(x && x.suporta === true);
const mesmaCurva = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const zeroDe = (v) => (v && v.zeroRpm && v.zeroRpm.suporta === true ? v.zeroRpm : null);

/* o ajuste que a placa tem agora */
function ajusteDaLeitura(p) {
  const a = {};
  for (const k of CAMPOS) if (tem(p[k])) a[k] = p[k].atual;
  const v = p.ventoinha;
  if (tem(v)) {
    const z = zeroDe(v), vel = (v.curva || []).map((x) => x[1]);
    if (mesmaCurva(v.curva, v.curvaPadrao) && (!z || z.atual === z.padrao)) a.ventoinha = { modo: "auto" };
    else if (vel.length === 5 && vel.every((x) => x === vel[0]) && (!z || z.atual === 0)) a.ventoinha = { modo: "fixa", pct: vel[0] };
    else a.ventoinha = { modo: "curva", curva: (v.curva || []).map((x) => [x[0], x[1]]), zeroRpm: z ? z.atual : 0 };
  }
  return a;
}

/* o padrão de cada ajuste, com a ventoinha automática */
function ajusteDeFabrica(p) {
  const a = {};
  for (const k of CAMPOS) if (tem(p[k])) a[k] = p[k].padrao;
  if (tem(p.ventoinha)) a.ventoinha = { modo: "auto" };
  return a;
}

/* a curva e o zero rpm que um ajuste de ventoinha pede, nesta placa */
function curvaDoAjuste(v, f) {
  if (f.modo === "auto") { const z = zeroDe(v); return { curva: v.curvaPadrao, zero: z ? z.padrao : null }; }
  if (f.modo === "fixa") return { curva: (v.curva || []).map((x) => [x[0], f.pct]), zero: 0 };
  if (f.modo === "curva") return { curva: f.curva, zero: f.zeroRpm };
  return null;
}

/* a placa está exatamente com esse ajuste? */
function igual(p, a) {
  if (!p || !a) return false;
  for (const k of CAMPOS) if (k in a && (!tem(p[k]) || p[k].atual !== a[k])) return false;
  if (a.ventoinha) {
    const v = p.ventoinha;
    if (!tem(v)) return false;
    const alvo = curvaDoAjuste(v, a.ventoinha), z = zeroDe(v);
    if (!alvo || !mesmaCurva(v.curva, alvo.curva)) return false;
    if (z && alvo.zero != null && z.atual !== alvo.zero) return false;
  }
  return true;
}

function canonico(a) {
  if (!a || typeof a !== "object") return null;
  const o = {};
  for (const k of CAMPOS) if (k in a) o[k] = a[k];
  const f = a.ventoinha;
  if (f) o.ventoinha = f.modo === "fixa" ? { modo: "fixa", pct: f.pct } : f.modo === "curva" ? { modo: "curva", curva: f.curva, zeroRpm: f.zeroRpm } : { modo: f.modo };
  return JSON.stringify(o);
}
function mesmoAjuste(a, b) { const x = canonico(a); return x !== null && x === canonico(b); }

/* confere os valores na faixa do driver (as mesmas regras do leitor) */
function faixa(min, max, v, nome) {
  if (!Number.isInteger(v)) return { erro: "pedido", msg: `valor que não é inteiro em ${nome}` };
  if (v < min || v > max) return { erro: "fora-da-faixa", msg: `${nome} ${v} fora da faixa (de ${min} a ${max})` };
  return null;
}
function validar(p, a) {
  for (const k of CAMPOS) {
    if (!(k in a)) continue;
    if (!tem(p[k])) return { erro: "sem-ajuste", msg: `a placa não tem ${NOMES[k]}` };
    const op = k === "temporizacao" ? (p.temporizacao.opcoes || []) : null;
    const r = op ? faixa(op.length ? Math.min(...op) : 0, op.length ? Math.max(...op) : 0, a[k], NOMES[k]) : faixa(p[k].min, p[k].max, a[k], NOMES[k]);
    if (r) return r;
  }
  const f = a.ventoinha;
  if (f) {
    const v = p.ventoinha;
    if (!tem(v)) return { erro: "sem-ajuste", msg: "a placa não tem a curva da ventoinha" };
    if (f.modo === "fixa") { const r = faixa(v.velMin, v.velMax, f.pct, "ventoinha"); if (r) return r; }
    else if (f.modo === "curva") {
      if (!Array.isArray(f.curva) || f.curva.length !== 5) return { erro: "pedido", msg: "a curva da ventoinha precisa de 5 pontos" };
      for (let i = 0; i < 5; i++) {
        const [c, s] = f.curva[i];
        const r = faixa(v.tempMin, v.tempMax, c, "temperatura da curva") || faixa(v.velMin, v.velMax, s, "ventoinha");
        if (r) return r;
        if (i && c <= f.curva[i - 1][0]) return { erro: "fora-da-faixa", msg: "as temperaturas da curva da ventoinha têm de subir de um ponto para o outro" };
      }
    } else if (f.modo !== "auto") return { erro: "pedido", msg: "modo da ventoinha desconhecido" };
  }
  return null;
}

/* o ajuste que vem da página: só as chaves do formato, com inteiros; qualquer outra coisa, null */
function limparVentoinha(v) {
  if (!v || typeof v !== "object" || Array.isArray(v)) return null;
  const chaves = Object.keys(v).sort().join();
  if (v.modo === "auto") return chaves === "modo" ? { modo: "auto" } : null;
  if (v.modo === "fixa") return chaves === "modo,pct" && Number.isInteger(v.pct) ? { modo: "fixa", pct: v.pct } : null;
  if (v.modo !== "curva" || chaves !== "curva,modo,zeroRpm" || !Array.isArray(v.curva) || v.curva.length !== 5 || (v.zeroRpm !== 0 && v.zeroRpm !== 1)) return null;
  const curva = [];
  for (const p of v.curva) {
    if (!Array.isArray(p) || p.length !== 2 || !Number.isInteger(p[0]) || !Number.isInteger(p[1])) return null;
    curva.push([p[0], p[1]]);
  }
  return { modo: "curva", curva, zeroRpm: v.zeroRpm };
}
function limparAjuste(x) {
  if (!x || typeof x !== "object" || Array.isArray(x)) return null;
  const a = {};
  for (const [k, v] of Object.entries(x)) {
    if (CAMPOS.includes(k)) { if (!Number.isInteger(v)) return null; a[k] = v; }
    else if (k === "ventoinha") { const f = limparVentoinha(v); if (!f) return null; a.ventoinha = f; }
    else return null;
  }
  return a;
}

/* o Windows ligou de novo depois de "desde"? "normal" (houve o desligamento normal, ou o painel tinha saído pelo Sair e
   não teria como marcá-lo), "repente" (o PC apagou com o painel aberto) ou null */
function reiniciou(energia, desde, saiu) {
  const m = energia && Array.isArray(energia.marcas) ? energia.marcas : [];
  const ligou = m.filter((x) => x && x.tipo === "ligou" && x.t > desde).sort((a, b) => a.t - b.t)[0];
  if (!ligou) return null;
  if (m.some((x) => x && x.tipo === "desligou" && x.t > desde && x.t < ligou.t)) return "normal";
  if (saiu > desde && saiu < ligou.t) return "normal";
  return "repente";
}

/* a ventoinha fixa foi para o automático: as rotações caíram mais de 15% da referência */
function quedaVentoinha(placa, e) {
  const f = e.salvo && e.salvo.ventoinha, ref = e.rpm && e.rpm.referencia;
  const rpm = placa.agora ? placa.agora.ventoinhaRpm : null;
  return !!(f && f.modo === "fixa" && ref > 0 && rpm != null && rpm < QUEDA * ref);
}

/* a decisão da vigia para uma placa, a cada minuto */
function decidir({ placa, e, energia, saiu, agora }) {
  if (!placa || !e || !e.salvo) return { acao: "nada" };
  if (e.erroAte > agora) return { acao: "esperar" };
  const ok = igual(placa, e.salvo);
  if (e.teste) {
    const r = reiniciou(energia, e.teste.desde, saiu || 0);
    if (r === "repente") return { acao: "travou", motivo: "o PC desligou de repente durante o teste", volta: "bom" };
    if (r === "normal") return { acao: "aplicar", reiniciarTeste: true };
    if (placa.deFabrica && !igual(placa, e.teste.ajuste)) return { acao: "travou", motivo: "o driver de vídeo reiniciou durante o teste", volta: "bom" };
    if (!ok) return { acao: "aplicar", aviso: "outro" };
    if (quedaVentoinha(placa, e)) return { acao: "aplicar", aviso: "ventoinha" };
    const uso = placa.agora ? placa.agora.usoPct : null;
    if (uso != null && uso >= USO_MIN) return (e.teste.minutos || 0) + 1 >= TESTE_MIN ? { acao: "bom" } : { acao: "contar" };
    return { acao: "nada" };
  }
  if (ok) return quedaVentoinha(placa, e) ? { acao: "aplicar", aviso: "ventoinha" } : { acao: "nada" };
  if (placa.deFabrica) {
    if (reiniciou(energia, e.ultimaVigia || 0, saiu || 0)) return { acao: "aplicar" };   /* o PC reiniciou: o normal */
    const n = (e.resetes || []).filter((t) => t > agora - DIA).length + 1;
    if (n >= 2 && !mesmoAjuste(e.salvo, ajusteDeFabrica(placa)))
      return { acao: "travou", motivo: "o driver de vídeo reiniciou 2 vezes em 24 horas", volta: "fabrica", contarReset: true };
    return { acao: "aplicar", contarReset: true };
  }
  return { acao: "aplicar", aviso: "outro" };
}

function mediana(l) {
  const v = (Array.isArray(l) ? l : []).filter(Number.isFinite).slice().sort((a, b) => a - b);
  if (!v.length) return 0;
  const m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

module.exports = { ajusteDaLeitura, ajusteDeFabrica, igual, mesmoAjuste, validar, limparAjuste, reiniciou, decidir, mediana, TESTE_MIN };
