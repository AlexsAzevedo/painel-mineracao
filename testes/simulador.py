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


with sync_playwright() as p:
    contas(p)
fim()
