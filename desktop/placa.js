"use strict";
/* Os ajustes da placa de vídeo: o estado (placa.json, na pasta de dados), a vigia de cada minuto e as ações da página
   (cuidar, aplicar, de fábrica). Quem fala com a placa é o leitor (placa-amd.js); quem decide é placa-regras.js.
   - Assumir: ao marcar "O painel cuida dos ajustes da placa", guarda o que a placa já tem, sem gravar nada.
   - Aplicar: o ajuste novo fica "em teste" até completar 15 minutos com a placa minerando. O arquivo é gravado (e já no
     disco) antes de pedir ao leitor: se o PC travar logo depois, o painel sabe, na volta, que o ajuste estava em teste.
   - A vigia: confere a placa e aplica de novo quando ela sai do ajuste guardado (o PC reiniciou, o driver reiniciou, outro
     programa mexeu, a ventoinha fixa caiu); um ajuste em teste que trava a placa volta para o último bom.
   - Os avisos ficam em "pendentes" (também no arquivo) até a página pedir o estado(), que os entrega uma vez só.
   Tudo numa fila: a vigia e as ações nunca mandam dois pedidos ao leitor ao mesmo tempo. */
const fs = require("fs");
const R = require("./placa-regras.js");

const ESPERA_ERRO = 10 * 60e3, AVISO_CADA = 3600e3, DIA = 24 * 3600e3, MAX_TRAVOU = 10, MAX_PENDENTES = 20;
const vazio = () => ({ v: 1, cuidar: false, saiu: 0, pendentes: [], placas: {} });
const copia = (o) => (o == null ? o : JSON.parse(JSON.stringify(o)));
const rpmNovo = () => ({ referencia: 0, amostras: [] });

function criar({ arquivo, amd, energia = () => null, agora = Date.now, aoMudar = () => {} }) {
  let st = carregar(), leitura = null, erro = null, fila = Promise.resolve();

  function carregar() {
    try {
      const j = JSON.parse(fs.readFileSync(arquivo, "utf8"));
      if (j && j.v === 1 && j.placas && typeof j.placas === "object" && !Array.isArray(j.placas))
        return { v: 1, cuidar: !!j.cuidar, saiu: Number(j.saiu) || 0, pendentes: Array.isArray(j.pendentes) ? j.pendentes.slice(-MAX_PENDENTES) : [], placas: j.placas };
    } catch (e) {}
    return vazio();
  }
  /* inteiro, e já no disco (como o app-celular.json) */
  function gravar() {
    const tmp = arquivo + ".tmp";
    const fd = fs.openSync(tmp, "w");
    try { fs.writeSync(fd, JSON.stringify(st)); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
    try { fs.renameSync(tmp, arquivo); } catch (e) { fs.copyFileSync(tmp, arquivo); }
  }
  function tentaGravar() { try { gravar(); return true; } catch (e) { return false; } }
  function mudou() { try { aoMudar(); } catch (e) {} }
  function emFila(fn) { const r = fila.then(fn); fila = r.then(() => {}, () => {}); return r; }

  function entrada(chave, nome) {
    if (!st.placas[chave]) st.placas[chave] = { nome, salvo: null, bom: null, bomDesde: 0, teste: null, travou: [], resetes: [], rpm: rpmNovo(), avisos: {}, ultimaVigia: 0, erroAte: 0 };
    const e = st.placas[chave];
    if (nome) e.nome = nome;
    for (const [k, v] of [["travou", []], ["resetes", []], ["avisos", {}]]) if (!e[k] || typeof e[k] !== "object") e[k] = v;
    if (!e.rpm || typeof e.rpm !== "object") e.rpm = rpmNovo();
    return e;
  }

  function situacao(e) {
    if (!st.cuidar) return "sem";
    if (e.teste) return "teste";
    if (e.travou[0] && e.travou[0].quando >= (e.bomDesde || 0)) return "travou";
    return "bom";
  }
  function publico(eventos = []) {
    const placas = {};
    for (const chave of Object.keys(st.placas)) {
      const e = entrada(chave);
      placas[chave] = { nome: e.nome, salvo: e.salvo, bom: e.bom, teste: e.teste, travou: e.travou, situacao: situacao(e), bomDesde: e.bomDesde || 0,
        faltam: e.teste ? Math.max(0, R.TESTE_MIN - (e.teste.minutos || 0)) : null };
    }
    return copia({ cuidar: st.cuidar, leitura, erro, placas, eventos });
  }

  /* ---------- ler ---------- */
  async function lerAgora() {
    const r = await amd.pedir("ler");
    if (r && r.ok) {
      leitura = { quando: agora(), placas: Array.isArray(r.placas) ? r.placas : [], afterburner: !!r.afterburner };
      erro = null;
      for (const p of leitura.placas) if (st.placas[p.chave]) st.placas[p.chave].nome = p.nome;
      return leitura;
    }
    erro = { erro: (r && r.erro) || "falhou", msg: (r && r.msg) || "" };
    return { erro: erro.erro, msg: erro.msg };
  }
  /* troca, na última leitura, a placa que acabou de ser lida de novo (depois de aplicar) */
  function atualizarLeitura(p) {
    if (!p || !p.chave) return;
    if (!leitura) leitura = { quando: agora(), placas: [], afterburner: false };
    const i = leitura.placas.findIndex((x) => x.chave === p.chave);
    if (i >= 0) leitura.placas[i] = p; else leitura.placas.push(p);
    leitura.quando = agora();
  }

  /* ---------- avisos ---------- */
  function avisar(chave, e, tipo, x = {}) {
    const t = agora();
    if (tipo !== "travou" && e.avisos[tipo] && t - e.avisos[tipo] < AVISO_CADA) return;
    e.avisos[tipo] = t;
    const nome = e.nome || "A placa", n = (v) => Math.round(Number(v) || 0).toLocaleString("pt-BR");
    const textos = {
      travou: ["O ajuste da placa travou", `${nome}: ${x.motivo}. ${x.fabrica ? "O painel voltou a placa para o de fábrica." : "O painel voltou para o ajuste anterior."}`],
      outro: ["Outro programa mudou o ajuste da placa", `${nome}: o painel aplicou o seu ajuste de novo. Se for o MSI Afterburner, desligue nele o "Aplicar overclock ao iniciar o sistema".`],
      ventoinha: ["A ventoinha da placa foi para o automático", `${nome}: as rotações caíram de ${n(x.ref)} para ${n(x.rpm)} rpm. O painel gravou a ventoinha de novo.`],
      parou: ["O painel não conseguiu aplicar o ajuste da placa", `${nome}: ${x.msg || "o leitor da placa não respondeu"}. Ele tenta de novo em 10 minutos.`]
    };
    const [titulo, corpo] = textos[tipo];
    st.pendentes = [...st.pendentes, { tipo, chave, nome, titulo, corpo, quando: t }].slice(-MAX_PENDENTES);
  }

  /* ---------- as ações da página ---------- */
  async function estado() {
    const eventos = st.pendentes;
    if (eventos.length) { st.pendentes = []; tentaGravar(); }
    return publico(eventos);
  }

  function ler() { return emFila(() => lerAgora()); }

  function cuidar(sim) {
    return emFila(async () => {
      if (sim && !st.cuidar) {
        const l = await lerAgora();
        if (l.erro) return { ...publico(), falha: l };
        const t = agora();
        st.cuidar = true;
        /* assume o que a placa tem agora, sem gravar nada nela */
        for (const p of l.placas) {
          const e = entrada(p.chave, p.nome);
          Object.assign(e, { salvo: R.ajusteDaLeitura(p), teste: null, resetes: [], rpm: rpmNovo(), erroAte: 0, ultimaVigia: t, bomDesde: t });
          e.bom = e.salvo;
        }
        tentaGravar(); mudou();
        return { ...publico(), assumiu: true };
      }
      if (!sim && st.cuidar) { st.cuidar = false; tentaGravar(); mudou(); }
      return publico();
    });
  }

  function aplicar(chave, ajuste, op = {}) {
    return emFila(async () => {
      if (!st.cuidar) return { ok: false, erro: "pedido", msg: "o painel não está cuidando da placa" };
      const a = R.limparAjuste(ajuste);
      if (!a) return { ok: false, erro: "pedido", msg: "ajuste inválido" };
      const e = st.placas[chave];
      if (!e) return { ok: false, erro: "sem-placa", msg: "a placa não foi encontrada" };
      entrada(chave);
      const t0 = e.travou.find((x) => R.mesmoAjuste(x.ajuste, a));
      if (t0 && !(op && op.mesmoQueTravou)) return { ok: false, precisaConfirmar: true, travou: { quando: t0.quando, motivo: t0.motivo } };
      const antes = copia({ salvo: e.salvo, teste: e.teste, resetes: e.resetes, rpm: e.rpm, erroAte: e.erroAte });
      Object.assign(e, { salvo: a, teste: { ajuste: a, desde: agora(), minutos: 0 }, resetes: [], rpm: rpmNovo(), erroAte: 0 });
      /* gravado antes de aplicar: sem isso, um travamento logo depois não seria visto */
      try { gravar(); } catch (err) { Object.assign(e, antes); return { ok: false, erro: "falhou", msg: "não deu para gravar o estado da placa" }; }
      const r = await amd.pedir("aplicar", { chave, ajuste: a });
      if (!r || !r.ok) {
        Object.assign(e, antes);
        tentaGravar(); mudou();
        return { ok: false, erro: (r && r.erro) || "falhou", msg: (r && r.msg) || "" };
      }
      const lido = R.ajusteDaLeitura(r.placa);
      e.salvo = lido; e.teste.ajuste = lido;
      atualizarLeitura(r.placa);
      tentaGravar(); mudou();
      return { ok: true, itens: r.itens, leitura: r.placa };
    });
  }

  function fabrica(chave) {
    return emFila(async () => {
      if (!st.cuidar) return { ok: false, erro: "pedido", msg: "o painel não está cuidando da placa" };
      const e = st.placas[chave];
      if (!e) return { ok: false, erro: "sem-placa", msg: "a placa não foi encontrada" };
      entrada(chave);
      const r = await amd.pedir("fabrica", { chave });
      if (!r || !r.ok) return { ok: false, erro: (r && r.erro) || "falhou", msg: (r && r.msg) || "" };
      const t = agora(), lido = R.ajusteDaLeitura(r.placa);
      Object.assign(e, { salvo: lido, bom: lido, bomDesde: t, teste: null, resetes: [], rpm: rpmNovo(), erroAte: 0 });
      atualizarLeitura(r.placa);
      tentaGravar(); mudou();
      return { ok: true, itens: r.itens, leitura: r.placa };
    });
  }

  /* ---------- a vigia ---------- */
  async function agir(p, e, d, t) {
    const chave = p.chave;
    if (d.acao === "contar") { e.teste.minutos = (e.teste.minutos || 0) + 1; return false; }
    if (d.acao === "bom") { e.bom = e.salvo; e.teste = null; e.bomDesde = t; return false; }
    if (d.acao === "aplicar") {
      if (d.reiniciarTeste && e.teste) { e.teste.desde = t; e.teste.minutos = 0; }
      if (d.contarReset) e.resetes = [...(e.resetes || []).filter((x) => x > t - DIA), t];
      tentaGravar();
      const ref = e.rpm.referencia, rpm = p.agora ? p.agora.ventoinhaRpm : null;
      const r = await amd.pedir("aplicar", { chave, ajuste: e.salvo });
      if (r && r.ok) {
        e.rpm = rpmNovo();
        atualizarLeitura(r.placa);
        if (d.aviso) avisar(chave, e, d.aviso, { ref, rpm });
      } else {
        e.erroAte = t + ESPERA_ERRO;
        avisar(chave, e, "parou", { msg: r && r.msg });
      }
      return true;
    }
    if (d.acao === "travou") {
      const fabricaJa = d.volta === "fabrica" || !e.bom;
      e.travou = [{ ajuste: e.teste ? e.teste.ajuste : e.salvo, quando: t, motivo: d.motivo }, ...(e.travou || [])].slice(0, MAX_TRAVOU);
      e.teste = null; e.resetes = []; e.rpm = rpmNovo();
      let r;
      if (fabricaJa) {
        e.salvo = e.bom = R.ajusteDeFabrica(p); e.bomDesde = t;
        tentaGravar();
        r = await amd.pedir("fabrica", { chave });
        if (r && r.ok) e.salvo = e.bom = R.ajusteDaLeitura(r.placa);
      } else {
        e.salvo = e.bom;
        tentaGravar();
        r = await amd.pedir("aplicar", { chave, ajuste: e.salvo });
      }
      if (r && r.ok) atualizarLeitura(r.placa); else e.erroAte = t + ESPERA_ERRO;
      avisar(chave, e, "travou", { motivo: d.motivo, fabrica: fabricaJa });
      return true;
    }
    return false;
  }

  function vigiar() {
    return emFila(async () => {
      if (!st.cuidar) return;
      const l = await lerAgora();
      if (l.erro) { mudou(); return; }
      const t = agora(), en = energia();
      for (const p of l.placas) {
        const e = entrada(p.chave, p.nome);
        if (!e.salvo) {
          /* uma placa nova, com o painel já cuidando: assume, como no começo */
          Object.assign(e, { salvo: R.ajusteDaLeitura(p), teste: null, rpm: rpmNovo(), bomDesde: t, ultimaVigia: t });
          e.bom = e.salvo;
          continue;
        }
        const d = R.decidir({ placa: p, e, energia: en, saiu: st.saiu, agora: t });
        const aplicou = await agir(p, e, d, t);
        /* a referência da ventoinha fixa: as 3 primeiras rotações depois de aplicar */
        const rpm = p.agora ? p.agora.ventoinhaRpm : null;
        if (!aplicou && e.salvo && e.salvo.ventoinha && e.salvo.ventoinha.modo === "fixa" && !(e.rpm.referencia > 0) && Number.isFinite(rpm)) {
          e.rpm.amostras = [...(e.rpm.amostras || []), rpm].slice(0, 3);
          if (e.rpm.amostras.length >= 3) e.rpm.referencia = R.mediana(e.rpm.amostras);
        }
        e.ultimaVigia = t;
      }
      tentaGravar(); mudou();
    }).catch(() => {});
  }

  /* o painel saiu pelo Sair: na volta, um PC ligado sem o desligamento normal não conta como travamento */
  function saiu() { st.saiu = agora(); tentaGravar(); }

  return { estado, ler, cuidar, aplicar, fabrica, vigiar, saiu };
}

module.exports = { criar };
