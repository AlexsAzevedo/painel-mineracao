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


with sync_playwright() as p:
    tema(p)
fim()
