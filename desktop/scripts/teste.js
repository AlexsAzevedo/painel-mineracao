"use strict";
/* Teste automático do aplicativo (PAINEL_TESTE=1): roda dentro do Electron, sem mostrar janela.
   Começa do zero (pasta de dados vazia), passa pela configuração inicial como uma pessoa faria,
   busca ofertas em páginas de teste no formato do Marketplace e da OLX e confere o resultado. */
const http = require("http");
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");

const Sincronia = require("../sincronia.js");
const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
const escXml = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const precoDe = (linhas) => { const l = linhas.find((s) => /^R\$/.test(s)); return l ? +l.replace(/\D/g, "") : 0; };

/* anúncios de mentira, no formato dos cards de busca do Marketplace */
const FB = [
  ["1000000000000001", ["R$1.800", "Placa GeForce 4060 8gb", "Navegantes, SC"]],
  ["1000000000000002", ["R$2.100", "R$2.500", "RTX 3070 Ti 8GB GDDR6X – Placa de Vídeo Gamer", "Blumenau, SC"]],
  ["1000000000000003", ["R$2.500", "PC Gamer i5 10400 RTX 3060", "Itajaí, SC"]],
  ["1000000000000004", ["Acabou de chegar", "R$4.800", "RTX 5070 lacrada nova", "Penha, SC"]],
  ["1000000000000005", ["R$1.300", "RTX 3060 Ti 8GB Funcionando (no estado)", "Balneário Camboriú, SC"]],
  ["1000000000000006", ["R$2.200", "RTX 3070 Ti ROG", "Curitiba, PR"]],
  ["1000000000000007", ["R$2.750", "Rtx 3080 galax 10gb RGB com Caixa", "Joinville, SC"]],
  ["1000000000000008", ["R$5.499", "4070 16gb ti super", "Guabiruba, SC"]],
  ["1000000000000009", ["R$900", "RTX 3070 8GB", "Itajaí, SC"]],
  ["1000000000000010", ["R$3.000", "Notebook Acer Nitro 5 RTX 4060", "Itajaí, SC"]],
  ["1000000000000011", ["R$3.200", "Compro RTX 3080", "Itajaí, SC"]],
  /* estes só aparecem depois de rolar a página */
  ["1000000000000012", ["R$2.000", "RTX 3070 8GB", "Florianópolis, SC"]],
  ["1000000000000013", ["R$2.399", "RTX 5060 8gb", "Joinville, SC"]],
  ["1000000000000014", ["R$1.950", "RTX 3070 Gainward", "São José, SC"]],
  ["1000000000000015", ["R$2.300", "RTX 3070 8gb", "Joinville, SC"]],
  ["1000000000000016", ["R$1.500", "RTX 3070", "Itajaí, SC", "Vendido"]]
];
const PRIMEIROS = 11;
/* alerta de ofertas: na fase 2 aparecem anúncios novos e um baixa de preço; "login" faz o Marketplace pedir login */
const FB_FASE2 = [
  ["1000000000000017", ["R$1.600", "RTX 3070 8GB", "Itajaí, SC"]],             /* nova e compensa: vira aviso */
  ["1000000000000018", ["R$2.900", "RTX 3060 12GB", "Itajaí, SC"]],            /* nova, mas não compensa */
  ["1000000000000019", ["R$850", "RTX 3070 8GB revisada", "Navegantes, SC"]]   /* nova, preço suspeito */
];
const fase = { n: 1, login: false };
const listaFb = () => fase.n < 2 ? FB : [...FB.map(([id, l]) => (id === "1000000000000012" ? [id, ["R$1.700", ...l.slice(1)]] : [id, l])), ...FB_FASE2];
/* cards da OLX: [url, título, preço, local, data, entrega fácil, garantia da OLX] */
const OLX = {
  sc: [
    ["https://sc.olx.com.br/norte-de-santa-catarina/informatica/placas-de-video/placa-de-video-rtx-4060-galax-8gb-1546350701", "Placa de vídeo RTX 4060 Galax 8GB", "R$ 1.850", "Navegantes, São Domingos", "Ontem, 19:06", true, false],
    ["https://sc.olx.com.br/florianopolis-e-regiao/informatica/pecas-de-hardware/rtx-5060ti-8gb-msi-1543531037", "RTX 5060TI 8GB MSI", "R$ 3.000", "Florianópolis, Rio Vermelho", "12 de out, 10:46", true, true],
    ["https://sc.olx.com.br/norte-de-santa-catarina/informatica/placas-de-video/rtx-3080-galax-10gb-1545290099", "Rtx 3080 galax 10gb", "R$ 2.750", "Joinville, Espinheiros", "18 de out, 14:31", false, false],
    ["https://sc.olx.com.br/oeste-de-santa-catarina/informatica/placas-de-video/rtx-3070-1541068483", "RTX 3070", "R$ 1.900", "Chapecó, Centro", "3 de out, 12:56", false, false],
    ["https://sc.olx.com.br/norte-de-santa-catarina/informatica/computadores-e-desktops/pc-gamer-5600-32gb-rtx-3070-1546603380", "PC Gamer 5600 - 32GB - RTX 3070", "R$ 2.900", "Blumenau, Centro", "Hoje, 14:18", true, false]
  ],
  pr: [
    ["https://pr.olx.com.br/regiao-de-curitiba-e-paranagua/informatica/placas-de-video/placa-de-video-rtx-3070-gamingpro-1569359811", "Placa de Vídeo RTX 3070 GamingPro", "R$ 2.000", "Guaratuba, Centro", "20 de out, 09:12", false, false],
    ["https://pr.olx.com.br/regiao-de-curitiba-e-paranagua/informatica/placas-de-video/rtx-3060-ti-1569359812", "RTX 3060 Ti", "R$ 1.700", "Curitiba, Centro", "21 de out, 08:00", false, false]
  ]
};
const DETALHE_FB = ["Rtx 3080 galax 10gb RGB com Caixa", "R$2.750", "Anunciado há uma semana em Joinville, SC", "Envie uma mensagem ao vendedor", "Enviar", "Salvar", "Compartilhar", "Detalhes",
  "Condição", "Usado — seminovo", "Rtx 3080 galax 10gb RGB. Placa sem defeito, nunca usada em mineração, funcionando perfeitamente, com caixa.", "Joinville, SC · A localização é aproximada",
  "Informações do vendedor", "Detalhes do vendedor", "Hermes Hilbert Junior", "(45)", "Com alta classificação no Marketplace", "Entrou no Facebook em 2011"];
const DETALHE_OLX = ["RTX 5060TI 8GB MSI", "Entrega Fácil", "Parcele sem juros", "Garantia da OLX", "R$ 3.000", "R$ 2.910", "no Pix", "Comprar", "Chat", "Descrição",
  "Placa de vídeo MSI RTX 5060 Ti Ventus 2X com 8GB GDDR7.", "Ver descrição completa", "Detalhes", "Categoria", "Peças De Hardware", "Condição", "Usado - Excelente",
  "Sobre o anunciante", "Conta verificada", "Alex", "Último acesso há 21 horas", "Na OLX desde outubro de 2026", "00", "Vendas concluídas", "Publicado em 12/10 às 10:46"];

function paginaBuscaFb(q) {
  if (fase.login) return `<!doctype html><html><head><meta charset="utf-8"><title>Facebook – entre ou cadastre-se</title></head><body><form><input name="email"><input name="pass" type="password"><button>Entrar</button></form></body></html>`;
  const min = +q.get("minPrice") || 0, max = +q.get("maxPrice") || Infinity;
  const lista = listaFb().map(([id, l], i) => ({ id, l, i })).filter((x) => { const p = precoDe(x.l); return p >= min && p <= max; });
  const card = (x) => `<a href="/marketplace/item/${x.id}/?ref=search" style="display:block;height:150px"><img src="https://scontent.teste.fbcdn.net/v/t45/${x.id}.jpg" alt="" width="1" height="1">${x.l.map((s) => `<div>${esc(s)}</div>`).join("")}</a>`;
  const primeiros = lista.filter((x) => x.i < PRIMEIROS).map(card), resto = lista.filter((x) => x.i >= PRIMEIROS).map(card);
  return `<!doctype html><html><head><meta charset="utf-8"><title>Facebook</title></head><body>
    <div role="banner">menu do topo</div><div aria-label="Localização: Itajaí, No raio de ${esc(q.get("radius") || "40")} km">Itajaí · 40 km</div>
    <div role="main" id="lista">${primeiros.join("")}</div><div id="fim" style="height:20px"></div>
    <script>const resto = ${JSON.stringify(resto)}; let i = 0;
      new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting) && i < resto.length) { const b = resto.slice(i, i + 4); i += 4;
        setTimeout(() => document.getElementById("lista").insertAdjacentHTML("beforeend", b.join("")), 300); } }).observe(document.getElementById("fim"));</script>
  </body></html>`;
}
function paginaBuscaOlx(uf, q) {
  const min = +q.get("ps") || 0, max = +q.get("pe") || Infinity;
  const cards = (OLX[uf] || []).filter((c) => { const p = +c[2].replace(/\D/g, ""); return p >= min && p <= max; }).map(([url, t, p, l, d, ent, gar]) =>
    `<section class="olx-adcard olx-adcard__horizontal"><picture><img src="https://img.olx.com.br/thumbs500x360/${esc(url.split("-").pop())}.jpg" alt="" width="1" height="1"></picture><div class="olx-adcard__content"><a data-testid="adcard-link" class="olx-adcard__link" title="${esc(t)}" href="${esc(url)}"><h2 class="olx-adcard__title">${esc(t)}</h2></a>
      <div class="olx-adcard__badges">${ent ? "<div>Entrega Fácil</div>" : ""}${gar ? "<div>Garantia da OLX</div>" : ""}</div>
      <h3 class="olx-adcard__price">${esc(p)}</h3><p class="olx-adcard__location">${esc(l)}</p><p class="olx-adcard__date">${esc(d)}</p></div></section>`);
  return `<!doctype html><html><head><meta charset="utf-8"><title>"${esc(q.get("q") || "")}" | OLX</title></head><body><main><p>1 - ${cards.length} de ${cards.length} resultados</p>${cards.join("")}</main></body></html>`;
}
const paginaTexto = (titulo, linhas, papel) => `<!doctype html><html><head><meta charset="utf-8"><title>${esc(titulo)}</title></head><body><div ${papel}>${linhas.map((s) => `<div>${esc(s)}</div>`).join("")}</div></body></html>`;

/* um QR code (o SVG que o PC mostra) em pixels: cada quadradinho do SVG vira um bloco escuro numa imagem clara */
function qrDoSvg(svg, escala) {
  const vb = /viewBox="0 0 (\d+) (\d+)"/.exec(svg), lado = +vb[1] * escala;
  const px = new Uint8ClampedArray(lado * lado).fill(255);
  for (const m of svg.matchAll(/M(\d+),(\d+)l(\d+),0/g)) {
    const x0 = +m[1] * escala, y0 = +m[2] * escala, t = +m[3] * escala;
    for (let y = y0; y < y0 + t; y++) px.fill(20, y * lado + x0, y * lado + x0 + t);
  }
  return { lado, px };
}
/* vídeo Y4M (a "câmera" do Chromium no teste): o QR no meio de uma mesa cinza */
function videoDoQr(q, arquivo) {
  const W = 640, H = 480, Y = Buffer.alloc(W * H, 190), x0 = (W - q.lado) >> 1, y0 = (H - q.lado) >> 1;
  for (let y = 0; y < q.lado; y++) for (let x = 0; x < q.lado; x++) Y[(y0 + y) * W + x0 + x] = q.px[y * q.lado + x];
  const UV = Buffer.alloc((W / 2) * (H / 2), 128), quadro = Buffer.concat([Buffer.from("FRAME\n"), Y, UV, UV]);
  fs.writeFileSync(arquivo, Buffer.concat([Buffer.from(`YUV4MPEG2 W${W} H${H} F15:1 Ip A1:1 C420jpeg\n`), ...Array(20).fill(quadro)]));
}

module.exports = function (principal, { app, pegarLeitor, iniciarAtualizacao, mostrarPrincipal, testeSegundoPlano, segundoPlano, comoAbrir, testeArquivos, testeKryptex, celular: celularMain, acesso: acessoMain, appCelular: appMain }) {
  /* versões de mentira no formato das Releases do GitHub, para a atualização automática.
     modo "igual": a última versão publicada é a que está instalada; "defeito": versão nova com o arquivo corrompido; "ok": versão nova certa */
  const versaoApp = app.getVersion(), proxima = versaoApp.replace(/(\d+)$/, (n) => String(+n + 1));
  const instalador = crypto.randomBytes(256 * 1024), shaInstalador = crypto.createHash("sha512").update(instalador).digest("base64");
  const atu = { modo: "vazio", pedidos: [] };   /* "vazio": o repositório ainda não tem nenhuma versão publicada */
  const versaoServida = () => (atu.modo === "igual" ? versaoApp : proxima);
  const nomeInstalador = (v) => `Painel-de-Mineracao-Setup-${v}.exe`;
  const ymlVersao = (v) => {
    const sha = atu.modo === "defeito" ? crypto.createHash("sha512").update("outro arquivo").digest("base64") : shaInstalador;
    return `version: ${v}\nfiles:\n  - url: ${nomeInstalador(v)}\n    sha512: ${sha}\n    size: ${instalador.length}\npath: ${nomeInstalador(v)}\nsha512: ${sha}\nreleaseDate: '2026-10-22T18:00:00.000Z'\n`;
  };
  const feedVazio = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-US"><id>tag:github.com,2008:https://github.com/teste/painel-mineracao/releases</id><title>Release notes from painel-mineracao</title><updated>2026-10-22T18:00:00Z</updated></feed>`;
  const feedAtom = (v) => `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-US">
  <id>tag:github.com,2008:https://github.com/teste/painel-mineracao/releases</id>
  <title>Release notes from painel-mineracao</title>
  <updated>2026-10-22T18:00:00Z</updated>
  <entry>
    <id>tag:github.com,2008:Repository/1/v${v}</id>
    <updated>2026-10-22T18:00:00Z</updated>
    <link rel="alternate" type="text/html" href="https://github.com/teste/painel-mineracao/releases/tag/v${v}"/>
    <title>Versão ${v}</title>
    <content type="html">${escXml("<ul><li>Alerta de ofertas boas perto de você &amp; aviso no Windows</li><li>Correções &lt;menores&gt;</li></ul>")}</content>
    <author><name>teste</name></author>
  </entry>
</feed>`;
  const SAIDA = process.env.PAINEL_SAIDA || os.tmpdir();
  const fx = (n) => fs.readFileSync(path.join(process.env.PAINEL_FIXOS, n), "utf8");
  const emDivs = (txt) => txt.split("\n").map((l) => `<div>${esc(l)}</div>`).join("");
  const pedidos = [], agentes = [];
  /* conta da Kryptex de mentira: sem o cookie de sessão, a página pede login; "entrando" é a janela de login (o teste
     faz de conta que a pessoa entrou: a resposta grava o cookie); "desafio" serve antes a verificação contra robôs, que
     recarrega a página sozinha; a lista de máquinas vai num <script type="application/json" id="workerDataset">, como no site */
  const kxf = { entrando: false, desafio: 0, pedidos: [], saldo: "0.00010000", fiat: "$6.80",
    maquinas: [{ name: "RIG-ALEX", coin: "xtm", scheme: "pplns", agent: "lolMiner 1.92", is_online: true, avg_hashrate_30m: 58300000, avg_hashrate_24h: 60100000, profit_daily: 1.23, profit_monthly: 36.9, valid: 1234, stale: 3, invalid: 0 }] };
  const paginaKx = (titulo, corpo, extra) => `<html><head><title>${titulo} | Kryptex</title></head><body><header><span>alex.teste@example.com</span><span>ID 7f3a9c2e1b4d5f60718293a4b5c6d7e8f9</span></header><main><h1>${titulo}</h1>${corpo}</main>${extra || ""}</body></html>`;
  function respostaKryptex(req, res, p) {
    const logado = /(^|;\s*)kxsessao=1/.test(String(req.headers.cookie || ""));
    kxf.pedidos.push(p + (logado ? "" : " (sem login)"));
    const cab = { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" };
    if (!logado) {
      if (kxf.entrando) { kxf.entrando = false; cab["Set-Cookie"] = "kxsessao=1; Path=/; HttpOnly"; }
      res.writeHead(200, cab); res.end(paginaKx("Log in", '<form><input name="email" type="email"><input name="password" type="password"><button>Log in</button></form>'));
      return;
    }
    if (kxf.desafio > 0) {
      kxf.desafio--;
      res.writeHead(200, cab); res.end(`<html><head><title>Kryptex</title></head><body><div class="gorizontal-vertikal">Verificando o navegador…</div><script>setTimeout(()=>location.reload(), 800)</script></body></html>`);
      return;
    }
    if (p === "/kryptex/site/hardware") { res.writeHead(200, cab); res.end(paginaKx("Hardware", kxf.maquinas.map((m) => `<div>${esc(m.name)}</div><div>${m.is_online ? "Online" : "Offline"}</div>`).join(""), `<script id="workerDataset" type="application/json">${JSON.stringify(kxf.maquinas)}</script>`)); return; }
    if (p === "/kryptex/site/dashboard") { res.writeHead(200, cab); res.end(paginaKx("Dashboard", `<div>Balance</div><div>${kxf.saldo} BTC</div><div>≈ ${kxf.fiat}</div><div>Withdraw</div><div>Wallet bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh</div>`)); return; }
    res.writeHead(404, cab); res.end("nada");
  }
  /* ntfy de mentira (avisos no celular e app do celular): guarda o que o painel publicou, agenda/substitui/cancela o "sinal de vida"
     como o ntfy.sh faz (mesmo sequence_id substitui o agendado), guarda as cartas da sincronia e os anexos e entrega a quem escuta */
  let baseNtfy = "";
  const falso = require("./ntfy-falso.js")(() => baseNtfy), ntfy = falso.ntfy;
  /* o botão Atualizar no celular: uma mensagem chega no tópico de pedidos (o nome dos avisos + "-p") */
  const ntfyPedir = (texto) => { for (const t of new Set(ntfy.escutas.map((e) => e.topico).filter((t) => /^painel-.*-p$/.test(t)))) falso.entregar(t, texto); };
  const ntfyUltimo = (filtro) => ntfy.publicados.filter(filtro).slice(-1)[0] || null;
  const srv = http.createServer((req, res) => {
    const u = new URL(req.url, "http://x"), p = u.pathname;
    if (p === "/ntfy" || p.startsWith("/ntfy/")) { falso.tratar(req, res, u, p.slice(5)); return; }
    pedidos.push(p + u.search);
    let corpo = null, tipo = "text/html; charset=utf-8";
    /* releases (a atualização usa o próprio identificador, "electron-builder"; o navegador escondido não passa por aqui) */
    if (/^\/(teste|api)\//.test(p)) {
      atu.pedidos.push(p);
      const m = /\/releases\/download\/v([\d.]+)\/(.+)$/.exec(p);
      if (p === "/teste/painel-mineracao/releases.atom") { corpo = atu.modo === "vazio" ? feedVazio : feedAtom(versaoServida()); tipo = "application/atom+xml; charset=utf-8"; }
      else if (p === "/api/v3/repos/teste/painel-mineracao/releases/latest") { corpo = JSON.stringify({ tag_name: "v" + versaoServida() }); tipo = "application/json"; }
      else if (m && /^latest(-linux)?\.yml$/.test(m[2])) { corpo = ymlVersao(m[1]); tipo = "text/yaml"; }
      else if (m && m[2] === nomeInstalador(m[1])) { res.writeHead(200, { "Content-Type": "application/octet-stream", "Content-Length": instalador.length, "Cache-Control": "no-store" }); res.end(instalador); return; }
      res.writeHead(corpo ? 200 : 404, { "Content-Type": tipo, "Cache-Control": "no-store" }); res.end(corpo || "nada"); return;
    }
    agentes.push(String(req.headers["user-agent"] || ""));
    if (p.startsWith("/kryptex/")) { respostaKryptex(req, res, p); return; }
    if (p === "/fb/marketplace/category/search/") corpo = paginaBuscaFb(u.searchParams);
    else if (/^\/fb\/marketplace\/item\/1000000000000007\/?$/.test(p)) corpo = paginaTexto("Marketplace — Rtx 3080 galax 10gb RGB com Caixa | Facebook", DETALHE_FB, 'role="main"');
    else if (/^\/olx\/www\/estado-(sc|pr)$/.test(p)) corpo = paginaBuscaOlx(p.slice(-2), u.searchParams);
    else if (/^\/olx\/sc\/.*-1543531037$/.test(p)) corpo = paginaTexto("RTX 5060TI 8GB MSI | OLX", DETALHE_OLX, "");
    else if (p === "/promo") corpo = `<html><head><title>RTX 5060 Ti 16GB vs RTX 5060 Ti 8GB | Promotech</title></head><body><main>${emDivs(fx("promo_5060ti.txt"))}</main></body></html>`;
    else if (p === "/dolar") { corpo = '{"USDBRL":{"code":"USD","codein":"BRL","bid":"5.0497","create_date":"2026-10-22 11:49:25"}}'; tipo = "application/json"; }
    res.writeHead(corpo ? 200 : 404, { "Content-Type": tipo });
    res.end(corpo || "nada");
  }).listen(0, "127.0.0.1", () => {
    const base = `http://127.0.0.1:${srv.address().port}`;
    process.env.PAINEL_REDIRECIONAR = base;
    process.env.PAINEL_NTFY = base + "/ntfy";
    baseNtfy = base + "/ntfy";
    principal.webContents.once("did-finish-load", async () => {
      const r = { erros: [], passos: {} };
      principal.webContents.on("console-message", (e) => { if (e.level === "error") r.erros.push(e.message); });
      const js = (code) => principal.webContents.executeJavaScript(code);
      const esperar = (ms) => new Promise((ok) => setTimeout(ok, ms));
      const foto = async (nome) => { await esperar(700); principal.webContents.invalidate(); await esperar(300); fs.writeFileSync(path.join(SAIDA, `desktop_${nome}.png`), (await principal.webContents.capturePage()).toPNG()); };
      const seguir = () => js(`document.getElementById("bv-seguir").click()`);
      try {
        /* atualização automática apontando para o servidor de mentira; ao abrir, ainda não há versão nova */
        const cfgAtu = path.join(app.getPath("userData"), "teste-app-update.yml");
        fs.writeFileSync(cfgAtu, `provider: github\nowner: teste\nrepo: painel-mineracao\nhost: 127.0.0.1:${srv.address().port}\nprotocol: http\nupdaterCacheDirName: painel-mineracao-updater-teste\n`);
        iniciarAtualizacao({ config: cfgAtu });
        r.novidInicio = await js(`({visivel:!document.getElementById("novid").hidden, vista:JSON.parse(localStorage.getItem("min-versao"))})`);
        await esperar(1500);
        r.inicio = await js(`({desktop:DESKTOP, versao:window.desktop.versao, configInicialAberta:!document.getElementById("bv").hidden, semente:!!localStorage.getItem("min-desktop-iniciado"),
          placas:placas.length, anuncios:anuncios.length, maquinas:setup.maquinas.length, ofertasNoMenu:!document.getElementById("nav-ofertas").hidden, appInerte:document.querySelector(".app").inert,
          passo:document.getElementById("bv-onde").textContent})`);
        await foto("inicial_1");

        /* 1. nome */
        await js(`document.getElementById("bv-nome").value = "Teste"`); await seguir(); await esperar(200);
        /* 2. cidade: digita o começo e escolhe na lista com Enter */
        r.passos.semCidade = await js(`(()=>{ document.getElementById("bv-seguir").click(); return document.getElementById("bv-erro-cidade").textContent; })()`);
        r.passos.lista = await js(`(async()=>{ const i = document.getElementById("bv-cidade"); i.focus(); i.value = "itajai"; i.dispatchEvent(new Event("input", {bubbles:true}));
          await new Promise(o=>setTimeout(o,100)); const l = [...document.querySelectorAll("#bv-cidades li")].map(li=>li.textContent);
          i.dispatchEvent(new KeyboardEvent("keydown", {key:"Enter", bubbles:true, cancelable:true})); document.getElementById("bv-raio").value = "150"; return {lista:l, escolhida:i.value}; })()`);
        await foto("inicial_2");
        await seguir(); await esperar(200);
        /* 3. luz, calculada pela conta */
        r.passos.luz = await js(`(()=>{ document.getElementById("bv-conta").open = true; document.getElementById("bv-conta-valor").value = "460"; document.getElementById("bv-conta-kwh").value = "500";
          document.getElementById("bv-conta-usar").click(); return {tarifa:document.getElementById("bv-tarifa").value, msg:document.getElementById("bv-conta-res").textContent}; })()`);
        await foto("inicial_3");
        await seguir(); await esperar(200);
        /* 4. dinheiro: fica o padrão */
        r.passos.dinheiro = await js(`({meses:document.getElementById("bv-meses").value, margem:document.getElementById("bv-margem").value, cdi:document.getElementById("bv-pctcdi").value})`);
        await seguir(); await esperar(200);
        /* 5. computadores: um PC com fonte de 650 W e 1 vaga x1 */
        await js(`(()=>{ const set = (k, v) => { const e = document.querySelector('#bv-pcs .bv-pc [data-k="'+k+'"]'); e.value = v; e.dispatchEvent(new Event("change", {bubbles:true})); };
          set("nome","PC da sala"); set("fonteW","650"); set("selo","Gold"); set("x16","1"); set("x1","1"); })()`);
        await foto("inicial_5");
        await seguir(); await esperar(200);
        /* 6. Facebook: pula */
        r.passos.facebook = await js(`document.querySelector('#bv-form .bv-sec[data-passo="facebook"]').hidden === false`);
        await seguir(); await esperar(200);
        r.passos.resumo = await js(`document.getElementById("bv-resumo").innerText`);
        await foto("inicial_pronto");
        await seguir(); await esperar(600);
        r.depoisDaConfig = await js(`({fechada:document.getElementById("bv").hidden, inerte:document.querySelector(".app").inert, perfil:cfg.perfil, tarifa:cfg.tarifa, meses:cfg.meses, margem:cfg.margem, pctCdi:cfg.pctCdi,
          maquinas:setup.maquinas.map(m=>({nome:m.nome, fonteW:m.fonteW, selo:m.selo, x16:m.x16, x1:m.x1})), tela:location.hash, marca:document.getElementById("marca-sub").textContent,
          ola:document.getElementById("resumo-sub").textContent, modelos:modelosOfertas(), grupos:gruposDeBusca(modelosOfertas(), 0).map(g=>g.q+" "+g.min+"-"+g.max), ufs:ufsNoRaio(perfil(), 150, 3)})`);
        await foto("ofertas_vazia");

        /* ofertas */
        await js(`document.getElementById("of-buscar").click()`);
        for (let i = 0; i < 240; i++) { await esperar(500); if (!(await js("ofEst.rodando"))) break; }
        r.ofertas = await js(`(()=>{ if(!ofertas) return {status:document.getElementById("of-status").textContent, avisos:document.getElementById("of-avisos").innerText}; const it = ofertas.itens, ach = k => it.find(x=>x.k===k);
          return {status:document.getElementById("of-status").textContent, n:it.length, fora:ofertas.fora, avisos:ofertas.avisos, fbLocal:ofertas.fbLocal, brutos:ofertas.brutos,
            chaves:it.map(x=>x.k), modelos:Object.fromEntries(it.map(x=>[x.k, x.modelo])), km:Object.fromEntries(it.map(x=>[x.k, x.km])), flags:Object.fromEntries(it.filter(x=>x.flags.length).map(x=>[x.k, x.flags])),
            tambem:Object.fromEntries(it.filter(x=>x.tambem).map(x=>[x.k, x.tambem.map(t=>t.url)])),
            ordemTela:[...document.querySelectorAll("#of-lista .of")].slice(0,6).map(e=>e.dataset.k+" "+e.querySelector(".of-ret .pill").textContent),
            vendedor:[...document.querySelectorAll("#of-lista .of")].map(e=>{ const v = e.querySelector('[data-of="vendedor"]'), t = e.querySelector(".of-tit"); return {k:e.dataset.k, href:v && v.getAttribute("href"), igualTitulo:!!(v && t && v.getAttribute("href")===t.getAttribute("href")), alvo:v && v.target}; }),
            cont:document.getElementById("of-cont").textContent, badge:document.getElementById("b-ofertas").textContent, usadas:Object.keys(cfg.precosAtual||{}).length}; })()`);
        r.pedidos = pedidos.filter((p) => /^\/(fb|olx)\//.test(p));
        await foto("ofertas");

        /* detalhes de um anúncio do Marketplace e de um da OLX */
        await js(`document.querySelector('#of-lista .of[data-k="fb:1000000000000007"] [data-of="det"]').click()`);
        for (let i = 0; i < 60; i++) { await esperar(300); if (!(await js(`ofEst.lendo.size`))) break; }
        r.detalheFb = await js(`(()=>{ const d = document.querySelector('#of-lista .of[data-k="fb:1000000000000007"] .of-det'); return {texto:d && d.innerText, det:ofertas.itens.find(x=>x.k==="fb:1000000000000007").det, foco:document.activeElement && document.activeElement.dataset.of}; })()`);
        await js(`document.getElementById("of-so-compensa").checked = false; document.getElementById("of-so-compensa").dispatchEvent(new Event("change"))`);
        await js(`document.querySelector('#of-lista .of[data-k="olx:1543531037"] [data-of="det"]').click()`);
        for (let i = 0; i < 60; i++) { await esperar(300); if (!(await js(`ofEst.lendo.size`))) break; }
        r.detalheOlx = await js(`ofertas.itens.find(x=>x.k==="olx:1543531037").det`);
        await foto("ofertas_detalhe");
        /* salvar, descartar e mandar para Analisar */
        await js(`document.querySelector('#of-lista .of[data-k="fb:1000000000000001"] [data-of="salvar"]').click()`);
        await js(`document.querySelector('#of-lista .of[data-k="fb:1000000000000005"] [data-of="desc"]').click()`);
        r.marcas = await js(`({salvos:Object.keys(ofMarcas.salvos), descartados:Object.keys(ofMarcas.descartados), aindaNaLista:!!document.querySelector('#of-lista .of[data-k="fb:1000000000000005"]')})`);
        await js(`document.querySelector('#of-lista .of[data-k="fb:1000000000000002"] [data-of="analisar"]').click()`);
        await esperar(500);
        r.analisar = await js(`({n:anuncios.length, modelo:anuncios[0] && anuncios[0].modelo, preco:anuncios[0] && anuncios[0].preco, local:anuncios[0] && anuncios[0].local, url:anuncios[0] && anuncios[0].url, tela:location.hash})`);

        /* Comprei esta placa: vai para Minhas placas com a placa e o preço; antes de cadastrar, pergunta como pagou */
        await js(`document.getElementById("a-comprei").click()`); await esperar(300);
        r.minhas = await js(`(async()=>{ const pausa = ms => new Promise(ok=>setTimeout(ok,ms)), enviar = () => document.querySelector('#addform button[type=submit]').click();
          const o = {tela:location.hash, placa:document.getElementById("f-placa").value, preco:document.getElementById("f-preco").value, parcVisivel:!document.getElementById("f-parc-c").hidden};
          enviar(); await pausa(200);
          o.semPagamento = {placas:placas.length, erro:document.getElementById("f-erro").hidden ? "" : document.getElementById("f-erro").textContent};
          document.querySelector('#f-pag input[value="cartao"]').click(); await pausa(100);
          o.cartao = {parcVisivel:!document.getElementById("f-parc-c").hidden, parcelas:document.getElementById("f-parc").value, parcela:document.getElementById("f-parc-h").textContent, rotulo:document.getElementById("f-preco-l").textContent};
          enviar(); await pausa(300);
          const p = placas[placas.length-1]; o.salva = p ? {modelo:p.modelo, preco:p.preco, pagamento:p.pagamento, parcelas:p.parcelas} : null;
          o.guardada = (JSON.parse(localStorage.getItem("min-placas"))||[]).map(x=>x.pagamento+" "+x.parcelas+"x");
          o.lista = [...document.querySelectorAll("#riglist tbody tr")].map(tr=>tr.children[2].innerText.replace(/\\s+/g," ").trim());
          o.perguntaDeNovo = !document.querySelector('input[name="f-pag"]:checked');
          return o; })()`);
        await foto("minhas_placas");
        await js(`delPlaca(placas[placas.length-1]._id)`); await esperar(200);
        r.minhas.depoisDeRemover = await js(`placas.length`);

        /* atualização automática: sem versão nova → versão nova com arquivo corrompido → versão nova certa */
        const estadoAtu = `({estado:atuEst.estado, versao:atuEst.versao, erro:atuEst.erro, msg:document.getElementById("atu-msg").textContent, botao:document.getElementById("atu-btn").hidden ? "" : document.getElementById("atu-btn").textContent, aviso:!document.getElementById("aviso-atu").hidden})`;
        const ateEstado = async (alvo, n = 80) => { const vistos = []; for (let i = 0; i < n; i++) { await esperar(250); const e = await js("atuEst.estado"); if (vistos[vistos.length - 1] !== e) vistos.push(e); if (e === alvo) break; } return vistos; };
        r.atualizacao = { versaoApp, proxima };
        r.atualizacao.semVersao = await js(`({...${estadoAtu}, classe:document.getElementById("atu-msg").className})`);
        atu.modo = "igual";
        await js(`document.getElementById("atu-btn").click()`);
        r.atualizacao.estadosIgual = await ateEstado("em-dia");
        r.atualizacao.inicio = await js(estadoAtu);
        await js(`irPara("premissas"); document.getElementById("este-pc").scrollIntoView()`);
        atu.modo = "defeito";
        await js(`document.getElementById("atu-btn").click()`);
        r.atualizacao.estadosDefeito = await ateEstado("erro");
        r.atualizacao.defeito = await js(estadoAtu);
        atu.modo = "ok";
        await js(`document.getElementById("atu-btn").click()`);
        r.atualizacao.estadosOk = await ateEstado("pronta");
        r.atualizacao.pronta = await js(`({...${estadoAtu}, notas:atuEst.notas, avisoTitulo:document.getElementById("aviso-atu-t").textContent,
          avisoNotas:[...document.querySelectorAll("#aviso-atu-notas li")].map(li=>li.textContent), avisoHtml:document.getElementById("aviso-atu-notas").innerHTML})`);
        await foto("atualizacao_pronta");
        /* com uma busca em andamento, não reinicia */
        await js(`ofEst.rodando = true; document.getElementById("aviso-atu-agora").click()`);
        await esperar(400);
        r.atualizacao.ocupado = await js(`({instalando:!!atuEst.instalando, aviso:document.getElementById("aviso-atu-sub").textContent})`);
        await js(`ofEst.rodando = false`);
        /* "Depois" esconde o aviso; o botão em Premissas instala */
        await js(`document.getElementById("aviso-atu-depois").click()`);
        r.atualizacao.avisoDepoisDeDepois = await js(`!document.getElementById("aviso-atu").hidden`);
        await js(`document.getElementById("atu-btn").click()`);
        await esperar(500);
        r.atualizacao.instalar = await js(`({instalando:!!atuEst.instalando, msg:document.getElementById("atu-msg").textContent, botao:!document.getElementById("atu-btn").hidden})`);
        r.atualizacao.pedidos = atu.pedidos;
        r.atualizacao.baixado = (() => { try { return fs.readdirSync(path.join(process.env.XDG_CACHE_HOME || path.join(os.homedir(), ".cache"), "painel-mineracao-updater-teste", "pending")); } catch (e) { return String(e.message); } })();
        r.atualizacao.logLinhas = (() => { try { return fs.readFileSync(path.join(app.getPath("userData"), "atualizacao.log"), "utf8").split("\n").filter(Boolean).map((l) => l.slice(25, 200)); } catch (e) { return String(e.message); } })();

        /* avisos no celular: liga, nome do tópico, teste, resumo (na hora, automático e pedido pelo celular), sinal de vida e volta */
        r.celular = {};
        const naoSinal = (m) => m.sequence_id !== "pc-sinal";
        await js(`irPara("premissas"); document.getElementById("celular-p").scrollIntoView()`);
        r.celular.antes = await js(`({visivel:!document.getElementById("celular-p").hidden, botaoLigar:!document.getElementById("cel-desligado").hidden, passos:!document.getElementById("cel-ligado").hidden})`);
        await js(`document.getElementById("cel-ligar").click()`); await esperar(800);
        r.celular.ligado = await js(`({topico:document.getElementById("cel-topico").textContent, passos:!document.getElementById("cel-ligado").hidden, botaoLigar:!document.getElementById("cel-desligado").hidden,
          status:document.getElementById("cel-status").textContent, resumo:celCfg.resumo, ofertas:celCfg.ofertas, sinal:celCfg.sinal, hora:celCfg.hora, resumoDia:celCfg.resumoDia})`);
        const topico = r.celular.ligado.topico;
        /* com os avisos ligados, o painel fica no ícone perto do relógio e abre com o Windows (sem escolha da pessoa, vale o que
           os avisos pedem); em Premissas › Este computador dá para escolher abrir com o Windows e abrir minimizado */
        await esperar(300);
        r.celular.segundoPlano = { config: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows, abre: comoAbrir(true), abreNaMao: comoAbrir(false) };
        const marcarPc = (id, v) => js(`(()=>{ const c = document.getElementById("${id}"); c.checked = ${v}; c.dispatchEvent(new Event("change", {bubbles:true})); })()`);
        const telaInicio = () => js(`({visivel:!document.getElementById("inicio").hidden, iniciar:document.getElementById("pc-iniciar").checked, minimizado:document.getElementById("pc-minimizado").checked,
          minimizadoDesligado:document.getElementById("pc-minimizado").disabled, dica:document.getElementById("pc-iniciar-dica").hidden ? "" : document.getElementById("pc-iniciar-dica").textContent, minH:document.getElementById("pc-minimizado-h").textContent})`);
        const arquivoSp = () => { try { const j = JSON.parse(fs.readFileSync(path.join(app.getPath("userData"), "segundo-plano.json"), "utf8")); return { comWindows: j.comWindows, minimizado: j.minimizado }; } catch (e) { return String(e.message); } };
        r.celular.inicio = { tela: await telaInicio() };
        await marcarPc("pc-minimizado", false); await esperar(400);
        r.celular.inicio.semMinimizar = { abre: comoAbrir(true), arquivo: arquivoSp(), tela: await telaInicio() };
        await marcarPc("pc-minimizado", true); await esperar(400);
        r.celular.inicio.minimizadoDeNovo = { abre: comoAbrir(true), arquivo: arquivoSp() };
        await marcarPc("pc-iniciar", false); await esperar(500);
        r.celular.semIniciar = { config: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows, arquivo: arquivoSp(), tela: await telaInicio() };
        await marcarPc("pc-iniciar", true); await esperar(500);
        r.celular.iniciarDeNovo = testeSegundoPlano.inicioComWindows;
        r.celular.inicio.textoAlerta = await js(`[...document.querySelectorAll("#al-opcoes .hint")].map(x=>x.textContent).join(" | ")`);
        r.celular.formatoTopico = /^painel-[a-hj-km-np-z2-9]{4}-[a-hj-km-np-z2-9]{4}-[a-hj-km-np-z2-9]{4}-[a-hj-km-np-z2-9]{4}$/.test(topico);
        r.celular.arquivo = (() => { try { const c = JSON.parse(fs.readFileSync(path.join(app.getPath("userData"), "celular.json"), "utf8")); return { topicoIgual: c.topico === topico, ligado: c.ligado }; } catch (e) { return String(e.message); } })();
        await esperar(Number(process.env.PAINEL_SINAL_MS || 2000) * 2 + 600);
        const sinais = ntfy.publicados.filter((m) => m.sequence_id === "pc-sinal" && m.topic === topico);
        const ag = ntfy.agendados[`${topico}/pc-sinal`];
        r.celular.sinal = { quantos: sinais.length, agendadosNoTopico: Object.keys(ntfy.agendados).filter((k) => k.startsWith(topico + "/")).length,
          delay: ag && ag.delay, titulo: ag && ag.title, prioridade: ag && ag.priority, texto: ag && ag.message, ultimoSinal: celularMain.estado().ultimoSinal > 0 };
        r.celular.escuta = ntfy.escutas.map((e) => ({ topico: e.topico, since: e.since }));
        await js(`document.getElementById("cel-copiar").click()`); await esperar(300);
        r.celular.copiou = { igual: (await require("electron").clipboard.readText()) === topico, status: await js(`document.getElementById("cel-status").textContent`) };
        await js(`document.getElementById("cel-teste").click()`); await esperar(800);
        const teste = ntfyUltimo(naoSinal);
        r.celular.teste = teste && { topic: teste.topic === topico, title: teste.title, message: teste.message, tags: teste.tags, status: await js(`document.getElementById("cel-status").textContent`) };
        await js(`document.getElementById("cel-resumo-agora").click()`); await esperar(800);
        const resumo = ntfyUltimo((m) => m.sequence_id === "resumo");
        r.celular.resumo = resumo && { title: resumo.title, linhas: String(resumo.message).split("\n"), tags: resumo.tags, acoes: resumo.actions, status: await js(`document.getElementById("cel-status").textContent`) };
        /* resumo automático: passou da hora e ainda não mandou hoje; depois de mandar, não manda de novo no mesmo dia */
        const nResumos = () => ntfy.publicados.filter((m) => m.sequence_id === "resumo").length;
        const n0 = nResumos();
        r.celular.automatico = await js(`(async()=>{ await mudarCelular({hora:"00:00", resumoDia:"2020-01-01"}); const rodou = await verificarResumoCelular(); const deNovo = await verificarResumoCelular(); return {rodou, deNovo, resumoDia:celCfg.resumoDia, hoje:hojeISO()}; })()`);
        r.celular.automatico.publicou = nResumos() - n0;
        /* botão Atualizar no celular: chega um pedido, sai um resumo; outro pedido logo em seguida é ignorado */
        const n1 = nResumos();
        ntfyPedir("resumo"); await esperar(1200);
        r.celular.pedido = { publicou: nResumos() - n1, pedidos: celularMain.registro.pedidos };
        ntfyPedir("resumo"); await esperar(1000);
        r.celular.pedidoRepetido = nResumos() - n1;
        /* o PC ficou 2 horas sem sinal (sem sair pelo painel): ao voltar, avisa que voltou */
        celularMain.mudar({ ultimoSinal: Date.now() - 2 * 3600e3, saiuAMao: false });
        r.celular.volta = { avisou: await celularMain.verificarVolta() };
        const volta = ntfyUltimo(naoSinal); r.celular.volta.titulo = volta && volta.title; r.celular.volta.texto = volta && volta.message;
        celularMain.mudar({ ultimoSinal: Date.now() - 10 * 60e3 });
        r.celular.volta.recente = await celularMain.verificarVolta();   /* 10 minutos: o aviso nem chegou, não manda nada */
        await foto("celular");
        /* desligar o "sinal de vida" cancela o aviso agendado; ligar de novo agenda outro */
        const marcarCel = (id, v) => js(`(()=>{ const c = document.getElementById("${id}"); c.checked = ${v}; c.dispatchEvent(new Event("change", {bubbles:true})); })()`);
        await marcarCel("cel-sinal", false); await esperar(600);
        r.celular.semSinal = { apagou: ntfy.apagados.includes(`${topico}/pc-sinal`), agendado: !!ntfy.agendados[`${topico}/pc-sinal`] };
        await marcarCel("cel-sinal", true); await esperar(600);
        r.celular.sinalDeNovo = !!ntfy.agendados[`${topico}/pc-sinal`];
        /* o aviso de máquina parada (conta da Kryptex) desliga e liga de novo */
        await marcarCel("cel-maquinas", false); await esperar(400);
        r.celular.semMaquinas = { app: celularMain.estado().maquinas, tela: await js(`document.getElementById("cel-maquinas").checked`) };
        await marcarCel("cel-maquinas", true); await esperar(400);
        r.celular.comMaquinas = { app: celularMain.estado().maquinas, tela: await js(`document.getElementById("cel-maquinas").checked`) };

        /* abrir no celular: liga o servidor, entra com a senha numa janela de celular e confere que os dois mexem nos mesmos dados */
        r.acesso = {};
        await js(`irPara("premissas"); document.getElementById("acesso-p").scrollIntoView()`);
        r.acesso.antes = await js(`({visivel:!document.getElementById("acesso-p").hidden, botao:!document.getElementById("ac-desligado").hidden})`);
        await js(`document.getElementById("ac-ligar").click()`); await esperar(1000);
        const ac = acessoMain.estado(), urlCel = `http://127.0.0.1:${ac.porta}`;
        r.acesso.ligado = { rodando: ac.rodando, pinOk: /^\d{6}$/.test(ac.pin), tiposEndereco: ac.enderecos.map((e) => e.tipo),
          tela: await js(`({pin:document.getElementById("ac-pin").textContent, ends:document.querySelectorAll("#ac-end li").length, status:document.getElementById("ac-status").textContent, mandar:document.getElementById("ac-mandar").disabled})`) };
        r.acesso.segundoPlano = { config: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows };
        r.acesso.arquivo = (() => { try { const c = JSON.parse(fs.readFileSync(path.join(app.getPath("userData"), "acesso.json"), "utf8")); return { ligado: c.ligado, pinIgual: c.pin === ac.pin, temSegredo: /^[0-9a-f]{64}$/.test(c.segredo || "") }; } catch (e) { return String(e.message); } })();
        const pedir = (caminho, op = {}) => new Promise((ok, nao) => {
          const req = http.request(urlCel + caminho, { method: op.method || "GET", headers: op.headers || {} }, (res) => {
            let b = ""; res.setEncoding("utf8"); res.on("data", (d) => { b += d; }); res.on("end", () => ok({ status: res.statusCode, headers: res.headers, corpo: b }));
          });
          req.on("error", nao); if (op.body) req.write(op.body); req.end();
        });
        const form = { "Content-Type": "application/x-www-form-urlencoded" };
        const outroPin = ac.pin === "000000" ? "111111" : "000000";
        r.acesso.semSenha = { pedeSenha: (await pedir("/")).corpo.includes('name="pin"'), api: (await pedir("/api/dados")).status, fonte: (await pedir("/fonts/public-sans-latin-400-normal.woff2")).status, manifesto: (await pedir("/manifest.webmanifest")).status };
        const errada = await pedir("/entrar", { method: "POST", headers: form, body: "pin=" + outroPin });
        r.acesso.senhaErrada = { status: errada.status, avisa: /Senha errada/.test(errada.corpo), cookie: !!errada.headers["set-cookie"] };
        const certa = await pedir("/entrar", { method: "POST", headers: form, body: "pin=" + ac.pin });
        const cookie = String((certa.headers["set-cookie"] || [""])[0]).split(";")[0];
        r.acesso.senhaCerta = { status: certa.status, vaiPara: certa.headers.location, cookie: /^painel=[0-9a-f]{32}\.[0-9a-f]{64}$/.test(cookie), atributos: String((certa.headers["set-cookie"] || [""])[0]).replace(/painel=[^;]+/, "painel=…") };
        const comCookie = (extra) => ({ Cookie: cookie, ...(extra || {}) });
        const pag = await pedir("/", { headers: comCookie() });
        r.acesso.pagina = { status: pag.status, temDados: pag.corpo.includes("window.__PC__="), ponte: pag.corpo.includes("remoto: true"), csp: /connect-src 'self'/.test(pag.corpo), semNone: !/connect-src 'none'/.test(pag.corpo), tamanhoKB: Math.round(pag.corpo.length / 1024) };
        const dados = JSON.parse((await pedir("/api/dados", { headers: comCookie() })).corpo);
        r.acesso.dados = { chaves: Object.keys(dados.chaves).sort(), cfgTemPerfil: !!(JSON.parse(dados.chaves["min-cfg"] || "{}").perfil), versao: typeof dados.versao };
        r.acesso.semCabecalho = (await pedir("/api/dados", { method: "POST", headers: comCookie({ "Content-Type": "application/json" }), body: "{}" })).status;
        /* escuta os eventos como o celular faz */
        const evs = [];
        const sse = http.request(urlCel + "/api/eventos?cliente=teste-http", { headers: comCookie() }, (res) => { res.setEncoding("utf8"); res.on("data", (d) => evs.push(d)); });
        sse.on("error", () => {}); sse.end();
        await esperar(500);
        /* o PC cadastra uma placa: o celular fica sabendo */
        await js(`addPlaca({modelo:"rtx-3070", qtd:1, preco:1800, pagamento:"avista", parcelas:1, data:hojeISO(), criado:Date.now()})`); await esperar(900);
        r.acesso.eventoDoPc = evs.join("").split("\n\n").filter((b) => /event: mudou/.test(b)).map((b) => JSON.parse(b.split("data: ")[1] || "{}"));
        /* o "celular" grava um dia no diário pela API: chega no PC e na tela do PC */
        const hojePc = await js(`hojeISO()`);
        const dia = JSON.stringify([{ data: hojePc, valor: 3.05, moeda: "USD", dolar: 5.03, horas: 24, obs: "pelo celular", criado: Date.now(), _id: hojePc }]);
        const gravou = await pedir("/api/dados", { method: "POST", headers: comCookie({ "Content-Type": "application/json", "X-Painel": "1", "X-Cliente": "teste-http" }), body: JSON.stringify({ chaves: { "min-diario": dia } }) });
        await esperar(500);
        r.acesso.gravouDoCelular = { status: gravou.status, mudou: JSON.parse(gravou.corpo).mudou, noPc: await js(`({dias:diario.length, obs:(diario[0]||{}).obs, badge:document.getElementById("b-diario").textContent})`),
          eventoComOrigem: evs.join("").split("\n\n").filter((b) => /event: mudou/.test(b)).map((b) => JSON.parse(b.split("data: ")[1] || "{}")).filter((e) => e.origem === "teste-http").length };
        /* a busca pedida pelo celular roda no navegador escondido do PC */
        const busca = await pedir("/api/acao", { method: "POST", headers: comCookie({ "Content-Type": "application/json", "X-Painel": "1" }),
          body: JSON.stringify({ nome: "buscar-anuncios", args: { site: "fb", url: "https://www.facebook.com/marketplace/category/search/?query=rtx%203070&exact=false", rolar: 0 } }) });
        r.acesso.buscaPeloPc = { status: busca.status, itens: (() => { try { return JSON.parse(busca.corpo).resultado.itens.length; } catch (e) { return busca.corpo.slice(0, 200); } })() };
        const proibida = await pedir("/api/acao", { method: "POST", headers: comCookie({ "Content-Type": "application/json", "X-Painel": "1" }), body: JSON.stringify({ nome: "buscar-anuncios", args: { site: "fb", url: "https://example.com/x" } }) });
        r.acesso.buscaProibida = { status: proibida.status, erro: (() => { try { return JSON.parse(proibida.corpo).erro; } catch (e) { return ""; } })() };
        sse.destroy();

        /* a janela de celular: entra com a senha, vê os dados do PC, anota um dia e o PC recebe */
        const { BrowserWindow } = require("electron");
        const cel = new BrowserWindow({ show: false, width: 390, height: 844, webPreferences: { partition: "celular-teste", contextIsolation: true, sandbox: true, backgroundThrottling: false } });
        cel.webContents.setUserAgent("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Mobile Safari/537.36");
        const errosCel = []; cel.webContents.on("console-message", (e) => { if (e.level === "error") errosCel.push(e.message); });
        await cel.loadURL(urlCel + "/");
        const jc = (code) => cel.webContents.executeJavaScript(code);
        const fotoCel = async (nome) => { await esperar(600); cel.webContents.invalidate(); await esperar(300); fs.writeFileSync(path.join(SAIDA, `celular_${nome}.png`), (await cel.webContents.capturePage()).toPNG()); };
        r.acesso.celular = { pedeSenha: await jc(`!!document.querySelector('input[name="pin"]')`) };
        await fotoCel("senha");
        const carregou = new Promise((ok) => cel.webContents.once("did-finish-load", ok));
        await jc(`document.querySelector('input[name="pin"]').value = "${ac.pin}"; document.querySelector("form").submit(); true`);
        await carregou; await esperar(1500);
        r.acesso.celular.painel = await jc(`({remoto:REMOTO, desktop:DESKTOP, sync:document.getElementById("sync").textContent.trim(), placas:placas.length, dias:diario.length, perfil:!!cfg.perfil,
          ofertas:!!(ofertas && ofertas.itens && ofertas.itens.length), navOfertas:!document.getElementById("nav-ofertas").hidden, alertaOculto:document.getElementById("of-alerta").hidden,
          estePcOculto:document.getElementById("este-pc").hidden, avisosOculto:document.getElementById("celular-p").hidden, acessoOculto:document.getElementById("acesso-p").hidden, boasVindasOculta:document.getElementById("bv").hidden,
          largura:[document.documentElement.scrollWidth, window.innerWidth]})`);
        await fotoCel("resumo");
        /* o PC muda a margem: o celular atualiza sozinho */
        await js(`cfg.margem = 25; salvarCfg(); render();`); await esperar(1600);
        r.acesso.celular.margemDoPc = await jc(`cfg.margem`);
        /* o celular anota o ganho de ontem pelo formulário do Diário */
        const ontemPc = await js(`isoLocal(new Date(Date.now()-864e5))`);
        await jc(`irPara("diario"); document.getElementById("d-data").value = "${ontemPc}"; document.getElementById("d-valor").value = "2.9"; document.getElementById("dform").requestSubmit(); true`);
        await esperar(1600);
        r.acesso.celular.anotou = { noCelular: await jc(`diario.length`), noPc: await js(`({dias:diario.length, ontem:!!diario.find(e=>e.data==="${ontemPc}")})`), sync: await jc(`document.getElementById("sync").textContent.trim()`) };
        await fotoCel("diario");
        /* o celular pede ao PC para ler um anúncio: a leitura roda no navegador escondido do PC e volta para o celular */
        r.acesso.celular.detalhe = await jc(`(async()=>{ const x = ofertas.itens.find(i=>i.k==="fb:1000000000000007"); delete x.det; await lerDetalhesOferta(x);
          return {condicao:(x.det||{}).condicao, vendedor:(x.det||{}).vendedor, erro:(x.det||{}).erro||"", semNavegadorAqui:!window.desktop.detalhesAnuncio}; })()`);
        /* o PC some (acesso desligado): o celular avisa; o acesso volta: o aviso some sozinho */
        await js(`document.getElementById("ac-desligar").click()`); await esperar(2500);
        const avisoCel = `({aviso:!!document.getElementById("remoto-aviso") && !document.getElementById("remoto-aviso").hidden, sync:document.getElementById("sync").textContent.trim()})`;
        r.acesso.celular.semPc = await jc(avisoCel);
        await fotoCel("sem_pc");
        await js(`document.getElementById("ac-ligar").click()`); await esperar(6000);
        r.acesso.celular.pcVoltou = await jc(avisoCel);
        r.acesso.celular.erros = errosCel.filter((m) => !/ERR_CONNECTION_REFUSED|EventSource|api\/eventos/.test(m));
        r.acesso.conectados = acessoMain.estado().conectados;
        cel.destroy(); await esperar(400);
        r.acesso.depoisDeFechar = acessoMain.estado().conectados;
        /* desconectar os celulares: a sessão antiga deixa de valer */
        await js(`document.getElementById("ac-desconectar").click()`); await esperar(500);
        r.acesso.sessaoDepoisDeDesconectar = (await pedir("/api/dados", { headers: comCookie() })).status;
        /* 5 senhas erradas: bloqueia por 15 minutos, mesmo com a senha certa */
        for (let i = 0; i < 5; i++) await pedir("/entrar", { method: "POST", headers: form, body: "pin=" + outroPin });
        const bloq = await pedir("/entrar", { method: "POST", headers: form, body: "pin=" + ac.pin });
        r.acesso.bloqueio = { status: bloq.status, avisa: /Muitas tentativas/.test(bloq.corpo), cookie: !!bloq.headers["set-cookie"] };
        await foto("acesso");

        /* app do celular: vincula pelo QR code (câmera de mentira), sincroniza nos dois sentidos pelo ntfy, pedidos ao PC e desvincular */
        r.app = {};
        const pastaApp = path.join(SAIDA, "app-www");
        try { require("child_process").execFileSync("python3", [path.join(__dirname, "..", "..", "celular", "scripts", "montar-www.py"), "--saida", pastaApp, "--ntfy", base + "/ntfy"], { stdio: "pipe" }); }
        catch (e) { r.app.montar = String(e.stderr || e.message).slice(0, 400); }
        const tiposApp = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".png": "image/png", ".woff2": "font/woff2" };
        const srvApp = http.createServer((req, res) => {
          const f = path.join(pastaApp, decodeURIComponent(new URL(req.url, "http://x").pathname));
          if (!f.startsWith(pastaApp) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
          res.writeHead(200, { "Content-Type": tiposApp[path.extname(f)] || "application/octet-stream" }); res.end(fs.readFileSync(f));
        });
        await new Promise((ok) => srvApp.listen(0, "127.0.0.1", ok));
        /* no PC: Premissas › App do celular › Vincular um celular */
        await js(`irPara("premissas"); document.getElementById("appcel-p").scrollIntoView()`);
        r.app.antes = await js(`({visivel:!document.getElementById("appcel-p").hidden, botao:!document.getElementById("appcel-desligado").hidden, titulo:document.getElementById("t-appcel").textContent})`);
        await js(`document.getElementById("appcel-vincular").click()`); await esperar(1200);
        const ap = appMain.publico();
        r.app.vinculando = { ligado: ap.ligado, codigoOk: /^PM1-[\w-]{43}$/.test(ap.codigo), escutando: appMain.conectado(),
          tela: await js(`({qr:!document.getElementById("appcel-qr").hidden, svgCod:!!document.querySelector("#appcel-qr-cod svg"), svgApk:!!document.querySelector("#appcel-qr-apk svg"), link:document.getElementById("appcel-url").href, status:document.getElementById("appcel-status").textContent})`),
          segundoPlano: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows };
        await foto("app_qr");
        /* o QR que o PC mostra, lido de verdade com o mesmo leitor do app (jsQR) */
        const jsQR = require(path.join(__dirname, "..", "..", "celular", "node_modules", "jsqr"));
        const rgba = (q) => { const d = new Uint8ClampedArray(q.lado * q.lado * 4); for (let i = 0; i < q.px.length; i++) { d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = q.px[i]; d[i * 4 + 3] = 255; } return d; };
        const qCod = qrDoSvg(ap.qr, 2), qApk = qrDoSvg(ap.qrApk, 2);
        r.app.qrLido = { codigo: (jsQR(rgba(qCod), qCod.lado, qCod.lado) || {}).data === ap.codigo, apk: (jsQR(rgba(qApk), qApk.lado, qApk.lado) || {}).data };
        if (process.env.PAINEL_CAMERA) videoDoQr(qCod, process.env.PAINEL_CAMERA);
        /* o "celular": a página do app, num outro endereço (como no Android) */
        const { BrowserWindow: JanelaApp } = require("electron");
        const celApp = new JanelaApp({ show: false, width: 390, height: 844, webPreferences: { partition: "app-teste", contextIsolation: true, sandbox: true, backgroundThrottling: false } });
        celApp.webContents.setUserAgent("Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.0.0 Mobile Safari/537.36");
        const errosApp = []; celApp.webContents.on("console-message", (e) => { if (e.level === "error") errosApp.push(e.message); });
        await celApp.loadURL(`http://127.0.0.1:${srvApp.address().port}/index.html`);
        const ja = (code) => celApp.webContents.executeJavaScript(code);
        const fotoApp = async (nome) => { await esperar(600); celApp.webContents.invalidate(); await esperar(300); fs.writeFileSync(path.join(SAIDA, `app_${nome}.png`), (await celApp.webContents.capturePage()).toPNG()); };
        await esperar(800);
        r.app.celular = { inicio: await ja(`({app:APP, remoto:REMOTO, tela:!!document.getElementById("pm-vinc"), escondido:document.documentElement.classList.contains("pm-vinculando"), placas:placas.length})`) };
        await fotoApp("vincular");
        /* lê o QR pela câmera de mentira (sem ela, cola o código no meio de um texto) */
        if (process.env.PAINEL_CAMERA) await ja(`document.getElementById("pm-ler").click()`);
        else await ja(`document.getElementById("pm-colar-b").click(); document.getElementById("pm-cod").value = ${JSON.stringify("Meu código: " + ap.codigo + " (do PC)")}; document.getElementById("pm-vincular").click()`);
        for (let i = 0; i < 80 && await ja(`!!document.getElementById("pm-vinc")`); i++) await esperar(250);
        await esperar(800);
        r.app.celular.vinculou = await ja(`({tela:!!document.getElementById("pm-vinc"), pelaCamera:${!!process.env.PAINEL_CAMERA}, codigoIgual:localStorage.getItem("pm-codigo")===${JSON.stringify(ap.codigo)},
          nome:(cfg.perfil||{}).nome, placas:placas.length, dias:diario.length, ofertas:(ofertas&&ofertas.itens||[]).length, anuncios:anuncios.length, maquinas:setup.maquinas.length,
          sync:document.getElementById("sync").textContent.trim(), navOfertas:!document.getElementById("nav-ofertas").hidden, alertaOculto:document.getElementById("of-alerta").hidden,
          estecel:!document.getElementById("estecel-p").hidden, appcelOculto:document.getElementById("appcel-p").hidden, estePcOculto:document.getElementById("este-pc").hidden, largura:[document.documentElement.scrollWidth, innerWidth]})`);
        r.app.pc = await js(`({placas:placas.length, dias:diario.length, ofertas:(ofertas&&ofertas.itens||[]).length, anuncios:anuncios.length})`);
        /* os dados do celular são iguais aos do PC, chave por chave */
        const chavesDiferentes = async () => {
          const ler = `JSON.stringify(${JSON.stringify(Sincronia.SINCRONIZADAS)}.map(k=>localStorage.getItem(k)))`;
          const x = JSON.parse(await js(ler)), y = JSON.parse(await ja(ler));
          return Sincronia.SINCRONIZADAS.filter((k, i) => x[i] !== y[i]);
        };
        r.app.diferentesDepoisDeVincular = await chavesDiferentes();
        await esperar(4500);   /* o QR some sozinho depois de vincular */
        r.app.pcVinculado = { aparelhos: appMain.publico().aparelhos, tela: await js(`({qr:!document.getElementById("appcel-qr").hidden, lista:document.getElementById("appcel-lista").innerText, status:document.getElementById("appcel-status").textContent})`) };
        await foto("app_vinculado");
        await ja(`irPara("resumo")`); await fotoApp("resumo");
        /* o celular anota um dia no Diário (formulário): chega no PC */
        const anteontem = await js(`isoLocal(new Date(Date.now()-2*864e5))`);
        await ja(`irPara("diario"); document.getElementById("d-data").value = "${anteontem}"; document.getElementById("d-valor").value = "3.1"; document.getElementById("dform").requestSubmit(); true`);
        for (let i = 0; i < 40 && !(await js(`!!diario.find(e=>e.data==="${anteontem}")`)); i++) await esperar(250);
        await esperar(1500);
        r.app.doCelular = { noPc: await js(`({dias:diario.length, anteontem:!!diario.find(e=>e.data==="${anteontem}")})`), pendentes: await ja(`window.desktop.sync.info().pendentes`) };
        await fotoApp("diario");
        /* o PC muda a margem: com o app aberto, chega no celular sozinho */
        await js(`cfg.margem = 15; salvarCfg(); render(); true`);
        for (let i = 0; i < 40 && (await ja(`cfg.margem`)) !== 15; i++) await esperar(250);
        r.app.doPc = { margem: await ja(`cfg.margem`) };
        /* pedidos ao PC: ler um anúncio da OLX e analisar um link do Marketplace (rodam no navegador escondido do PC) */
        r.app.detalhe = await ja(`(async()=>{ irPara("ofertas"); const x = ofertas.itens.find(i=>i.k==="olx:1543531037"); delete x.det; await lerDetalhesOferta(x);
          return {condicao:(x.det||{}).condicao, vendedor:(x.det||{}).vendedor, erro:(x.det||{}).erro||""}; })()`);
        r.app.analisar = await ja(`(async()=>{ irPara("anuncio"); const n0 = anuncios.length; await analisarLink("https://www.facebook.com/marketplace/item/1000000000000007/");
          return {antes:n0, depois:anuncios.length, atual:atualId, status:document.getElementById("a-status").textContent, modelo:(anuncios.find(a=>a._id===atualId)||{}).modelo}; })()`);
        r.app.analisarNoPc = await js(`anuncios.length`);
        await fotoApp("analisar");
        /* busca de ofertas pedida no celular, só com a RTX 3070 (escolhida no celular, em Modelos procurados) */
        await ja(`irPara("ofertas"); ofSel = ["rtx-3070"]; lsSet("min-ofertas-modelos", ofSel); renderOfModelos(); true`);
        await esperar(3000);
        const quandoAntes = await js(`ofertas.quando`);
        await ja(`document.getElementById("of-buscar").click()`);
        await esperar(1500);
        r.app.buscaRodando = { celular: await ja(`({rodando:ofEst.rodando, botao:document.getElementById("of-buscar").textContent, status:document.getElementById("of-status").textContent, barra:document.getElementById("of-prog").className})`), pc: await js(`ofEst.rodando`) };
        await fotoApp("buscando");
        for (let i = 0; i < 240 && (await ja(`ofEst.rodando`)); i++) await esperar(500);
        await esperar(1000);
        r.app.busca = { status: await ja(`document.getElementById("of-status").textContent`), novaBusca: (await ja(`ofertas.quando`)) !== quandoAntes, igualAoPc: (await ja(`ofertas.quando`)) === (await js(`ofertas.quando`)),
          modelosNoPc: await js(`ofSel`), pedidos: appMain.registro.pedidos.slice() };
        await fotoApp("ofertas");
        r.app.diferentesDepoisDosPedidos = await chavesDiferentes();
        /* app fechado há mais de 20 minutos: o PC não manda as mudanças na hora (economia); o Atualizar agora busca */
        appMain.esquecerAtivos();
        const nCartas = appMain.registro.cartas.length;
        await js(`cfg.margem = 18; salvarCfg(); render(); true`); await esperar(4500);
        r.app.semAppAberto = { cartas: appMain.registro.cartas.length - nCartas, margemNoCelular: await ja(`cfg.margem`) };
        await ja(`window.desktop.sync.atualizar().then(()=>true)`);
        r.app.semAppAberto.depoisDeAtualizar = await ja(`cfg.margem`);
        /* o app fecha e abre de novo: os dados continuam lá, sem pedir nada ao PC (perguntou há menos de 10 minutos) */
        const nRec = appMain.registro.recebidas.length;
        await new Promise((ok) => { celApp.webContents.once("did-finish-load", ok); celApp.webContents.reload(); }); await esperar(1500);
        r.app.reaberto = await ja(`({tela:!!document.getElementById("pm-vinc"), margem:cfg.margem, placas:placas.length, ofertas:(ofertas&&ofertas.itens||[]).length, sync:document.getElementById("sync").textContent.trim()})`);
        r.app.reaberto.cartasDoCelular = appMain.registro.recebidas.length - nRec;
        /* mudanças nos dois lados quase ao mesmo tempo (chaves diferentes): no fim, os dois ficam iguais */
        await ja(`cfg.cdi = 12.5; salvarCfg(); true`); await js(`ofMarcas.salvos["fb:1000000000000013"] = {t:Date.now()}; salvarMarcas(); true`);
        await esperar(7000);
        r.app.diferentesNoFim = await chavesDiferentes();
        r.app.cdi = { pc: await js(`cfg.cdi`), celular: await ja(`cfg.cdi`) };
        /* relógio do celular errado: 1 hora atrasado e depois 1 hora adiantado. A mudança entra no PC (ninguém mais mexeu
           nela) e o PC confirma; nada fica indo e voltando */
        const msgsCel = () => (ntfy.topicos.get([...ntfy.topicos.keys()].find((t) => /^pm-.*-cel$/.test(t))) || []).length;
        const msgsPc = () => (ntfy.topicos.get([...ntfy.topicos.keys()].find((t) => /^pm-.*-pc$/.test(t))) || []).length;
        r.app.relogio = {};
        for (const [nome, desvio, valor] of [["atrasado", -3600e3, 0.97], ["adiantado", 3600e3, 0.98]]) {
          await ja(`(()=>{ const f = (window.__agoraReal = window.__agoraReal || Date.now.bind(Date)); Date.now = () => f() + (${desvio}); return true; })()`);
          const c0 = msgsCel(), p0 = msgsPc();
          await ja(`cfg.tarifa = ${valor}; salvarCfg(); true`);
          for (let i = 0; i < 40 && (await js(`cfg.tarifa`)) !== valor; i++) await esperar(250);
          await esperar(6000);
          r.app.relogio[nome] = { noPc: await js(`cfg.tarifa`), pendentes: await ja(`window.desktop.sync.info().pendentes`), msgsDoCelular: msgsCel() - c0, msgsDoPc: msgsPc() - p0 };
        }
        await ja(`Date.now = window.__agoraReal; true`);
        /* a escuta do celular cai (o que o PC manda fica no ntfy) e volta na hora em que o teste quer ("online") */
        const topicoPcApp = () => [...ntfy.topicos.keys()].find((t) => /^pm-.*-pc$/.test(t));
        const calarCelular = () => { falso.ntfy.recusar = (req, caminho) => (req.method === "GET" && /^\/pm-[\w]+-pc\/json$/.test(caminho) ? 503 : 0); falso.derrubar(topicoPcApp()); };
        const ouvirCelular = async () => { falso.ntfy.recusar = null; await ja(`window.dispatchEvent(new Event("online")); true`); };
        const ateIguais = async (n = 60) => { for (let i = 0; i < n && (await chavesDiferentes()).length; i++) await esperar(500); return chavesDiferentes(); };
        /* duas mudanças seguidas na mesma chave, com o relógio do celular 1 hora atrasado e sem ele ouvir o PC entre uma e
           outra: a segunda vai com a versão velha da chave, mas é continuação do mesmo celular e entra */
        await ja(`(()=>{ const f = window.__agoraReal; Date.now = () => f() - 3600e3; return true; })()`);
        let rec0 = appMain.registro.recusadas;
        calarCelular(); await esperar(300);
        await ja(`cfg.tarifa = 0.91; lsSet("min-cfg", cfg); true`);
        for (let i = 0; i < 40 && (await js(`cfg.tarifa`)) !== 0.91; i++) await esperar(250);
        await esperar(1500);
        await ja(`cfg.tarifa = 0.92; lsSet("min-cfg", cfg); true`);
        for (let i = 0; i < 40 && (await js(`cfg.tarifa`)) !== 0.92; i++) await esperar(250);
        await esperar(1500);
        await ouvirCelular();
        r.app.duasSeguidas = { diferentes: await ateIguais(), noPc: await js(`cfg.tarifa`), noCelular: await ja(`cfg.tarifa`), recusadas: appMain.registro.recusadas - rec0 };
        await esperar(1500);
        r.app.duasSeguidas.pendentes = await ja(`window.desktop.sync.info().pendentes`);
        await ja(`Date.now = window.__agoraReal; true`);
        /* o PC deixa de ouvir o celular (desligado, sem internet) e o celular muda a mesma chave duas vezes: quando o PC volta,
           as duas chegam na ordem e fica a última */
        rec0 = appMain.registro.recusadas;
        appMain.pararEscuta(); await esperar(300);
        await ja(`cfg.cdi = 13.1; lsSet("min-cfg", cfg); true`); await esperar(2500);
        await ja(`cfg.cdi = 13.2; lsSet("min-cfg", cfg); true`); await esperar(2500);
        const cdiParado = await js(`cfg.cdi`);
        appMain.voltarEscuta();
        r.app.pcParado = { enquantoParado: cdiParado, diferentes: await ateIguais(), noPc: await js(`cfg.cdi`), noCelular: await ja(`cfg.cdi`), recusadas: appMain.registro.recusadas - rec0 };
        await esperar(1500);
        r.app.pcParado.pendentes = await ja(`window.desktop.sync.info().pendentes`);
        appMain.zerarEnvios();   /* os testes abaixo mandam muitas mudanças: começam como numa hora nova (o teto é testado depois) */
        /* diagnóstico: o que o app entrega ao painel do celular, e o estado da sincronia no celular */
        await ja(`(()=>{ const o = aplicarDadosRemotos; window.__entregas = []; aplicarDadosRemotos = function(ch){ window.__entregas.push({ t: Date.now(), ks: Object.keys(ch||{}), cdi: (()=>{ try { return JSON.parse(ch["min-cfg"]).cdi; } catch (e) { return undefined; } })() }); return o(ch); }; return true; })()`);
        const estadoCel = () => ja(`(()=>{ const e = JSON.parse(localStorage.getItem("pm-sinc")); return { versao: e.versao, pend: e.pend, vk: e.vk["min-cfg"], ultimoId: e.ultimoId, info: window.desktop.sync.info(), entregas: (window.__entregas||[]).slice(-6) }; })()`);
        const escutasPc = () => ntfy.escutas.filter((e) => /-pc$/.test(e.topico)).length;
        /* corrida: o celular muda a margem e, antes de a mudança ser gravada (a configuração espera 0,5 s) e sair (mais
           1,2 s), chega uma mudança do PC na mesma chave (as horas). A do celular é a mais nova: não se perde */
        const margem0 = await js(`cfg.margem`), horas0 = await js(`cfg.horas`);
        calarCelular(); await esperar(300);
        const nC = appMain.registro.cartas.length;
        await js(`cfg.horas = 21; lsSet("min-cfg", cfg); true`);
        for (let i = 0; i < 40 && appMain.registro.cartas.length === nC; i++) await esperar(250);   /* o PC mandou (o celular ainda não ouviu) */
        await ja(`cfg.margem = 11; salvarCfg(); true`);
        await ouvirCelular();
        r.app.corrida = { pcMandou: appMain.registro.cartas.length > nC, diferentes: await ateIguais(), antes: { margem: margem0, horas: horas0 },
          pc: await js(`({margem:cfg.margem, horas:cfg.horas})`), celular: await ja(`({margem:cfg.margem, horas:cfg.horas})`) };
        const cartasDepoisDaCorrida = appMain.registro.cartas.length;
        /* cartas "de um celular" montadas pelo teste, com o código de vinculação (outro aparelho, para não mexer na conta do de verdade) */
        const canalTeste = await Sincronia.abrirCanal(ap.codigo, { servidor: base + "/ntfy" });
        const apCel = await ja(`localStorage.getItem("pm-aparelho")`);
        const outroCel = { id: "celular-de-teste", nome: "Outro celular", app: "1.4.0" };
        const cfgCom = async (mudar) => JSON.stringify(Object.assign(JSON.parse(await ja(`localStorage.getItem("min-cfg")`)), mudar));
        /* no PC: alguém digita (a configuração espera 0,5 s para gravar) e chega uma mudança do celular na mesma chave, feita
           antes: o PC grava o que foi digitado antes de comparar, e isso não se perde */
        let rec1 = appMain.registro.recusadas;
        const vCdi = await cfgCom({ cdi: 9.9 });
        const nRecPc = appMain.registro.recebidas.length;
        await js(`cfg.cdi = 11.1; salvarCfg(); true`);
        await canalTeste.publicar({ tipo: "dados", aparelho: outroCel, chaves: { "min-cfg": { v: vCdi, t: Date.now() - 5000, s: 1, n: appMain.estado().vers["min-cfg"] } } }, "cel");
        for (let i = 0; i < 40 && appMain.registro.recebidas.length === nRecPc; i++) await esperar(100);
        await esperar(3500);
        r.app.corridaPc = { chegou: appMain.registro.recebidas.length > nRecPc, diferentes: await ateIguais(), pc: await js(`cfg.cdi`), celular: await ja(`cfg.cdi`), recusadas: appMain.registro.recusadas - rec1,
          estado: await estadoCel(), escutasPc: escutasPc(), msgsNoTopicoPc: msgsPc(), cartasDepoisDaCorrida, cartasPc: appMain.registro.cartas.slice(-4), recebidasPc: appMain.registro.recebidas.slice(-3), errosApp: errosApp.slice(-5) };
        /* dois celulares mudam a mesma chave quase juntos: a carta do PC confirma as duas mudanças (nenhuma confirmação se perde) */
        calarCelular(); await esperar(300);
        await ja(`cfg.cdi = 14.4; lsSet("min-cfg", cfg); true`);
        for (let i = 0; i < 80 && (await js(`cfg.cdi`)) !== 14.4; i++) await esperar(50);
        const vDois = await ja(`localStorage.getItem("min-cfg")`);
        await canalTeste.publicar({ tipo: "dados", aparelho: outroCel, chaves: { "min-cfg": { v: vDois, t: Date.now(), s: 3, n: appMain.estado().vers["min-cfg"] } } }, "cel");
        await esperar(1500);
        const cartaDupla = appMain.registro.cartas.slice(-1)[0];
        await ouvirCelular();
        for (let i = 0; i < 20 && (await ja(`window.desktop.sync.info().pendentes`)); i++) await esperar(250);
        r.app.doisCelulares = { diferentes: await ateIguais(), pc: await js(`cfg.cdi`), celular: await ja(`cfg.cdi`), pendentes: await ja(`window.desktop.sync.info().pendentes`), acksNaCarta: cartaDupla && cartaDupla.acks };
        /* reenvio: o celular manda de novo uma mudança que o PC já tinha aplicado (a confirmação se perdeu), depois que o PC
           mudou a mesma chave e dizendo uma hora mais nova que a do PC: é a mesma mudança (mesmo número), o PC só confirma */
        calarCelular(); await esperar(300);
        await ja(`cfg.horas = 22; lsSet("min-cfg", cfg); true`);
        for (let i = 0; i < 40 && (await js(`cfg.horas`)) !== 22; i++) await esperar(250);
        const pendCel = await ja(`(()=>{ const e = JSON.parse(localStorage.getItem("pm-sinc")); return { p: e.pend["min-cfg"] || null, n: e.vk["min-cfg"] || 0, v: localStorage.getItem("min-cfg") }; })()`);
        await js(`cfg.horas = 20; lsSet("min-cfg", cfg); true`); await esperar(3500);
        rec1 = appMain.registro.recusadas;
        if (pendCel.p) await canalTeste.publicar({ tipo: "dados", aparelho: { id: apCel }, chaves: { "min-cfg": { v: pendCel.v, t: pendCel.p.t + 3600e3, s: pendCel.p.s, n: pendCel.n } } }, "cel");
        await esperar(2500);
        const pcDepoisDoReenvio = await js(`cfg.horas`);
        await ouvirCelular();
        r.app.reenvio = { tinhaPendente: !!pendCel.p, pcDepoisDoReenvio, diferentes: await ateIguais(), pc: await js(`cfg.horas`), celular: await ja(`cfg.horas`), recusadas: appMain.registro.recusadas - rec1 };
        await esperar(1500);
        r.app.reenvio.pendentes = await ja(`window.desktop.sync.info().pendentes`);
        /* conflito com o relógio do celular 1 hora adiantado: a mudança dele foi feita antes da do PC (pela hora do ntfy.sh);
           o PC acerta a hora do celular e fica com a dele */
        rec1 = appMain.registro.recusadas;
        await js(`cfg.horas = 19; lsSet("min-cfg", cfg); true`); await esperar(3500);
        const vHoras = await cfgCom({ horas: 17 });
        await canalTeste.publicar({ tipo: "dados", t: Date.now() + 3600e3, aparelho: outroCel, chaves: { "min-cfg": { v: vHoras, t: Date.now() - 10e3 + 3600e3, s: 4, n: 1 } } }, "cel");
        await esperar(1500);
        r.app.relogioConflito = { diferentes: await ateIguais(), pc: await js(`cfg.horas`), celular: await ja(`cfg.horas`), recusadas: appMain.registro.recusadas - rec1 };
        /* celular sem espaço para guardar: o que veio do PC não fica guardado, o celular avisa e não manda o valor velho
           de volta ao PC; com espaço de novo, o Atualizar pede a chave outra vez */
        const encheu = await ja(`(()=>{ let i = 0; for (const t of [1e6, 1e5, 1e4, 1e3, 100, 10, 1]) { try { for (;;) localStorage.setItem("lixo-" + (i++), "x".repeat(t)); } catch (e) {} } return i; })()`);
        await js(`cfg.tarifa = 0.8875; cfg.notaTeste = "x".repeat(300); lsSet("min-cfg", cfg); true`);   /* bem maior que o que o celular tem: não cabe */
        let avisoEspaco = "";
        for (let i = 0; i < 40 && !/espaço/.test(avisoEspaco); i++) { await esperar(250); avisoEspaco = await ja(`(document.getElementById("remoto-aviso")||{}).textContent||""`); }
        await esperar(2500);
        r.app.semEspaco = { encheu, avisou: /espaço/.test(avisoEspaco), pc: await js(`cfg.tarifa`), celularGuardou: await ja(`JSON.parse(localStorage.getItem("min-cfg")).tarifa`), pendentes: await ja(`window.desktop.sync.info().pendentes`) };
        await ja(`(()=>{ for (const k of Object.keys(localStorage)) if (k.startsWith("lixo-")) localStorage.removeItem(k); return true; })()`);
        await ja(`window.desktop.sync.atualizar().then(()=>true, (e)=>String(e.message))`);
        r.app.semEspaco.depois = { diferentes: await ateIguais(), pc: await js(`cfg.tarifa`), celular: await ja(`JSON.parse(localStorage.getItem("min-cfg")).tarifa`),
          avisoSumiu: await ja(`!document.getElementById("remoto-aviso") || document.getElementById("remoto-aviso").hidden`) };
        /* conflito de verdade: o celular sem internet muda a tarifa, o PC muda as horas (a mesma chave, min-cfg);
           quando a internet volta, vale a mudança mais nova (a do PC) e os dois ficam iguais */
        falso.ntfy.recusar = (req, caminho) => (req.method === "POST" && /-cel$/.test(caminho) ? 503 : 0);
        await ja(`cfg.tarifa = 0.99; salvarCfg(); true`); await esperar(2500);
        await js(`cfg.horas = 23; salvarCfg(); render(); true`); await esperar(3500);
        falso.ntfy.recusar = null;
        const c1 = msgsCel(), p1 = msgsPc();
        for (let i = 0; i < 60 && (await chavesDiferentes()).length; i++) await esperar(500);
        await esperar(4000);
        r.app.conflito = { diferentes: await chavesDiferentes(), pc: await js(`({tarifa:cfg.tarifa, horas:cfg.horas})`), celular: await ja(`({tarifa:cfg.tarifa, horas:cfg.horas})`),
          pendentes: await ja(`window.desktop.sync.info().pendentes`), recusadasNoPc: appMain.registro.recusadas, msgsDoCelular: msgsCel() - c1, msgsDoPc: msgsPc() - p1 };
        /* uma mudança grande no PC (vai como anexo no ntfy): 3.000 anúncios vistos pelo alerta de ofertas */
        await js(`(()=>{ for(let i=0;i<3000;i++) alerta.vistos["fb:" + (2e15+i)] = {t:Date.now(), p:1000+i}; salvarAlerta(); return true; })()`);
        for (let i = 0; i < 40 && (await chavesDiferentes()).length; i++) await esperar(500);
        r.app.grande = { diferentes: await chavesDiferentes(), vistosNoCelular: await ja(`Object.keys(alerta.vistos).length`), tamanhoKB: Math.round((await js(`localStorage.getItem("min-ofertas-alerta").length`)) / 1024) };
        /* teto do PC: com 20 mensagens ou mais na última hora, as mudanças do PC não vão sozinhas para o celular; a resposta
           ao Atualizar, sim */
        const naHora = () => appMain.estado().envios.filter((t) => Date.now() - t < 3600e3).length;
        appMain.encherEnvios(20);
        const h0 = naHora(), p3 = msgsPc();
        await js(`cfg.bandeira = 0.01; salvarCfg(); render(); true`); await esperar(5000);
        const sozinho = msgsPc() - p3;
        await ja(`window.desktop.sync.atualizar().then(()=>true)`);
        r.app.teto = { naUltimaHora: h0, mandouSozinho: sozinho, depoisDeAtualizar: { msgsDoPc: msgsPc() - p3, bandeira: await ja(`cfg.bandeira`) } };
        appMain.zerarEnvios();   /* daqui em diante, como numa hora nova */
        /* o anexo de uma carta do PC não baixa na hora (o ntfy recusa uma vez: 429): o celular tenta de novo sozinho em 5 s,
           sem pedir nada ao PC */
        const getsAnexo = () => ntfy.pedidos.filter((x) => x.startsWith("GET /file/")).length;
        let recusas = 0, g0 = getsAnexo(), c2 = msgsCel(), p2 = msgsPc();
        falso.ntfy.recusar = (req, caminho) => (req.method === "GET" && caminho.startsWith("/file/") && recusas++ < 1 ? 429 : 0);
        await js(`(()=>{ for(let i=0;i<400;i++) alerta.vistos["fb:" + (3e15+i)] = {t:Date.now(), p:2000+i}; salvarAlerta(); return true; })()`);
        r.app.anexoRecusado = { diferentes: await ateIguais(40), downloads: getsAnexo() - g0, msgsDoCelular: msgsCel() - c2, msgsDoPc: msgsPc() - p2 };
        /* o anexo sumiu do ntfy (404, como depois de 3 horas): o celular avisa e pede de novo ao PC, uma vez */
        let apagados = 0, avisoVisto = "";
        g0 = getsAnexo(); c2 = msgsCel(); p2 = msgsPc();
        falso.ntfy.recusar = (req, caminho) => (req.method === "GET" && caminho.startsWith("/file/") && apagados++ < 1 ? 404 : 0);
        await js(`(()=>{ for(let i=400;i<800;i++) alerta.vistos["fb:" + (3e15+i)] = {t:Date.now(), p:2000+i}; salvarAlerta(); return true; })()`);
        for (let i = 0; i < 80; i++) {
          await esperar(250);
          const a = await ja(`(document.getElementById("remoto-aviso")||{}).textContent||""`); if (/não chegou inteira/.test(a)) avisoVisto = a;
          if (avisoVisto && !(await chavesDiferentes()).length) break;
        }
        r.app.anexoPerdido = { diferentes: await ateIguais(40), downloads: getsAnexo() - g0, msgsDoCelular: msgsCel() - c2, msgsDoPc: msgsPc() - p2, avisou: !!avisoVisto,
          avisoSumiu: await ja(`!document.getElementById("remoto-aviso") || document.getElementById("remoto-aviso").hidden`) };
        /* no outro sentido: o PC não baixa na hora o anexo de uma mudança grande do celular (429); tenta de novo em 5 s e
           confirma, e o celular não precisa mandar de novo */
        recusas = 0; g0 = getsAnexo(); c2 = msgsCel();
        falso.ntfy.recusar = (req, caminho) => (req.method === "GET" && caminho.startsWith("/file/") && recusas++ < 1 ? 429 : 0);
        await ja(`(()=>{ for(let i=0;i<1200;i++) ofMarcas.descartados["fb:" + String(Math.random()).slice(2, 18)] = Date.now(); salvarMarcas(); return true; })()`);
        r.app.anexoNoPc = { diferentes: await ateIguais(40), downloads: getsAnexo() - g0, msgsDoCelular: msgsCel() - c2 };
        await esperar(2000);
        r.app.anexoNoPc.pendentes = await ja(`window.desktop.sync.info().pendentes`);
        falso.ntfy.recusar = null;
        await ja(`irPara("premissas")`); await fotoApp("premissas");
        r.app.esteCelular = await ja(`({tela:!document.getElementById("v-premissas").hidden, cartao:!document.getElementById("estecel-p").hidden, info:document.getElementById("estecel-info").innerText.replace(/\\n/g," | ")})`);
        /* quantas mensagens o teste gastou no ntfy (o ntfy.sh aceita 250 por dia de cada internet) e se tudo foi cifrado */
        const topicosApp = [...ntfy.topicos.keys()].filter((t) => /^pm-/.test(t));
        r.app.mensagens = Object.fromEntries(topicosApp.map((t) => [t.endsWith("-pc") ? "doPc" : "doCelular", ntfy.topicos.get(t).length]));
        r.app.anexos = topicosApp.reduce((n, t) => n + ntfy.topicos.get(t).filter((m) => m.attachment).length, 0);
        r.app.cifrado = topicosApp.length === 2 && topicosApp.every((t) => ntfy.topicos.get(t).every((m) => m.attachment ? m.message === "pm1" : /^pm1\.[\w-]+\.[\w-]+$/.test(m.message)));
        /* nada de JSON nem nomes das chaves no ntfy: só "pm1.<base64>.<base64>" nas mensagens e bytes cifrados nos anexos */
        r.app.textoClaroNoNtfy = topicosApp.some((t) => ntfy.topicos.get(t).some((m) => /["{}\s]|min-|perfil/.test(m.message || "")))
          || [...ntfy.arquivos.values()].some((b) => /min-cfg|"perfil"|Itaja/.test(b.toString("latin1")));
        r.app.cartasPc = appMain.registro.cartas.map((c) => `${c.base}→${c.versao} [${c.chaves.join(",")}] ${c.resps.join(" ")}`);
        r.app.recebidas = appMain.registro.recebidas.map((c) => `${c.tipo}${c.versao != null ? " v" + c.versao : ""} [${c.chaves.join(",")}]${c.nome ? " " + c.nome : ""}`);
        r.app.arquivoPc = (() => { try { const c = JSON.parse(fs.readFileSync(path.join(app.getPath("userData"), "app-celular.json"), "utf8")); return { codigoIgual: c.codigo === ap.codigo, versao: c.versao, aparelhos: Object.keys(c.aparelhos).length, envios: c.envios.length }; } catch (e) { return String(e.message); } })();
        /* desvincular no PC (dois cliques): o celular volta para a tela de vincular, sem os dados */
        await js(`irPara("premissas"); document.getElementById("appcel-desvincular").click()`); await esperar(300);
        r.app.desvincular = { confirmar: await js(`document.getElementById("appcel-desvincular").textContent`) };
        const recarregou = new Promise((ok) => celApp.webContents.once("did-finish-load", ok));
        await js(`document.getElementById("appcel-desvincular").click()`);
        await Promise.race([recarregou, esperar(12000)]); await esperar(1500);
        r.app.desvincular.celular = await ja(`({tela:!!document.getElementById("pm-vinc"), msg:document.getElementById("pm-status").textContent, codigo:localStorage.getItem("pm-codigo"), cfg:localStorage.getItem("min-cfg")})`);
        const pub = appMain.publico();
        r.app.desvincular.pc = { ligado: pub.ligado, codigo: pub.codigo, aparelhos: pub.aparelhos.length, escutando: appMain.conectado() };
        r.app.desvincular.tela = await js(`({botao:!document.getElementById("appcel-desligado").hidden, status:document.getElementById("appcel-status").textContent})`);
        await fotoApp("desvinculado");
        r.app.erros = errosApp;
        celApp.destroy(); srvApp.close();

        /* alerta de ofertas: liga, força a hora da busca automática e confere os avisos do Windows */
        r.alerta = {};
        await js(`irPara("ofertas")`);
        await js(`(()=>{ const s = document.getElementById("al-horas"); s.value = "6"; s.dispatchEvent(new Event("change", {bubbles:true})); })()`);
        r.alerta.ligado = await js(`({horas:alerta.horas, opcoes:!document.getElementById("al-opcoes").hidden, prox:document.getElementById("al-prox").textContent, vistos:Object.keys(alerta.vistos).length,
          salvo:JSON.parse(localStorage.getItem("min-ofertas-alerta")).horas})`);
        await js(`ofSel = ["rtx-3070"]; renderOfModelos()`);   /* busca curta: só a RTX 3070 */
        const forcarHora = `ofertas.quando -= 7*3600e3; alerta.ultima = ofertas.quando; true`;
        const rodarAuto = async () => { const ok = await js(`verificarAlerta()`); for (let i = 0; i < 240; i++) { if (!(await js("ofEst.rodando"))) break; await esperar(400); } return ok; };
        fase.n = 2;
        await js(forcarHora);
        r.alerta.rodou1 = await rodarAuto();
        r.alerta.avisos1 = testeSegundoPlano.notificacoes.slice();
        r.alerta.status1 = await js(`document.getElementById("of-status").textContent`);
        r.alerta.novosNaLista = await js(`[...document.querySelectorAll("#of-lista .of")].filter(e=>/Anúncio novo/.test(e.textContent)).map(e=>e.dataset.k)`);
        r.alerta.cedo = await js(`verificarAlerta()`);   /* logo depois: ainda não é hora */
        await js(forcarHora);
        r.alerta.rodou2 = await rodarAuto();
        r.alerta.avisosDepoisDaSegunda = testeSegundoPlano.notificacoes.length;   /* mesma lista: nada repetido */
        /* as marcas continuam por 24 horas, mesmo depois de outra busca */
        r.alerta.marcasDepoisDaSegunda = await js(`(()=>{ const ls = [...document.querySelectorAll("#of-lista .of")];
          return {novos:ls.filter(e=>/Anúncio novo/.test(e.textContent)).map(e=>e.dataset.k), baixou:ls.filter(e=>/Baixou de preço/.test(e.textContent)).map(e=>e.dataset.k+" "+(e.querySelector(".of-preco s")||{}).textContent)}; })()`);
        /* clique no aviso: abre Ofertas e mostra o anúncio */
        await js(`irPara("resumo")`);
        mostrarPrincipal("ofertas", "fb:1000000000000017");
        await esperar(700);
        r.alerta.clique = await js(`({tela:location.hash, destaque:[...document.querySelectorAll(".of.destaque")].map(e=>e.dataset.k), foco:document.activeElement && document.activeElement.className})`);
        await foto("ofertas_alerta");
        /* o Facebook pede login no meio das buscas automáticas: um aviso só, e não outro no mesmo dia */
        const nAntesLogin = testeSegundoPlano.notificacoes.length;
        fase.login = true;
        await js(forcarHora); await rodarAuto();
        await js(forcarHora); await rodarAuto();
        fase.login = false;
        r.alerta.avisosLogin = testeSegundoPlano.notificacoes.slice(nAntesLogin);
        r.alerta.statusLogin = await js(`document.getElementById("of-status").textContent`);
        r.celular.ofertas = ntfy.publicados.filter((m) => (m.tags || []).includes("moneybag")).map((m) => ({ title: m.title, message: m.message, click: m.click, acoes: m.actions }));
        r.celular.avisos = ntfy.publicados.filter((m) => (m.tags || []).includes("warning") && m.sequence_id !== "pc-sinal").map((m) => m.title + " | " + m.message);

        /* backup automático: um arquivo por dia, guarda os últimos 30, e dá para mudar a pasta */
        const pastaBk = path.join(app.getPath("userData"), "backups"), hojeLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
        r.backupAuto = {};
        r.backupAuto.feito = await js(`fazerBackup(true)`);
        r.backupAuto.arquivos = fs.readdirSync(pastaBk);
        r.backupAuto.msg = await js(`document.getElementById("bkp-msg").textContent`);
        try { const c = JSON.parse(fs.readFileSync(path.join(pastaBk, `painel-mineracao-${hojeLocal}.json`), "utf8")); r.backupAuto.conteudo = { app: c.app, chaves: Object.keys(c.dados).sort() }; } catch (e) { r.backupAuto.conteudo = String(e.message); }
        for (let i = 1; i <= 32; i++) fs.writeFileSync(path.join(pastaBk, `painel-mineracao-2025-${String(Math.ceil(i / 28)).padStart(2, "0")}-${String((i - 1) % 28 + 1).padStart(2, "0")}.json`), "{}");
        await js(`fazerBackup(true)`);
        const depois = fs.readdirSync(pastaBk);
        r.backupAuto.depoisDeLimpar = { total: depois.length, hojeFicou: depois.includes(`painel-mineracao-${hojeLocal}.json`), maisVelho: depois.sort()[0], semTmp: !depois.some((n) => /\.tmp$/.test(n)) };
        r.backupAuto.jaFezHoje = await js(`verificarBackup()`);
        await js(`document.getElementById("bkp-mudar").click()`); await esperar(800);
        r.backupAuto.novaPasta = await js(`bkpInfo && bkpInfo.pasta`);
        try { r.backupAuto.naNova = fs.readdirSync(path.join(app.getPath("userData"), "backups-escolhida")); } catch (e) { r.backupAuto.naNova = String(e.message); }

        /* dados de fora pelo navegador escondido (dólar e Promotech) */
        r.leitura = await js(`(async () => {
          const mcp = await window.claude.use("mcp");
          const t2 = await lerPaginaAte(mcp, "${base}/promo", t=>/Menor pre/.test(t), 6);
          const t3 = await lerPaginaAte(mcp, "${base}/dolar", t=>/USDBRL/.test(t), 5);
          return {promo:lerPromotech(corpoDe(t2), "rtx-5060-ti-16gb-vs-rtx-5060-ti-8gb"), dolar:lerDolar(t3)};
        })()`);
        r.backup = await js(`window.desktop.salvarArquivo("teste-backup.json", JSON.stringify(backupDados()))`);
        r.backupChaves = Object.keys(JSON.parse(fs.readFileSync(r.backup, "utf8")).dados).sort();

        /* relatório do ano: PDF e planilha pelos botões do Diário (no teste, salvos na pasta temporária) */
        await js(`irPara("diario")`); await esperar(400);
        r.relatorio = {};
        r.relatorio.antes = await js(`(()=>{ diario = diario.filter(e=>e.data!=="2026-10-20").concat([{data:"2026-10-20", valor:3, moeda:"USD", dolar:5.05, horas:24, obs:"teste; relatório", criado:1, btc:0.00002712}]); lsSet("min-diario", diario); renderDiario();
          return {anos:[...document.querySelectorAll("#rel-ano option")].map(o=>o.value), pdf:!document.querySelector("[data-rel=pdf]").hidden, csv:!document.querySelector("[data-rel=csv]").hidden, texto:document.getElementById("rel-res").innerText.slice(0,400)}; })()`);
        await js(`relAno = "2026"; renderRelatorio(); document.querySelector("[data-rel=pdf]").click()`);
        for (let i = 0; i < 40; i++) { await esperar(250); if (/PDF salvo|Não deu/.test(await js(`document.getElementById("rel-status").textContent`))) break; }
        r.relatorio.statusPdf = await js(`document.getElementById("rel-status").textContent`);
        await js(`document.querySelector("[data-rel=csv]").click()`); await esperar(500);
        r.relatorio.statusCsv = await js(`document.getElementById("rel-status").textContent`);
        await js(`document.querySelector("[data-rel=copiar]").click()`); await esperar(400);
        r.relatorio.copiado = testeArquivos.copiado.slice(0, 200);
        r.relatorio.salvos = testeArquivos.salvos.map((f) => path.basename(f));
        try { const pdf = fs.readFileSync(testeArquivos.salvos.find((f) => /\.pdf$/.test(f))); r.relatorio.pdf = { inicio: pdf.slice(0, 5).toString(), bytes: pdf.length, paginas: (pdf.toString("latin1").match(/\/Type\s*\/Page[^s]/g) || []).length }; } catch (e) { r.relatorio.pdf = String(e.message); }
        try { const csv = fs.readFileSync(testeArquivos.salvos.find((f) => /\.csv$/.test(f)), "utf8"); r.relatorio.csv = { bom: csv.charCodeAt(0) === 0xfeff, linhas: csv.split("\r\n").length, outubro: csv.split("\r\n").find((l) => l.startsWith("Outubro;")), obs: /"teste; relatório"/.test(csv) }; } catch (e) { r.relatorio.csv = String(e.message); }
        await foto("diario_relatorio");

        /* conta da Kryptex: sem login → entrar (janela) → verificação contra robôs → máquinas e saldo; máquina para, volta,
           rende menos; o ganho de um dia pelo saldo vira sugestão no Diário; copiar o que o painel leu (sem e-mail) */
        r.kryptex = {};
        await js(`irPara("resumo")`); await esperar(300);
        const kxEstado = `({estado:kx.estado, msg:kx.msg, maquinas:kx.maquinas.map(m=>({nome:m.nome, online:m.online, estado:m.estado, h30:m.h30, base:m.base})), saldo:kx.saldo && {btc:kx.saldo.btc, fiat:kx.saldo.fiat, moeda:kx.saldo.moeda, preco:kx.saldo.preco},
          alertas:kx.alertas.map(a=>a.tipo), card:document.getElementById("kx-corpo").innerText.slice(0,500), visivel:!document.getElementById("kx-p").hidden})`;
        r.kryptex.antes = await js(`({visivel:!document.getElementById("kx-p").hidden, botao:!!document.querySelector('#kx-acoes [data-kx="ligar"]'), entrarNoPc:!document.querySelector('[data-pc="kryptex"]').hidden})`);
        const notifAntes = testeSegundoPlano.notificacoes.length;
        await js(`mudarKxCfg({ligado:true}); lerKryptex(true)`);
        for (let i = 0; i < 80; i++) { await esperar(250); if (!(await js("kxLendo"))) break; }
        r.kryptex.semLogin = await js(kxEstado);
        r.kryptex.semLoginAvisou = testeSegundoPlano.notificacoes.length - notifAntes;
        r.kryptex.segundoPlano = segundoPlano();
        kxf.entrando = true; kxf.desafio = 1;
        await js(`document.querySelector('#kx-acoes [data-kx="entrar"]').click()`);
        for (let i = 0; i < 160; i++) { await esperar(250); if (testeKryptex.entrou && !(await js("kxLendo")) && (await js("kx.estado")) !== "login") break; }
        await esperar(500);
        r.kryptex.entrou = await js(`({...${kxEstado}, status:document.getElementById("kx-status").textContent})`);
        r.kryptex.janelas = testeKryptex.entrou;
        r.kryptex.pedidos = kxf.pedidos.slice();
        await foto("kryptex");
        /* a máquina para (a Kryptex marca offline): aviso no Windows e no celular; depois volta */
        const nAntes = testeSegundoPlano.notificacoes.length, pubAntes = ntfy.publicados.length;
        kxf.maquinas[0].is_online = false;
        await js(`lerKryptex(false)`); for (let i = 0; i < 80; i++) { await esperar(250); if (!(await js("kxLendo"))) break; }
        r.kryptex.parou = await js(kxEstado);
        kxf.maquinas[0].is_online = true;
        await js(`lerKryptex(false)`); for (let i = 0; i < 80; i++) { await esperar(250); if (!(await js("kxLendo"))) break; }
        r.kryptex.voltou = await js(kxEstado);
        /* rendendo menos: duas leituras seguidas abaixo de 70% do normal */
        kxf.maquinas[0].avg_hashrate_30m = 30000000;
        await js(`lerKryptex(false)`); for (let i = 0; i < 80; i++) { await esperar(250); if (!(await js("kxLendo"))) break; }
        r.kryptex.umaBaixa = await js(kxEstado);
        await js(`lerKryptex(false)`); for (let i = 0; i < 80; i++) { await esperar(250); if (!(await js("kxLendo"))) break; }
        r.kryptex.lenta = await js(kxEstado);
        kxf.maquinas[0].avg_hashrate_30m = 59000000;
        await js(`lerKryptex(false)`); for (let i = 0; i < 80; i++) { await esperar(250); if (!(await js("kxLendo"))) break; }
        r.kryptex.normal = await js(kxEstado);
        r.kryptex.avisos = testeSegundoPlano.notificacoes.slice(nAntes).map((n) => n.titulo);
        r.kryptex.celular = ntfy.publicados.slice(pubAntes).filter((m) => m.sequence_id !== "pc-sinal" && m.title).map((m) => m.title);
        /* o ganho de ontem pelo saldo (leituras às 00:10, 12:00 e 00:20 de hoje): vira sugestão no Diário e é anotado pelo botão */
        r.kryptex.dia = await js(`(async()=>{ const h = new Date(); h.setHours(0,0,0,0); const ontem = h.getTime() - 864e5, iso = isoLocal(new Date(ontem));
          diario = diario.filter(e=>e.data!==iso); lsSet("min-diario", diario); delete kx.dias[iso];
          kxHist.saldos = [[ontem + 10*60e3, 0.0001, 68000], [ontem + 12*3600e3, 0.000105, 68000], [h.getTime() + 20*60e3, 0.00011, 68100]];
          calcularDiasKx(); renderSugestoesKx(); irPara("diario"); await new Promise(o=>setTimeout(o,300));
          const sug = document.getElementById("kx-sug").innerText;
          document.querySelector('[data-kx-anotar="'+iso+'"]').click(); await new Promise(o=>setTimeout(o,400));
          const e = diario.find(x=>x.data===iso);
          return {iso, dia:kx.dias[iso], sugestao:sug.slice(0,300), anotado:e && {valor:e.valor, moeda:e.moeda, btc:e.btc, obs:e.obs, fonte:e.fonte}, sumiu:document.getElementById("kx-sug").hidden}; })()`);
        await foto("kryptex_diario");
        await js(`irPara("resumo")`); await esperar(300);
        await js(`document.querySelector('#kx-acoes [data-kx="copiar"]').click()`); await esperar(500);
        const diag = testeArquivos.copiado;
        r.kryptex.diag = { tamanho: diag.length, semEmail: !/alex\.teste@example\.com/.test(diag), semCarteira: !/bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh/.test(diag), semCodigo: !/7f3a9c2e1b4d5f60718293a4b5c6d7e8f9/.test(diag), temDataset: /workerDataset/.test(diag), oculto: /e-mail@oculto/.test(diag) };
        r.kryptex.sincronizada = await js(`({lista:SINCRONIZADAS.includes("min-kryptex"), gravada:!!localStorage.getItem("min-kryptex"), hist:!!localStorage.getItem("min-kx-hist")})`);

        for (const tela of ["resumo", "setup", "premissas"]) {
          await js(`irPara("${tela}")`); await esperar(500);
          (r.transbordo = r.transbordo || {})[tela] = await js(`(() => { const W = document.documentElement.clientWidth; return {janela: W, largura: document.documentElement.scrollWidth}; })()`);
          await foto(tela);
        }
        r.pastaDados = app.getPath("userData");
        r.agentes = [...new Set(agentes)];
        r.agenteLimpo = r.agentes.length > 0 && r.agentes.every((a) => /Chrome\/\d/.test(a) && !/Electron|Painel|painel|Minera/.test(a) && /^[\x20-\x7e]+$/.test(a));
        r.leitorAntes = pegarLeitor().webContents.getURL();
        await esperar(Number(process.env.PAINEL_DESCANSO || 0) + 1500);
        r.leitorDepoisDoDescanso = pegarLeitor().webContents.getURL();

        /* novidades: quem vinha da 1.1.0 vê o que mudou no Resumo, até clicar em Entendi */
        await js(`localStorage.setItem("min-versao", JSON.stringify("1.1.0"))`);
        await new Promise((ok) => { principal.webContents.once("did-finish-load", ok); principal.webContents.reload(); });
        await esperar(1500);
        await js(`irPara("resumo")`);
        r.novidades = await js(`({visivel:!document.getElementById("novid").hidden, titulo:document.getElementById("t-novid").textContent, itens:[...document.querySelectorAll("#novid-lista li")].map(li=>li.textContent)})`);
        await foto("novidades");
        await js(`document.getElementById("novid-ok").click()`);
        r.novidadesDepois = await js(`({visivel:!document.getElementById("novid").hidden, vista:JSON.parse(localStorage.getItem("min-versao")), foco:document.activeElement && document.activeElement.id})`);

        /* ícone perto do relógio e abrir junto com o Windows (por último: depois de esconder, a janela não tira mais foto) */
        await js(`irPara("ofertas")`);
        const marcar = (id, v) => js(`(()=>{ const c = document.getElementById("${id}"); c.checked = ${v}; c.dispatchEvent(new Event("change", {bubbles:true})); })()`);
        await marcar("al-bandeja", true); await esperar(300);
        await marcar("pc-iniciar", true); await esperar(300);
        r.bandeja = { config: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows, abre: comoAbrir(true) };
        try { r.bandeja.arquivo = JSON.parse(fs.readFileSync(path.join(app.getPath("userData"), "segundo-plano.json"), "utf8")); } catch (e) { r.bandeja.arquivo = String(e.message); }
        if (r.bandeja.config.temBandeja) {
          const n0 = testeSegundoPlano.notificacoes.length;
          principal.close(); await esperar(400);
          r.bandeja.fechar1 = { destruida: principal.isDestroyed(), escondeu: testeSegundoPlano.escondeu, avisos: testeSegundoPlano.notificacoes.slice(n0).map((n) => n.titulo + " | " + n.corpo) };
          principal.close(); await esperar(300);
          r.bandeja.fechar2 = { destruida: principal.isDestroyed(), escondeu: testeSegundoPlano.escondeu, avisos: testeSegundoPlano.notificacoes.length - n0 };
        }
        await marcar("al-bandeja", false); await esperar(300);
        r.bandeja.desligada = { config: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows, abre: comoAbrir(true) };

        /* Sair pelo painel: cancela o aviso agendado e marca que saiu de propósito (ao abrir, não diz que "voltou") */
        if (r.celular) {
          const topico = celularMain.estado().topico, antes = ntfy.apagados.length;
          await celularMain.sair();
          r.celular.sair = { apagou: ntfy.apagados.slice(antes), agendado: !!ntfy.agendados[`${topico}/pc-sinal`] };
          try { r.celular.sair.saiuAMao = JSON.parse(fs.readFileSync(path.join(app.getPath("userData"), "celular.json"), "utf8")).saiuAMao; } catch (e) { r.celular.sair.saiuAMao = String(e.message); }
          r.celular.sair.voltaDepoisDeSair = await celularMain.verificarVolta();
          r.celular.totalSinais = ntfy.publicados.filter((m) => m.sequence_id === "pc-sinal").length;
        }
      } catch (e) { r.falha = String((e && e.stack) || e); }
      fs.writeFileSync(path.join(SAIDA, "teste-desktop.json"), JSON.stringify(r, null, 1));
      for (const e of ntfy.escutas) { try { e.res.end(); } catch (err) {} }
      srv.close(); app.quit();
    });
  });
};
