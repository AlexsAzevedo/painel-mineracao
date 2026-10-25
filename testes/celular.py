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


def preenche(pg, sel, v):
    """Escreve num campo como a pessoa (evento input e change), mesmo escondido."""
    return pg.evaluate("([s, v]) => { const e = document.querySelector(s); if(!e) return false; e.value = v; e.dispatchEvent(new Event('input', {bubbles:true})); e.dispatchEvent(new Event('change', {bubbles:true})); return true; }", [sel, v])


def valor(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.value : null; }", sel)


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
    clica(pg, "#aba-mais"); pg.wait_for_timeout(100)
    checa("a folha Mais mostra a ligação com o PC", "Ligado ao PC" in texto(pg, "#mais-sync") and pg.evaluate("document.getElementById('mais-sync').classList.contains('ok')"), texto(pg, "#mais-sync"))
    pg.evaluate("fecharFolha()")
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


ROTULOS_RET = """(() => { const ts = [...document.querySelectorAll('#ret-graf svg text')], h = ts.find(t => t.textContent.trim() === 'hoje'), pz = ts.find(t => t.textContent.startsWith('prazo'));
  if(!h || !pz) return {falta: true, n: ts.length};
  const a = h.getBoundingClientRect(), b = pz.getBoundingClientRect(), s = pz.ownerSVGElement.getBoundingClientRect();
  return {encavalados: !(a.right <= b.left || b.right <= a.left), dentro: b.left >= s.left - 1 && b.right <= s.right + 1, hoje: [Math.round(a.left), Math.round(a.right)], prazo: [Math.round(b.left), Math.round(b.right)]}; })()"""
FOLHA = """(id) => { const f = document.getElementById(id); if(!f) return null; const r = f.getBoundingClientRect();
  return {vis: f.getClientRects().length > 0, fixa: getComputedStyle(f).position === 'fixed', fundo: Math.round(innerHeight - r.bottom), dialogo: f.getAttribute('role'),
          foco: f.contains(document.activeElement), pano: !!document.querySelector('.folha-fundo:not([hidden])')}; }"""
CARTOES = """(sel) => { const t = document.querySelector(sel); if(!t) return null; const tr = t.querySelector('tbody tr');
  return {cab: getComputedStyle(t.querySelector('thead')).display, larg: t.scrollWidth <= t.parentElement.clientWidth + 1, cartao: tr ? getComputedStyle(tr).display : '',
          rot: tr ? [...tr.querySelectorAll('td[data-l]')].map(td => td.dataset.l) : []}; }"""
SEM_LADO = "document.documentElement.scrollWidth <= innerWidth"


def resumo(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True)
    checa("linha do dia sem ganho não aparece", pg.evaluate("svgLinhaDia([[Date.now() - 3600e3, 0], [Date.now(), 0]], Date.now())") == "")
    checa("linha do dia com ganho aparece", "ag-linha" in pg.evaluate("svgLinhaDia([[Date.now() - 3600e3, 0], [Date.now(), 1.2]], Date.now())"))
    r = pg.evaluate("""(() => { const l = document.querySelector('#r-rig .rig-l'), nm = l.querySelector('.nm').getBoundingClientRect(), v = l.querySelector('.v').getBoundingClientRect();
      return {vTopo: Math.round(v.top), nmFim: Math.round(nm.bottom), nmLarg: Math.round(nm.width), larg: Math.round(l.getBoundingClientRect().width)}; })()""")
    checa("retorno das placas: nome em cima e previsão embaixo", r["vTopo"] >= r["nmFim"] - 1 and r["nmLarg"] >= r["larg"] * 0.9, r)
    pg.evaluate("irPara('minhas')"); pg.wait_for_timeout(400)
    rot = pg.evaluate(ROTULOS_RET)
    checa("gráfico do retorno: 'hoje' e 'prazo' sem encavalar", not rot.get("falta") and not rot["encavalados"] and rot["dentro"], rot)
    checa("sem rolagem para o lado (Resumo e Minhas placas)", pg.evaluate(SEM_LADO))
    checa("sem erros (Resumo)", not erros(pg), erros(pg)[:3])


def diario(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, hash="diario")
    checa("Diário: o formulário fica guardado", not visivel(pg, "#d-folha"))
    checa("Diário: botão Anotar", visivel(pg, "#d-fab") and "Anotar" in texto(pg, "#d-fab"), texto(pg, "#d-fab"))
    clica(pg, "#d-fab"); pg.wait_for_timeout(350)
    f = pg.evaluate(FOLHA, "d-folha")
    checa("Diário: a folha sobe de baixo", f and f["vis"] and f["fixa"] and abs(f["fundo"]) <= 1 and f["dialogo"] == "dialog" and f["foco"] and f["pano"], f)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
    checa("Esc fecha a folha e volta ao botão", not visivel(pg, "#d-folha") and pg.evaluate("document.activeElement.id") == "d-fab" and pg.evaluate("!document.querySelector('.folha-fundo:not([hidden])')"))
    clica(pg, "#d-fab"); pg.wait_for_timeout(200)
    clica(pg, ".folha-fundo"); pg.wait_for_timeout(100)
    checa("tocar fora fecha a folha", not visivel(pg, "#d-folha"))
    clica(pg, "#d-fab"); pg.wait_for_timeout(200)
    preenche(pg, "#d-valor", "3.5"); clica(pg, "#d-btn"); pg.wait_for_timeout(400)
    checa("salvar fecha a folha e avisa", not visivel(pg, "#d-folha") and "Salvo" in texto(pg, "#toast"), texto(pg, "#toast"))
    c = pg.evaluate(CARTOES, "#d-tab table")
    checa("Diário: dias em cartões", c and c["larg"] and c["cab"] == "none" and c["cartao"] == "grid" and "Estimado" in c["rot"], c)
    clica(pg, "#d-tab [data-acao=editar-dia]"); pg.wait_for_timeout(300)
    checa("editar abre a folha com o dia", visivel(pg, "#d-folha") and valor(pg, "#d-valor") not in ("", None) and pg.evaluate("document.activeElement.id") == "d-valor")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
    n = pg.evaluate("diario.length")
    clica(pg, "#d-tab [data-acao=apagar-dia]"); pg.wait_for_timeout(300)
    checa("apagar avisa embaixo, com Desfazer", "apagado" in texto(pg, "#toast") and visivel(pg, "#toast button") and pg.evaluate("diario.length") == n - 1, [texto(pg, "#toast"), pg.evaluate("diario.length"), n])
    clica(pg, "#toast button"); pg.wait_for_timeout(300)
    checa("Desfazer devolve o dia", pg.evaluate("diario.length") == n)
    rel = pg.evaluate(CARTOES, "#rel-res .rel-tab table")
    checa("relatório em cartões", rel and rel["larg"] and rel["cab"] == "none" and rel["cartao"] == "grid", rel)
    checa("sem rolagem para o lado (Diário)", pg.evaluate(SEM_LADO))
    checa("sem erros (Diário)", not erros(pg), erros(pg)[:3])
    pc = abrir(p, largura=1366, dados=DADOS, pc=True, hash="diario")
    checa("PC: formulário do Diário no lugar de sempre", visivel(pc, "#d-folha") and not visivel(pc, "#d-fab"))
    checa("PC: histórico em tabela", pc.evaluate("getComputedStyle(document.querySelector('#d-tab thead')).display") != "none")
    checa("sem erros (Diário no PC)", not erros(pc), erros(pc)[:3])


def placas(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, hash="placas")
    c = pg.evaluate(CARTOES, "#tabcat")
    checa("placas em cartões", c and c["larg"] and c["cab"] == "none" and c["cartao"] == "grid" and "Lucro/mês" in c["rot"], c)
    lista = pg.evaluate("""(() => { const trs = [...document.querySelectorAll('#cat tr')];
      return {vis: trs.filter(tr => tr.getClientRects().length).length, total: trs.length, rolagem: getComputedStyle(document.getElementById('tw-cat')).overflowY}; })()""")
    checa("placas: as 20 primeiras e o botão para ver todas", lista["vis"] == 20 and lista["total"] > 20 and visivel(pg, "#cat-mais"), lista)
    checa("placas: sem rolagem dentro da lista", lista["rolagem"] in ("visible", "clip"), lista)
    clica(pg, "#cat-mais"); pg.wait_for_timeout(100)
    checa("placas: mostrar todas", pg.evaluate("[...document.querySelectorAll('#cat tr')].filter(tr => tr.getClientRects().length).length") == lista["total"] and not visivel(pg, "#cat-mais"))
    checa("filtros recolhidos (só a busca à vista)", visivel(pg, "#busca") and not visivel(pg, "#marca") and visivel(pg, "#filtros-mais"))
    clica(pg, "#filtros-mais"); pg.wait_for_timeout(100)
    checa("filtros abrem", visivel(pg, "#marca") and visivel(pg, "#ordem") and pg.evaluate("(document.getElementById('filtros-mais') || {}).getAttribute?.('aria-expanded')") == "true")
    checa("sem rolagem para o lado (placas)", pg.evaluate(SEM_LADO))
    checa("sem erros (placas)", not erros(pg), erros(pg)[:3])
    pc = abrir(p, largura=1366, dados=DADOS, pc=True, hash="placas")
    checa("PC: tabela das placas", pc.evaluate("getComputedStyle(document.querySelector('#tabcat thead')).display") != "none"
          and pc.evaluate("[...document.querySelectorAll('#cat tr')].every(tr => tr.getClientRects().length)") and not visivel(pc, "#filtros-mais") and visivel(pc, "#marca"))


def ofertas(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, hash="ofertas")
    checa("ofertas: resumo da busca numa linha", visivel(pg, "#of-resumo") and "Itajaí" in texto(pg, "#of-resumo") and "100 km" in texto(pg, "#of-resumo"), texto(pg, "#of-resumo"))
    checa("ofertas: campos guardados e Buscar à vista", not visivel(pg, "#of-raio") and visivel(pg, "#of-buscar"))
    clica(pg, "#of-resumo [data-folha]"); pg.wait_for_timeout(300)
    f = pg.evaluate(FOLHA, "of-ajustes")
    checa("ofertas: Ajustar abre a folha com os campos", f and f["vis"] and f["fixa"] and abs(f["fundo"]) <= 1 and visivel(pg, "#of-raio") and visivel(pg, "#of-mods-d"), f)
    preenche(pg, "#of-teto", "2000")
    clica(pg, "#of-ajustes .folha-ok"); pg.wait_for_timeout(200)
    checa("ofertas: Pronto fecha e o resumo mostra o preço", not visivel(pg, "#of-ajustes") and "2.000" in texto(pg, "#of-resumo"), texto(pg, "#of-resumo"))
    preenche(pg, "#of-teto", "")
    c = pg.evaluate("""(() => { const a = document.querySelector('#of-lista .of'), img = a.querySelector('.of-img').getBoundingClientRect(), tit = a.querySelector('.of-tit').getBoundingClientRect(), r = a.getBoundingClientRect();
      const bs = [...a.querySelectorAll('.of-acoes > *')].map(b => Math.round(b.getBoundingClientRect().top));
      return {altura: Math.round(r.height), imgLarg: Math.round(img.width), vao: Math.round(tit.left - img.right), lado: tit.top < img.bottom, botoes: bs}; })()""")
    checa("ofertas: cartão compacto, com a foto ao lado", c["imgLarg"] <= 110 and c["vao"] >= 8 and c["lado"] and c["altura"] <= 300, c)
    checa("ofertas: os três botões numa linha", len(set(c["botoes"])) == 1, c["botoes"])
    checa("sem rolagem para o lado (ofertas)", pg.evaluate(SEM_LADO))
    checa("sem erros (ofertas)", not erros(pg), erros(pg)[:3])
    pc = abrir(p, largura=1366, dados=DADOS, pc=True, hash="ofertas")
    b = pc.evaluate("""(() => { const r = id => document.getElementById(id).getBoundingClientRect();
      return {raio: Math.round(r('of-raio').bottom), buscar: Math.round(r('of-buscar').bottom), mods: Math.round(r('of-mods-d').top), resumo: (document.getElementById('of-resumo') || {getClientRects: () => []}).getClientRects().length}; })()""")
    checa("PC: barra de busca como antes (campos e Buscar na mesma linha, modelos embaixo)", abs(b["raio"] - b["buscar"]) <= 4 and b["mods"] > b["buscar"] and not b["resumo"], b)
    foto = pc.evaluate("(() => { const a = document.querySelector('#of-lista .of'); return [Math.round(a.querySelector('.of-img').getBoundingClientRect().width), Math.round(a.getBoundingClientRect().width)]; })()")
    checa("PC: cartões com a foto em cima", abs(foto[0] - foto[1]) <= 2, foto)
    checa("sem erros (ofertas no PC)", not erros(pc), erros(pc)[:3])


SECOES = """[...document.querySelectorAll('#v-premissas .sec')].filter(s => s.getClientRects().length)
  .map(s => ({id: s.id, aberta: s.classList.contains('aberta'), exp: (s.querySelector('.sec-bt') || {getAttribute: () => null}).getAttribute('aria-expanded')}))"""


def premissas(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, hash="premissas")
    secs = pg.evaluate(SECOES)
    checa("premissas: quadros fechados, cada um com o botão de abrir", len(secs) >= 8 and all(not x["aberta"] and x["exp"] == "false" for x in secs), secs)
    alt = pg.evaluate("Math.round(document.getElementById('v-premissas').getBoundingClientRect().height)")
    checa("premissas: tela curta com tudo fechado", alt < 1500, alt)
    clica(pg, "#dados-fora .sec-bt"); pg.wait_for_timeout(100)
    checa("premissas: abrir um quadro", visivel(pg, "#dados-fora [data-x=dolar]") and pg.evaluate("(document.querySelector('#dados-fora .sec-bt') || {getAttribute: () => null}).getAttribute('aria-expanded')") == "true")
    clica(pg, "#dados-fora .sec-bt"); pg.wait_for_timeout(100)
    checa("premissas: fechar de novo", not visivel(pg, "#dados-fora [data-x=dolar]"))
    pg.evaluate("document.querySelector('#perfil-p h2').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(100)
    xy = pg.evaluate("(() => { const r = document.querySelector('#perfil-p h2').getBoundingClientRect(); return [r.left + 12, r.top + r.height / 2]; })()")
    pg.mouse.click(xy[0], xy[1]); pg.wait_for_timeout(100)
    checa("premissas: tocar no título também abre", visivel(pg, "#pf-cidade"))
    clica(pg, "#v-premissas fieldset.grupo .sec-bt"); pg.wait_for_timeout(100)
    checa("premissas: os grupos (receita, energia, investimento) também abrem", visivel(pg, "#dolar"))
    clica(pg, "#perfil-p .sec-bt"); pg.evaluate("irPara('ofertas')"); clica(pg, "#of-mudar"); pg.wait_for_timeout(300)
    checa("Mudar cidade (Ofertas) abre o perfil na cidade", pg.evaluate("document.getElementById('perfil-p').classList.contains('aberta') && document.activeElement.id === 'pf-cidade'"))
    checa("sem rolagem para o lado (premissas)", pg.evaluate(SEM_LADO))
    checa("sem erros (premissas)", not erros(pg), erros(pg)[:3])
    pc = abrir(p, largura=1366, dados=DADOS, pc=True, hash="premissas")
    checa("PC: premissas abertas, sem os botões de abrir", visivel(pc, "#dados-fora [data-x=dolar]") and visivel(pc, "#dolar") and visivel(pc, "#pf-cidade") and not visivel(pc, "#dados-fora .sec-bt"))


def minhas(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, hash="minhas")
    checa("minhas: formulário guardado e botão Adicionar", not visivel(pg, "#m-folha") and visivel(pg, "#m-fab") and "Adicionar" in texto(pg, "#m-fab"))
    c = pg.evaluate(CARTOES, "#riglist table")
    checa("minhas: placas em cartões", c and c["larg"] and c["cab"] == "none" and c["cartao"] == "grid" and "Lucro/mês" in c["rot"], c)
    clica(pg, "#m-fab"); pg.wait_for_timeout(350)
    f = pg.evaluate(FOLHA, "m-folha")
    checa("minhas: Adicionar abre a folha no campo da placa", f and f["vis"] and f["fixa"] and pg.evaluate("document.activeElement.id") == "f-placa", [f, pg.evaluate("document.activeElement.id")])
    pg.evaluate("comboForm.escolher(byId['rtx-4070-ti'] || CATALOGO[0], true)")
    clica(pg, "input[name='f-pag'][value='avista']"); preenche(pg, "#f-preco", "3500")
    n = pg.evaluate("placas.length")
    clica(pg, "#addform .af-btn"); pg.wait_for_timeout(400)
    checa("minhas: adicionar fecha a folha e avisa embaixo", not visivel(pg, "#m-folha") and pg.evaluate("placas.length") == n + 1 and "adicionad" in texto(pg, "#toast"), [pg.evaluate("placas.length"), n, texto(pg, "#toast")])
    pg.evaluate("irPara('anuncio')")
    checa("sem rolagem para o lado (minhas)", pg.evaluate(SEM_LADO))
    checa("sem erros (minhas)", not erros(pg), erros(pg)[:3])
    vazio = abrir(p, largura=390, altura=844, dados={k: v for k, v in DADOS.items() if k != "min-placas"}, celular=True, hash="minhas")
    clica(vazio, "#riglist [data-folha]"); vazio.wait_for_timeout(300)
    checa("minhas: sem placas, o aviso tem o botão de adicionar", visivel(vazio, "#m-folha"))
    pc = abrir(p, largura=1366, dados=DADOS, pc=True, hash="minhas")
    checa("PC: formulário de Minhas placas no lugar de sempre", visivel(pc, "#f-placa") and not visivel(pc, "#m-fab") and pc.evaluate("getComputedStyle(document.querySelector('#riglist thead')).display") != "none")


APP = "window.desktop.app = true;"   # o app do celular (Capacitor): puxar para atualizar


def toques(p):
    pg = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, extra="addEventListener('DOMContentLoaded', () => { const m = document.createElement('meta'); m.name = 'theme-color'; m.content = '#0C1016'; document.head.append(m); });")
    cor = lambda: pg.evaluate("document.querySelector('meta[name=theme-color]').content").lower()
    pg.evaluate("aplicarTema('claro')")
    checa("barra do navegador acompanha o tema claro", cor() == "#ffffff", cor())
    pg.evaluate("aplicarTema('escuro')")
    checa("barra do navegador acompanha o tema escuro", cor() == "#090c11", cor())
    pg.evaluate("irPara('diario')"); clica(pg, "#d-fab"); pg.wait_for_timeout(200)
    checa("voltar (fecharFolha) fecha a folha aberta", pg.evaluate("window.fecharFolha()") is True and not visivel(pg, "#d-folha"))
    checa("voltar sem folha aberta segue adiante", pg.evaluate("window.fecharFolha()") is False)
    app = abrir(p, largura=390, altura=844, dados=DADOS, celular=True, extra=APP, toque=True)
    app.evaluate("window.__atu = 0; window.desktop.sync.atualizar = async () => { window.__atu++; }; 0")
    puxar = """(dy) => { const t = (y) => new Touch({identifier: 1, target: document.body, clientX: 200, clientY: y});
      document.body.dispatchEvent(new TouchEvent('touchstart', {touches: [t(150)], changedTouches: [t(150)], bubbles: true}));
      for (let y = 150; y <= 150 + dy; y += 20) document.body.dispatchEvent(new TouchEvent('touchmove', {touches: [t(y)], changedTouches: [t(y)], bubbles: true}));
      document.body.dispatchEvent(new TouchEvent('touchend', {touches: [], changedTouches: [t(150 + dy)], bubbles: true})); }"""
    app.evaluate(puxar, 40); app.wait_for_timeout(200)
    checa("puxar pouco não atualiza", app.evaluate("window.__atu") == 0)
    app.evaluate(puxar, 160); app.wait_for_timeout(300)
    checa("puxar a tela para baixo atualiza (app)", app.evaluate("window.__atu") == 1 and "atualizad" in texto(app, "#toast"), [app.evaluate("window.__atu"), texto(app, "#toast")])
    app.evaluate("scrollTo(0, 600)"); app.wait_for_timeout(100); app.evaluate("atuPc.ultimo = 0; 0")
    app.evaluate(puxar, 160); app.wait_for_timeout(300)
    checa("no meio da página, puxar só rola", app.evaluate("window.__atu") == 1)
    checa("sem erros (toques)", not erros(pg) and not erros(app), (erros(pg) + erros(app))[:3])


with sync_playwright() as p:
    casca(p)
    resumo(p)
    diario(p)
    placas(p)
    ofertas(p)
    premissas(p)
    minhas(p)
    toques(p)
fim()
