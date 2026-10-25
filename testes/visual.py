"""Visual do painel: tema escuro e claro, fontes, contraste, menu, Resumo, ofertas e as outras telas (dados inventados).
Uso: python3 testes/visual.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403


def tema(p):
    pg = abrir(p, dados={"min-cfg": CFG})   # com perfil: sem a configuração inicial na frente
    checa("padrão escuro", pg.evaluate("document.documentElement.dataset.tema") == "escuro")
    checa("fundo escuro", pg.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(12, 16, 22)")
    pg.click('[data-tema-op="claro"]')
    checa("claro", pg.evaluate("[document.documentElement.dataset.tema, getComputedStyle(document.body).backgroundColor, localStorage.getItem('min-tema')]") == ["claro", "rgb(243, 245, 248)", "claro"])
    pg.reload(); pg.wait_for_timeout(300)
    checa("continua claro", pg.evaluate("document.documentElement.dataset.tema") == "claro")
    checa("botão marcado", pg.evaluate("[...document.querySelectorAll('[data-tema-op]')].every(b => b.getAttribute('aria-pressed') === String(b.dataset.temaOp === 'claro'))"))
    checa("fontes", "Sora" in pg.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily") and "Inter" in pg.evaluate("getComputedStyle(document.body).fontFamily"))
    # sem localStorage (navegação privada): escuro, sem erro
    pg2 = abrir(p, sem_storage=True)
    checa("sem storage", pg2.evaluate("document.documentElement.dataset.tema") == "escuro" and not [e for e in erros(pg2) if "armazenamento" not in e], erros(pg2)[:3])
    # contraste >= 4.5 nos dois temas
    for t in ("escuro", "claro"):
        for par, r in contrastes(pg, t).items():
            checa(f"contraste {t}: {par}", r >= 4.5, round(r, 2))


def menu(p):
    pg = abrir(p, dados={"min-cfg": CFG})  # 1366
    checa("grupos", pg.eval_on_selector_all(".menu-t", "e=>e.map(x=>x.textContent)") == ["Acompanhar", "Comprar", "Ajustes"])
    checa("ordem", pg.eval_on_selector_all(".menu .item[data-view]", "e=>e.map(x=>x.dataset.view)") == ["resumo", "diario", "minhas", "ofertas", "anuncio", "placas", "setup", "premissas"])
    checa("ordem das telas", pg.evaluate("VIEWS") == ["resumo", "diario", "minhas", "ofertas", "anuncio", "placas", "setup", "premissas"])
    checa("sem barra no PC", pg.is_hidden(".abas"))
    checa("estado no rodapé", pg.is_visible("#vivo") and pg.is_visible(".side-pe .tema-sel"))
    pg = abrir(p, largura=390, altura=844, dados={"min-cfg": CFG})
    checa("barra", pg.eval_on_selector_all(".abas .aba:not([hidden])", "e=>e.map(x=>x.textContent.trim())") == ["Resumo", "Diário", "Placas", "Mais"])  # online: sem Ofertas
    checa("botões da barra com 44 px", pg.eval_on_selector_all(".abas .aba:not([hidden])", "e=>e.every(x=>x.getBoundingClientRect().height>=44)"))
    pg.click("#aba-mais")
    checa("folha aberta", pg.is_visible("#mais") and pg.get_attribute("#aba-mais", "aria-expanded") == "true")
    pg.click('#mais [data-view="premissas"]')
    checa("foi para Premissas", pg.is_visible("#v-premissas") and pg.is_hidden("#mais") and pg.get_attribute("#aba-mais", "aria-current") == "page")
    pg.click("#aba-mais"); pg.keyboard.press("Escape")
    checa("Esc fecha", pg.is_hidden("#mais") and pg.get_attribute("#aba-mais", "aria-expanded") == "false")
    pg.click("#aba-mais"); pg.click('#mais [data-tema-op="claro"]')
    checa("tema pela folha", pg.evaluate("document.documentElement.dataset.tema") == "claro")
    checa("voltar fecha a folha", pg.evaluate("abrirMais(), [fecharMais(), fecharMais()]") == [True, False])
    pg.click('.abas [data-view="diario"]')
    checa("aba do Diário", pg.is_visible("#v-diario") and pg.get_attribute('.abas [data-view="diario"]', "aria-current") == "page")
    checa("menu de cima escondido", pg.is_hidden(".menu"))
    checa("sem rolagem lateral", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    pg = abrir(p, largura=390, altura=844, celular=True)
    checa("Ofertas na barra do celular", pg.is_visible("#aba-ofertas"))


def resumo(p):
    pg = abrir(p, dados=DADOS)
    ids = pg.eval_on_selector_all("#v-resumo [id]", "e=>e.map(x=>x.id)")
    checa("ordem", [i for i in ids if i in ("agora", "r-mes", "r-graf-p", "r-ret-p", "r-avisos-p")] == ["agora", "r-mes", "r-graf-p", "r-ret-p", "r-avisos-p"], ids)
    m = pg.evaluate("resumoMes()")
    checa("o mês", abs(m["recebido"] - DADOS_ESPERADO["recebido_mes"]) < 0.01 and m["dias"] == 14 and abs(m["lucro"] - (m["recebido"] - m["luz"])) < 0.01, m)
    checa("4 cartões do mês", pg.eval_on_selector_all("#r-mes .kpi .lbl", "e=>e.map(x=>x.textContent)") == ["Lucro do mês", "Recebido", "Previsto", "Recuperado"])
    checa("recuperado diz que é estimado (o real fica no Retorno)", "estimativa" in pg.inner_text("#r-mes .kpi:nth-child(4) small"), pg.inner_text("#r-mes .kpi:nth-child(4) small"))
    checa("14 dias no gráfico", pg.eval_on_selector_all("#r-graf .bar-hit", "e=>e.length") == 14)
    checa("Diário igual", pg.evaluate("irPara('diario'), document.querySelectorAll('#d-graf .bar-hit').length") == DADOS_ESPERADO["dias_grafico_diario"])
    checa("compras em Todas as placas", pg.evaluate("!!document.querySelector('#v-placas #r-compras') && document.querySelectorAll('#r-compras li').length > 0"))
    checa("analisados em Analisar anúncio", pg.evaluate("!!document.querySelector('#v-anuncio #r-anuncios')"))
    checa("cenário e conta da Kryptex em Premissas", pg.evaluate("!!document.querySelector('#v-premissas #r-cenario') && !!document.querySelector('#v-premissas #kx-p')"))
    pg.evaluate("irPara('resumo')")
    checa("agora sem app: frase do online", "No aplicativo do PC" in pg.inner_text("#agora"))
    checa("hoje até agora estimado", "hoje até agora" in pg.inner_text("#ag-hoje").lower())
    checa("retorno da placa", "AMD RX 9070 XT" in pg.inner_text("#r-rig"))
    checa("sem ofertas no online", pg.is_hidden("#r-of-p"))
    checa("avisos vazio", "Nenhum aviso nos últimos 7 dias." in pg.inner_text("#r-avisos"))
    checa("sem erros (PC)", not erros(pg), erros(pg)[:3])
    pgc = abrir(p, largura=390, altura=844, dados=DADOS, celular=True)
    checa("3 ofertas no Resumo do celular", pgc.eval_on_selector_all("#r-ofertas .of-mini", "e=>e.length") == 3)
    checa("a melhor oferta primeiro", "RTX 4060" in pgc.inner_text("#r-ofertas .of-mini"))
    checa("agora no celular", "O PC ainda não mandou" in pgc.inner_text("#agora"))
    checa("avisos", pgc.evaluate("kx.alertas=[{t:Date.now()-60e3,tipo:'parou',texto:'RX 9070 XT parou de minerar'}], renderAvisos(), document.querySelector('#r-avisos').innerText").startswith("RX 9070 XT parou"))
    checa("aviso de dias para anotar", pgc.evaluate("kx.dias={'2026-10-24':{btc:1e-5,valor:14,moeda:'BRL',horas:24,aproximado:false,fonte:'saldo'}}, diario=diario.filter(e=>e.data!=='2026-10-24'), renderResumo(), !document.getElementById('kx-aviso-sug').hidden"))
    checa("sem rolagem lateral 390", pgc.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    checa("sem erros (celular)", not erros(pgc), erros(pgc)[:3])
    for larg in (1366, 1280):
        pgp = abrir(p, largura=larg, altura=1200, dados=DADOS, pc=True)
        checa(f"prazo das ofertas sem cortar ({larg})", pgp.evaluate("""(() => { const ps = [...document.querySelectorAll('#r-ofertas .of-mini .pill')];
            return ps.length === 3 && ps.every(e => e.scrollWidth <= e.clientWidth + 1 && e.getBoundingClientRect().right <= e.closest('.of-mini').getBoundingClientRect().right); })()"""),
            pgp.evaluate("[...document.querySelectorAll('#r-ofertas .of-mini .pill')].map(e=>[e.scrollWidth, e.clientWidth])"))
        checa(f"Agora sem espaço vazio embaixo ({larg})", pgp.evaluate("""(() => { const a = document.getElementById('agora'), c = document.getElementById('ag-corpo');
            return a.getBoundingClientRect().bottom - c.getBoundingClientRect().bottom <= parseFloat(getComputedStyle(a).paddingBottom) + 2; })()"""))


def ofertas(p):
    pgc = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, hash="ofertas")
    checa("cartões", pgc.eval_on_selector_all("#of-lista .of", "e=>e.length") == DADOS_ESPERADO["ofertas_filtradas"])
    checa("foto válida", pgc.evaluate("[fotoValida('https://scontent-gru2-1.xx.fbcdn.net/v/t45/a.jpg'), fotoValida('http://x.fbcdn.net/a.jpg'), fotoValida('https://evil.com/a.jpg'), fotoValida('https://img.olx.com.br/thumbs/a.jpg'), fotoValida('https://fbcdn.net.evil.com/a.jpg')]")
          == ["https://scontent-gru2-1.xx.fbcdn.net/v/t45/a.jpg", "", "", "https://img.olx.com.br/thumbs/a.jpg", ""])
    checa("sem foto: desenho", pgc.evaluate("[...document.querySelectorAll('#of-lista .of')].filter(a=>!a.querySelector('img.of-foto')).length") == DADOS_ESPERADO["ofertas_sem_foto_visiveis"])
    checa("todo cartão tem o desenho por baixo", pgc.evaluate("[...document.querySelectorAll('#of-lista .of')].every(a=>a.querySelector('.of-img .of-ph'))"))
    for i in range(DADOS_ESPERADO["ofertas_filtradas"]):   # as fotos carregam quando o cartão aparece (loading=lazy)
        pgc.evaluate(f"document.querySelectorAll('#of-lista .of')[{i}].scrollIntoView()"); pgc.wait_for_timeout(120)
    pgc.wait_for_timeout(600)   # as fotos de teste apontam para endereços que não respondem
    checa("foto_quebrada", pgc.evaluate("[...document.querySelectorAll('img.of-foto')].every(i=>i.hidden)") and not erros(pgc), erros(pgc)[:3])
    checa("cartão: preço típico, lucro e prazo", all(s in pgc.inner_text("#of-lista .of") for s in ["R$ 1.480", "lucro", "abaixo do típico", "meses"]), pgc.inner_text("#of-lista .of")[:300])
    checa("cartão: barra do prazo", pgc.evaluate("!!document.querySelector('#of-lista .of .of-prazo span')"))
    checa("barra de busca inteira", pgc.evaluate("document.querySelector('#v-ofertas .of-barra').getBoundingClientRect().height") > 30)
    checa("gráfico", pgc.eval_on_selector_all("#of-graf .pt-hit", "e=>e.length") == DADOS_ESPERADO["ofertas_filtradas"])
    checa("gráfico: resumo para leitor de tela", "anúncios" in (pgc.get_attribute("#of-graf svg", "aria-label") or ""))
    checa("gráfico: legenda", all(s in pgc.inner_text("#of-leg") for s in ["compensa", "apertado"]))
    pgc.focus("#of-graf .pt-hit")
    checa("dica", pgc.is_visible("#of-graf .tip") and "R$" in pgc.inner_text("#of-graf .tip"))
    pgc.click("#of-graf .pt-hit")
    checa("leva ao cartão", pgc.evaluate("!!document.querySelector('.of.destaque')"))
    pgc.evaluate("document.getElementById('of-so-compensa').click()")
    checa("filtro muda o gráfico", pgc.eval_on_selector_all("#of-graf .pt-hit", "e=>e.length") == 12)
    checa("seletores antigos", pgc.evaluate("!!document.querySelector('#of-lista .of .of-tit') && !!document.querySelector('.of-ret .pill') && !!document.querySelector('.of-preco s') && !!document.querySelector('[data-of=\"det\"]') && !!document.querySelector('[data-of=\"desc\"]')"))
    checa("filtros numa linha (fichas)", pgc.evaluate("getComputedStyle(document.getElementById('of-filtros')).flexWrap") == "nowrap")
    checa("explicação no Saiba mais", pgc.evaluate("!!document.querySelector('#v-ofertas details.saiba')"))
    checa("sem rolagem lateral", pgc.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    # Ver detalhes (no menu ⋯ do cartão): a lista é desenhada de novo e o foco continua no mesmo cartão
    k = pgc.evaluate("document.querySelector('#of-lista .of').dataset.k")
    pgc.evaluate("document.querySelector('#of-lista .of details.of-mais').open = true")
    pgc.click("#of-lista .of [data-of='det']"); pgc.wait_for_timeout(300)
    checa("ver detalhes: o foco fica no cartão", pgc.evaluate("(k) => { const a = document.activeElement, c = a && a.closest('#of-lista .of'); return !!c && c.dataset.k === k; }", k),
          pgc.evaluate("document.activeElement && document.activeElement.outerHTML.slice(0, 120)"))
    # foto que carrega
    import copy
    d2 = copy.deepcopy(DADOS); d2["min-ofertas"]["itens"][1]["foto"] = OLX + "ok.jpg"
    pg2 = abrir(p, largura=1366, altura=900, dados=d2, celular=True, hash="ofertas")
    pg2.wait_for_timeout(800)
    checa("foto que carrega aparece", pg2.evaluate("(() => { const i = document.querySelector('img.of-foto[src$=\"ok.jpg\"]'); return !!i && !i.hidden && i.naturalWidth > 0; })()"))
    checa("sem erros (ofertas)", not erros(pg2), erros(pg2)[:3])


CONTRASTE_JS = """() => {
  const ler = c => { const m = /rgba?\\(([^)]+)\\)/.exec(c || ""); if (!m) return null; const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return {r:p[0], g:p[1], b:p[2], a: p.length > 3 ? p[3] : 1}; };
  const lum = ({r, g, b}) => { const f = v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const mix = (t, b) => ({r: t.r * t.a + b.r * (1 - t.a), g: t.g * t.a + b.g * (1 - t.a), b: t.b * t.a + b.b * (1 - t.a), a: 1});
  const fundo = el => { const pilha = []; for (let e = el; e; e = e.parentElement) { const c = ler(getComputedStyle(e).backgroundColor); if (c && c.a > 0) { pilha.push(c); if (c.a >= 1) break; } }
    let base = {r: 255, g: 255, b: 255, a: 1}; for (let i = pilha.length - 1; i >= 0; i--) base = pilha[i].a >= 1 ? pilha[i] : mix(pilha[i], base); return base; };
  const view = document.querySelector(".view:not([hidden])"); if (!view) return [["sem tela", "", 0]];
  const els = [...view.querySelectorAll(".sub, .lbl, .hint, .pill, .nota-mini, small, .status")].filter(e => e.offsetParent && e.textContent.trim() && !e.closest(".desc")).slice(0, 120);
  const ruins = [];
  for (const e of els) {
    const fg = ler(getComputedStyle(e).color); if (!fg) continue;
    const bg = fundo(e), f = fg.a < 1 ? mix(fg, bg) : fg, a = lum(f), b = lum(bg), r = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (r < 4.5) ruins.push([e.className, e.textContent.trim().slice(0, 40), +r.toFixed(2)]);
  }
  return ruins;
}"""


FOTOS = sys.argv[sys.argv.index("--fotos") + 1] if "--fotos" in sys.argv else ""   # pasta para as fotos de cada tela


def telas(p):
    import re as _re
    if FOTOS:
        os.makedirs(FOTOS, exist_ok=True)
    css = open(PAGINA, encoding="utf-8").read()
    css = css[css.index("<style>"):css.index("</style>")]
    css = _re.sub(r":root(\[data-tema=\"claro\"\])?\{[^}]*\}", "", css)
    fixas = [c for c in _re.findall(r"[^{}\n]*\{[^}]*#[0-9a-fA-F]{3,6}\b[^}]*\}", css) if not c.strip().startswith(".appcel-codigo")]
    checa("nenhuma cor fixa fora das variáveis", not fixas, [f[:80] for f in fixas[:3]])
    for largura, modo in ((1366, "pc"), (390, "celular")):
        pg = abrir(p, largura=largura, altura=900, dados=DADOS, pc=(modo == "pc"), celular=(modo == "celular"))
        pg.wait_for_timeout(400)
        for tema in ("escuro", "claro"):
            pg.evaluate(f"aplicarTema('{tema}')")
            for v in pg.evaluate("VIEWS"):
                pg.evaluate(f"irPara('{v}')"); pg.wait_for_timeout(120)
                onde = f"{modo} {tema} {v}"
                checa(f"{onde}: sem rolagem lateral", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), pg.evaluate("document.documentElement.scrollWidth"))
                sub = pg.evaluate("(() => { const e = document.querySelector('.view:not([hidden]) .vh .sub'); return e ? e.textContent.trim() : ''; })()")
                checa(f"{onde}: subtítulo curto", len(sub) <= 160, f"{len(sub)}: {sub[:60]}")
                ruins = pg.evaluate(CONTRASTE_JS)
                checa(f"{onde}: contraste", not ruins, ruins[:3])
                if FOTOS:
                    pg.screenshot(path=os.path.join(FOTOS, f"{modo}_{tema}_{v}.png"), full_page=True)
        checa(f"{modo}: sem erros", not erros(pg), erros(pg)[:3])
    pg = abrir(p, dados=DADOS, hash="placas")
    checa("Saiba mais em Todas as placas", pg.evaluate("!!document.querySelector('#v-placas details.saiba')"))
    checa("selo com ícone além da cor", pg.evaluate("getComputedStyle(document.querySelector('.pill.g') || document.body, '::before').content") not in ("none", "normal", ""))


with sync_playwright() as p:
    tema(p)
    menu(p)
    resumo(p)
    ofertas(p)
    telas(p)
fim()
