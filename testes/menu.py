"""O menu novo (1.12.0): três áreas (Resumo geral, Comprar e Configurações), os botões das telas no alto, Configurações
em cinco telas e os endereços de antes (dados inventados).
Uso: python3 testes/menu.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

AREAS = {"resumo": ["resumo", "diario", "minhas", "setup"], "comprar": ["ofertas", "anuncio", "placas", "sim"],
         "config": ["mineracao", "perfil", "integracoes", "computador", "sobre"]}
BOTOES = {"resumo": ["Visão geral", "Diário de ganhos", "Minhas placas", "Meu setup"],
          "comprar": ["Ofertas", "Analisar anúncio", "Todas as placas", "Simulador"],
          "config": ["Mineração", "Perfil", "Integrações", "Este computador", "Sobre"]}
QUADROS = {"mineracao": ["cen-p", "placa-p", "placa-cel", "protecao-p", "branca-p", "notas-prem"], "perfil": ["perfil-p", "fb-p", "kx-p"],
           "integracoes": ["kxa-p", "appcel-p", "celular-p", "acesso-p", "dados-fora"],
           "computador": ["mais-sync", "estecel-p", "este-pc", "aparencia-p"], "sobre": ["sobre-p"]}
TODAS = [v for a in AREAS.values() for v in a]


def texto(pg, sel):
    """Texto visível de um elemento ("" se ele não existe)."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText.trim() : ''; }", sel)


def visivel(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'; }", sel)


def clica(pg, sel):
    """Clica pelo próprio painel (sem esperar o elemento aparecer): False se ele não existe."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); if(!e) return false; e.click(); return true; }", sel)


def atual(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.getAttribute('aria-current') : null; }", sel)


def nomes(pg, sel):
    """Os nomes dos botões, sem os números (o span.badge)."""
    return pg.evaluate("""(s) => [...document.querySelectorAll(s)].map(b => {
      const n = b.querySelector('span:not(.badge)'); return (n ? n.textContent : b.textContent).trim(); })""", sel)


def titulo(pg, v):
    return pg.evaluate("(v) => { const h = document.getElementById('t-' + v); return h ? h.textContent.trim() : null; }", v)


def pc(p):
    pg = abrir(p, dados=DADOS, pc=True)
    areas = pg.evaluate("[...document.querySelectorAll('.menu .item[data-area]')].map(b => b.dataset.area)")
    checa("três áreas no menu", areas == ["resumo", "comprar", "config"] and nomes(pg, ".menu .item[data-area]") == ["Resumo geral", "Comprar", "Configurações"],
          [areas, nomes(pg, ".menu .item[data-area]")])
    checa("sem títulos de grupo nem folha Mais", pg.evaluate("!document.querySelector('.menu-t, #mais, #aba-mais')"))
    checa("telas", pg.evaluate("VIEWS") == TODAS, pg.evaluate("VIEWS"))
    navs = pg.evaluate("[...document.querySelectorAll('.area-nav')].filter(n => n.getClientRects().length).map(n => n.dataset.area)")
    telas = pg.evaluate("[...document.querySelectorAll('.area-nav[data-area=resumo] .tela-bt')].map(b => b.dataset.view)")
    checa("cabeçalho do Resumo geral", texto(pg, "#area-t") == "Resumo geral" and navs == ["resumo"] and telas == AREAS["resumo"]
          and nomes(pg, ".area-nav[data-area=resumo] .tela-bt") == BOTOES["resumo"], [texto(pg, "#area-t"), navs, telas, nomes(pg, ".area-nav[data-area=resumo] .tela-bt")])
    for a in ("comprar", "config"):
        checa(f"botões de {a}", pg.evaluate(f"[...document.querySelectorAll('.area-nav[data-area={a}] .tela-bt')].map(b => b.dataset.view)") == AREAS[a]
              and nomes(pg, f".area-nav[data-area={a}] .tela-bt") == BOTOES[a], nomes(pg, f".area-nav[data-area={a}] .tela-bt"))
    checa("área e tela marcadas", atual(pg, ".item[data-area=resumo]") == "page" and atual(pg, ".tela-bt[data-view=resumo]") == "page"
          and atual(pg, ".item[data-area=comprar]") == "false")
    clica(pg, ".item[data-area=comprar]"); pg.wait_for_timeout(150)
    checa("Comprar abre Ofertas", visivel(pg, "#v-ofertas") and texto(pg, "#area-t") == "Comprar" and atual(pg, ".item[data-area=comprar]") == "page")
    clica(pg, ".tela-bt[data-view=sim]"); pg.wait_for_timeout(150)
    checa("Simulador pelo botão", visivel(pg, "#v-sim") and atual(pg, ".tela-bt[data-view=sim]") == "page")
    clica(pg, ".item[data-area=resumo]"); pg.wait_for_timeout(150)
    volta = visivel(pg, "#v-resumo")
    clica(pg, ".item[data-area=comprar]"); pg.wait_for_timeout(150)
    checa("lembra a tela da área", volta and visivel(pg, "#v-sim"))
    clica(pg, ".item[data-area=config]"); pg.wait_for_timeout(150)
    checa("Configurações abre Mineração", visivel(pg, "#v-mineracao") and pg.evaluate("location.hash") == "#mineracao", pg.evaluate("location.hash"))
    checa("Este computador no PC", titulo(pg, "computador") == "Este computador" and nomes(pg, ".tela-bt[data-view=computador]") == ["Este computador"],
          [titulo(pg, "computador"), nomes(pg, ".tela-bt[data-view=computador]")])
    checa("títulos das telas", [titulo(pg, v) for v in ("resumo", "setup", "mineracao", "perfil", "integracoes", "sobre")]
          == ["Resumo geral", "Meu setup", "Mineração", "Perfil", "Integrações", "Sobre"], [titulo(pg, v) for v in ("resumo", "setup")])
    badge = pg.evaluate("(() => { const b = document.getElementById('b-diario'); return b && b.closest('.tela-bt[data-view=diario]') ? b.textContent.trim() : null; })()")
    checa("números nos botões", badge == "14", badge)
    checa("sem erros", not erros(pg), erros(pg)[:3])
    pg.context.close()


def online(p):
    pg = abrir(p, dados=DADOS)
    clica(pg, ".item[data-area=comprar]"); pg.wait_for_timeout(150)
    checa("sem Ofertas, Comprar abre Analisar anúncio", visivel(pg, "#v-anuncio") and not visivel(pg, "#nav-ofertas"))
    checa("Este aparelho", titulo(pg, "computador") == "Este aparelho" and nomes(pg, ".tela-bt[data-view=computador]") == ["Este aparelho"], titulo(pg, "computador"))
    pg.evaluate("irPara('perfil')"); pg.wait_for_timeout(100)
    checa("sem Facebook no painel online", pg.evaluate("!!document.getElementById('fb-p')") and not visivel(pg, "#fb-p"))
    checa("sem erros (online)", not erros(pg), erros(pg)[:3])
    pg.context.close()


def enderecos(p):
    pg = abrir(p, dados=DADOS, hash="premissas")
    checa("#premissas abre Mineração", visivel(pg, "#v-mineracao") and pg.evaluate("location.hash") == "#mineracao", pg.evaluate("location.hash"))
    pg.evaluate("irPara('xyz')"); pg.wait_for_timeout(100)
    checa("nome qualquer abre a Visão geral", visivel(pg, "#v-resumo") and pg.evaluate("location.hash") == "#resumo")
    pg.context.close()
    pg = abrir(p, dados=DADOS, hash="", extra="try{ localStorage.setItem('min-view', 'premissas'); }catch(e){}")
    checa("tela guardada antiga", visivel(pg, "#v-mineracao"))
    pg.context.close()
    pg = abrir(p, dados=DADOS, pc=True, extra="window.desktop.aoAbrir = fn => { window.__abrir = fn; };")
    pg.evaluate("window.__abrir({tela: 'premissas', chave: ''})"); pg.wait_for_timeout(100)
    checa("aviso antigo", visivel(pg, "#v-mineracao"))
    checa("sem erros (endereços)", not erros(pg), erros(pg)[:3])
    pg.context.close()


def quadros(p):
    pg = abrir(p, dados=DADOS, pc=True)
    for tela, ids in QUADROS.items():
        for i in ids:
            onde = pg.evaluate("(i) => { const e = document.getElementById(i); const v = e && e.closest('.view'); return v ? v.id : null; }", i)
            checa(f"{i} em {tela}", onde == "v-" + tela, onde)
    checa("sem v-premissas", pg.evaluate("!document.getElementById('v-premissas')"))
    pg.context.close()


def celular(p):
    pg = abrir(p, 390, 844, dados=DADOS, celular=True)
    abas = pg.evaluate("[...document.querySelectorAll('.abas .aba[data-area]')].map(b => [b.textContent.trim(), Math.round(b.getBoundingClientRect().height)])")
    checa("barra de baixo", [a[0] for a in abas] == ["Resumo", "Comprar", "Configurações"] and all(a[1] >= 44 for a in abas), abas)
    checa("sem o nome grande da área", not visivel(pg, "#area-t"))
    bts = pg.evaluate("[...document.querySelectorAll('.tela-bt')].filter(b => b.getClientRects().length).map(b => [Math.round(b.getBoundingClientRect().top), Math.round(b.getBoundingClientRect().height)])")
    checa("botões numa linha", len(bts) == 4 and len({b[0] for b in bts}) == 1 and all(b[1] >= 44 for b in bts), bts)
    clica(pg, ".abas [data-area=config]"); pg.wait_for_timeout(150)
    checa("Configurações pela barra", visivel(pg, "#v-mineracao") and atual(pg, ".abas [data-area=config]") == "page" and atual(pg, ".abas [data-area=resumo]") == "false")
    clica(pg, ".tela-bt[data-view=computador]"); pg.wait_for_timeout(150)
    checa("Este celular", visivel(pg, "#v-computador") and nomes(pg, ".tela-bt[data-view=computador]") == ["Este celular"]
          and titulo(pg, "computador") == "Este celular" and visivel(pg, "#mais-sync"),
          [nomes(pg, ".tela-bt[data-view=computador]"), titulo(pg, "computador"), visivel(pg, "#mais-sync")])
    checa("Aparência aberta", visivel(pg, "#aparencia-p [data-tema-op=claro]"))
    clica(pg, "#aparencia-p [data-tema-op=claro]"); pg.wait_for_timeout(100)
    checa("tema claro pela Aparência", pg.evaluate("document.documentElement.dataset.tema") == "claro")
    checa("os dois seletores marcam o mesmo tema", pg.evaluate("(() => { const b = [...document.querySelectorAll('[data-tema-op=claro]')]; return b.length >= 2 && b.every(x => x.getAttribute('aria-pressed') === 'true'); })()"))
    checa("voltar sem folha", pg.evaluate("[fecharFolha(), fecharMais()]") == [False, False])
    for v in TODAS:
        pg.evaluate(f"irPara('{v}')"); pg.wait_for_timeout(60)
        checa(f"sem rolagem para o lado ({v})", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), pg.evaluate("document.documentElement.scrollWidth"))
    checa("sem erros (celular)", not erros(pg), erros(pg)[:3])
    pg.context.close()


def largura(p):
    pg = abrir(p, dados=DADOS, pc=True)
    pg.evaluate("irPara('placas')"); pg.wait_for_timeout(100)
    pg.set_viewport_size({"width": 390, "height": 844}); pg.wait_for_timeout(250)
    checa("estreita: Comprar marcado embaixo", atual(pg, ".abas [data-area=comprar]") == "page" and visivel(pg, ".area-nav[data-area=comprar]") and visivel(pg, "#v-placas"))
    pg.set_viewport_size({"width": 1366, "height": 900}); pg.wait_for_timeout(250)
    checa("larga: menu e cabeçalho", visivel(pg, "#area-t") and texto(pg, "#area-t") == "Comprar" and atual(pg, ".item[data-area=comprar]") == "page")
    checa("sem erros (largura)", not erros(pg), erros(pg)[:3])
    pg.context.close()


def facebook(p):
    pg = abrir(p, dados=DADOS, pc=True, hash="perfil")
    checa("quadro do Facebook", visivel(pg, "#fb-p") and visivel(pg, "#fb-p [data-pc=facebook]"))
    checa("sem o Entrar na Kryptex repetido", pg.evaluate("!document.querySelector('[data-pc=kryptex]')"))
    clica(pg, "#fb-p [data-pc=facebook]"); pg.wait_for_timeout(300)
    checa("entrar no Facebook", texto(pg, "#fb-status") == "Pronto: os links de anúncio e as buscas do Marketplace usam essa conta.", texto(pg, "#fb-status"))
    checa("sem erros (Facebook)", not erros(pg), erros(pg)[:3])
    pg.context.close()


def links(p):
    pg = abrir(p, dados=DADOS, pc=True)
    clica(pg, ".credito button"); pg.wait_for_timeout(250)
    checa("crédito abre Sobre", visivel(pg, "#v-sobre"))
    cen = pg.evaluate("(() => { const c = document.getElementById('chips-cen'); const b = c && c.querySelector('[data-ir=mineracao]'); return b ? b.textContent.trim() : null; })()")
    checa("Mudar em Configurações", cen == "Mudar em Configurações", cen)
    pg.context.close()
    pg = abrir(p, 390, 844, dados=DADOS, celular=True)
    pg.evaluate("irPara('ofertas')"); pg.wait_for_timeout(100)
    clica(pg, "#of-mudar"); pg.wait_for_timeout(300)
    checa("Mudar cidade abre Perfil", visivel(pg, "#v-perfil") and pg.evaluate("document.getElementById('perfil-p').classList.contains('aberta')") and visivel(pg, "#pf-cidade"))
    checa("sem erros (links)", not erros(pg), erros(pg)[:3])
    pg.context.close()


with sync_playwright() as p:
    pc(p)
    online(p)
    enderecos(p)
    quadros(p)
    celular(p)
    largura(p)
    facebook(p)
    links(p)
fim()
