/* Ponte do app do celular (Android): faz o painel (mineracao.html) funcionar com os dados do PC.
   - window.desktop: a mesma interface do celular pelo navegador (remoto, sync, pedirAoPc), com app: true;
   - sincronia com o PC pelo ntfy.sh (sincronia.js), tudo cifrado com a chave do código de vinculação:
     "ola" ao abrir o app (com a versão dos dados que o celular tem), mudanças daqui como "dados", pedidos ao PC;
   - tela de vincular (QR code pela câmera, ou colar o código) enquanto o celular não estiver ligado a um PC.
   Guarda no localStorage: pm-codigo (o código), pm-sinc (versões, o que falta confirmar, quando o PC mandou), pm-aparelho. */
(function () {
  "use strict";
  const VERSAO = "__VERSAO__";
  const SERVIDOR = String(window.__NTFY__ || "https://ntfy.sh").replace(/\/+$/, "");
  const URL_APK = "https://github.com/AlexsAzevedo/painel-mineracao/releases/latest/download/Painel-de-Mineracao.apk";
  const API_VERSAO = "https://api.github.com/repos/AlexsAzevedo/painel-mineracao/releases/latest";
  const S = window.Sincronia, SINC = S.SINCRONIZADAS;
  const nativo = !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
  const plugin = (n) => { try { return nativo && window.Capacitor.registerPlugin ? window.Capacitor.registerPlugin(n) : null; } catch (e) { return null; } };
  const AppP = plugin("App"), DeviceP = plugin("Device");
  const L = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} },
    json(k, d) { try { const v = JSON.parse(localStorage.getItem(k)); return v && typeof v === "object" ? v : d; } catch (e) { return d; } }
  };
  /* versao: até onde o celular tem os dados do PC; vk: a versão de cada chave no PC (vai junto com a mudança feita aqui);
     hashes: o último valor conhecido de cada chave (para saber se mudou); pend: mudanças daqui que o PC ainda não confirmou */
  const vazio = () => ({ versao: 0, vk: {}, hashes: {}, pend: {}, ultimoId: "", ultimaVez: 0, ultimaOla: 0, pc: null, vistos: [], pronto: false, versaoNova: "", conferiuVersao: 0, envios: [] });
  let codigo = S.lerCodigo(L.get("pm-codigo"));
  let est = Object.assign(vazio(), L.json("pm-sinc", {}));
  let aparelho = L.get("pm-aparelho");
  if (!/^[\w-]{8,40}$/.test(aparelho || "")) { aparelho = S.novoId(); L.set("pm-aparelho", aparelho); }
  let nomeAparelho = "";
  let canal = null, abort = null, conectado = false, caiuDesde = 0, olaEsperando = 0, olaId = "", receberFn = null, estadoFn = null;
  let mudT = null, salvarT = null, olaT = null, reenviarT = null, lacunaT = null, esperaEnvio = 5000, enviando = false, tentativasOla = 0;
  const mudados = new Set(), pedidos = new Map();
  const $ = (id) => document.getElementById(id);

  function salvar() { clearTimeout(salvarT); salvarT = setTimeout(() => L.set("pm-sinc", JSON.stringify(est)), 300); }
  function salvarJa() { clearTimeout(salvarT); L.set("pm-sinc", JSON.stringify(est)); }
  const hora = (t) => new Date(t).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  const quandoTxt = (t) => { const d = new Date(t), hoje = new Date(); return d.toDateString() === hoje.toDateString() ? "hoje às " + hora(t) : d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) + " às " + hora(t); };
  function maisNova(a, b) {
    const x = String(a || "0").split(".").map((n) => parseInt(n, 10) || 0), y = String(b || "0").split(".").map((n) => parseInt(n, 10) || 0);
    for (let i = 0; i < 3; i++) { const d = (x[i] || 0) - (y[i] || 0); if (d) return d > 0; }
    return false;
  }

  /* ---------- estado para o painel (selo do canto e faixa de aviso) ---------- */
  function info() {
    return { pc: est.pc, ultimaVez: est.ultimaVez, conectado, pendentes: Object.keys(est.pend).length, versaoNova: maisNova(est.versaoNova, VERSAO) ? est.versaoNova : "", urlApk: URL_APK, vinculado: !!codigo };
  }
  function avisar() {
    if (!estadoFn || !codigo) return;
    const dados = est.ultimaVez ? ` Mostrando os dados do PC de ${quandoTxt(est.ultimaVez)}.` : "";
    const caiu = !conectado && caiuDesde && Date.now() - caiuDesde > 8000;
    const semPc = olaEsperando && Date.now() - olaEsperando > 25000;
    let s;
    if (caiu) s = { ok: false, texto: "Sem internet", aviso: (navigator.onLine === false ? "Sem internet agora." : "Sem conexão com o ntfy.sh agora. Tentando de novo…") + dados };
    else if (semPc) s = { ok: false, texto: "O PC não respondeu", aviso: "O PC não respondeu. Confira se ele está ligado, com o painel aberto e com internet." + dados };
    else s = { ok: true, texto: est.ultimaVez ? `Dados do PC · ${hora(est.ultimaVez)}` : "Ligando ao PC…" };
    try { estadoFn(s); } catch (e) {}
  }

  /* ---------- falar com o PC ---------- */
  const quem = () => ({ id: aparelho, nome: nomeAparelho || "Celular Android", app: VERSAO });
  /* teto de mensagens do app: 40 por hora e 100 por dia (o ntfy.sh aceita 250 por dia de cada internet, e em casa o
     celular divide a conta com o PC). Uso normal fica bem abaixo; o teto só segura um defeito. */
  async function publicar(c) {
    const agora = Date.now();
    est.envios = (est.envios || []).filter((t) => agora - t < 864e5 && t <= agora + 60e3);
    if (est.envios.filter((t) => agora - t < 3600e3).length >= 40 || est.envios.length >= 100) {
      const e = new Error("o app mandou mensagens demais nas últimas horas; espere um pouco"); e.teto = true; throw e;
    }
    const r = await canal.publicar({ aparelho: { id: aparelho }, ...c }, "cel");
    est.envios.push(Date.now()); salvar();
    return r;
  }
  /* "ola": diz ao PC qual versão dos dados este celular tem; o PC responde com o que mudou (e passa a mandar
     as mudanças na hora pelos próximos 20 minutos) e devolve o id da pergunta. Sem forçar, no máximo um a cada 10 minutos.
     Devolve o id (vazio se não deu para mandar). */
  function ola(forcar, pedir) {
    if (!canal) return Promise.resolve("");
    if (!forcar && est.pronto && Date.now() - est.ultimaOla < 10 * 60e3) return Promise.resolve("");
    const id = S.novoId();
    est.ultimaOla = Date.now(); olaEsperando = Date.now(); olaId = id; salvar();
    clearTimeout(olaT); olaT = setTimeout(avisar, 26000);
    return publicar({ id, tipo: "ola", versao: est.pronto ? est.versao : 0, aparelho: quem(), ...(pedir && pedir.length ? { pedir } : {}) })
      .then(() => id)
      .catch((e) => { if (olaId === id) { olaId = ""; olaEsperando = 0; } if (!(e && e.teto)) caiuDesde = caiuDesde || Date.now() - 9000; avisar(); return ""; });
  }
  /* faltou alguma carta (anexo que expirou, celular desligado por muito tempo): pede de novo o que mudou */
  function pedirDeNovo() { clearTimeout(lacunaT); lacunaT = setTimeout(() => ola(true), 1500); }

  async function receber(m) {
    est.ultimoId = m.id; salvar();
    let c = null;
    try { c = await canal.lerMensagem(m, "pc"); } catch (e) { if (e && e.anexoPerdido && est.pronto) pedirDeNovo(); return; }
    if (!c || !c.id || est.vistos.includes(c.id)) return;
    est.vistos.push(c.id);
    if (est.vistos.length > 200) est.vistos.splice(0, est.vistos.length - 200);
    if (c.tipo === "tchau") { desvinculado("O PC desvinculou este celular. Para usar de novo, vincule outra vez."); return; }
    if (c.tipo !== "dados") return;
    /* a resposta à última pergunta: o PC está aí */
    if (olaId && [].concat(c.olas || []).includes(olaId)) { olaId = ""; olaEsperando = 0; clearTimeout(olaT); }
    /* "dados do PC de": quando o PC mandou (a hora do ntfy.sh), não quando o app abriu e leu */
    const quando = Math.min(Date.now(), (Number(m.time) || 0) * 1000 || Date.now());
    est.ultimaVez = Math.max(est.ultimaVez || 0, quando);
    if (c.pc) est.pc = { nome: String(c.pc.nome || "PC").slice(0, 60), app: String(c.pc.app || "").slice(0, 20) };
    const lacuna = Number(c.base) > est.versao;
    /* o PC confirma as mudanças daqui que já viu (aceitas ou não): a partir daí, vale o que ele mandar */
    const ack = c.ack || {};
    for (const k of Object.keys(est.pend)) if (Number(ack[k]) === est.pend[k].t) delete est.pend[k];
    await aplicar(c.chaves || {});
    if (!lacuna && Number(c.versao) > est.versao) est.versao = Number(c.versao);
    if (!est.pronto && !lacuna) { est.pronto = true; esconderVincular(); }
    conferirPendentes();
    responder(c.resps);
    salvar(); avisar();
    if (lacuna && est.pronto) pedirDeNovo();
  }
  /* o que vem do PC entra, menos as chaves com mudança daqui ainda sem confirmação: essas o PC decide quando receber */
  async function aplicar(chaves) {
    const valores = {};
    for (const k of Object.keys(chaves)) {
      const x = chaves[k];
      if (!SINC.includes(k) || !x || typeof x !== "object") continue;
      const v = x.v === null ? null : typeof x.v === "string" ? x.v : undefined;
      if (v === undefined || est.pend[k]) continue;
      valores[k] = v; est.hashes[k] = await S.resumo(v);
      if (Number(x.n) > 0) est.vk[k] = Number(x.n);
    }
    if (Object.keys(valores).length) entregar(valores);
  }
  function entregar(valores) {
    if (receberFn) { try { receberFn(valores); } catch (e) {} return; }
    for (const k of Object.keys(valores)) { if (valores[k] === null) L.del(k); else L.set(k, valores[k]); }
  }
  /* o PC respondeu e uma mudança daqui mandada há mais de 2 minutos continua sem confirmação: a carta se perdeu
     (o PC ficou desligado mais de 12 horas, por exemplo) e vai de novo. Pelo relógio daqui, sem depender do do PC. */
  const REENVIO = 2 * 60e3;
  function conferirPendentes() {
    const agora = Date.now();
    if (Object.values(est.pend).some((p) => !p.enviado || agora - p.enviado > REENVIO)) agendarEnvio(2000);
  }
  function responder(resps) {
    for (const r of [].concat(resps || [])) {
      const p = r && pedidos.get(r.pid);
      if (!p) continue;
      if (r.estado === "rodando") { p.ack = true; clearTimeout(p.tAck); continue; }
      clearTimeout(p.tAck); clearTimeout(p.tFim); pedidos.delete(r.pid);
      const res = { ...r }; delete res.pid; delete res.estado;
      p.ok(res);
    }
  }

  /* mudanças feitas aqui: junta por 1,2 s, confere se mudou de verdade e manda */
  function mudou(k) {
    if (!codigo || !est.pronto || !SINC.includes(k)) return;
    mudados.add(k); clearTimeout(mudT); mudT = setTimeout(() => { juntarMudancas().catch(() => {}); }, 1200);
  }
  async function juntarMudancas() {
    const ks = [...mudados]; mudados.clear();
    let novas = 0;
    for (const k of ks) {
      const h = await S.resumo(L.get(k));
      if (h === est.hashes[k]) continue;
      /* a hora de cada mudança é única (dá para o PC confirmar exatamente esta) */
      const t = Math.max(Date.now(), est.pend[k] ? est.pend[k].t + 1 : 0);
      est.hashes[k] = h; est.pend[k] = { t, enviado: 0 }; novas++;
    }
    if (!novas) return;
    salvar(); avisar(); enviarPendentes();
  }
  function agendarEnvio(ms) { clearTimeout(reenviarT); reenviarT = setTimeout(() => { enviarPendentes(); }, ms); }
  /* manda as mudanças sem confirmação que ainda não foram, ou que foram há mais de 2 minutos */
  async function enviarPendentes() {
    const agora0 = Date.now();
    const ks = Object.keys(est.pend).filter((k) => !est.pend[k].enviado || agora0 - est.pend[k].enviado > REENVIO);
    if (!ks.length || !canal) return;
    if (enviando) { agendarEnvio(1000); return; }
    enviando = true;
    const chaves = {};
    for (const k of ks) chaves[k] = { v: L.get(k), t: est.pend[k].t, n: est.vk[k] || 0 };
    try {
      await publicar({ tipo: "dados", versao: est.versao, chaves });
      const agora = Date.now();
      /* só marca como mandada a mudança que foi mesmo (outra pode ter chegado enquanto mandava) */
      for (const k of ks) if (est.pend[k] && est.pend[k].t === chaves[k].t) est.pend[k].enviado = agora;
      esperaEnvio = 5000; salvar();
      if (Object.values(est.pend).some((p) => !p.enviado)) agendarEnvio(1000);
    } catch (e) {
      agendarEnvio(esperaEnvio); esperaEnvio = Math.min(esperaEnvio * 2, 10 * 60e3);   /* sem internet: tenta de novo */
    } finally { enviando = false; avisar(); }
  }

  /* pedido ao PC: o PC confirma que começou ("rodando") e depois manda o resultado, junto com os dados que mudaram */
  const LIMITE = { "buscar-ofertas": 25 * 60e3, atualizar: 20 * 60e3, analisar: 5 * 60e3, detalhes: 4 * 60e3, parar: 2 * 60e3 };
  function pedirAoPc(nome, args) {
    return new Promise((ok, nao) => {
      if (!canal || !est.pronto) { nao(new Error("este celular ainda não está ligado ao PC")); return; }
      const pid = S.novoId(), p = { nome, ok, ack: false };
      const desistir = (msg) => { if (!pedidos.has(pid)) return; clearTimeout(p.tAck); clearTimeout(p.tFim); pedidos.delete(pid); nao(new Error(msg)); };
      p.armar = () => { clearTimeout(p.tAck); if (!p.ack) p.tAck = setTimeout(() => desistir("o PC não respondeu. Confira se ele está ligado, com o painel aberto e com internet"), 50e3); };
      p.tFim = setTimeout(() => desistir("o PC demorou demais para responder"), LIMITE[nome] || 5 * 60e3);
      pedidos.set(pid, p); p.armar();
      publicar({ tipo: "pedido", pid, nome: String(nome), args: args || {} })
        .catch((e) => desistir(e && (e.status === 429 || e.teto) ? e.message : "sem conexão com a internet agora"));
    });
  }
  /* Atualizar agora: pergunta ao PC e espera a resposta (até 30 s) */
  function atualizar() {
    return new Promise((ok, nao) => {
      if (!canal) { nao(new Error("Este celular não está vinculado a um PC.")); return; }
      ola(true).then((id) => {
        if (!id) { nao(new Error("Sem conexão com a internet agora.")); return; }
        const t0 = Date.now();
        const iv = setInterval(() => {
          if (olaId !== id) { clearInterval(iv); ok(); }   /* respondida */
          else if (Date.now() - t0 > 30000) { clearInterval(iv); nao(new Error("O PC não respondeu. Confira se ele está ligado, com o painel aberto e com internet.")); }
        }, 300);
      });
    });
  }

  /* ---------- escuta do tópico do PC ---------- */
  function escutar() {
    if (abort) abort.abort();
    if (!canal) return;
    const ctrl = new AbortController(); abort = ctrl;
    const desde = est.ultimoId || String(Math.floor(Date.now() / 1000) - 120);
    canal.escutar({ de: "pc", desde, sinal: ctrl.signal, aoReceber: receber,
      aoEstado: (ok) => {
        conectado = ok;
        if (ok) { caiuDesde = 0; if (Object.keys(est.pend).length) agendarEnvio(500); }
        else if (!caiuDesde) caiuDesde = Date.now();
        avisar(); setTimeout(avisar, 8500);
      } }).catch(() => {});
  }
  function pausar() { if (abort) { abort.abort(); abort = null; } conectado = false; }
  /* o app voltou para a frente: reconecta, refaz os prazos dos pedidos e, se faz tempo, pergunta as novidades */
  let voltouEm = 0;
  function voltou() {
    if (!codigo || Date.now() - voltouEm < 1500) return;
    voltouEm = Date.now();
    caiuDesde = 0; escutar();
    for (const p of pedidos.values()) p.armar();
    ola(false); conferirVersaoApp();
    if (Object.keys(est.pend).length) agendarEnvio(1500);
  }

  /* ---------- versão nova do app (Releases do GitHub), no máximo a cada 12 horas ---------- */
  async function conferirVersaoApp() {
    if (Date.now() - (est.conferiuVersao || 0) < 12 * 3600e3) return;
    est.conferiuVersao = Date.now(); salvar();
    try {
      const r = await fetch(API_VERSAO, { cache: "no-store" });
      if (!r.ok) return;
      const j = await r.json(), v = String(j.tag_name || "").replace(/^v/, "");
      if ((j.assets || []).some((a) => a && a.name === "Painel-de-Mineracao.apk") && maisNova(v, VERSAO)) { est.versaoNova = v; salvar(); avisar(); }
    } catch (e) {}
  }

  /* ---------- tela de vincular ---------- */
  const CSS = `
html.pm-vinculando .app{visibility:hidden}
.pm-vinc{position:fixed;inset:0;z-index:200;background:var(--bg);color:var(--fg);overflow-y:auto;font-family:var(--body);
  padding:max(24px,env(safe-area-inset-top)) 20px max(24px,env(safe-area-inset-bottom))}
.pm-c{max-width:420px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
.pm-topo{display:flex;align-items:center;gap:12px}
.pm-topo img{width:52px;height:52px;border-radius:14px}
.pm-topo h1{font-family:var(--display);font-size:1.35rem;line-height:1.2;margin:0}
.pm-topo small{display:block;color:var(--muted);font-size:.8rem;margin-top:2px}
.pm-sub{color:var(--muted);margin:0;line-height:1.5}
.pm-passos{margin:0;padding-left:1.3em;display:flex;flex-direction:column;gap:8px;line-height:1.45}
.pm-passos li::marker{color:var(--muted);font-weight:600}
.pm-botoes{display:flex;flex-direction:column;gap:10px}
.pm-vinc button{font:600 1rem var(--body);padding:13px 16px;border-radius:10px;border:1px solid var(--line);background:var(--surface);color:var(--fg);cursor:pointer}
.pm-vinc button.pri{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.pm-vinc button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pm-vinc label{font-size:.85rem;color:var(--muted);display:block;margin-bottom:6px}
.pm-vinc textarea{width:100%;box-sizing:border-box;font:500 .95rem var(--mono);padding:10px;border-radius:10px;border:1px solid var(--line);background:var(--surface);color:var(--fg);resize:vertical}
.pm-colar{display:flex;flex-direction:column;gap:10px}
.pm-camera{display:flex;flex-direction:column;gap:10px}
.pm-camera .pm-visor{position:relative;border-radius:14px;overflow:hidden;background:#000;aspect-ratio:3/4}
.pm-camera video{width:100%;height:100%;object-fit:cover;display:block}
.pm-camera .pm-mira{position:absolute;inset:18%;border:3px solid rgba(255,255,255,.85);border-radius:16px;box-shadow:0 0 0 999px rgba(0,0,0,.35)}
.pm-esperando{display:flex;flex-direction:column;gap:12px}
.pm-roda{width:28px;height:28px;border-radius:50%;border:3px solid var(--line);border-top-color:var(--accent);animation:pm-gira 1s linear infinite}
@keyframes pm-gira{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion: reduce){.pm-roda{animation-duration:3s}}
.pm-status{margin:0;min-height:1.4em;font-size:.92rem;color:var(--muted)}
.pm-status.erro{color:var(--bad)}
.pm-status.ok{color:var(--good)}
.pm-nota{font-size:.8rem;color:var(--muted);margin:0}`;
  let vincEl = null;
  function montarVincular() {
    if (vincEl) return vincEl;
    const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    vincEl = document.createElement("div");
    vincEl.className = "pm-vinc"; vincEl.id = "pm-vinc";
    vincEl.setAttribute("role", "dialog"); vincEl.setAttribute("aria-modal", "true"); vincEl.setAttribute("aria-labelledby", "pm-t");
    vincEl.innerHTML = `<div class="pm-c">
      <div class="pm-topo"><img src="icone.png" alt=""><div><h1 id="pm-t" tabindex="-1">Painel de Mineração</h1><small>app do celular · versão ${VERSAO}</small></div></div>
      <div id="pm-inicio" class="pm-c" style="gap:16px">
        <p class="pm-sub">Vincule este celular ao painel do seu PC. Os dados ficam no PC e chegam aqui criptografados; o que você mudar aqui vai para lá.</p>
        <ol class="pm-passos"><li>No PC, abra o painel e vá em <b>Premissas › App do celular</b>.</li><li>Clique em <b>Vincular um celular</b>.</li><li>Aqui, toque em <b>Ler o QR code</b> e aponte a câmera para o código da tela do PC.</li></ol>
        <div class="pm-botoes"><button type="button" class="pri" id="pm-ler">Ler o QR code</button><button type="button" id="pm-colar-b">Colar o código</button></div>
        <div class="pm-colar" id="pm-colar" hidden>
          <div><label for="pm-cod">Código do PC (começa com PM1-)</label><textarea id="pm-cod" rows="3" spellcheck="false" autocapitalize="off" autocomplete="off" autocorrect="off"></textarea></div>
          <button type="button" class="pri" id="pm-vincular">Vincular</button>
        </div>
      </div>
      <div id="pm-camera" class="pm-camera" hidden>
        <div class="pm-visor"><video id="pm-video" playsinline muted autoplay></video><div class="pm-mira" aria-hidden="true"></div></div>
        <p class="pm-sub">Aponte para o QR code de vincular, na tela do PC.</p>
        <button type="button" id="pm-cancelar">Cancelar</button>
      </div>
      <div id="pm-esperando" class="pm-esperando" hidden>
        <div class="pm-roda" aria-hidden="true"></div>
        <p class="pm-sub" id="pm-esp-txt">Ligando ao PC…</p>
        <button type="button" id="pm-desistir">Cancelar</button>
      </div>
      <p class="pm-status" id="pm-status" role="status" aria-live="polite"></p>
      <p class="pm-nota">Os avisos (resumo do dia, ofertas, PC parado) continuam chegando pelo app ntfy, se você ligou em Premissas › Avisos no celular.</p>
    </div>`;
    document.body.appendChild(vincEl);
    $("pm-ler").addEventListener("click", lerQr);
    $("pm-colar-b").addEventListener("click", () => { $("pm-colar").hidden = false; $("pm-cod").focus(); });
    $("pm-vincular").addEventListener("click", () => vincular($("pm-cod").value));
    $("pm-cancelar").addEventListener("click", () => { pararCamera(); mostrar("inicio"); status(""); });
    $("pm-desistir").addEventListener("click", () => desvincular(false, ""));
    return vincEl;
  }
  function mostrar(qual) {
    montarVincular();
    for (const q of ["inicio", "camera", "esperando"]) $("pm-" + q).hidden = q !== qual;
  }
  function status(t, tipo) { if (!vincEl) return; const el = $("pm-status"); el.textContent = t || ""; el.className = "pm-status" + (tipo ? " " + tipo : ""); }
  function mostrarVincular(qual, msg, tipo) {
    document.documentElement.classList.add("pm-vinculando");
    mostrar(qual || "inicio");
    if (msg) status(msg, tipo);
  }
  function esconderVincular() {
    pararCamera();
    document.documentElement.classList.remove("pm-vinculando");
    if (vincEl) { vincEl.remove(); vincEl = null; }
    clearInterval(esperaIv);
    const h = document.getElementById("t-resumo"); if (h) try { h.focus({ preventScroll: true }); } catch (e) {}
  }

  /* câmera + jsQR (carregado só na hora de ler) */
  let stream = null, lendo = false;
  function carregarJsQR() {
    if (window.jsQR) return Promise.resolve();
    return new Promise((ok, nao) => { const s = document.createElement("script"); s.src = "jsQR.js"; s.onload = ok; s.onerror = nao; document.head.appendChild(s); });
  }
  async function lerQr() {
    status("");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { status("Este celular não deixa o app usar a câmera. Use Colar o código.", "erro"); return; }
    try { await carregarJsQR(); } catch (e) { status("Não deu para abrir o leitor de QR code. Use Colar o código.", "erro"); return; }
    try { stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 960 } }, audio: false }); }
    catch (e) {
      status(e && e.name === "NotAllowedError" ? "Sem permissão para usar a câmera. Permita a câmera para o app Mineração (Configurações do Android › Apps › Mineração › Permissões) ou use Colar o código."
        : "Não deu para abrir a câmera. Use Colar o código.", "erro");
      return;
    }
    const v = $("pm-video"); v.srcObject = stream;
    mostrar("camera");
    try { await v.play(); } catch (e) {}
    lendo = true;
    const cv = document.createElement("canvas"), ctx = cv.getContext("2d", { willReadFrequently: true });
    let avisouOutro = 0;
    const passo = () => {
      if (!lendo) return;
      if (v.readyState >= 2 && v.videoWidth) {
        const f = Math.min(1, 900 / Math.max(v.videoWidth, v.videoHeight));
        cv.width = Math.round(v.videoWidth * f); cv.height = Math.round(v.videoHeight * f);
        ctx.drawImage(v, 0, 0, cv.width, cv.height);
        const r = window.jsQR(ctx.getImageData(0, 0, cv.width, cv.height).data, cv.width, cv.height, { inversionAttempts: "dontInvert" });
        if (r && r.data) {
          const cod = S.lerCodigo(r.data);
          if (cod) { pararCamera(); vincular(cod); return; }
          if (Date.now() - avisouOutro > 3000) {
            avisouOutro = Date.now();
            status(/\.apk/i.test(r.data) ? "Esse é o código para baixar o app. Aponte para o outro, o de vincular." : "Esse QR code não é do painel. Aponte para o código em Premissas › App do celular, no PC.", "erro");
          }
        }
      }
      setTimeout(passo, 160);
    };
    passo();
  }
  function pararCamera() {
    lendo = false;
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    const v = document.getElementById("pm-video"); if (v) v.srcObject = null;
  }
  let esperaIv = null;
  async function vincular(txt) {
    const cod = S.lerCodigo(txt);
    if (!cod) { status("Esse código não é o do painel. Ele começa com PM1- e aparece em Premissas › App do celular, no PC.", "erro"); return; }
    let c;
    try { c = await S.abrirCanal(cod, { servidor: SERVIDOR }); } catch (e) { status("Esse código não é o do painel.", "erro"); return; }
    /* vínculo novo: esquece o que havia e começa do zero com os dados do PC */
    pausar();
    for (const k of SINC) L.del(k);
    codigo = cod; L.set("pm-codigo", cod);
    est = Object.assign(vazio(), { envios: est.envios || [] }); salvarJa();
    canal = c;
    entregar(Object.fromEntries(SINC.map((k) => [k, null])));
    mostrarVincular("esperando"); status("");
    escutar();
    tentativasOla = 0;
    await ola(true);
    esperarPc();
  }
  /* espera a primeira carta do PC; sem resposta, pergunta de novo a cada minuto (o painel do PC pode estar fechado) */
  function esperarPc() {
    clearInterval(esperaIv);
    const t0 = Date.now();
    const txt = () => { const el = document.getElementById("pm-esp-txt"); if (!el) return;
      const s = Math.round((Date.now() - t0) / 1000);
      el.textContent = s < 20 ? "Ligando ao PC… o PC manda os dados do painel em seguida."
        : "O PC ainda não respondeu. Confira se o painel está aberto no PC e com internet. Continuo tentando."; };
    txt();
    esperaIv = setInterval(() => {
      if (est.pronto) { clearInterval(esperaIv); return; }
      txt();
      /* a cada minuto nas 5 primeiras vezes, depois a cada 10 (cada pergunta é uma mensagem no ntfy.sh) */
      if (Date.now() - est.ultimaOla > (tentativasOla < 5 ? 60e3 : 10 * 60e3) && tentativasOla < 20) { tentativasOla++; ola(true); }
    }, 2000);
  }
  /* desvincular: daqui (avisa o PC) ou porque o PC desvinculou; volta para a tela de vincular, sem os dados */
  async function desvincular(avisarPc, msg) {
    if (canal && avisarPc) { try { await Promise.race([publicar({ tipo: "tchau" }), new Promise((ok) => setTimeout(ok, 3000))]); } catch (e) {} }
    pausar(); canal = null; codigo = null;
    L.del("pm-codigo"); est = Object.assign(vazio(), { envios: est.envios || [] }); salvarJa();
    for (const k of SINC) L.del(k);
    try { if (msg) sessionStorage.setItem("pm-msg", msg); } catch (e) {}
    location.reload();
  }
  function desvinculado(msg) { desvincular(false, msg); }

  /* ---------- começo ---------- */
  window.desktop = Object.freeze({
    versao: VERSAO, remoto: true, app: true,
    sync: Object.freeze({
      mudou,
      aoReceber: (fn) => { receberFn = typeof fn === "function" ? fn : null; },
      aoEstado: (fn) => { estadoFn = typeof fn === "function" ? fn : null; avisar(); },
      atualizar, info
    }),
    pedirAoPc,
    desvincular: () => desvincular(true, "Este celular foi desvinculado. Para usar de novo, vincule outra vez.")
  });
  /* sem vínculo (ou vinculado sem ter recebido os dados ainda): a tela de vincular cobre o painel desde o começo */
  if (!codigo || !est.pronto) {
    const msg = (() => { try { const m = sessionStorage.getItem("pm-msg"); sessionStorage.removeItem("pm-msg"); return m; } catch (e) { return ""; } })();
    if (document.body) mostrarVincular(codigo ? "esperando" : "inicio", msg, "ok");
    else document.addEventListener("DOMContentLoaded", () => mostrarVincular(codigo ? "esperando" : "inicio", msg, "ok"));
  }
  async function iniciar() {
    if (DeviceP) {
      try { const d = await DeviceP.getInfo(); nomeAparelho = String(d.name || [d.manufacturer, d.model].filter(Boolean).join(" ") || "").slice(0, 60); } catch (e) {}
    }
    if (!nomeAparelho) { const m = /Android [\d.]+; ([^;)]+?)(?: Build|\))/.exec(navigator.userAgent); nomeAparelho = m && m[1] !== "K" ? m[1] : "Celular Android"; }
    if (!codigo) return;
    try { canal = await S.abrirCanal(codigo, { servidor: SERVIDOR }); }
    catch (e) { desvincular(false, "O código guardado não vale mais. Vincule de novo."); return; }
    escutar();
    if (!est.pronto) { ola(true); esperarPc(); }
    else { ola(false); if (Object.keys(est.pend).length) agendarEnvio(1500); }
    conferirVersaoApp();
    avisar();
  }
  /* com o app aberto, a cada 10 minutos diz ao PC que continua aqui (assim as mudanças continuam chegando na hora) */
  setInterval(() => { if (codigo && canal && est.pronto && document.visibilityState === "visible") { ola(false); avisar(); } }, 60e3);
  if (AppP) {
    try {
      AppP.addListener("pause", () => pausar());
      AppP.addListener("resume", () => voltou());
      /* voltar do Android: fecha a câmera, a configuração inicial ou volta para o Resumo; no Resumo, sai do app */
      AppP.addListener("backButton", () => {
        if (lendo) { pararCamera(); mostrar("inicio"); status(""); return; }
        const bv = document.getElementById("bv");
        if (!vincEl && bv && !bv.hidden) { const d = document.getElementById("bv-depois"); if (d) d.click(); return; }
        const tela = (location.hash || "#resumo").slice(1);
        if (!vincEl && tela !== "resumo" && typeof window.irPara === "function") { window.irPara("resumo", true); return; }
        AppP.minimizeApp().catch(() => {});
      });
    } catch (e) {}
  }
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") voltou(); });
  window.addEventListener("online", () => { if (codigo) { caiuDesde = 0; escutar(); } });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => { iniciar(); }); else iniciar();
})();
