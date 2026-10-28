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
    /* a ligação do Windows desta vez; abrir o painel de novo na mesma ligação não repete a marca. Devolve a hora da
       última ligação */
    registrarLigou() {
      const ag = agora(), t = Math.round(ag - uptime() * 1000);
      const ultima = (tipo) => e.marcas.reduce((x, m) => (m.tipo === tipo && (!x || m.t > x.t) ? m : x), null);
      let mudou = false;
      /* pela hora do boot: o Windows ligou do zero (falta de energia, reinício ou desligamento completo) */
      if (t >= ag - DIAS * 864e5 && !e.marcas.some((m) => m.tipo === "ligou" && Math.abs(m.t - t) <= MESMA_LIGACAO)) { e.marcas.push({ t, tipo: "ligou" }); mudou = true; }
      /* com a inicialização rápida do Windows (o padrão), desligar e ligar não zera o tempo ligado e a hora do boot fica a
         mesma: um desligamento normal depois da última ligação quer dizer que o PC ligou de novo, na hora em que o
         programa abriu (ele abre com o Windows). Sair e entrar no Windows também conta assim */
      const d = ultima("desligou"), l = ultima("ligou");
      if (d && (!l || d.t > l.t)) { e.marcas.push({ t: Math.round(ag), tipo: "ligou" }); mudou = true; }
      if (mudou) gravar();
      const l2 = ultima("ligou");
      return l2 ? l2.t : t;
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
