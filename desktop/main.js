"use strict";
/* Painel de Mineração — aplicativo do computador.
   A janela principal mostra o painel (app/index.html, os dados ficam no localStorage deste app).
   Um navegador escondido (sessão própria e permanente) abre as páginas de fora — anúncio do Facebook,
   Kryptex, Promotech, cotação do dólar — e devolve o texto para o painel, no mesmo formato que o
   navegador do app Claude devolvia. */
const { app, BrowserWindow, ipcMain, shell, dialog, Menu, Tray, Notification, nativeImage, net, clipboard } = require("electron");
const path = require("path");
const fs = require("fs");
const os = require("os");
const http = require("http");
const crypto = require("crypto");
const zlib = require("zlib");

const PARTICAO = "persist:navegador";
const TESTE = process.env.PAINEL_TESTE === "1";
/* aberto pelo Windows ao ligar o computador: começa escondido, só com o ícone perto do relógio */
const NA_BANDEJA = process.argv.includes("--na-bandeja");
let principal = null, leitor = null, saindo = false;

/* pasta dos dados: %APPDATA%\painel-mineracao (o mesmo nome da pasta de instalação). Precisa ser sem
   acento: com "Mineração" o Electron desiste da subpasta e grava tudo solto na pasta-mãe. Vem antes da
   trava de instância única, que também mora nessa pasta. */
const PASTA_DADOS = (TESTE && process.env.PAINEL_DADOS) || path.join(app.getPath("appData"), "painel-mineracao");
app.setPath("userData", PASTA_DADOS);
app.setPath("sessionData", PASTA_DADOS);
try { app.setPath("crashDumps", path.join(PASTA_DADOS, "Crashpad")); } catch (e) {}

/* user agent igual ao do Chrome comum (sem o nome do app nem "Electron"), para os sites mostrarem a página normal */
const AGENTE = app.userAgentFallback
  .replace(/\(KHTML, like Gecko\).*?Chrome\//, "(KHTML, like Gecko) Chrome/")
  .replace(/\sElectron\/\S+/, "")
  .replace(/Chrome\/(\d+)[\d.]*/, "Chrome/$1.0.0.0");
app.userAgentFallback = AGENTE;
const agente = () => AGENTE;

/* um painel aberto por vez: abrir de novo só traz a janela que já está aberta para a frente */
const UNICO = app.requestSingleInstanceLock();
if (!UNICO) { app.quit(); }
else {
  app.on("second-instance", () => mostrarPrincipal());
}
app.setAppUserModelId("br.alex.painelmineracao");

/* as placas de vídeo ficam só para a mineração: o painel é desenhado pelo processador */
app.disableHardwareAcceleration();

/* ---------- janela principal ---------- */
const arquivoJanela = () => path.join(app.getPath("userData"), "janela.json");
function lerJanela() { try { return JSON.parse(fs.readFileSync(arquivoJanela(), "utf8")); } catch (e) { return {}; } }
function guardarJanela() {
  try { if (!principal || principal.isDestroyed()) return; fs.writeFileSync(arquivoJanela(), JSON.stringify({ ...principal.getNormalBounds(), max: principal.isMaximized() })); } catch (e) {}
}
function criarPrincipal() {
  const j = lerJanela();
  principal = new BrowserWindow({
    width: j.width || 1360, height: j.height || 900, x: j.x, y: j.y, minWidth: 380, minHeight: 520,
    title: "Painel de Mineração", autoHideMenuBar: true, show: false, backgroundColor: "#17181b",
    icon: path.join(__dirname, "app", "icone.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"), contextIsolation: true, nodeIntegration: false, sandbox: true, spellcheck: false,
      /* sem freio quando a janela está escondida ou minimizada: a busca automática de ofertas continua no ritmo normal
         (e no teste, em que a janela nunca aparece, a página continua desenhando para as fotos) */
      backgroundThrottling: false,
      additionalArguments: [`--painel-versao=${app.getVersion()}`]
    }
  });
  if (j.max) principal.maximize();
  principal.once("ready-to-show", () => { if (!TESTE && !(NA_BANDEJA && segundoPlano.bandeja)) principal.show(); });
  principal.loadFile(path.join(__dirname, "app", "index.html"));
  /* links de lojas, Kryptex etc. abrem no navegador padrão do Windows */
  /* links de fora (https e o e-mail de contato) abrem fora do painel */
  const linkDeFora = (url) => /^https?:\/\//i.test(url) || /^mailto:[^\s"'<>]+$/i.test(url);
  principal.webContents.setWindowOpenHandler(({ url }) => { if (linkDeFora(url)) shell.openExternal(url); return { action: "deny" }; });
  principal.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith("file:")) { e.preventDefault(); if (linkDeFora(url)) shell.openExternal(url); }
  });
  /* grava no disco o que ainda estiver pendente ao fechar, e também se o Windows for desligado com o painel aberto */
  const gravarPendentes = () => { try { principal.webContents.session.flushStorageData(); } catch (e) {} };
  principal.on("close", (e) => {
    guardarJanela(); gravarPendentes();
    /* com o alerta de ofertas rodando com a janela fechada, fechar só esconde (Sair fica no ícone perto do relógio) */
    if (segundoPlano.bandeja && bandeja && !saindo) { e.preventDefault(); principal.hide(); escondeuNaBandeja(); }
  });
  /* Windows desligando ou saindo da conta: fecha de verdade, sem segurar o desligamento
     (e o aviso "o PC parou de dar sinal" continua agendado no celular) */
  principal.on("session-end", () => { saindo = true; encerrandoWindows = true; gravarPendentes(); });
  principal.on("closed", () => { principal = null; if (leitor && !leitor.isDestroyed()) leitor.destroy(); });
}

/* trazer o painel para a frente (ícone perto do relógio, segunda instância, clique num aviso) e, se for o caso, abrir uma tela */
function mostrarPrincipal(tela, chave) {
  if (!principal || principal.isDestroyed()) criarPrincipal();
  if (!TESTE) { if (principal.isMinimized()) principal.restore(); principal.show(); principal.focus(); }
  if (tela) {
    const enviar = () => principal.webContents.send("abrir", { tela: String(tela), chave: String(chave || "") });
    if (principal.webContents.isLoading()) principal.webContents.once("did-finish-load", enviar); else enviar();
  }
}

/* ---------- segundo plano: ícone perto do relógio e abrir junto com o Windows ---------- */
const arquivoSegundoPlano = () => path.join(app.getPath("userData"), "segundo-plano.json");
let segundoPlano = { bandeja: false, iniciar: false, avisouBandeja: false };
let bandeja = null;
const testeSegundoPlano = { escondeu: 0, inicioComWindows: null, notificacoes: [] };
function lerSegundoPlano() { try { segundoPlano = { ...segundoPlano, ...JSON.parse(fs.readFileSync(arquivoSegundoPlano(), "utf8")) }; } catch (e) {} }
function gravarSegundoPlano() { try { fs.writeFileSync(arquivoSegundoPlano(), JSON.stringify(segundoPlano)); } catch (e) {} }
function criarBandeja() {
  if (bandeja) return;
  try {
    bandeja = new Tray(nativeImage.createFromPath(path.join(__dirname, "app", "icone.png")).resize({ width: 32, height: 32 }));
  } catch (e) { bandeja = null; return; }
  bandeja.setToolTip("Painel de Mineração (continua rodando)");
  bandeja.setContextMenu(Menu.buildFromTemplate([
    { label: "Abrir o painel", click: () => mostrarPrincipal() },
    { label: "Ver ofertas", click: () => mostrarPrincipal("ofertas") },
    { type: "separator" },
    { label: "Sair", click: () => { saindo = true; app.quit(); } }
  ]));
  bandeja.on("click", () => mostrarPrincipal());
}
function aplicarSegundoPlano() {
  if (segundoPlano.bandeja) criarBandeja();
  else if (bandeja) { bandeja.destroy(); bandeja = null; }
  const iniciar = !!(segundoPlano.bandeja && segundoPlano.iniciar);
  if (TESTE) testeSegundoPlano.inicioComWindows = iniciar;
  else if (app.isPackaged) { try { app.setLoginItemSettings({ openAtLogin: iniciar, args: ["--na-bandeja"] }); } catch (e) {} }
}
function escondeuNaBandeja() {
  testeSegundoPlano.escondeu++;
  if (segundoPlano.avisouBandeja) return;
  segundoPlano.avisouBandeja = true; gravarSegundoPlano();
  notificar({ titulo: "O painel continua aberto", corpo: "Ele fica no ícone perto do relógio, procurando ofertas e mandando os avisos. Para fechar de vez, clique com o botão direito no ícone e escolha Sair." });
}
/* avisos do Windows; o clique abre o painel na tela do aviso */
function notificar({ titulo, corpo, tela, chave }) {
  const n = { titulo: String(titulo || "").slice(0, 120), corpo: String(corpo || "").slice(0, 500), tela: String(tela || ""), chave: String(chave || "").slice(0, 80) };
  if (TESTE) { testeSegundoPlano.notificacoes.push(n); return true; }
  if (!Notification.isSupported()) return false;
  const aviso = new Notification({ title: n.titulo, body: n.corpo, icon: path.join(__dirname, "app", "icone.png") });
  aviso.on("click", () => mostrarPrincipal(n.tela || null, n.chave));
  aviso.show();
  return true;
}
ipcMain.handle("segundo-plano", (e, op) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  if (op && typeof op === "object") {
    segundoPlano.bandeja = !!op.bandeja; segundoPlano.iniciar = !!op.iniciar;
    gravarSegundoPlano(); aplicarSegundoPlano();
  }
  return { bandeja: segundoPlano.bandeja, iniciar: segundoPlano.iniciar, temBandeja: !!bandeja };
});
ipcMain.handle("notificar", (e, n) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); return notificar(n || {}); });
ipcMain.handle("janela-visivel", (e) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); return !!(principal && principal.isVisible() && !principal.isMinimized()); });
/* a área de transferência do Electron 44 é assíncrona */
ipcMain.handle("copiar", async (e, t) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); await clipboard.writeText(String(t || "").slice(0, 2000)); return true; });

/* ---------- avisos no celular, pelo app ntfy ----------
   O painel publica num "tópico" do ntfy.sh com nome aleatório, que funciona como senha; o celular assina esse tópico no app ntfy.
   - resumo do dia, ofertas boas e avisos: publicados na hora;
   - sinal de vida: a cada 15 minutos o painel reagenda, para daqui a 45 minutos, o aviso "o PC parou de dar sinal". Se o
     computador desliga, trava ou fica sem internet, ninguém reagenda e o próprio ntfy entrega o aviso. No Sair, o aviso é cancelado;
   - o botão Atualizar do resumo, no celular, publica num segundo tópico (o mesmo nome + "-p"), que o painel fica escutando.
   O ntfy.sh aceita 250 mensagens por dia de cada internet: o sinal de vida usa 96. */
const ntfy = () => ((TESTE && process.env.PAINEL_NTFY) || "https://ntfy.sh").replace(/\/+$/, "");
const SINAL_CADA = TESTE ? Math.max(500, Number(process.env.PAINEL_SINAL_MS) || 60000) : 15 * 60e3;
const SINAL_ESPERA_MIN = 45;
const arquivoCelular = () => path.join(app.getPath("userData"), "celular.json");
let celular = { topico: "", ligado: false, resumo: true, hora: "08:00", ofertas: true, sinal: true, iniciar: true, resumoDia: "", ultimoSinal: 0, saiuAMao: false, ultimoEnvio: 0, erro: "" };
let encerrandoWindows = false, atualizandoAgora = false, sinalCancelado = false;
const testeCelular = { publicados: [], cancelados: [], pedidos: 0 };
function lerCelular() { try { celular = { ...celular, ...JSON.parse(fs.readFileSync(arquivoCelular(), "utf8")) }; } catch (e) {} }
function gravarCelular() { try { fs.writeFileSync(arquivoCelular(), JSON.stringify(celular)); } catch (e) {} }
/* 16 letras e números sem os que se confundem (0/o, 1/l/i): fácil de digitar no celular e impossível de adivinhar */
function novoTopico() {
  const A = "abcdefghjkmnpqrstuvwxyz23456789", s = [...require("crypto").randomBytes(16)].map((x) => A[x % A.length]).join("");
  return `painel-${s.slice(0, 4)}-${s.slice(4, 8)}-${s.slice(8, 12)}-${s.slice(12, 16)}`;
}
const celularPublico = () => ({ topico: celular.topico, ligado: celular.ligado, resumo: celular.resumo, hora: celular.hora, ofertas: celular.ofertas, sinal: celular.sinal, iniciar: celular.iniciar !== false,
  resumoDia: celular.resumoDia, ultimoEnvio: celular.ultimoEnvio, ultimoSinal: celular.ultimoSinal, erro: celular.erro, esperaMin: SINAL_ESPERA_MIN });
function avisarCelular() { if (principal && !principal.isDestroyed()) principal.webContents.send("celular", celularPublico()); }
const dataHora = (t) => new Date(t).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).replace(",", "");
const horaMin = (t) => new Date(t).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

/* publica uma mensagem (formato JSON do ntfy); "sinal" não conta como aviso enviado */
async function publicarNtfy(msg, sinal) {
  if (!celular.topico) throw new Error("os avisos no celular estão desligados");
  let r = null;
  try { r = await net.fetch(ntfy() + "/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ topic: celular.topico, ...msg }) }); }
  catch (e) { r = null; }
  const erro = !r ? "sem conexão com o ntfy.sh agora (o computador está sem internet?)"
    : r.status === 429 ? "o ntfy.sh chegou ao limite de mensagens de hoje desta internet; amanhã volta ao normal"
    : !r.ok ? `o ntfy.sh recusou a mensagem (HTTP ${r.status})` : "";
  if (TESTE && !erro) testeCelular.publicados.push(msg);
  if (erro || celular.erro || !sinal) { celular.erro = erro; if (!erro && !sinal) celular.ultimoEnvio = Date.now(); gravarCelular(); avisarCelular(); }
  if (erro) throw new Error(erro);
  return true;
}
/* o que o painel pediu para mandar → mensagem do ntfy (os links e botões são montados aqui) */
function mensagemCelular({ tipo, titulo, corpo, url }) {
  const title = String(titulo || "").slice(0, 200), message = String(corpo || "").slice(0, 3500);
  const link = /^https:\/\/\S{1,800}$/i.test(String(url || "")) ? String(url) : "";
  if (tipo === "resumo") return { title, message, tags: ["bar_chart"], priority: 3, sequence_id: "resumo",
    actions: [{ action: "http", label: "Atualizar", url: `${ntfy()}/${celular.topico}-p`, method: "POST", body: "resumo" }] };
  if (tipo === "oferta") return { title, message, tags: ["moneybag"], priority: 4, ...(link ? { click: link, actions: [{ action: "view", label: "Abrir o anúncio", url: link }] } : {}) };
  if (tipo === "teste") return { title: title || "Painel de Mineração", message: message || "Funcionou! Os avisos do painel vão chegar aqui.", tags: ["white_check_mark"], priority: 3 };
  /* endereço do painel deste PC (rede de casa ou Tailscale): http, com número de porta */
  if (tipo === "endereco") {
    const end = /^http:\/\/[\w.-]{1,64}:\d{2,5}\/?$/i.test(String(url || "")) ? String(url) : "";
    return { title, message, tags: ["iphone"], priority: 3, ...(end ? { click: end, actions: [{ action: "view", label: "Abrir o painel", url: end }] } : {}) };
  }
  return { title, message, tags: ["warning"], priority: 4 };
}

/* sinal de vida: reagenda o aviso de "parou" para daqui a 45 minutos */
let timerSinal = null, sinalEmCurso = false;
async function darSinal() {
  if (!celular.ligado || !celular.sinal || !celular.topico || sinalEmCurso || sinalCancelado) return;
  sinalEmCurso = true;
  try {
    await publicarNtfy({ sequence_id: "pc-sinal", delay: `${SINAL_ESPERA_MIN}m`, title: "O PC parou de dar sinal", tags: ["warning"], priority: 4,
      message: `O Painel de Mineração não dá sinal desde ${dataHora(Date.now())}. O computador pode ter desligado, travado ou ficado sem internet, e a mineração deve ter parado junto.` }, true);
    celular.ultimoSinal = Date.now(); celular.saiuAMao = false; gravarCelular();
  } catch (e) {} finally { sinalEmCurso = false; }
}
async function cancelarSinal(topico) {
  topico = topico || celular.topico; if (!topico) return;
  try { await net.fetch(`${ntfy()}/${topico}/pc-sinal`, { method: "DELETE" }); if (TESTE) testeCelular.cancelados.push(topico); } catch (e) {}
}
/* ao abrir: se ficou mais de 45 minutos sem sinal (sem ter saído pelo Sair), o celular recebeu o aviso; conta que voltou */
async function verificarVolta() {
  if (!celular.ligado || !celular.sinal || !celular.topico || !celular.ultimoSinal || celular.saiuAMao) return false;
  if (Date.now() - celular.ultimoSinal < (SINAL_ESPERA_MIN + 1) * 60e3) return false;
  await publicarNtfy({ title: "O PC voltou", tags: ["white_check_mark"], priority: 3,
    message: `O Painel de Mineração voltou a dar sinal às ${horaMin(Date.now())}. Estava sem sinal desde ${dataHora(celular.ultimoSinal)}.` }).catch(() => {});
  return true;
}

/* escuta o tópico de pedidos (botão Atualizar no celular) */
let escuta = null, ultimoPedido = 0;
const pedidosVistos = new Set();
function pararEscuta() { if (escuta) { try { escuta.abort(); } catch (e) {} escuta = null; } }
function pedidoRecebido(linha) {
  let m = null; try { m = JSON.parse(linha); } catch (e) { return; }
  if (!m || m.event !== "message" || !m.id || pedidosVistos.has(m.id)) return;
  pedidosVistos.add(m.id); if (pedidosVistos.size > 200) pedidosVistos.delete(pedidosVistos.values().next().value);
  if (Date.now() / 1000 - (Number(m.time) || 0) > 600 || !/resumo/i.test(String(m.message || ""))) return;   /* pedido velho ou de outra coisa */
  if (Date.now() - ultimoPedido < 30e3) return;                                                                /* no máximo um a cada 30 segundos */
  ultimoPedido = Date.now();
  if (TESTE) testeCelular.pedidos++;
  if (principal && !principal.isDestroyed()) principal.webContents.send("celular-pedido", { tipo: "resumo" });
}
async function escutarPedidos() {
  pararEscuta();
  const ctrl = new AbortController(); escuta = ctrl;
  let espera = 5000;
  while (escuta === ctrl) {
    try {
      /* since: pega também o que chegou nos últimos 2 minutos (enquanto a conexão caiu); os repetidos são ignorados */
      const r = await net.fetch(`${ntfy()}/${celular.topico}-p/json?since=${Math.floor(Date.now() / 1000) - 120}`, { signal: ctrl.signal, cache: "no-store" });
      if (!r.ok || !r.body) throw new Error(`HTTP ${r.status}`);
      espera = 5000;
      const leitor = r.body.getReader(), dec = new TextDecoder(); let resto = "";
      for (;;) {
        const { value, done } = await leitor.read(); if (done) break;
        resto += dec.decode(value, { stream: true });
        for (let i; (i = resto.indexOf("\n")) >= 0;) { const linha = resto.slice(0, i).trim(); resto = resto.slice(i + 1); if (linha) pedidoRecebido(linha); }
      }
    } catch (e) {}
    if (escuta !== ctrl) return;
    await new Promise((ok) => setTimeout(ok, espera)); espera = Math.min(espera * 2, 10 * 60e3);
  }
}
/* liga/desliga o sinal de vida e a escuta conforme a configuração */
function aplicarSinal() {
  clearInterval(timerSinal); timerSinal = null;
  if (celular.ligado && celular.sinal && celular.topico) { darSinal(); timerSinal = setInterval(darSinal, SINAL_CADA); }
}
function aplicarEscuta() { if (celular.ligado && celular.topico) escutarPedidos(); else pararEscuta(); }
function iniciarCelular() {
  lerCelular();
  verificarVolta().finally(() => { aplicarSinal(); aplicarEscuta(); });
}
ipcMain.handle("celular-config", async (e, op) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  if (op && typeof op === "object") {
    const antes = { ...celular };
    if ("ligado" in op) celular.ligado = !!op.ligado;
    if (op.novoTopico || (celular.ligado && !celular.topico)) { celular.topico = novoTopico(); celular.ultimoSinal = 0; }
    for (const k of ["resumo", "ofertas", "sinal", "iniciar"]) if (k in op) celular[k] = !!op[k];
    if (typeof op.hora === "string" && /^([01]\d|2[0-3]):[0-5]\d$/.test(op.hora)) celular.hora = op.hora;
    if (typeof op.resumoDia === "string" && /^\d{4}-\d{2}-\d{2}$/.test(op.resumoDia)) celular.resumoDia = op.resumoDia;
    if (celular.ligado && !antes.ligado) celular.erro = "";
    gravarCelular();
    const sinalAntes = !!(antes.ligado && antes.sinal && antes.topico), sinalAgora = !!(celular.ligado && celular.sinal && celular.topico);
    const mudouTopico = antes.topico !== celular.topico;
    /* parou de dar sinal (ou trocou o nome): cancela o aviso que estava agendado, senão ele chegaria no celular */
    if (sinalAntes && (!sinalAgora || mudouTopico)) { await cancelarSinal(antes.topico); celular.ultimoSinal = 0; celular.saiuAMao = false; gravarCelular(); }
    if (sinalAntes !== sinalAgora || mudouTopico) aplicarSinal();
    if (antes.ligado !== celular.ligado || mudouTopico) aplicarEscuta();
  }
  return celularPublico();
});
ipcMain.handle("celular-enviar", async (e, m) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  if (!celular.ligado || !celular.topico) throw new Error("os avisos no celular estão desligados");
  await publicarNtfy(mensagemCelular(m || {}));
  return celularPublico();
});
/* Sair pelo painel ou pelo ícone: cancela o aviso agendado (quem fechou sabe que fechou). Desligar o Windows ou
   instalar uma versão nova não cancela: se o painel não voltar, o aviso chega no celular. */
async function sairCancelandoSinal() {
  sinalCancelado = true;
  clearInterval(timerSinal); timerSinal = null; pararEscuta();
  celular.saiuAMao = true; gravarCelular();
  await Promise.race([cancelarSinal(), new Promise((ok) => setTimeout(ok, 3000))]);
}
app.on("before-quit", (e) => {
  if (sinalCancelado || encerrandoWindows || atualizandoAgora) return;
  if (!(celular.ligado && celular.sinal && celular.topico && celular.ultimoSinal)) return;
  e.preventDefault();
  sairCancelandoSinal().finally(() => app.quit());
});

/* ---------- abrir o painel no celular ----------
   O PC serve o painel na rede de casa e na do Tailscale (porta 7777), protegido por uma senha de 6 números.
   Os dados continuam só neste computador: a página do celular chega com um retrato deles, cada mudança no
   celular vem para cá (/api/dados) e cada mudança aqui vai para o celular na hora (/api/eventos). A busca de
   ofertas e a leitura de anúncios pedidas no celular rodam no navegador escondido deste PC (/api/acao). */
const SINCRONIZADAS = ["min-cfg", "min-placas", "min-anuncios", "min-setup", "min-diario", "min-ofertas", "min-ofertas-marcas", "min-ofertas-alerta", "min-ofertas-modelos"];
const arquivoAcesso = () => path.join(app.getPath("userData"), "acesso.json");
let acesso = { ligado: false, porta: 7777, pin: "", segredo: "" };
let servidor = null, servidorErro = "", versaoDados = Date.now(), paginaBaseCache = null, pcAvisouT = null;
const pcMudou = new Set(), eventos = new Set(), tentativas = new Map();
function lerAcesso() { try { acesso = { ...acesso, ...JSON.parse(fs.readFileSync(arquivoAcesso(), "utf8")) }; } catch (e) {} }
function gravarAcesso() { try { fs.writeFileSync(arquivoAcesso(), JSON.stringify(acesso)); } catch (e) {} }
const novoPin = () => String(crypto.randomInt(0, 1000000)).padStart(6, "0");
const novoSegredo = () => crypto.randomBytes(32).toString("hex");
/* sessão do celular: id aleatório + assinatura com o segredo (trocar o segredo desconecta todos os celulares) */
const assinar = (id) => crypto.createHmac("sha256", acesso.segredo).update(id).digest("hex");
const novoToken = () => { const id = crypto.randomBytes(16).toString("hex"); return `${id}.${assinar(id)}`; };
function tokenDe(req) { const m = /(?:^|;\s*)painel=([0-9a-f]{32})\.([0-9a-f]{64})/.exec(String(req.headers.cookie || "")); return m ? { id: m[1], mac: m[2] } : null; }
function autenticado(req) {
  const t = tokenDe(req); if (!t || !acesso.segredo) return false;
  const a = Buffer.from(assinar(t.id), "hex"), b = Buffer.from(t.mac, "hex");
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
function pinCerto(pin) {
  const a = Buffer.from(String(pin || "").replace(/\D/g, "").padEnd(6, "x").slice(0, 6)), b = Buffer.from(String(acesso.pin).padEnd(6, "y").slice(0, 6));
  return a.length === b.length && crypto.timingSafeEqual(a, b) && /^\d{6}$/.test(acesso.pin);
}
/* endereços deste PC: rede de casa e Tailscale (100.64.0.0/10) */
function enderecos() {
  const porta = servidor && servidor.address() ? servidor.address().port : acesso.porta, l = [];
  for (const [rede, ifs] of Object.entries(os.networkInterfaces())) {
    if (/vEthernet|VirtualBox|VMware|WSL|Hyper-V|Loopback|docker|br-|veth/i.test(rede)) continue;
    for (const i of ifs || []) {
      if (i.family !== "IPv4" || i.internal || /^169\.254\./.test(i.address)) continue;
      const ts = /^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\./.test(i.address) || /tailscale/i.test(rede);
      l.push({ tipo: ts ? "tailscale" : "casa", url: `http://${i.address}:${porta}` });
    }
  }
  if (l.some((x) => x.tipo === "tailscale")) l.push({ tipo: "tailscale-nome", url: `http://${os.hostname().toLowerCase()}:${porta}` });
  return l.slice(0, 6);
}
const acessoPublico = () => ({ ligado: acesso.ligado, pin: acesso.pin, porta: servidor && servidor.address() ? servidor.address().port : acesso.porta,
  rodando: !!(servidor && servidor.listening), erro: servidorErro, enderecos: servidor && servidor.listening ? enderecos() : [], conectados: eventos.size });
function avisarAcesso() { if (principal && !principal.isDestroyed()) principal.webContents.send("acesso", acessoPublico()); }

/* dados do painel deste PC (o localStorage da janela principal) */
async function janelaPronta() {
  if (!principal || principal.isDestroyed()) throw new Error("o painel do PC está fechado");
  if (principal.webContents.isLoading()) await new Promise((ok) => principal.webContents.once("did-finish-load", ok));
}
async function lerDadosPc(chaves) {
  await janelaPronta();
  return principal.webContents.executeJavaScript(`(()=>{ const o = {}; for (const k of ${JSON.stringify(chaves)}) o[k] = localStorage.getItem(k); return o; })()`, true);
}
async function aplicarNoPc(chaves) {
  await janelaPronta();
  return principal.webContents.executeJavaScript(`aplicarDadosRemotos(${JSON.stringify(chaves)})`, true);
}
function avisarMudanca(chaves, origem) {
  versaoDados++;
  const msg = `event: mudou\ndata: ${JSON.stringify({ versao: versaoDados, chaves, origem })}\n\n`;
  for (const e of eventos) { try { e.res.write(msg); } catch (err) {} }
}
/* o painel do PC gravou algo: junta as mudanças por 250 ms e avisa os celulares */
ipcMain.on("dados-mudaram", (e, k) => {
  if (!deUmaJanelaNossa(e) || !SINCRONIZADAS.includes(k)) return;
  pcMudou.add(k); clearTimeout(pcAvisouT);
  pcAvisouT = setTimeout(() => { const ks = [...pcMudou]; pcMudou.clear(); if (eventos.size) avisarMudanca(ks, "pc"); else versaoDados++; }, 250);
});

/* página do celular: o mesmo painel, com a ponte que fala com este PC e um retrato dos dados */
function paginaBase() {
  if (paginaBaseCache) return paginaBaseCache;
  let h = fs.readFileSync(path.join(__dirname, "app", "index.html"), "utf8");
  h = h.replace("connect-src 'none'", "connect-src 'self'");
  const cabeca = '<meta name="theme-color" content="#17181b"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">' +
    '<meta name="apple-mobile-web-app-title" content="Mineração"><link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icone.png"><link rel="icon" href="/icone.png">';
  const i = h.indexOf("<script>");
  paginaBaseCache = h.slice(0, i) + cabeca + "<!--DADOS-DO-PC-->" + h.slice(i);
  return paginaBaseCache;
}
const PONTE_CELULAR = `(function(){
  var P = window.__PC__ || {}, c = P.chaves || {};
  /* grava o retrato dos dados do PC antes de o painel ler */
  try{ Object.keys(c).forEach(function(k){ if(c[k] === null) localStorage.removeItem(k); else localStorage.setItem(k, c[k]); }); }catch(e){}
  function acao(nome, args){
    return fetch("/api/acao", {method:"POST", headers:{"Content-Type":"application/json","X-Painel":"1","X-Cliente":P.cliente}, body:JSON.stringify({nome:nome, args:args||{}})})
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(j){ if(!r.ok) throw new Error(j.erro || ("o PC respondeu " + r.status)); return j.resultado; }); });
  }
  window.desktop = Object.freeze({
    versao: P.versaoApp, remoto: true, cliente: P.cliente, versaoDados: P.versao,
    navegar: function(url){ return acao("navegar", {url:String(url||"")}); },
    texto: function(max){ return acao("texto", {max:Number(max)||50000}); },
    buscarAnuncios: function(op){ return acao("buscar-anuncios", {site:String(op&&op.site||""), url:String(op&&op.url||""), rolar:Number(op&&op.rolar)||0}); },
    detalhesAnuncio: function(op){ return acao("detalhes-anuncio", {site:String(op&&op.site||""), url:String(op&&op.url||"")}); }
  });
})();`;
async function paginaCelular() {
  const dados = { versao: versaoDados, chaves: await lerDadosPc(SINCRONIZADAS), cliente: crypto.randomBytes(8).toString("hex"), versaoApp: app.getVersion() };
  const json = JSON.stringify(dados).replace(/</g, "\\u003c").replace(/[\u2028\u2029]/g, (c) => "\\u" + c.charCodeAt(0).toString(16));
  return paginaBase().replace("<!--DADOS-DO-PC-->", `<script>window.__PC__=${json};</script><script>${PONTE_CELULAR}</script>`);
}
const ESTILO_ENTRAR = "body{margin:0;font:16px/1.5 system-ui,sans-serif;background:#17181b;color:#ece9e2;display:flex;min-height:100vh;align-items:center;justify-content:center}" +
  "main{width:min(360px,calc(100% - 32px))}h1{font-size:1.4rem;margin:0 0 8px}p{color:#a9a49a;margin:0 0 18px}" +
  "input{box-sizing:border-box;width:100%;font:600 1.6rem/1 ui-monospace,monospace;letter-spacing:.3em;text-align:center;padding:12px;border-radius:10px;border:1px solid #3a3b40;background:#222327;color:#ece9e2}" +
  "button{margin-top:12px;width:100%;font:600 1rem system-ui,sans-serif;padding:12px;border:0;border-radius:10px;background:#e8a33d;color:#17181b}.erro{color:#ef8a7a;margin-top:12px}";
function paginaEntrar(erro) {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#17181b">` +
    `<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/icone.png"><title>Painel de Mineração</title><style>${ESTILO_ENTRAR}</style></head><body><main>` +
    `<h1>Painel de Mineração</h1><p>Digite a senha de 6 números que aparece no PC, em Premissas › Abrir no celular.</p>` +
    `<form method="post" action="/entrar"><input name="pin" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="one-time-code" aria-label="Senha" required autofocus><button type="submit">Entrar</button></form>` +
    (erro ? `<p class="erro" role="alert">${erro}</p>` : "") + `</main></body></html>`;
}
const MANIFESTO = JSON.stringify({ name: "Painel de Mineração", short_name: "Mineração", start_url: "/", display: "standalone", background_color: "#17181b", theme_color: "#17181b", lang: "pt-BR",
  icons: [{ src: "/icone.png", sizes: "256x256", type: "image/png" }] });

function responder(req, res, status, tipo, corpo, extra) {
  let b = Buffer.isBuffer(corpo) ? corpo : Buffer.from(String(corpo));
  const h = { "Content-Type": tipo, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", ...(extra || {}) };
  if (b.length > 1024 && /gzip/.test(String(req.headers["accept-encoding"] || "")) && /text|json|javascript/.test(tipo)) { b = zlib.gzipSync(b); h["Content-Encoding"] = "gzip"; }
  h["Content-Length"] = b.length;
  res.writeHead(status, h); res.end(req.method === "HEAD" ? undefined : b);
}
const json = (req, res, status, o) => responder(req, res, status, "application/json; charset=utf-8", JSON.stringify(o));
function lerCorpo(req, max) {
  return new Promise((ok, nao) => {
    const partes = []; let n = 0;
    req.on("data", (d) => { n += d.length; if (n > max) { nao(new Error("grande demais")); req.destroy(); } else partes.push(d); });
    req.on("end", () => ok(Buffer.concat(partes).toString("utf8"))); req.on("error", nao);
  });
}
/* no máximo 5 senhas erradas a cada 15 minutos por aparelho */
function bloqueado(ip) { const t = tentativas.get(ip); return t && t.n >= 5 && Date.now() - t.desde < 15 * 60e3 ? Math.ceil((15 * 60e3 - (Date.now() - t.desde)) / 60e3) : 0; }
function errou(ip) { const t = tentativas.get(ip); if (!t || Date.now() - t.desde > 15 * 60e3) tentativas.set(ip, { n: 1, desde: Date.now() }); else t.n++; }
const ACOES = { "navegar": (a) => navegarLeitor(a.url), "texto": (a) => textoLeitor(a.max), "buscar-anuncios": (a) => buscarAnunciosLeitor(a), "detalhes-anuncio": (a) => detalhesAnuncioLeitor(a) };

async function tratarPedido(req, res) {
  const u = new URL(req.url, "http://painel"), p = u.pathname, ip = req.socket.remoteAddress || "";
  try {
    if (p === "/manifest.webmanifest") return responder(req, res, 200, "application/manifest+json", MANIFESTO);
    if (p === "/icone.png") return responder(req, res, 200, "image/png", fs.readFileSync(path.join(__dirname, "app", "icone.png")), { "Cache-Control": "max-age=86400" });
    const fonte = /^\/fonts\/([\w.-]+\.woff2)$/.exec(p);
    if (fonte) { const f = path.join(__dirname, "app", "fonts", fonte[1]); return fs.existsSync(f) ? responder(req, res, 200, "font/woff2", fs.readFileSync(f), { "Cache-Control": "max-age=604800" }) : responder(req, res, 404, "text/plain", "nada"); }
    if (p === "/entrar" && req.method === "POST") {
      const espera = bloqueado(ip);
      if (espera) return responder(req, res, 429, "text/html; charset=utf-8", paginaEntrar(`Muitas tentativas. Tente de novo em ${espera} ${espera === 1 ? "minuto" : "minutos"}.`));
      const pin = new URLSearchParams(await lerCorpo(req, 4096)).get("pin");
      if (!pinCerto(pin)) { errou(ip); return responder(req, res, 401, "text/html; charset=utf-8", paginaEntrar("Senha errada. Confira no PC, em Premissas › Abrir no celular.")); }
      tentativas.delete(ip);
      return responder(req, res, 303, "text/plain", "", { "Location": "/", "Set-Cookie": `painel=${novoToken()}; Path=/; Max-Age=34560000; HttpOnly; SameSite=Strict` });
    }
    if (!autenticado(req)) {
      if (p.startsWith("/api/")) return json(req, res, 401, { erro: "entre de novo com a senha do PC" });
      return responder(req, res, (p === "/" || p === "/entrar") ? 200 : 404, "text/html; charset=utf-8", paginaEntrar(""));
    }
    if (p === "/entrar") return responder(req, res, 303, "text/plain", "", { "Location": "/" });
    if (p === "/" && (req.method === "GET" || req.method === "HEAD")) return responder(req, res, 200, "text/html; charset=utf-8", await paginaCelular());
    if (p === "/api/eventos" && req.method === "GET") {
      res.writeHead(200, { "Content-Type": "text/event-stream; charset=utf-8", "Cache-Control": "no-store", "Connection": "keep-alive", "X-Accel-Buffering": "no" });
      res.write(`retry: 3000\nevent: ola\ndata: ${JSON.stringify({ versao: versaoDados })}\n\n`);
      const e = { res, cliente: u.searchParams.get("cliente") || "" }; eventos.add(e); avisarAcesso();
      const vivo = setInterval(() => { try { res.write(": ok\n\n"); } catch (err) {} }, 20000);
      req.on("close", () => { clearInterval(vivo); eventos.delete(e); avisarAcesso(); });
      return;
    }
    if (p.startsWith("/api/") && req.method === "POST" && req.headers["x-painel"] !== "1") return json(req, res, 403, { erro: "pedido recusado" });
    if (p === "/api/dados" && req.method === "GET") {
      const pedidas = (u.searchParams.get("chaves") || "").split(",").filter((k) => SINCRONIZADAS.includes(k));
      return json(req, res, 200, { versao: versaoDados, chaves: await lerDadosPc(pedidas.length ? pedidas : SINCRONIZADAS) });
    }
    if (p === "/api/dados" && req.method === "POST") {
      const corpo = JSON.parse(await lerCorpo(req, 20 * 1024 * 1024)), chaves = {};
      for (const [k, v] of Object.entries((corpo && corpo.chaves) || {})) if (SINCRONIZADAS.includes(k) && (v === null || typeof v === "string")) chaves[k] = v;
      const mudou = await aplicarNoPc(chaves);
      if (mudou && mudou.length) avisarMudanca(mudou, String(req.headers["x-cliente"] || ""));
      return json(req, res, 200, { versao: versaoDados, mudou: mudou || [] });
    }
    if (p === "/api/acao" && req.method === "POST") {
      const corpo = JSON.parse(await lerCorpo(req, 64 * 1024)), fn = corpo && ACOES[corpo.nome];
      if (!fn) return json(req, res, 400, { erro: "ação desconhecida" });
      try { return json(req, res, 200, { resultado: await fn(corpo.args || {}) }); }
      catch (err) { return json(req, res, 502, { erro: String((err && err.message) || err) }); }
    }
    return responder(req, res, 404, "text/plain", "nada");
  } catch (err) {
    if (!res.headersSent) json(req, res, 500, { erro: String((err && err.message) || err) });
  }
}
function iniciarServidor() {
  if (servidor) return;
  const s = http.createServer(tratarPedido);
  servidor = s; servidorErro = "";
  s.on("error", (e) => { servidorErro = e && e.code === "EADDRINUSE" ? `a porta ${acesso.porta} já está sendo usada por outro programa` : String((e && e.message) || e); if (servidor === s) servidor = null; avisarAcesso(); });
  s.listen(TESTE ? Number(process.env.PAINEL_PORTA || 0) : acesso.porta, "0.0.0.0", () => avisarAcesso());
}
function pararServidor() {
  if (!servidor) return;
  for (const e of eventos) { try { e.res.end(); } catch (err) {} }
  eventos.clear();
  try { servidor.close(); } catch (e) {}
  servidor = null; avisarAcesso();
}
function iniciarAcesso() { lerAcesso(); if (acesso.ligado) iniciarServidor(); }
ipcMain.handle("acesso-config", (e, op) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  if (op && typeof op === "object") {
    if ("ligado" in op) acesso.ligado = !!op.ligado;
    if (acesso.ligado && !/^\d{6}$/.test(acesso.pin)) acesso.pin = novoPin();
    if (acesso.ligado && !acesso.segredo) acesso.segredo = novoSegredo();
    if (op.novoPin) acesso.pin = novoPin();
    /* desconectar os celulares: a sessão de todos deixa de valer */
    if (op.desconectar) { acesso.segredo = novoSegredo(); for (const ev of eventos) { try { ev.res.end(); } catch (err) {} } eventos.clear(); }
    gravarAcesso();
    if (acesso.ligado) iniciarServidor(); else pararServidor();
  }
  return acessoPublico();
});

/* ---------- navegador escondido ---------- */
function criarLeitor() {
  leitor = new BrowserWindow({
    show: false, width: 1280, height: 900, title: "Navegador do Painel", autoHideMenuBar: true,
    icon: path.join(__dirname, "app", "icone.png"),
    webPreferences: { partition: PARTICAO, contextIsolation: true, nodeIntegration: false, sandbox: true, backgroundThrottling: false, spellcheck: false }
  });
  leitor.webContents.setAudioMuted(true);
  leitor.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  /* fechar de verdade: a próxima leitura abre outro navegador escondido (o login fica guardado na sessão).
     Uma janela que nunca apareceu continua desenhando a página, e isso faz a busca do Facebook carregar mais anúncios ao rolar. */
  leitor.on("closed", () => { leitor = null; });
  return leitor;
}
const pegarLeitor = () => (leitor && !leitor.isDestroyed()) ? leitor : criarLeitor();

/* 1 min e meio depois da última leitura o navegador escondido sai da página (o Facebook, por exemplo,
   continua rodando sozinho e gastando processador e memória), a não ser que ele esteja na tela */
let ocioso = null;
function agendarDescanso() {
  clearTimeout(ocioso);
  ocioso = setTimeout(() => {
    if (leitor && !leitor.isDestroyed() && !leitor.isVisible()) leitor.webContents.loadURL("about:blank").catch(() => {});
  }, TESTE ? Number(process.env.PAINEL_DESCANSO || 90000) : 90000);
}

async function carregar(win, url) {
  const tempo = new Promise((ok) => setTimeout(() => ok("tempo"), 25000));
  const r = await Promise.race([win.loadURL(url, { userAgent: agente() }).then(() => "ok", (e) => e), tempo]);
  if (r instanceof Error) {
    /* ERR_ABORTED: o site redirecionou para outra página, que segue carregando */
    if (/ERR_ABORTED|\(-3\)/.test(String(r.message || r.code))) return;
    throw new Error(`não consegui abrir a página (${r.code || r.message})`);
  }
}
const deUmaJanelaNossa = (e) => principal && e.sender === principal.webContents;

/* uma leitura por vez no navegador escondido; enquanto lê, o "descanso" (sair da página) fica suspenso */
let fila = Promise.resolve();
function emFila(fn) {
  const tarefa = async () => { clearTimeout(ocioso); try { return await fn(); } finally { agendarDescanso(); } };
  const p = fila.then(tarefa, tarefa); fila = p.catch(() => {}); return p;
}
/* os scripts de leitura rodam num "mundo" separado da página: veem o que está na tela, mas não mexem nos scripts do site.
   Se a página sair do lugar no meio da leitura, a resposta nunca chega: por isso o limite de tempo. */
const MUNDO = 1012;
const rodarNoLeitor = (w, codigo, ms = 40000) => Promise.race([
  w.webContents.executeJavaScriptInIsolatedWorld(MUNDO, [{ code: codigo }], true),
  new Promise((_, nao) => setTimeout(() => nao(new Error("a página demorou demais para responder")), ms))
]);

/* no teste automático, as páginas do Facebook e da OLX vêm de um servidor local */
function paraTeste(url) {
  const base = TESTE && process.env.PAINEL_REDIRECIONAR;
  if (!base) return url;
  const u = new URL(url);
  if (/(^|\.)facebook\.com$/.test(u.hostname)) return `${base}/fb${u.pathname}${u.search}`;
  if (/(^|\.)olx\.com\.br$/.test(u.hostname)) return `${base}/olx/${u.hostname.split(".")[0]}${u.pathname}${u.search}`;
  return url;
}
/* só o Marketplace e a OLX, por https */
function urlPermitida(site, url, detalhe) {
  let u; try { u = new URL(url); } catch (e) { return false; }
  if (u.protocol !== "https:") return false;
  if (site === "fb") return /^(www\.|m\.)?facebook\.com$/.test(u.hostname) && (detalhe ? /^\/marketplace\/item\/\d+\/?$/ : /^\/marketplace\//).test(u.pathname);
  if (site === "olx") return /^([a-z]{2}|www)\.olx\.com\.br$/.test(u.hostname) && (!detalhe || /-\d{6,}$/.test(u.pathname));
  return false;
}

/* ---------- scripts que rodam dentro da página (sem acesso a nada do aplicativo) ---------- */
/* busca do Marketplace: espera os cards, rola para carregar mais e devolve id + linhas de cada card */
async function paginaBuscaFb(rolar) {
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  const cards = () => document.querySelectorAll('a[href*="/marketplace/item/"]');
  const login = () => !!document.querySelector('input[name="email"], input[name="pass"]') || /\/(login|checkpoint)/.test(location.pathname);
  const vazio = () => /Nenhum (classificado|resultado|anúncio) encontrado|No (listings|results) found/i.test(document.body ? document.body.innerText : "");
  for (let i = 0; i < 24 && !cards().length && !login() && !vazio(); i++) await esperar(500);
  if (!cards().length && login()) return { bloqueio: /checkpoint/.test(location.pathname) ? "verificacao" : "login" };
  let n = cards().length;
  for (let i = 0; i < rolar && n; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await esperar(1300 + Math.random() * 700);
    const m = cards().length; if (m <= n) break; n = m;
  }
  const vistos = new Set(), itens = [];
  for (const a of cards()) {
    const m = a.href.match(/\/marketplace\/item\/(\d+)/);
    if (!m || vistos.has(m[1])) continue;
    vistos.add(m[1]);
    itens.push({ id: m[1], linhas: (a.innerText || "").split("\n").map((s) => s.trim()).filter(Boolean).slice(0, 8) });
  }
  const local = [...document.querySelectorAll("[aria-label]")].map((e) => e.getAttribute("aria-label")).find((t) => /^(Localização|Location):/i.test(t)) || "";
  return { itens, local, url: location.href };
}
/* busca da OLX: os cards já vêm todos na página */
async function paginaBuscaOlx() {
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  const cards = () => document.querySelectorAll("section.olx-adcard");
  const verif = () => /Just a moment|Verifique se você é humano|Attention Required|challenge-platform/i.test(document.title + " " + (document.body ? document.body.textContent.slice(0, 3000) : ""));
  const vazio = () => /Nenhum anúncio encontrado|não encontramos|nenhum resultado|\b0 resultados/i.test(document.body ? document.body.textContent : "");
  for (let i = 0; i < 24 && !cards().length && !vazio(); i++) { if (verif()) return { bloqueio: "verificacao" }; await esperar(500); }
  const itens = [];
  for (const s of cards()) {
    const a = s.querySelector('a[data-testid="adcard-link"], a.olx-adcard__link'); if (!a) continue;
    const q = (sel) => { const e = s.querySelector(sel); return e ? e.textContent.trim() : ""; };
    const tx = s.textContent || "";
    itens.push({ url: a.href, titulo: (a.getAttribute("title") || a.textContent || "").trim(), preco: q(".olx-adcard__price"), antigo: q(".olx-adcard__old-price"),
      local: q(".olx-adcard__location"), data: q(".olx-adcard__date"), entrega: /Entrega Fácil/i.test(tx), garantia: /Garantia da OLX/i.test(tx) });
  }
  return { itens, total: ((document.body.textContent.match(/de ([\d.]+) resultados/) || [])[1] || ""), url: location.href };
}
/* página de um anúncio: o texto do conteúdo principal */
async function paginaDetalhe() {
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  const login = () => !!document.querySelector('input[name="email"], input[name="pass"]') || /\/(login|checkpoint)/.test(location.pathname);
  const principal = () => [...document.querySelectorAll('[role="main"], [role="dialog"], main')].map((e) => e.innerText || "").sort((a, b) => b.length - a.length)[0] || (document.body ? document.body.innerText : "");
  for (let i = 0; i < 24; i++) { const t = principal(); if (/R\$\s?\d/.test(t) && t.length > 200) break; if (login()) break; await esperar(500); }
  const texto = principal();
  if (/Just a moment|Verifique se você é humano|challenge-platform/i.test(document.title + " " + texto.slice(0, 500))) return { bloqueio: "verificacao" };
  if (!/R\$\s?\d/.test(texto) && login()) return { bloqueio: /checkpoint/.test(location.pathname) ? "verificacao" : "login" };
  return { texto: texto.slice(0, 20000), titulo: document.title, url: location.href };
}

function navegarLeitor(url) {
  url = String(url || "");
  if (!/^https?:\/\//i.test(url)) throw new Error("endereço inválido");
  return emFila(async () => {
    const w = pegarLeitor();
    await carregar(w, url);
    return { url: w.webContents.getURL(), title: w.webContents.getTitle() };
  });
}
function textoLeitor(max) {
  return emFila(async () => {
    if (!leitor || leitor.isDestroyed()) return { url: "", title: "", el: "body", text: "" };
    /* como o navegador do app Claude: primeiro o conteúdo principal (article/main), senão a página inteira */
    const r = await rodarNoLeitor(leitor, `(() => {
        const corpo = document.body ? (document.body.innerText || "") : "";
        const el = document.querySelector("article, main, [role=main]");
        const t = el ? (el.innerText || "") : "";
        return t.length >= 200 ? { el: el.tagName.toLowerCase(), text: t } : { el: "body", text: corpo };
      })()`).catch(() => ({ el: "body", text: "" }));
    const n = Math.max(1000, Math.min(200000, Number(max) || 50000));
    return { url: leitor.webContents.getURL(), title: leitor.webContents.getTitle(), el: (r && r.el) || "body", text: String((r && r.text) || "").slice(0, n) };
  });
}
/* busca de anúncios (tela Ofertas e preço das usadas) */
function buscarAnunciosLeitor(op) {
  const site = op && op.site, url = String((op && op.url) || ""), rolar = Math.max(0, Math.min(6, Math.round(Number(op && op.rolar) || 0)));
  if (!urlPermitida(site, url, false)) throw new Error("endereço não permitido");
  return emFila(async () => {
    const w = pegarLeitor();
    await carregar(w, paraTeste(url));
    const r = await rodarNoLeitor(w, `(${site === "fb" ? paginaBuscaFb : paginaBuscaOlx})(${rolar})`);
    return r || { itens: [] };
  });
}
/* um anúncio aberto: texto para ler condição, descrição e vendedor */
function detalhesAnuncioLeitor(op) {
  const site = op && op.site, url = String((op && op.url) || "");
  if (!urlPermitida(site, url, true)) throw new Error("endereço não permitido");
  return emFila(async () => {
    const w = pegarLeitor();
    await carregar(w, paraTeste(url));
    const r = await rodarNoLeitor(w, `(${paginaDetalhe})()`);
    return r || {};
  });
}
const doPainel = (fn) => (e, ...a) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); return fn(...a); };
ipcMain.handle("navegar", doPainel(navegarLeitor));
ipcMain.handle("texto", doPainel(textoLeitor));
ipcMain.handle("buscar-anuncios", doPainel(buscarAnunciosLeitor));
ipcMain.handle("detalhes-anuncio", doPainel(detalhesAnuncioLeitor));

function abrirFacebook() {
  return new Promise((ok) => {
    const w = new BrowserWindow({
      width: 1000, height: 820, title: "Entrar no Facebook", parent: principal || undefined, autoHideMenuBar: true,
      icon: path.join(__dirname, "app", "icone.png"),
      webPreferences: { partition: PARTICAO, contextIsolation: true, nodeIntegration: false, sandbox: true }
    });
    w.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:\/\//i.test(url)) w.loadURL(url, { userAgent: agente() }); return { action: "deny" }; });
    w.loadURL("https://www.facebook.com/login", { userAgent: agente() });
    w.on("closed", () => ok(true));
  });
}
function mostrarLeitor() { const w = pegarLeitor(); w.show(); w.focus(); return true; }
ipcMain.handle("facebook", (e) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); return abrirFacebook(); });
ipcMain.handle("mostrar-navegador", (e) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); return mostrarLeitor(); });

/* ---------- backup ---------- */
ipcMain.handle("salvar-arquivo", async (e, nome, conteudo) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  const sugestao = String(nome || "painel-mineracao.json").replace(/[\\/:*?"<>|]/g, "_");
  let destino = null;
  if (TESTE) destino = path.join(os.tmpdir(), sugestao);
  else {
    const r = await dialog.showSaveDialog(principal, { title: "Salvar backup", defaultPath: path.join(app.getPath("documents"), sugestao), filters: [{ name: "Backup do painel", extensions: ["json"] }] });
    if (r.canceled || !r.filePath) return null;
    destino = r.filePath;
  }
  fs.writeFileSync(destino, String(conteudo), "utf8");
  return destino;
});
ipcMain.handle("abrir-arquivo", async (e) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  const r = await dialog.showOpenDialog(principal, { title: "Importar backup", properties: ["openFile"], filters: [{ name: "Backup do painel", extensions: ["json"] }] });
  if (r.canceled || !r.filePaths[0]) return null;
  if (fs.statSync(r.filePaths[0]).size > 20 * 1024 * 1024) throw new Error("arquivo grande demais");
  return fs.readFileSync(r.filePaths[0], "utf8");
});

/* ---------- atualização automática: as versões novas ficam nas Releases do GitHub ----------
   Procura ao abrir e a cada 6 horas, baixa em segundo plano e instala quando o painel fecha
   (ou na hora, pelo botão "Reiniciar e atualizar"). O que acontece fica em atualizacao.log, na pasta de dados. */
const { NsisUpdater } = require("electron-updater");
let atualizador = null;
let estadoAtualizacao = { estado: "parado" };   /* parado | desligada | procurando | em-dia | baixando | pronta | erro */
function registrarAtualizacao(nivel, msg) {
  try {
    const f = path.join(app.getPath("userData"), "atualizacao.log");
    try { if (fs.statSync(f).size > 512 * 1024) fs.renameSync(f, f + ".antigo"); } catch (e) {}
    fs.appendFileSync(f, `${new Date().toISOString()} ${nivel} ${String(msg).slice(0, 2000)}\n`);
  } catch (e) {}
}
/* notas da versão (vêm do GitHub em HTML) → linhas de texto simples; o painel mostra como texto */
function notasEmTexto(n) {
  const html = Array.isArray(n) ? n.map((x) => (x && x.note) || "").join("\n") : String(n || "");
  return html.replace(/<li[^>]*>/gi, "\n").replace(/<\/(p|li|h\d|div|ul|ol)>|<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&#x27;/g, "'").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&")
    .split("\n").map((s) => s.replace(/^\s*[•*-]\s*/, "").trim()).filter(Boolean).slice(0, 12);
}
function erroAtualizacao(e) {
  const t = `${(e && e.code) || ""} ${(e && e.message) || e}`;
  if (/ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|ERR_INTERNET_DISCONNECTED|ERR_NAME_NOT_RESOLVED|ERR_NETWORK|ERR_CONNECTION|ERR_TIMED_OUT|ERR_PROXY|ERR_ADDRESS_UNREACHABLE/i.test(t)) return "sem conexão com a internet agora";
  if (/LATEST_VERSION_NOT_FOUND|No published versions|HttpError: 404|status code 404/i.test(t)) return "ainda não há nenhuma versão publicada";
  if (/checksum|sha512/i.test(t)) return "o arquivo baixado veio com defeito (o painel baixa de novo na próxima procura)";
  if (/ENOSPC/i.test(t)) return "falta espaço no disco";
  return "erro inesperado (os detalhes ficam em atualizacao.log, na pasta de dados)";
}
function mudarAtualizacao(novo) {
  estadoAtualizacao = { ...novo, versaoAtual: app.getVersion() };
  if (principal && !principal.isDestroyed()) principal.webContents.send("atualizacao", estadoAtualizacao);
}
function procurarAtualizacao() {
  if (!atualizador || !atualizador.isUpdaterActive()) return;
  if (["procurando", "baixando", "pronta"].includes(estadoAtualizacao.estado)) return;   /* já tem uma a caminho */
  /* os erros (da procura e do download) chegam pelo evento "error" */
  atualizador.checkForUpdates().then((r) => { if (r && r.downloadPromise) r.downloadPromise.catch(() => {}); }).catch(() => {});
}
function instalarAtualizacao() {
  registrarAtualizacao("info", "instalar agora (pedido no painel)");
  atualizandoAgora = true;
  mudarAtualizacao({ ...estadoAtualizacao, instalando: true });
  if (TESTE) return;   /* no teste o "instalador" é de mentira */
  guardarJanela();
  try { if (principal) principal.webContents.session.flushStorageData(); } catch (e) {}
  /* silencioso, e abre o painel de novo quando terminar */
  setTimeout(() => atualizador.quitAndInstall(true, true), 400);
}
function iniciarAtualizacao(teste) {
  atualizador = new NsisUpdater();
  atualizador.logger = { info: (m) => registrarAtualizacao("info", m), warn: (m) => registrarAtualizacao("aviso", m), error: (m) => registrarAtualizacao("erro", m), debug: () => {} };
  atualizador.autoDownload = true;
  atualizador.autoInstallOnAppQuit = !TESTE;
  atualizador.disableWebInstaller = true;
  if (teste && teste.config) { atualizador.forceDevUpdateConfig = true; atualizador.updateConfigPath = teste.config; }
  atualizador.on("checking-for-update", () => mudarAtualizacao({ estado: "procurando" }));
  atualizador.on("update-not-available", () => mudarAtualizacao({ estado: "em-dia", procurado: Date.now() }));
  atualizador.on("update-available", (i) => mudarAtualizacao({ estado: "baixando", versao: i.version, notas: notasEmTexto(i.releaseNotes), pct: 0 }));
  atualizador.on("download-progress", (p) => {
    const pct = Math.floor((p && p.percent) || 0);
    if (estadoAtualizacao.estado === "baixando" && pct !== estadoAtualizacao.pct) mudarAtualizacao({ ...estadoAtualizacao, pct });
  });
  atualizador.on("update-downloaded", (i) => mudarAtualizacao({ estado: "pronta", versao: i.version, notas: notasEmTexto(i.releaseNotes) }));
  atualizador.on("error", (e) => mudarAtualizacao({ estado: "erro", erro: erroAtualizacao(e), versao: estadoAtualizacao.versao, procurado: Date.now() }));
  if (!atualizador.isUpdaterActive()) { mudarAtualizacao({ estado: "desligada" }); return; }
  setTimeout(procurarAtualizacao, TESTE ? 1200 : 20000);
  setInterval(procurarAtualizacao, 6 * 3600 * 1000);
}
ipcMain.handle("atualizacao-estado", (e) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); return estadoAtualizacao; });
ipcMain.handle("atualizacao-procurar", (e) => { if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida"); procurarAtualizacao(); return estadoAtualizacao; });
ipcMain.handle("atualizacao-instalar", (e) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  if (estadoAtualizacao.estado !== "pronta" || estadoAtualizacao.instalando) return false;
  instalarAtualizacao();
  return true;
});

/* ---------- backup automático: um arquivo por dia numa pasta (por padrão, Documentos › Painel de Mineração › Backups) ---------- */
const MANTER_BACKUPS = 30;
const arquivoCfgBackup = () => path.join(app.getPath("userData"), "backup.json");
const pastaBackupPadrao = () => TESTE ? path.join(app.getPath("userData"), "backups") : path.join(app.getPath("documents"), "Painel de Mineração", "Backups");
function pastaBackup() { try { const p = JSON.parse(fs.readFileSync(arquivoCfgBackup(), "utf8")).pasta; if (p && fs.existsSync(p)) return p; } catch (e) {} return pastaBackupPadrao(); }
const NOME_BACKUP = /^painel-mineracao-\d{4}-\d{2}-\d{2}\.json$/;
function listarBackups(pasta) {
  try { return fs.readdirSync(pasta).filter((n) => NOME_BACKUP.test(n)).sort(); } catch (e) { return []; }
}
ipcMain.handle("backup-salvar", (e, dia, conteudo) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  dia = String(dia || ""); conteudo = String(conteudo || "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dia)) throw new Error("data inválida");
  if (conteudo.length > 20 * 1024 * 1024) throw new Error("backup grande demais");
  const pasta = pastaBackup();
  fs.mkdirSync(pasta, { recursive: true });
  const nome = `painel-mineracao-${dia}.json`, destino = path.join(pasta, nome), tmp = destino + ".tmp";
  fs.writeFileSync(tmp, conteudo, "utf8"); fs.renameSync(tmp, destino);   /* grava inteiro ou nada */
  const todos = listarBackups(pasta);
  for (const velho of todos.slice(0, Math.max(0, todos.length - MANTER_BACKUPS))) { try { fs.unlinkSync(path.join(pasta, velho)); } catch (err) {} }
  return { arquivo: destino, pasta, total: Math.min(todos.length, MANTER_BACKUPS) };
});
ipcMain.handle("backup-info", (e) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  const pasta = pastaBackup(), l = listarBackups(pasta);
  return { pasta, padrao: pasta === pastaBackupPadrao(), total: l.length, ultimo: l.length ? l[l.length - 1].slice(17, 27) : "", manter: MANTER_BACKUPS };
});
ipcMain.handle("backup-escolher-pasta", async (e) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  let pasta = null;
  if (TESTE) pasta = path.join(app.getPath("userData"), "backups-escolhida");
  else {
    const r = await dialog.showOpenDialog(principal, { title: "Pasta dos backups automáticos", defaultPath: pastaBackup(), properties: ["openDirectory", "createDirectory"] });
    if (r.canceled || !r.filePaths[0]) return null;
    pasta = r.filePaths[0];
  }
  fs.mkdirSync(pasta, { recursive: true });
  fs.writeFileSync(arquivoCfgBackup(), JSON.stringify({ pasta }));
  return pasta;
});
ipcMain.handle("backup-abrir-pasta", async (e) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  const pasta = pastaBackup(); fs.mkdirSync(pasta, { recursive: true });
  if (!TESTE) await shell.openPath(pasta);
  return pasta;
});

/* ---------- menu ---------- */
const AUTOR = { nome: "Alexsander Azevedo", contato: ["alexs_azevedo@hotmail.com", "WhatsApp (79) 99920-2165"] };
function montarMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: "Painel", submenu: [{ label: "Recarregar", role: "reload" }, { label: "Tela cheia", role: "togglefullscreen" }, { type: "separator" }, { label: "Sair", role: "quit" }] },
    { label: "Navegador", submenu: [{ label: "Entrar no Facebook", click: () => abrirFacebook() }, { label: "Mostrar o navegador escondido", click: () => mostrarLeitor() }] },
    { label: "Ajuda", submenu: [
      { label: "Ferramentas do desenvolvedor", role: "toggleDevTools" },
      { label: "Sobre", click: () => dialog.showMessageBox(principal, { type: "info", title: "Sobre o Painel de Mineração", message: `Painel de Mineração ${app.getVersion()}`,
        detail: `Criado por ${AUTOR.nome}\nContato: ${AUTOR.contato.join(" · ")}\n\nDesenvolvido com a ajuda do Claude, a inteligência artificial da Anthropic.\n\nOs dados ficam neste computador, em ${app.getPath("userData")}` }) }
    ] }
  ]));
}

app.on("before-quit", () => { saindo = true; });
if (UNICO) app.whenReady().then(() => {
  montarMenu();
  lerSegundoPlano();
  criarPrincipal();
  aplicarSegundoPlano();
  iniciarCelular();
  iniciarAcesso();
  /* no teste, quem liga a atualização é o próprio teste, depois de subir o servidor de versões de mentira */
  if (TESTE) require("./scripts/teste.js")(principal, { app, mostrarLeitor, pegarLeitor, iniciarAtualizacao, mostrarPrincipal, testeSegundoPlano, segundoPlano: () => ({ ...segundoPlano, temBandeja: !!bandeja }),
    celular: { estado: () => ({ ...celular }), mudar: (o) => { Object.assign(celular, o); gravarCelular(); }, verificarVolta, cancelarSinal, darSinal, sair: sairCancelandoSinal, registro: testeCelular },
    acesso: { estado: acessoPublico, config: () => ({ ...acesso }), versao: () => versaoDados } });
  else iniciarAtualizacao();
});
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => { if (bandeja) { bandeja.destroy(); bandeja = null; } });
