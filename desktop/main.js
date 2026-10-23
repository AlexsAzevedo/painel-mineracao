"use strict";
/* Painel de Mineração — aplicativo do computador.
   A janela principal mostra o painel (app/index.html, os dados ficam no localStorage deste app).
   Um navegador escondido (sessão própria e permanente) abre as páginas de fora — anúncio do Facebook,
   Kryptex, Promotech, cotação do dólar — e devolve o texto para o painel, no mesmo formato que o
   navegador do app Claude devolvia. */
const { app, BrowserWindow, ipcMain, shell, dialog, Menu, Tray, Notification, nativeImage } = require("electron");
const path = require("path");
const fs = require("fs");
const os = require("os");

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
  /* Windows desligando ou saindo da conta: fecha de verdade, sem segurar o desligamento */
  principal.on("session-end", () => { saindo = true; gravarPendentes(); });
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
  bandeja.setToolTip("Painel de Mineração: procurando ofertas");
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
  notificar({ titulo: "O painel continua aberto", corpo: "Ele fica no ícone perto do relógio, procurando ofertas. Para fechar de vez, clique com o botão direito no ícone e escolha Sair." });
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

ipcMain.handle("navegar", (e, url) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  url = String(url || "");
  if (!/^https?:\/\//i.test(url)) throw new Error("endereço inválido");
  return emFila(async () => {
    const w = pegarLeitor();
    await carregar(w, url);
    return { url: w.webContents.getURL(), title: w.webContents.getTitle() };
  });
});
ipcMain.handle("texto", (e, max) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
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
});
/* busca de anúncios (tela Ofertas e preço das usadas) */
ipcMain.handle("buscar-anuncios", (e, op) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  const site = op && op.site, url = String((op && op.url) || ""), rolar = Math.max(0, Math.min(6, Math.round(Number(op && op.rolar) || 0)));
  if (!urlPermitida(site, url, false)) throw new Error("endereço não permitido");
  return emFila(async () => {
    const w = pegarLeitor();
    await carregar(w, paraTeste(url));
    const r = await rodarNoLeitor(w, `(${site === "fb" ? paginaBuscaFb : paginaBuscaOlx})(${rolar})`);
    return r || { itens: [] };
  });
});
/* um anúncio aberto: texto para ler condição, descrição e vendedor */
ipcMain.handle("detalhes-anuncio", (e, op) => {
  if (!deUmaJanelaNossa(e)) throw new Error("origem não permitida");
  const site = op && op.site, url = String((op && op.url) || "");
  if (!urlPermitida(site, url, true)) throw new Error("endereço não permitido");
  return emFila(async () => {
    const w = pegarLeitor();
    await carregar(w, paraTeste(url));
    const r = await rodarNoLeitor(w, `(${paginaDetalhe})()`);
    return r || {};
  });
});

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
  /* no teste, quem liga a atualização é o próprio teste, depois de subir o servidor de versões de mentira */
  if (TESTE) require("./scripts/teste.js")(principal, { app, mostrarLeitor, pegarLeitor, iniciarAtualizacao, mostrarPrincipal, testeSegundoPlano, segundoPlano: () => ({ ...segundoPlano, temBandeja: !!bandeja }) });
  else iniciarAtualizacao();
});
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => { if (bandeja) { bandeja.destroy(); bandeja = null; } });
