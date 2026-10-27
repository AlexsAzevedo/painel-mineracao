"""Simulador de compra de placas (1.9.0): as contas (juros do empréstimo, CDI e o fluxo mês a mês), a mineração de cada
opção, a tela, guardar e o celular (dados inventados).
Uso: python3 testes/simulador.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import *  # noqa: F401,F403

# uma máquina no Montar setup (a RX 9070 XT de Minhas placas fica nela): fonte de 750 W Gold, 40 W para o resto do PC
SETUP = {"v": 1, "tensao": 220, "parcelas": 12, "aloc": {"l1": "m-pc"},
         "maquinas": [{"id": "m-pc", "nome": "PC principal", "cpu": "outro", "minerarCpu": False, "x16": 1, "x1": 3, "base": 40,
                       "fonteW": 750, "selo": "Gold", "gpus": [], "extras": [], "nova": False}]}
DADOS_SIM = {**DADOS, "min-setup": SETUP}
LIQ_1200_12 = 69.0198788680342   # rendimentoParcelado(1200, 12).liquido antes do simulador (CDI 13,65%, 100%)


def js(pg, expr):
    """Roda uma expressão na página; um erro volta como {"erro": ...} (o teste vermelho lista as falhas em vez de parar)."""
    return pg.evaluate("(e) => { try { return (0, eval)(e); } catch (x) { return {erro: String(x)}; } }", expr)


def campo(r, *ks):
    """r[k1][k2]... ou None se faltar algum (um erro da página volta como {"erro": ...})"""
    for k in ks:
        try:
            r = r[k]
        except (KeyError, IndexError, TypeError):
            return None
    return r


def perto(v, alvo, tol):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v - alvo) < tol


def texto(pg, sel):
    """Texto visível de um elemento ("" se ele não existe)."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.innerText.trim() : ''; }", sel)


def existe(pg, sel):
    return pg.evaluate("(s) => !!document.querySelector(s)", sel)


def visivel(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden'; }", sel)


def clica(pg, sel):
    """Clica pelo próprio painel: False se o elemento não existe."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); if(!e) return false; e.click(); return true; }", sel)


def preenche(pg, sel, v):
    """Escreve num campo como a pessoa (evento input e change)."""
    return pg.evaluate("([s, v]) => { const e = document.querySelector(s); if(!e) return false; e.value = v; e.dispatchEvent(new Event('input', {bubbles:true})); e.dispatchEvent(new Event('change', {bubbles:true})); return true; }", [sel, v])


def escolhe(pg, sel, v):
    """Escolhe numa lista (evento change)."""
    return pg.evaluate("([s, v]) => { const e = document.querySelector(s); if(!e) return false; e.value = v; e.dispatchEvent(new Event('change', {bubbles:true})); return true; }", [sel, v])


def marca(pg, sel):
    """Marca um botão de opção (rádio)."""
    return pg.evaluate("(s) => { const e = document.querySelector(s); if(!e) return false; e.checked = true; e.dispatchEvent(new Event('change', {bubbles:true})); return true; }", sel)


def valor(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e ? e.value : null; }", sel)


def contas(p):
    pg = abrir(p, dados=DADOS_SIM)
    F = "(o) => fluxoSim({preco:1200, cartao:0, emprestimo:null, bruto:200, luz:50, taxa:0, prazo:12, rendMes:0, revendaEm:()=>0, ...o})"
    i = js(pg, "taxaEmprestimo(10000, 20, 674.65)")
    checa("empréstimo do Alex: 3,04% ao mês", isinstance(i, float) and abs(i - 0.030401) < 5e-6, i)
    a = js(pg, "Math.pow(1 + taxaEmprestimo(10000, 20, 674.65), 12) - 1")
    checa("43,2% ao ano", isinstance(a, float) and abs(a - 0.432432) < 5e-5, a)
    checa("parcelas que somam o valor: 0", js(pg, "taxaEmprestimo(1200, 12, 100)") == 0)
    r = js(pg, "[[1200,12,90],[0,12,100],[1000,0,100],[1000,12,0],[NaN,12,100],['',12,100],[1000,12,2000],[1000,200,10]].map(a => taxaEmprestimo(...a))")
    checa("empréstimo inválido: null", r == [None] * 8, r)
    c = js(pg, "taxaMesCdi()")
    checa("CDI do mês (13,65% e 100%)", isinstance(c, float) and abs(c - 0.0107198) < 1e-6, c)
    r = js(pg, "[1,6,7,12,13,24,25].map(irRegressivo)")
    checa("IR regressivo", r == [0.225, 0.225, 0.2, 0.2, 0.175, 0.175, 0.15], r)
    r = js(pg, "rendimentoParcelado(1200, 12).liquido")
    checa("rendimentoParcelado igual ao de antes", isinstance(r, float) and abs(r - LIQ_1200_12) < 1e-9, r)
    r = js(pg, f"({F})({{}})")
    ok = isinstance(r, dict) and "meses" in r
    checa("à vista: mês 0 é −preço, se paga no mês 8, sobram R$ 600",
          ok and r["meses"][0]["resultado"] == -1200 and r["sePaga"] == 8 and round(r["fim"]["resultado"], 2) == 600, r if not ok else "")
    checa("no cartão em 12×: se paga no mês 8", js(pg, f"({F})({{cartao:12}}).sePaga") == 8)
    r = js(pg, f"({F})({{taxa:-4}})")
    checa("caindo 4% ao mês: mês 11, R$ 136,45", isinstance(r, dict) and r.get("sePaga") == 11 and round(r["fim"]["resultado"], 2) == 136.45)
    r = js(pg, f"({F})({{emprestimo:{{valor:1200, parcelas:12, parcela:113.47}}}})")
    checa("empréstimo a 2% ao mês: mês 9, R$ 438,36, juros de R$ 161,64, conta nunca negativa",
          isinstance(r, dict) and r.get("sePaga") == 9 and round(r["fim"]["resultado"], 2) == 438.36
          and round(r["juros"]["total"], 2) == 161.64 and r["pior"]["conta"] >= 0)
    r = js(pg, f"({F})({{bruto:100, luz:150}})")
    checa("prejuízo: não se paga, faltam R$ 1.800", isinstance(r, dict) and "sePaga" in r and r["sePaga"] is None and round(r["fim"]["resultado"], 2) == -1800)
    r = js(pg, f"({F})({{preco:1000, cartao:10, bruto:0, luz:0, rendMes:0.01}})")
    checa("a conta rende com o IR de 22,5% no 1º mês",
          isinstance(r, dict) and "meses" in r and round(r["meses"][1]["resultado"] - r["meses"][0]["resultado"], 2) == 7.75)
    r = js(pg, f"({F})({{preco:1000, emprestimo:{{valor:1000, parcelas:10, parcela:120}}, bruto:100, luz:40}})")
    checa("pior mês da conta: mês 10 com −R$ 600", isinstance(r, dict) and "pior" in r and r["pior"]["m"] == 10 and round(r["pior"]["conta"], 2) == -600)
    checa("revenda no fim", js(pg, f"({F})({{revendaEm: m => 1000 - m*10}}).fim.comRevenda") == 1480)
    r = js(pg, f"[({F})({{preco:0}}), ({F})({{emprestimo:{{valor:1200, parcelas:12, parcela:90}}}})]")
    checa("preço zero ou empréstimo inválido: null", r == [None, None], r)
    checa("sem erros", not erros(pg), erros(pg)[:3])


def mineracao(p):
    pg = abrir(p, dados=DADOS_SIM)
    LEIT_9070 = "u => ({ok:true, placas:[{tipo:'gpu', nome:'AMD Radeon RX 9070 XT', minerando:true, rendimentoUsd:u}]})"
    r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5070', qtd:2, preco:5159, maq:'m-pc'}]})")
    ref = js(pg, "(() => { const m = setup.maquinas[0], a = calcMaq(m), b = calcMaq(m, {extra:[{tipo:'plano', c:byId['rtx-5070'], q:2, preco:5159}]}); return b.luz - a.luz; })()")
    checa("2× RTX 5070 no PC principal: bruto sem margem e luz do setup",
          perto(campo(r, "bruto"), 1295.7633, 0.01) and perto(campo(r, "luz"), ref, 0.01), r)
    r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5060', qtd:3, preco:2665, maq:'novo'}]})")
    ref = js(pg, "calcMaq(maqNovaSim(), {extra:[{tipo:'plano', c:byId['rtx-5060'], q:3, preco:2665}]})")
    checa("PC novo conta inteiro (placas, 10 W do processador parado, 30 W de base)",
          campo(r, "usaNovo") is True and campo(ref, "dc") == 340 and perto(campo(r, "luz"), campo(ref, "luz") or 0, 0.01), [r, campo(ref, "dc")])
    r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5070', qtd:3, preco:5159, maq:'m-pc'}]})")
    checa("fonte de 750 W a 113%: avisa", campo(r, "maqs", 0, "avisoFonte") is True and round((campo(r, "maqs", 0, "carga") or 0) * 100) == 113, r)
    r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5060', qtd:1, preco:2665, maq:'m-apagada'}]})")
    checa("máquina que sumiu vira PC novo", campo(r, "maqs", 0, "id") == "novo" and campo(r, "maqs", 0, "sumiu") is True and campo(r, "usaNovo") is True, r)
    checa("preço vazio: o melhorPreco", js(pg, "linhasSim({placas:[{modelo:'rtx-5060', qtd:1, preco:null, maq:'novo'}]})[0].preco") == 2600)
    r = js(pg, "[12, 24].map(m => revendaSim({placas:[{modelo:'rtx-5060', qtd:2, preco:2000, maq:'novo'}]}, m))")
    checa("revenda com 25% ao ano", r == [3000, 2250], r)
    r = js(pg, f"fatorKxReal(({LEIT_9070})(2.965))")
    checa("correção pelo real", perto(r, 0.871357, 1e-5), r)
    r = js(pg, f"[0.1, 20].map(u => fatorKxReal(({LEIT_9070})(u)))")
    checa("correção entre 20% e 200%", r == [0.2, 2], r)
    r = js(pg, "[null, {ok:false}, {ok:true, placas:[{tipo:'gpu', nome:'AMD Radeon RX 9070 XT', minerando:false, rendimentoUsd:2}]}, {ok:true, placas:[{tipo:'gpu', nome:'Placa Inventada 9000', minerando:true, rendimentoUsd:2}]}, {ok:true, placas:[{tipo:'gpu', nome:'AMD Radeon RX 9070 XT', minerando:true}]}].map(fatorKxReal)")
    checa("sem placa minerando, fora do catálogo ou sem rendimento: null", r == [None] * 5, r)
    r = js(pg, "fatorSim()")
    checa("sem leitura: a estimativa com a margem", r == {"f": 0.8, "fonte": "estimativa", "placas": []}, r)
    pg.evaluate("kxaSnap = {v:1, fatorKx:0.74, placas:[{nome:'RX 9070 XT', tipo:'gpu', minerando:true}]}")
    r = js(pg, "fatorSim()")
    checa("com o retrato do PC: o real", r == {"f": 0.74, "fonte": "real", "placas": ["RX 9070 XT"]}, r)
    checa("sem erros (mineração)", not erros(pg), erros(pg)[:3])


OP = "{nome:'A', placas:[{modelo:'rtx-5070', qtd:2, preco:5159, maq:'m-pc'}], pcNovo:{custo:0}, pagamento:{tipo:'cartao', parcelas:12}, dinheiro:{tipo:'emprestimo', valor:10000, parcelas:20, parcela:674.65}}"


def opcoes(p):
    pg = abrir(p, dados=DADOS_SIM)
    r = js(pg, "(() => { delete cfg.sim; const s = simCfg(); return [s.opcoes.map(o => o.nome), s.opcoes[0].placas.length, s.prazo, s.cenarios, s.cenarioGrafico]; })()")
    checa("padrão: a opção A vazia", r == [["A"], 1, 0, {"estavel": 0, "devagar": -1.5, "rapido": -4}, "estavel"], r)
    r = js(pg, "(() => { cfg.sim = {opcoes:[{nome:'A', placas:'x'}, null, {nome:'Z'}, {nome:'B', placas:[{modelo:'rtx-5070', qtd:'2', preco:'5159', maq:'m-pc'}], pagamento:{tipo:'cartao', parcelas:99}}, {nome:'C'}, {nome:'A'}], prazo:'24', cenarios:{estavel:'x', devagar:-50, rapido:3}, cenarioGrafico:'outro'}; const s = simCfg(); return [s.opcoes.map(o => o.nome), s.opcoes[0].placas, s.opcoes[1].placas[0].qtd, s.opcoes[1].placas[0].preco, s.opcoes[1].pagamento.parcelas, s.prazo, s.cenarios, s.cenarioGrafico]; })()")
    checa("cfg.sim estragado é arrumado ao ler", r == [["A", "B", "C"], [], 2, 5159, 24, 24, {"estavel": 0, "devagar": -20, "rapido": 3}, "estavel"], r)
    r = js(pg, "[prazoSim({prazo:0, opcoes:[{pagamento:{tipo:'cartao', parcelas:10}, dinheiro:{tipo:'meu'}}]}), prazoSim({prazo:0, opcoes:[{pagamento:{tipo:'cartao', parcelas:12}, dinheiro:{tipo:'emprestimo', parcelas:20}}, {pagamento:{tipo:'avista'}, dinheiro:{tipo:'meu'}}]}), prazoSim({prazo:0, opcoes:[{pagamento:{tipo:'avista'}, dinheiro:{tipo:'emprestimo', parcelas:96}}]}), prazoSim({prazo:36, opcoes:[]})]")
    checa("prazo automático", r == [12, 20, 60, 36], r)
    R = js(pg, f"(() => {{ const r = simularOpcao({OP}, {{f:0.74, fonte:'real', placas:[]}}, 20, {{estavel:0, devagar:-1.5, rapido:-4}}); return {{ok:r.ok, preco:r.preco, i:r.juros.i, total:r.juros.total, b1:r.cen.estavel.meses[1].bruto, d2:r.cen.devagar.meses[2].bruto, n:r.cen.rapido.meses.length}}; }})()")
    checa("2× RTX 5070 com o empréstimo do Alex", campo(R, "ok") is True and campo(R, "preco") == 10318 and perto(campo(R, "i"), 0.030401, 5e-6)
          and round(campo(R, "total") or 0) == 3493 and campo(R, "n") == 21, R)
    checa("bruto = estimativa sem margem × correção, e o cenário cai",
          perto(campo(R, "b1"), 1295.7633 * 0.74, 0.01) and perto(campo(R, "d2"), (campo(R, "b1") or 0) * 0.985, 1e-6), R)
    r = js(pg, "[{valor:0, parcelas:20, parcela:674.65}, {valor:10000, parcelas:20, parcela:0}, {valor:10000, parcelas:20, parcela:400}].map(d => simularOpcao({...%s, dinheiro:{tipo:'emprestimo', ...d}}, fatorSim(), 20).texto)" % OP)
    checa("empréstimo pela metade ou impossível: diz o que falta",
          isinstance(r, list) and str(r[0]).startswith("Preencha") and str(r[1]).startswith("Preencha") and "somam menos" in str(r[2]), r)
    checa("sem placa", js(pg, "simularOpcao({...%s, placas:[{modelo:'', qtd:1, preco:null, maq:'novo'}]}, fatorSim(), 12).motivo" % OP) == "placa")
    r = js(pg, "simularOpcao({...%s, placas:[{modelo:'placa-que-nao-existe', qtd:1, preco:900, maq:'novo'}, {modelo:'rtx-5060', qtd:1, preco:2665, maq:'novo'}], pcNovo:{custo:1500}}, fatorSim(), 20).preco" % OP)
    checa("modelo fora do catálogo é ignorado; o PC novo entra no preço", r == 4165, r)
    r = js(pg, "simularOpcao({...%s, placas:[{modelo:'rtx-5060', qtd:1, preco:2665, maq:'m-apagada'}]}, fatorSim(), 20).avisos.map(a => a.t).join(' ')" % OP)
    checa("aviso da máquina que sumiu", "não existe mais" in str(r), r)
    r = js(pg, "simularOpcao({...%s, placas:[{modelo:'rtx-5070', qtd:3, preco:5159, maq:'m-pc'}]}, fatorSim(), 20).avisos.map(a => a.t).join(' ')" % OP)
    checa("aviso da fonte acima de 80%", "A fonte de 750 W do PC principal fica com 113% de carga" in str(r), r)
    # gravar gasta mensagem (o PC e o celular sincronizam o min-cfg): mudarSim muda na hora e só grava depois de SIM_GRAVA;
    # gravarSimJa e salvarPendentes gravam já o que estava esperando, uma vez só
    pg.evaluate("window.__gravouCfg = 0; (() => { const s = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { if (k === 'min-cfg') window.__gravouCfg++; return s.call(this, k, v); }; })()")
    js(pg, "mudarSim(s => { s.prazo = 24; })")
    pg.wait_for_timeout(1200)
    r = js(pg, "[simCfg().prazo, window.__gravouCfg]")
    checa("mudarSim muda na hora e não grava antes de SIM_GRAVA", r == [24, 0], r)
    js(pg, "gravarSimJa()")
    r = js(pg, "[window.__gravouCfg, JSON.parse(localStorage.getItem('min-cfg')).sim.prazo]")
    checa("gravarSimJa grava uma vez", r == [1, 24], r)
    js(pg, "gravarSimJa()")
    checa("sem nada esperando, gravarSimJa não grava", js(pg, "window.__gravouCfg") == 1)
    js(pg, "mudarSim(s => { s.prazo = 36; }); salvarPendentes()")
    r = js(pg, "[window.__gravouCfg, JSON.parse(localStorage.getItem('min-cfg')).sim.prazo]")
    checa("salvarPendentes grava o que o simulador esperava", r == [2, 36], r)
    checa("sem erros (opções)", not erros(pg), erros(pg)[:3])


A, B, C = (".sim-op[data-op='%s']" % x for x in "ABC")
# conta as gravações da configuração (cada uma vira mensagem entre o PC e o celular)
CONTA_CFG = "window.__gravouCfg = 0; (() => { const s = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { if (k === 'min-cfg') window.__gravouCfg++; return s.call(this, k, v); }; })();"
# o retrato do app da Kryptex que o PC mandou (com a correção pelo real da RX 9070 XT)
RETRATO = {"v": 1, "quando": AGORA_MS - 60_000, "estado": "minerando", "pausaAte": None, "computador": "PC-TESTE", "fatorKx": 0.74,
           "placas": [{"nome": "RX 9070 XT", "tipo": "gpu", "minerando": True, "moeda": "PRL", "minerador": "srbminer", "hash": 1.13e14, "temp": 63, "watts": 286}],
           "hoje": {"ganho": 9.62, "luz": 5.09, "lucro": 4.53, "kwh": 5.3, "desde": None}, "ritmo": {"brutoDia": 14.7, "lucroDia": 6.9},
           "saldoBtc": 0.00012, "saldoUsd": 9.7, "precoBtc": 401000, "linha": [], "protecao": None, "minerandoDesde": AGORA_MS - 5 * 3600_000, "hash24": 1.12e14}
# três opções prontas: A com o empréstimo do Alex no cartão, B num PC novo, C no PC principal
SIM_PRONTO = {"opcoes": [
    {"nome": "A", "placas": [{"modelo": "rtx-5070", "qtd": 2, "preco": 5159, "maq": "m-pc"}], "pagamento": {"tipo": "cartao", "parcelas": 12},
     "dinheiro": {"tipo": "emprestimo", "valor": 10000, "parcelas": 20, "parcela": 674.65}},
    {"nome": "B", "placas": [{"modelo": "rtx-5060", "qtd": 3, "preco": None, "maq": "novo"}], "pcNovo": {"custo": 1500}},
    {"nome": "C", "placas": [{"modelo": "rtx-5070", "qtd": 1, "preco": None, "maq": "m-pc"}]}], "prazo": 0}


def tela(p):
    pg = abrir(p, dados=DADOS_SIM, pc=True, hash="sim")
    checa("abre o Simulador", visivel(pg, "#v-sim") and texto(pg, "#t-sim") == "Simulador", texto(pg, "#t-sim"))
    checa("começa com a opção A vazia e o + Opção", js(pg, "document.querySelectorAll('#sim-ops .sim-op').length") == 1 and visivel(pg, "[data-sim='add-op']"))
    escolhe(pg, f"{A} [data-i='0'][data-campo='modelo']", "rtx-5070")
    checa("preço sugerido (o melhorPreco)", valor(pg, f"{A} [data-i='0'][data-campo='preco']") == "5159", valor(pg, f"{A} [data-i='0'][data-campo='preco']"))
    preenche(pg, f"{A} [data-i='0'][data-campo='qtd']", "2")
    marca(pg, f"{A} input[name='sim-pag-A'][value='cartao']")
    preenche(pg, f"{A} [data-campo='pagamento.parcelas']", "12")
    marca(pg, f"{A} input[name='sim-din-A'][value='emprestimo']")
    preenche(pg, f"{A} [data-campo='dinheiro.valor']", "10000")
    t = texto(pg, f"{A} .sim-res")
    checa("empréstimo só com o valor: diz o que falta", t.startswith("Preencha"), t)
    preenche(pg, f"{A} [data-campo='dinheiro.parcela']", "400")
    t = texto(pg, f"{A} .sim-res")
    checa("parcelas que somam menos que o valor: avisa", "somam menos" in t, t)
    preenche(pg, f"{A} [data-campo='dinheiro.parcelas']", "20")
    preenche(pg, f"{A} [data-campo='dinheiro.parcela']", "674.65")
    j = texto(pg, f"{A} .sim-juros")
    checa("juros do empréstimo do Alex", "3,04% ao mês" in j and "43,2% ao ano" in j and "R$ 3.493" in j, j)
    cen = pg.evaluate("(s) => [...document.querySelectorAll(s + ' .sim-cen')].map(e => e.innerText)", A)
    checa("três cenários, cada um com o mês em que se paga", len(cen) == 3 and all("Se paga" in c or "Não se paga" in c for c in cen), cen)
    clica(pg, "[data-sim='add-op']")
    escolhe(pg, f"{B} [data-i='0'][data-campo='modelo']", "rtx-5060")
    preenche(pg, f"{B} [data-i='0'][data-campo='qtd']", "3")
    checa("sem PC novo, sem o custo do PC", not existe(pg, f"{B} [data-campo='pcNovo.custo']"))
    escolhe(pg, f"{B} [data-i='0'][data-campo='maq']", "novo")
    checa("PC novo: aparece o custo do PC", visivel(pg, f"{B} [data-campo='pcNovo.custo']"))
    preenche(pg, f"{B} [data-campo='pcNovo.custo']", "1500")
    checa("o PC novo entra no preço", "R$ 9.300" in texto(pg, f"{B} .sim-res"), texto(pg, f"{B} .sim-res"))
    clica(pg, "[data-sim='add-op']")
    escolhe(pg, f"{C} [data-i='0'][data-campo='modelo']", "rtx-5070")
    preenche(pg, f"{C} [data-i='0'][data-campo='qtd']", "3")
    checa("três opções: o + Opção some", not existe(pg, "[data-sim='add-op']"))
    checa("aviso da fonte acima de 80%", "113%" in texto(pg, f"{C} .avisos"), texto(pg, f"{C} .avisos"))
    t = texto(pg, "#v-sim")
    checa("sem NaN, Infinity nem undefined na tela", not any(x in t for x in ("NaN", "Infinity", "undefined")), [x for x in ("NaN", "Infinity", "undefined") if x in t])
    # com o cursor num campo, o render() (que roda quando chegam dados do PC) não tira o foco nem o que foi digitado
    pg.fill(f"{A} [data-campo='dinheiro.valor']", "12000")
    pg.evaluate("render()")
    r = pg.evaluate("(() => { const a = document.activeElement; return [a.dataset.campo, a.closest('.sim-op') && a.closest('.sim-op').dataset.op, a.value]; })()")
    checa("render() com o cursor num campo mantém o foco e o valor", r == ["dinheiro.valor", "A", "12000"], r)
    clica(pg, f"{A} [data-sim='del-op']")
    r = pg.evaluate("[...document.querySelectorAll('#sim-ops .sim-op')].map(e => e.dataset.op)")
    checa("apagar A: B e C continuam com as letras e o + Opção volta", r == ["B", "C"] and existe(pg, "[data-sim='add-op']"), r)
    pg.evaluate("setup.maquinas = []; render()")
    checa("máquina apagada no Montar setup: C avisa e usa o PC novo", "não existe mais" in texto(pg, f"{C} .avisos"), texto(pg, f"{C} .avisos"))
    checa("sem erros (tela)", not erros(pg), erros(pg)[:3])


def guardar(p):
    pg = abrir(p, dados=DADOS_SIM, pc=True, extra=CONTA_CFG)
    pg.wait_for_timeout(1000)
    n0 = js(pg, "window.__gravouCfg")
    pg.evaluate("irPara('sim')")
    pg.wait_for_timeout(1000)
    checa("só abrir o Simulador não grava", js(pg, "window.__gravouCfg") == n0, [n0, js(pg, "window.__gravouCfg")])
    escolhe(pg, f"{A} [data-i='0'][data-campo='modelo']", "rtx-5070")
    preenche(pg, f"{A} [data-i='0'][data-campo='qtd']", "2")
    pg.wait_for_timeout(1500)
    checa("mexer não grava na hora", js(pg, "window.__gravouCfg") == n0, [n0, js(pg, "window.__gravouCfg")])
    pg.evaluate("irPara('resumo')")
    checa("sair da tela grava uma vez", js(pg, "window.__gravouCfg") == n0 + 1, [n0, js(pg, "window.__gravouCfg")])
    salvo = js(pg, "JSON.parse(localStorage.getItem('min-cfg'))")
    pg2 = abrir(p, dados={**DADOS_SIM, "min-cfg": salvo}, hash="sim")
    r = [valor(pg2, f"{A} [data-i='0'][data-campo='modelo']"), valor(pg2, f"{A} [data-i='0'][data-campo='qtd']")]
    checa("abre de novo igual", r == ["rtx-5070", "2"], r)
    pg.evaluate("irPara('sim')")
    preenche(pg, f"{A} [data-i='0'][data-campo='qtd']", "3")
    js(pg, "salvarPendentes()")
    checa("salvarPendentes grava o que o simulador esperava", js(pg, "window.__gravouCfg") == n0 + 2, [n0, js(pg, "window.__gravouCfg")])
    preenche(pg, f"{A} [data-i='0'][data-campo='qtd']", "4")
    pg.evaluate("Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true}); document.dispatchEvent(new Event('visibilitychange'))")
    checa("esconder a página grava", js(pg, "window.__gravouCfg") == n0 + 3, [n0, js(pg, "window.__gravouCfg")])
    checa("sem erros (guardar)", not erros(pg) and not erros(pg2), (erros(pg) + erros(pg2))[:3])


def celular(p):
    pg = abrir(p, largura=390, altura=844, dados={**DADOS_SIM, "min-cfg": {**CFG, "sim": SIM_PRONTO}, "min-kx-app": RETRATO}, celular=True)
    pg.evaluate("irPara('sim')")
    pg.wait_for_timeout(300)
    checa("celular: título no topo", texto(pg, "#topo-t") == "Simulador", texto(pg, "#topo-t"))
    checa("celular: na folha Mais", existe(pg, "#mais .mais-item[data-view='sim']"))
    caixas = pg.evaluate("[...document.querySelectorAll('#sim-ops .sim-op')].map(e => { const r = e.getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom]; })")
    checa("celular: as 3 opções uma embaixo da outra", len(caixas) == 3 and all(c[0] >= 0 and c[1] <= 390 for c in caixas)
          and all(caixas[i + 1][2] >= caixas[i][3] for i in range(2)), caixas)
    checa("celular: sem rolagem para o lado", pg.evaluate("document.documentElement.scrollWidth <= innerWidth"), pg.evaluate("document.documentElement.scrollWidth"))
    f = texto(pg, "#sim-fator")
    checa("celular: a correção pelo real do PC", "74%" in f and "RX 9070 XT" in f, f)
    altos = pg.evaluate("[...document.querySelectorAll('#sim-ops input:not([type=radio]), #sim-ops select')].filter(e => e.getClientRects().length).every(e => e.getBoundingClientRect().height >= 44)")
    checa("celular: campos com 44 px de altura", altos)
    checa("sem erros (celular)", not erros(pg), erros(pg)[:3])


def grafico(p):
    # A: 2× RTX 5070 no PC principal, no cartão em 12×, com o empréstimo do Alex; B: 3× RTX 5060 num PC novo, à vista, com
    # dinheiro seu; C: sem placa (fica fora do gráfico)
    sim = {"opcoes": [SIM_PRONTO["opcoes"][0],
                      {"nome": "B", "placas": [{"modelo": "rtx-5060", "qtd": 3, "preco": None, "maq": "novo"}]},
                      {"nome": "C", "placas": [{"modelo": "", "qtd": 1, "preco": None, "maq": "m-pc"}]}], "prazo": 0}
    pg = abrir(p, dados={**DADOS_SIM, "min-cfg": {**CFG, "sim": sim}}, pc=True, hash="sim")
    linhas = "[...document.querySelectorAll('#sim-graf path.sim-l')].map(e => [e.dataset.op, e.getAttribute('stroke')])"
    rotulo = "(document.querySelector('#sim-graf svg') || {getAttribute: () => ''}).getAttribute('aria-label')"
    r = js(pg, linhas)
    checa("uma linha por opção que deu conta, com a cor da letra", r == [["A", "var(--viz-a)"], ["B", "var(--viz-b)"]], r)
    rot = js(pg, rotulo)
    checa("linha do zero e descrição", existe(pg, "#sim-graf line.sim-zero") and "cenário estável" in str(rot), rot)
    escolhe(pg, "#sim-cen", "rapido")
    rot = js(pg, rotulo)
    checa("trocar o cenário do gráfico", js(pg, "simCfg().cenarioGrafico") == "rapido" and "caindo rápido" in str(rot), rot)
    if existe(pg, "#sim-graf svg"):
        pg.focus("#sim-graf svg")
        pg.keyboard.press("ArrowRight")
    dica = texto(pg, "#sim-graf .tip")
    checa("dica com o mês e as duas opções", "mês 1" in dica and "Opção A" in dica and "Opção B" in dica, dica)
    clica(pg, "#sim-tab-d summary")
    escolhe(pg, "#sim-tab-op", "B")
    r = [js(pg, "document.querySelectorAll('#sim-tab tbody tr').length"), js(pg, "simularTudo().prazo")]
    checa("tabela mês a mês da opção B", isinstance(r[1], int) and r[0] == r[1] + 1 and "Opção B" in texto(pg, "#sim-tab-op"), r)
    checa("legenda com as opções", texto(pg, "#sim-leg").count("Opção") == 2, texto(pg, "#sim-leg"))
    clica(pg, ".sim-op[data-op='A'] [data-sim='del-op']")
    r = js(pg, linhas)
    checa("apagar A não troca a cor de B", r == [["B", "var(--viz-b)"]], r)
    pg.evaluate("cfg.tarifa = 5; render()")   # luz cara: B (3× RTX 5060 num PC novo, pela estimativa) dá prejuízo
    rot = js(pg, rotulo)
    checa("prejuízo: B não se paga, sem NaN no gráfico", "Opção B não se paga" in str(rot) and "NaN" not in js(pg, "document.getElementById('sim-graf').innerHTML"), rot)
    checa("prejuízo: o eixo desce abaixo de zero", "−" in texto(pg, "#sim-graf"), texto(pg, "#sim-graf")[:200])
    checa("sem erros (gráfico)", not erros(pg), erros(pg)[:3])


with sync_playwright() as p:
    contas(p)
    mineracao(p)
    opcoes(p)
    tela(p)
    guardar(p)
    celular(p)
    grafico(p)
fim()
