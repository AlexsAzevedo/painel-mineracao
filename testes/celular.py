"""O painel no celular (menos de 900 px) com cara de app: barra de cima com o título da tela, listas no lugar de
tabelas, folhas que sobem de baixo, Premissas em seções e os toques de app (dados inventados).
Uso: python3 testes/celular.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

TITULOS = {"resumo": "Resumo", "diario": "Diário de ganhos", "minhas": "Minhas placas", "ofertas": "Ofertas", "anuncio": "Analisar anúncio",
           "placas": "Todas as placas", "setup": "Montar setup", "premissas": "Premissas"}
# números grandes que quebram em duas linhas (a altura passa de 1,6 vez o tamanho da letra)
QUEBRADOS = """[...document.querySelectorAll('.view:not([hidden]) .kpi b, .view:not([hidden]) .tile b')]
  .filter(b => b.getClientRects().length && b.getBoundingClientRect().height > parseFloat(getComputedStyle(b).fontSize) * 1.6).map(b => b.textContent.trim())"""


def texto(pg, sel):
    """Texto visível de um elemento ("" se ele não existe)."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText.trim() : ''; }", sel)


def visivel(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'; }", sel)


def clica(pg, sel):
    """Clica pelo próprio painel (sem esperar o elemento aparecer): False se ele não existe."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); if(!e) return false; e.click(); return true; }", sel)


def casca(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True)
    for v, t in TITULOS.items():
        pg.evaluate(f"irPara('{v}')")
        checa(f"título no topo: {v}", texto(pg, "#topo-t") == t, texto(pg, "#topo-t"))
        checa(f"h1 só para o leitor de tela: {v}", pg.evaluate(f"(() => {{ const b = document.getElementById('t-{v}').getBoundingClientRect(); return b.width <= 1 && b.height <= 1; }})()"))
        checa(f"sem o subtítulo longo: {v}", pg.evaluate(f"[...document.querySelectorAll('#v-{v} .vh .sub')].every(e => getComputedStyle(e).display === 'none')"))
        quebrados = pg.evaluate(QUEBRADOS)
        checa(f"números grandes numa linha: {v}", not quebrados, quebrados)
    pg.evaluate("irPara('premissas'); scrollTo(0, 1500)"); pg.wait_for_timeout(100)
    checa("a barra de cima fica no topo ao rolar", abs(pg.evaluate("document.querySelector('.side').getBoundingClientRect().top")) < 1)
    pg.evaluate("irPara('resumo')")
    checa("cartões com 16 px por dentro", pg.evaluate("getComputedStyle(document.querySelector('#v-resumo #r-graf-p')).paddingLeft") == "16px")
    checa("a barra de cima numa linha só", pg.evaluate("document.querySelector('.side').getBoundingClientRect().height") <= 64,
          pg.evaluate("document.querySelector('.side').getBoundingClientRect().height"))
    # o estado da mineração no topo: bolinha e valor, numa linha (o nome do estado fica para o leitor de tela)
    pg.evaluate("kxaSnap = {v:1, estado:'parada', quando:Date.now(), hoje:{ganho:12.34, lucro:3.21}}; renderVivo()")
    chip = pg.evaluate("(() => { const c = document.getElementById('g-chip'), r = c.getBoundingClientRect(); return {t: c.innerText, h: r.height, w: r.width, bola: !!c.querySelector('i.b')}; })()")
    checa("chip do topo compacto", chip["h"] <= 32 and chip["w"] <= 130 and chip["bola"] and "Parada" in chip["t"] and "R$ 12,34" in chip["t"], chip)
    pg.evaluate("kxaSnap = null; renderVivo()")
    # PC desligado ou sem internet: a faixa fica no alto da tela, embaixo da barra de cima, e acompanha a rolagem
    pg.evaluate("remotoEstado({ok:false, texto:'O PC não respondeu', aviso:'O PC não respondeu. Confira se ele está ligado.'})")
    faixa = pg.evaluate("""(() => { const f = document.getElementById('remoto-aviso'), s = document.querySelector('.side').getBoundingClientRect();
      if(!f) return null; const r = f.getBoundingClientRect(); return {topo: r.top - s.bottom, dentro: !!f.closest('.main'), alt: r.height}; })()""")
    checa("faixa do PC no alto da tela", faixa and faixa["dentro"] and 0 <= faixa["topo"] <= 24, faixa)
    pg.evaluate("scrollTo(0, 900)"); pg.wait_for_timeout(100)
    faixa = pg.evaluate("document.getElementById('remoto-aviso').getBoundingClientRect().top - document.querySelector('.side').getBoundingClientRect().bottom")
    checa("a faixa acompanha a rolagem", 0 <= faixa <= 12, faixa)
    pg.evaluate("remotoEstado({ok:true, texto:'Ligado ao PC'})")
    checa("a faixa some quando o PC volta", not visivel(pg, "#remoto-aviso"))
    # Atualizar pelo topo: pede ao PC e diz como foi, sem deixar apertar de novo em seguida
    pg.evaluate("window.__atu = 0; window.desktop.sync.atualizar = async () => { window.__atu++; }; 0")   # "; 0": o Playwright chamaria a função
    checa("botão de atualizar no topo", visivel(pg, "#topo-atu"))
    clica(pg, "#topo-atu"); pg.wait_for_timeout(200)
    checa("atualizar pede ao PC", pg.evaluate("window.__atu") == 1 and "atualizad" in texto(pg, "#toast").lower(), [pg.evaluate("window.__atu"), texto(pg, "#toast")])
    clica(pg, "#topo-atu"); pg.wait_for_timeout(200)
    checa("não pede de novo em seguida", pg.evaluate("window.__atu") == 1, pg.evaluate("window.__atu"))
    pg.evaluate("window.desktop.sync.atualizar = async () => { throw new Error('O PC não respondeu. Confira se ele está ligado.'); }; if(window.atuPc) atuPc.ultimo = 0; 0")
    clica(pg, "#topo-atu"); pg.wait_for_timeout(200)
    checa("atualizar diz quando o PC não responde", "não respondeu" in texto(pg, "#toast"), texto(pg, "#toast"))
    # barra de baixo: a aba aberta ganha uma pílula atrás do ícone (e não o botão inteiro pintado)
    abas = pg.evaluate("""(() => { const a = document.querySelector('.aba[aria-current="page"]');
      return {svg: getComputedStyle(a.querySelector('svg')).backgroundColor, botao: getComputedStyle(a).backgroundColor}; })()""")
    checa("pílula na aba aberta", abas["svg"] not in ("rgba(0, 0, 0, 0)", "transparent") and abas["botao"] in ("rgba(0, 0, 0, 0)", "transparent"), abas)
    checa("sem rolagem para o lado", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"))
    checa("sem erros no celular", not erros(pg), erros(pg)[:3])
    # o painel online no celular (sem PC): sem botão de atualizar
    on = abrir(p, largura=390, altura=844, dados=DADOS)
    checa("painel online: sem atualizar no topo", not visivel(on, "#topo-atu") and texto(on, "#topo-t") == "Resumo")
    # no PC nada disso aparece
    pc = abrir(p, largura=1366, dados=DADOS, pc=True)
    checa("PC: sem título de app e com o h1", not visivel(pc, "#topo-t") and pc.evaluate("document.getElementById('t-resumo').getBoundingClientRect().height") > 20)
    checa("PC: com o subtítulo", pc.is_visible("#resumo-sub"))
    checa("PC: sem atualizar no topo", not visivel(pc, "#topo-atu"))
    checa("sem erros no PC", not erros(pc), erros(pc)[:3])


with sync_playwright() as p:
    casca(p)
fim()
