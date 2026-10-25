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


with sync_playwright() as p:
    tema(p)
    menu(p)
    resumo(p)
fim()
