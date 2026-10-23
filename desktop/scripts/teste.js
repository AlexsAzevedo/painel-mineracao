"use strict";
/* Teste automático do aplicativo (PAINEL_TESTE=1): roda dentro do Electron, sem mostrar janela.
   Começa do zero (pasta de dados vazia), passa pela configuração inicial como uma pessoa faria,
   busca ofertas em páginas de teste no formato do Marketplace e da OLX e confere o resultado. */
const http = require("http");
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");

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
  const card = (x) => `<a href="/marketplace/item/${x.id}/?ref=search" style="display:block;height:150px">${x.l.map((s) => `<div>${esc(s)}</div>`).join("")}</a>`;
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
    `<section class="olx-adcard olx-adcard__horizontal"><div class="olx-adcard__content"><a data-testid="adcard-link" class="olx-adcard__link" title="${esc(t)}" href="${esc(url)}"><h2 class="olx-adcard__title">${esc(t)}</h2></a>
      <div class="olx-adcard__badges">${ent ? "<div>Entrega Fácil</div>" : ""}${gar ? "<div>Garantia da OLX</div>" : ""}</div>
      <h3 class="olx-adcard__price">${esc(p)}</h3><p class="olx-adcard__location">${esc(l)}</p><p class="olx-adcard__date">${esc(d)}</p></div></section>`);
  return `<!doctype html><html><head><meta charset="utf-8"><title>"${esc(q.get("q") || "")}" | OLX</title></head><body><main><p>1 - ${cards.length} de ${cards.length} resultados</p>${cards.join("")}</main></body></html>`;
}
const paginaTexto = (titulo, linhas, papel) => `<!doctype html><html><head><meta charset="utf-8"><title>${esc(titulo)}</title></head><body><div ${papel}>${linhas.map((s) => `<div>${esc(s)}</div>`).join("")}</div></body></html>`;

module.exports = function (principal, { app, pegarLeitor, iniciarAtualizacao, mostrarPrincipal, testeSegundoPlano, segundoPlano }) {
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
  const srv = http.createServer((req, res) => {
    const u = new URL(req.url, "http://x"), p = u.pathname;
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
        await marcar("al-iniciar", true); await esperar(300);
        r.bandeja = { config: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows };
        try { r.bandeja.arquivo = JSON.parse(fs.readFileSync(path.join(app.getPath("userData"), "segundo-plano.json"), "utf8")); } catch (e) { r.bandeja.arquivo = String(e.message); }
        if (r.bandeja.config.temBandeja) {
          const n0 = testeSegundoPlano.notificacoes.length;
          principal.close(); await esperar(400);
          r.bandeja.fechar1 = { destruida: principal.isDestroyed(), escondeu: testeSegundoPlano.escondeu, avisos: testeSegundoPlano.notificacoes.slice(n0).map((n) => n.titulo + " | " + n.corpo) };
          principal.close(); await esperar(300);
          r.bandeja.fechar2 = { destruida: principal.isDestroyed(), escondeu: testeSegundoPlano.escondeu, avisos: testeSegundoPlano.notificacoes.length - n0 };
        }
        await marcar("al-bandeja", false); await esperar(300);
        r.bandeja.desligada = { config: segundoPlano(), inicioComWindows: testeSegundoPlano.inicioComWindows, iniciarDesabilitado: await js(`document.getElementById("al-iniciar").disabled`) };

      } catch (e) { r.falha = String((e && e.stack) || e); }
      fs.writeFileSync(path.join(SAIDA, "teste-desktop.json"), JSON.stringify(r, null, 1));
      srv.close(); app.quit();
    });
  });
};
