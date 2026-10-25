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


with sync_playwright() as p:
    tema(p)
    menu(p)
fim()
