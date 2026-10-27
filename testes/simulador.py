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


with sync_playwright() as p:
    contas(p)
    mineracao(p)
    opcoes(p)
fim()
