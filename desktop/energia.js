"use strict";
/* As marcas de energia deste PC, para o painel saber por que a mineração parou: quando o Windows ligou (a hora de agora
   menos o tempo que ele está ligado), quando desligou normalmente (ou reiniciou) e quando suspendeu e acordou.
   Ficam num arquivo da pasta de dados (energia.json: {v: 1, desde, marcas}), gravado na hora a cada marca, porque o
   desligamento do Windows não espera. desde: quando o painel começou a anotar; antes disso, um buraco nas leituras do
   app da Kryptex não tem motivo conhecido. Guarda 30 dias, no máximo 300 marcas. */
const fs = require("fs");
const os = require("os");

const TIPOS = new Set(["desligou", "suspendeu", "acordou"]);   /* "ligou" só vem de registrarLigou */
const DIAS = 30, MAX = 300, MESMA_LIGACAO = 120e3;

function criar({ arquivo, agora = () => Date.now(), uptime = () => os.uptime() }) {
  let e = null;
  try {
    const j = JSON.parse(fs.readFileSync(arquivo, "utf8"));
    if (j && typeof j === "object" && Number.isFinite(j.desde) && Array.isArray(j.marcas))
      e = { v: 1, desde: j.desde, marcas: j.marcas.filter((m) => m && Number.isFinite(m.t) && (TIPOS.has(m.tipo) || m.tipo === "ligou")).map((m) => ({ t: m.t, tipo: m.tipo })) };
  } catch (err) {}
  const novo = !e;
  if (novo) e = { v: 1, desde: agora(), marcas: [] };
  const cortar = () => {
    const lim = agora() - DIAS * 864e5;
    e.marcas = e.marcas.filter((m) => m.t >= lim).sort((a, b) => a.t - b.t).slice(-MAX);
  };
  /* uma falha de escrita (disco cheio, pasta sem permissão) não pode derrubar o programa: a marca fica na memória */
  const gravar = () => { cortar(); try { fs.writeFileSync(arquivo, JSON.stringify(e)); } catch (err) {} };
  if (novo) gravar();
  return {
    /* a ligação do Windows desta vez; abrir o painel de novo na mesma ligação não repete a marca */
    registrarLigou() {
      const t = Math.round(agora() - uptime() * 1000);
      const ult = e.marcas.filter((m) => m.tipo === "ligou").pop();
      if (ult && Math.abs(ult.t - t) <= MESMA_LIGACAO) return ult.t;
      e.marcas.push({ t, tipo: "ligou" });
      gravar();
      return t;
    },
    marcar(tipo) {
      if (!TIPOS.has(tipo)) return;
      e.marcas.push({ t: agora(), tipo });
      gravar();
    },
    estado() {
      cortar();
      return { desde: e.desde, marcas: e.marcas.map((m) => ({ t: m.t, tipo: m.tipo })) };
    }
  };
}

module.exports = { criar };
