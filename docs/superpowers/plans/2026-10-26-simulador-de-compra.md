# Simulador de compra de placas (1.9.0): plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** uma tela nova, Simulador, em que o Alex monta até 3 opções de compra de placas (à vista, no cartão ou com empréstimo) e vê, mês a mês e em 3 cenários de mercado, quando cada uma se paga, quanto sobra no fim (com e sem a revenda) e se a mineração dá conta das parcelas. Sai como 1.9.0 (só o PC; o app do celular continua 1.8.0 e recebe a página sozinho).

**Arquitetura:** tudo em `mineracao.html`, num bloco novo `/* ---------- simulador de compra ---------- */` colocado logo antes de `/* ---------- carga inicial ---------- */` (o `render()` da carga inicial já chama o simulador, então nada do bloco pode ser `let`/`const` usado antes dessa linha). Três camadas: contas puras (`fluxoSim` e os juros), a ligação com o painel (`mineracaoSim` usa o `calcMaq` do Montar setup; `fatorSim` usa a leitura do app da Kryptex ou o retrato `min-kx-app`) e a tela (`renderSim`, `renderSimRes`, `desenharSim`). Os dados ficam em `cfg.sim`, que já sincroniza.

**Tecnologia:** HTML/CSS/JS sem biblioteca (SVG feito à mão, como `desenharRetorno`); testes em Python + Playwright com `testes/apoio.py` (relógio em 25/10/2026 14:00, dados inventados).

**Especificação:** `docs/superpowers/specs/2026-10-26-simulador-de-compra-design.md`.

## Global Constraints

- Textos em português do Brasil, frases curtas, sem jargão. Rodapé exato: "Conta com estimativas: o rendimento da mineração e o preço das placas mudam. Não é recomendação de compra nem de empréstimo."
- Nada vai para o `main` sem o OK do Alex (o push no `main` publica a release). Trabalho no branch `simulador-1.9.0`. Testes só com dados inventados; nunca `--com-dados`.
- Nada do que existe muda: as telas, as contas e os testes de hoje continuam passando (critério 6). A única mudança fora do simulador é o campo `fatorKx` no retrato `min-kx-app`.
- Cores só por variáveis CSS (o `visual.py` recusa cor fixa fora dos blocos `:root`). As 3 opções usam tokens novos, validados com o validador da skill dataviz (todos os pares, nos dois temas): escuro (`:root`) `--viz-a:#3987e5; --viz-b:#d95926; --viz-c:#199e70`; claro (`:root[data-tema="claro"]`) `--viz-a:#2a78d6; --viz-b:#eb6834; --viz-c:#1baf7a`. No claro, o verde fica abaixo de 3:1: por isso há legenda, rótulo no fim de cada linha e a tabela. Traço como segunda pista: A cheio, B `7 5`, C `2 5` (pontas redondas). A cor segue a opção (a letra), nunca a posição na tela.
- Opções: no máximo 3, com as letras "A", "B" e "C" (a letra é a identidade e a cor). Linhas: modelo do catálogo, quantidade de 1 a 20, preço ≥ 0 (vazio = o `melhorPreco`), PC = id de uma máquina de `maqsReais()` ou `"novo"`. Cartão de 1 a 24 vezes; empréstimo de 1 a 120 parcelas. Cenários em % ao mês, entre −20 e 10 (padrão estável 0, devagar −1,5, rápido −4). Prazo: 0 (automático), 12, 24 ou 36; o automático é o mesmo para todas as opções: o maior fim de parcelas (cartão e empréstimo), no mínimo 12 e no máximo 60.
- **Correção pelo real no lugar da margem de segurança.** A margem de segurança das Premissas e a correção medem a mesma coisa (quanto o real fica abaixo da estimativa da Kryptex; o Diário até sugere a margem por isso). Com leitura: bruto = estimativa da Kryptex sem margem × `fatorKx`. Sem leitura: a estimativa com a margem de segurança, como no resto do painel. Usar as duas contaria o desconto duas vezes.
- PCs da lista: as máquinas que já existem (`maqsReais()`) e "Um PC novo" (`maqBase({id:"novo", nome:"Um PC novo", fonteW:650, selo:"Gold", base:30, cpu:"outro", minerarCpu:false})`). As máquinas planejadas do setup (`nova: true`) ficam de fora: para elas, "Um PC novo".
- Gravar gasta mensagem do ntfy.sh (PC e celular sincronizam o `min-cfg`): o simulador guarda as mudanças em `cfg.sim` na hora, mas só grava 15 s depois da última (`var SIM_GRAVA = 15e3`), ao sair da tela, ao esconder a página e em `salvarPendentes()`. Abrir a tela sem mexer não grava nada.
- Versão 1.9.0 em `desktop/package.json` e no topo de `desktop/package-lock.json`; `celular/package.json` não muda.

## Review Focus

1. **Gravar a cada tecla** (o Alex acabou de passar pelo limite de mensagens): mexer no simulador não pode mandar uma mensagem por campo. Teste na Tarefa 4 (nada gravado antes de `SIM_GRAVA`; uma gravação ao sair; nenhuma ao só abrir).
2. **Empréstimo digitado aos poucos** (valor primeiro, parcelas depois, ou parcelas que somam menos que o valor): a opção mostra o que falta, sem NaN nem Infinity na tela e no gráfico. Testes nas Tarefas 1, 3 e 4.
3. **Máquina apagada no Montar setup** depois de montar a opção: a linha passa a contar como "Um PC novo" e avisa, sem erro. Testes nas Tarefas 2 e 4.
4. **Prejuízo e números negativos** (luz maior que o ganho, cenário de −20% ao mês): "não se paga", "faltam R$ …" e o gráfico com o eixo abaixo de zero. Testes nas Tarefas 1 e 5.
5. **`cfg.sim` estragado ou de outra versão** chegando pela sincronia (texto no lugar de número, mais de 3 opções, letra repetida, cenário fora da faixa): `simCfg()` arruma tudo ao ler. Teste na Tarefa 3.

---

### Task 1: Contas puras (juros, CDI e o fluxo mês a mês)

**Files:**
- Modify: `mineracao.html` (bloco novo do simulador; `rendimentoParcelado`, perto da linha 1828, passa a usar `taxaMesCdi` e `irRegressivo`, com o mesmo resultado)
- Create: `testes/simulador.py`

**Interfaces:**
- Produces: `irRegressivo(m) → 0.225|0.20|0.175|0.15` (até 6, 12, 24 meses e depois). `taxaMesCdi() → number` (`dia=(1+cdi/100)^(1/252)−1; mes=(1+dia·pctCdi/100)^21−1`, com `cfg.cdi` e `cfg.pctCdi`). `taxaEmprestimo(valor, parcelas, parcela) → number|null`: juros ao mês da tabela Price (bisseção em [0, 1]); 0 quando as parcelas somam o valor; `null` quando algum número falta ou não é finito, valor ≤ 0, parcela ≤ 0, parcelas fora de 1..120 (arredonda), as parcelas somam menos que o valor ou os juros passariam de 100% ao mês. `fluxoSim(e) → objeto|null`, abaixo.
- `fluxoSim({preco, cartao, emprestimo, bruto, luz, taxa, prazo, rendMes, revendaEm})`: `cartao` 0 = à vista, N = no cartão em N vezes; `emprestimo` `null` (dinheiro seu) ou `{valor, parcelas, parcela}`; `bruto` = ganho bruto do 1º mês já corrigido (R$); `luz` R$/mês; `taxa` % ao mês do cenário; `revendaEm(m)` = quanto as placas valem no mês m. Devolve `null` se `preco ≤ 0` ou o empréstimo é inválido; senão `{meses: [{m, bruto, luz, lucro, parcCartao, parcEmp, rend, conta, saldo, falta, resultado, revenda}] (m = 0..prazo), sePaga: m|null, pior: {m, conta}, fim: {resultado, revenda, comRevenda}, juros: {i, iAno, total}|null}`.

- [ ] **Step 1: Escrever o teste** `testes/simulador.py` no padrão de `kryptex_app.py` (`from apoio import *`, `checa`, `fim`). Dados: `SETUP = {"v":1, "tensao":220, "parcelas":12, "aloc":{"l1":"m-pc"}, "maquinas":[{"id":"m-pc", "nome":"PC principal", "cpu":"outro", "minerarCpu":False, "x16":1, "x1":3, "base":40, "fonteW":750, "selo":"Gold", "gpus":[], "extras":[], "nova":False}]}` e `DADOS_SIM = {**DADOS, "min-setup": SETUP}`. Ajudante `js(pg, expr)` que roda `try { return (expr) } catch(e) { return {erro: String(e)} }` (assim o teste vermelho lista as falhas em vez de parar). Função `contas(p)` com `pg = abrir(p, dados=DADOS_SIM)` e `F = "(o) => fluxoSim({preco:1200, cartao:0, emprestimo:null, bruto:200, luz:50, taxa:0, prazo:12, rendMes:0, revendaEm:()=>0, ...o})"`:
  ```python
  i = js(pg, "taxaEmprestimo(10000, 20, 674.65)")
  checa("empréstimo do Alex: 3,04% ao mês", isinstance(i, float) and abs(i - 0.030401) < 5e-6, i)
  checa("43,2% ao ano", abs(js(pg, "Math.pow(1 + taxaEmprestimo(10000, 20, 674.65), 12) - 1") - 0.432432) < 5e-5)
  checa("parcelas que somam o valor: 0", js(pg, "taxaEmprestimo(1200, 12, 100)") == 0)
  checa("empréstimo inválido: null", js(pg, "[[1200,12,90],[0,12,100],[1000,0,100],[1000,12,0],[NaN,12,100],['',12,100],[1000,12,2000],[1000,200,10]].map(a => taxaEmprestimo(...a))") == [None] * 8)
  checa("CDI do mês (13,65% e 100%)", abs(js(pg, "taxaMesCdi()") - 0.0107198) < 1e-6)
  checa("IR regressivo", js(pg, "[1,6,7,12,13,24,25].map(irRegressivo)") == [0.225, 0.225, 0.2, 0.2, 0.175, 0.175, 0.15])
  checa("rendimentoParcelado igual ao de antes", abs(js(pg, "rendimentoParcelado(1200, 12).liquido") - LIQ_1200_12) < 1e-9)
  r = js(pg, f"({F})({{}})")
  checa("à vista: mês 0 é −preço, se paga no mês 8, sobram R$ 600", r["meses"][0]["resultado"] == -1200 and r["sePaga"] == 8 and round(r["fim"]["resultado"], 2) == 600)
  checa("no cartão em 12×: se paga no mês 8", js(pg, f"({F})({{cartao:12}}).sePaga") == 8)
  r = js(pg, f"({F})({{taxa:-4}})"); checa("caindo 4% ao mês: mês 11, R$ 136,45", r["sePaga"] == 11 and round(r["fim"]["resultado"], 2) == 136.45)
  r = js(pg, f"({F})({{emprestimo:{{valor:1200, parcelas:12, parcela:113.47}}}})")
  checa("empréstimo a 2% ao mês: mês 9, R$ 438,36, juros de R$ 161,64, conta nunca negativa", r["sePaga"] == 9 and round(r["fim"]["resultado"], 2) == 438.36 and round(r["juros"]["total"], 2) == 161.64 and r["pior"]["conta"] >= 0)
  r = js(pg, f"({F})({{bruto:100, luz:150}})"); checa("prejuízo: não se paga, faltam R$ 1.800", r["sePaga"] is None and round(r["fim"]["resultado"], 2) == -1800)
  r = js(pg, f"({F})({{preco:1000, cartao:10, bruto:0, luz:0, rendMes:0.01}})")
  checa("a conta rende com o IR de 22,5% no 1º mês", round(r["meses"][1]["resultado"] - r["meses"][0]["resultado"], 2) == 7.75)
  r = js(pg, f"({F})({{preco:1000, emprestimo:{{valor:1000, parcelas:10, parcela:120}}, bruto:100, luz:40}})")
  checa("pior mês da conta: mês 10 com −R$ 600", r["pior"]["m"] == 10 and round(r["pior"]["conta"], 2) == -600)
  checa("revenda no fim", js(pg, f"({F})({{revendaEm: m => 1000 - m*10}}).fim.comRevenda") == 1480)
  checa("preço zero ou empréstimo inválido: null", js(pg, f"[({F})({{preco:0}}), ({F})({{emprestimo:{{valor:1200, parcelas:12, parcela:90}}}})]") == [None, None])
  checa("sem erros", not erros(pg), erros(pg)[:3])
  ```
  `LIQ_1200_12`: rode `rendimentoParcelado(1200, 12).liquido` na página **antes** de mexer nela e escreva o número no teste.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador.py` → sai com 1; as falhas dizem `taxaEmprestimo is not defined` (e as outras funções).
- [ ] **Step 3: Implementar** `irRegressivo`, `taxaMesCdi`, `taxaEmprestimo` e `fluxoSim` no bloco novo; `rendimentoParcelado` passa a usar as duas primeiras. O fluxo, nesta ordem (é ele que dá os números do teste):
  ```js
  // mês 0: conta = preco (dinheiro seu, "proprio" = preco) ou = valor do empréstimo (proprio = 0, saldo = valor);
  //        à vista: conta −= preco; no cartão: falta = preco. resultado = conta − saldo − falta − proprio (= −preco)
  for (m = 1..prazo) {
    rend = max(0, conta) × rendMes × (1 − irRegressivo(m))          // a conta do mês anterior
    parcCartao = cartão e m ≤ N ? preco/N : 0;  parcEmp = m ≤ n ? parcela : 0
    saldo = m ≤ n ? (m === n ? 0 : max(0, saldo × (1+i) − parcela)) : saldo
    bruto_m = bruto × (1 + taxa/100)^(m−1);  lucro = bruto_m − luz
    conta += rend − parcCartao − parcEmp + lucro;  falta = cartão ? preco − min(m, N) × preco/N : 0
    resultado = conta − saldo − falta − proprio;  revenda = revendaEm(m)
  }
  // sePaga: o 1º m ≥ 1 com resultado ≥ −0,005; pior: a menor conta de 0..prazo (a primeira, no empate);
  // fim: o último mês; juros: {i, iAno: (1+i)^12 − 1, total: n × parcela − valor}
  ```
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador.py` → `"falhas": []`, saída 0.
- [ ] **Step 5: Commit:** `git add mineracao.html testes/simulador.py && git commit -m "Simulador (1.9.0): contas do empréstimo, do CDI e o fluxo mês a mês"`

### Task 2: Mineração, revenda e a correção pelo real

**Files:**
- Modify: `mineracao.html` (bloco do simulador; `retratoKxa`, perto da linha 5681)
- Test: `testes/simulador.py` (função `mineracao(p)`), `testes/kryptex_app.py`

**Interfaces:**
- Consumes: `calcMaq(m, {extra})`, `maqsReais()`, `maqBase(o)`, `melhorPreco(c)`, `deprecModelo(id).d`, `acharModelo(nome, "")`, `dados(c).rec`, `byId`, `novoId`, `kxa.leitura`, `kxaSnap`, `PODE_KXA()`, `nomePlaca`.
- Produces: `maqNovaSim() → máquina` (a das Global Constraints). `linhasSim(op) → [{c, q, preco, maq, sumiu}]`: só as linhas com modelo do catálogo (`byId[novoId(modelo)]`); `q` inteiro de 1 a 20; `preco` = o da linha se > 0, senão `melhorPreco(c)?.v || 0`; `maq` = o id da máquina ou `"novo"`; `sumiu` = a linha apontava para uma máquina que não está em `maqsReais()`. `mineracaoSim(op) → {maqs: [{id, nome, n, carga, fonteW, avisoFonte, sumiu}], bruto, luz, usaNovo}`: por máquina, `calcMaq(m, {extra})` − `calcMaq(m)` com `extra = linhas.map(l => ({tipo:"plano", c:l.c, q:l.q, preco:l.preco}))`; `bruto` é a soma das diferenças de `brutoGpu` ÷ `max(0.01, 1 − cfg.margem/100)` (a estimativa da Kryptex, sem margem); `luz` é a soma das diferenças de `luz`; `avisoFonte` = `carga > 0.8` com as placas. `revendaSim(op, m) → R$` = Σ `preco × q × (1 − deprecModelo(c.id).d)^(m/12)` (o PC novo fica de fora). `fatorKxReal(l) → number|null` = Σ `rendimentoUsd` ÷ Σ `dados(c).rec/365` das placas `tipo:"gpu"` minerando e achadas no catálogo, entre 0,2 e 2; `null` sem `l.ok`, sem placa assim ou sem `rendimentoUsd`. `fatorSim() → {f, fonte:"real"|"estimativa", placas:[nomes]}`: no PC, `fatorKxReal(kxa.leitura)`; senão (ou no celular) o `kxaSnap.fatorKx`; sem nenhum, `{f: 1 − cfg.margem/100, fonte:"estimativa", placas:[]}`. `placas` = os nomes (`nomePlaca`, sem repetir) das placas de vídeo da fonte usada. `retratoKxa()` ganha `fatorKx: fatorKxReal(l) ?? (o fatorKx do retrato anterior, se for número) ?? null`.

- [ ] **Step 1: Escrever os testes.** Em `simulador.py`, `mineracao(p)` com `pg = abrir(p, dados=DADOS_SIM)` e `LEIT_9070 = "u => ({ok:true, placas:[{tipo:'gpu', nome:'AMD Radeon RX 9070 XT', minerando:true, rendimentoUsd:u}]})"`:
  ```python
  r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5070', qtd:2, preco:5159, maq:'m-pc'}]})")
  ref = js(pg, "(() => { const m = setup.maquinas[0], a = calcMaq(m), b = calcMaq(m, {extra:[{tipo:'plano', c:byId['rtx-5070'], q:2, preco:5159}]}); return b.luz - a.luz; })()")
  checa("2× RTX 5070 no PC principal: bruto sem margem e luz do setup", abs(r["bruto"] - 1295.7633) < 0.01 and abs(r["luz"] - ref) < 0.01)
  r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5060', qtd:3, preco:2665, maq:'novo'}]})")
  ref = js(pg, "calcMaq(maqNovaSim(), {extra:[{tipo:'plano', c:byId['rtx-5060'], q:3, preco:2665}]})")
  checa("PC novo conta inteiro (placas, 10 W do processador parado, 30 W de base)", r["usaNovo"] and ref["dc"] == 340 and abs(r["luz"] - ref["luz"]) < 0.01)
  r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5070', qtd:3, preco:5159, maq:'m-pc'}]})")
  checa("fonte de 750 W a 113%: avisa", r["maqs"][0]["avisoFonte"] and round(r["maqs"][0]["carga"] * 100) == 113)
  r = js(pg, "mineracaoSim({placas:[{modelo:'rtx-5060', qtd:1, preco:2665, maq:'m-apagada'}]})")
  checa("máquina que sumiu vira PC novo", r["maqs"][0]["id"] == "novo" and r["maqs"][0]["sumiu"] and r["usaNovo"])
  checa("preço vazio: o melhorPreco", js(pg, "linhasSim({placas:[{modelo:'rtx-5060', qtd:1, preco:null, maq:'novo'}]})[0].preco") == 2600)
  checa("revenda com 25% ao ano", js(pg, "[12, 24].map(m => revendaSim({placas:[{modelo:'rtx-5060', qtd:2, preco:2000, maq:'novo'}]}, m))") == [3000, 2250])
  checa("correção pelo real", abs(js(pg, f"fatorKxReal(({LEIT_9070})(2.965))") - 0.871357) < 1e-5)
  checa("correção entre 20% e 200%", js(pg, f"[0.1, 20].map(u => fatorKxReal(({LEIT_9070})(u)))") == [0.2, 2])
  checa("sem placa minerando, fora do catálogo ou sem rendimento: null", js(pg, "[null, {ok:false}, {ok:true, placas:[{tipo:'gpu', nome:'AMD Radeon RX 9070 XT', minerando:false, rendimentoUsd:2}]}, {ok:true, placas:[{tipo:'gpu', nome:'Placa Inventada 9000', minerando:true, rendimentoUsd:2}]}, {ok:true, placas:[{tipo:'gpu', nome:'AMD Radeon RX 9070 XT', minerando:true}]}].map(fatorKxReal)") == [None] * 5)
  checa("sem leitura: a estimativa com a margem", js(pg, "fatorSim()") == {"f": 0.8, "fonte": "estimativa", "placas": []})
  pg.evaluate("kxaSnap = {v:1, fatorKx:0.74, placas:[{nome:'RX 9070 XT', tipo:'gpu', minerando:true}]}")
  checa("com o retrato do PC: o real", js(pg, "fatorSim()") == {"f": 0.74, "fonte": "real", "placas": ["RX 9070 XT"]})
  ```
  Em `kryptex_app.py`, dentro de `kryptex_app(p)` (página do PC com as `FIXTURAS`):
  ```python
  checa("retrato leva a correção pelo real", abs(pg.evaluate("simularLeituras([MIN]).then(() => kxaSnap.fatorKx)") - 0.871357) < 1e-5)
  checa("parada, a correção de antes continua", abs(pg.evaluate("simularLeituras([MIN, PARADO]).then(() => kxaSnap.fatorKx)") - 0.871357) < 1e-5)
  checa("sem leitura minerando: sem correção", pg.evaluate("simularLeituras([PARADO]).then(() => kxaSnap.fatorKx)") is None)
  ```
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador.py` e `python3 testes/kryptex_app.py` → as checagens novas falham (`mineracaoSim is not defined`; `fatorKx` vem `undefined`).
- [ ] **Step 3: Implementar** as funções do Produces e o campo no `retratoKxa`. Em `simulador.py`, o bloco final passa a chamar `contas(p)` e `mineracao(p)` (e cada tarefa seguinte acrescenta a sua função ali).
- [ ] **Step 4: Rodar e ver passar:** os dois arquivos → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador (1.9.0): mineração por máquina, revenda e a correção pelo real (fatorKx no retrato)"`

### Task 3: Configuração (`cfg.sim`) e a conta de cada opção

**Files:**
- Modify: `mineracao.html` (bloco do simulador; `salvarPendentes`, perto da linha 1866)
- Test: `testes/simulador.py` (função `opcoes(p)`)

**Interfaces:**
- Consumes: as funções das Tarefas 1 e 2.
- Produces: `simCfg() → {opcoes, prazo, cenarios, cenarioGrafico}` normalizado ao ler, como `kxaCfg()` (no lugar de mexer em `migrar`, porque a configuração chega por três caminhos): `opcoes` = só objetos com letra `"A"|"B"|"C"`, a primeira de cada letra, em ordem de letra; cada opção `{nome, placas:[{modelo, qtd, preco, maq}], pcNovo:{custo}, pagamento:{tipo:"avista"|"cartao", parcelas}, dinheiro:{tipo:"meu"|"emprestimo", valor, parcelas, parcela}}` com números convertidos e limitados (Global Constraints; preço vazio, negativo ou inválido = `null`; padrões: cartão 12×, empréstimo 12 parcelas, valores 0); sem opção, `[opcaoVazia("A")]`. `opcaoVazia(letra)` = uma linha `{modelo:"", qtd:1, preco:null, maq: maqsReais()[0]?.id || "novo"}`, à vista, dinheiro seu. `mudarSim(fn)`: aplica `fn` numa cópia de `simCfg()`, põe em `cfg.sim` e agenda `gravarSim` em `SIM_GRAVA`. `gravarSimJa()`: se há gravação esperando, grava já (`gravarCfg()`). `var simT = null` (é lido por `salvarPendentes`, que passa a chamar `gravarSimJa()`). `prazoSim(s) → meses`. `simularOpcao(op, F, prazo, cenarios = simCfg().cenarios) → {ok:true, nome, linhas, preco, precoPlacas, custoPc, min, bruto1, juros, cen:{estavel, devagar, rapido}, avisos:[{c:"w", t}]}` ou `{ok:false, nome, motivo:"placa"|"preco"|"emprestimo", texto, avisos}`. `preco` = placas + `pcNovo.custo` (só se alguma linha usa o PC novo). `bruto1 = min.bruto × F.f`. Cada cenário é `fluxoSim` com `cartao` = parcelas do cartão (0 à vista), `rendMes: taxaMesCdi()` e `revendaEm: m => revendaSim(op, m)`. `simularTudo() → {s, F, prazo, ops}`.
- Textos: "Escolha uma placa para ver as contas." · "Ponha o preço das placas." · "Preencha o valor do empréstimo, o número de parcelas e o valor de cada parcela." · "Confira o empréstimo: as parcelas somam menos que o valor recebido." · "Confira o empréstimo: os juros passam de 100% ao mês." · "A fonte de {W} W do {nome} fica com {N}% de carga com estas placas (o bom é até 80%)." · "A máquina escolhida não existe mais em Montar setup: a conta usa Um PC novo."

- [ ] **Step 1: Escrever o teste** `opcoes(p)` (`pg = abrir(p, dados=DADOS_SIM)`; `OP = "{nome:'A', placas:[{modelo:'rtx-5070', qtd:2, preco:5159, maq:'m-pc'}], pcNovo:{custo:0}, pagamento:{tipo:'cartao', parcelas:12}, dinheiro:{tipo:'emprestimo', valor:10000, parcelas:20, parcela:674.65}}"`):
  ```python
  checa("padrão: a opção A vazia", js(pg, "(() => { delete cfg.sim; const s = simCfg(); return [s.opcoes.map(o => o.nome), s.opcoes[0].placas.length, s.prazo, s.cenarios, s.cenarioGrafico]; })()") == [["A"], 1, 0, {"estavel": 0, "devagar": -1.5, "rapido": -4}, "estavel"])
  r = js(pg, "(() => { cfg.sim = {opcoes:[{nome:'A', placas:'x'}, null, {nome:'Z'}, {nome:'B', placas:[{modelo:'rtx-5070', qtd:'2', preco:'5159', maq:'m-pc'}], pagamento:{tipo:'cartao', parcelas:99}}, {nome:'C'}, {nome:'A'}], prazo:'24', cenarios:{estavel:'x', devagar:-50, rapido:3}, cenarioGrafico:'outro'}; const s = simCfg(); return [s.opcoes.map(o => o.nome), s.opcoes[0].placas, s.opcoes[1].placas[0].qtd, s.opcoes[1].placas[0].preco, s.opcoes[1].pagamento.parcelas, s.prazo, s.cenarios, s.cenarioGrafico]; })()")
  checa("cfg.sim estragado é arrumado ao ler", r == [["A", "B", "C"], [], 2, 5159, 24, 24, {"estavel": 0, "devagar": -20, "rapido": 3}, "estavel"], r)
  checa("prazo automático", js(pg, "[prazoSim({prazo:0, opcoes:[{pagamento:{tipo:'cartao', parcelas:10}, dinheiro:{tipo:'meu'}}]}), prazoSim({prazo:0, opcoes:[{pagamento:{tipo:'cartao', parcelas:12}, dinheiro:{tipo:'emprestimo', parcelas:20}}, {pagamento:{tipo:'avista'}, dinheiro:{tipo:'meu'}}]}), prazoSim({prazo:0, opcoes:[{pagamento:{tipo:'avista'}, dinheiro:{tipo:'emprestimo', parcelas:96}}]}), prazoSim({prazo:36, opcoes:[]})]") == [12, 20, 60, 36])
  R = js(pg, f"(() => {{ const r = simularOpcao({OP}, {{f:0.74, fonte:'real', placas:[]}}, 20, {{estavel:0, devagar:-1.5, rapido:-4}}); return {{ok:r.ok, preco:r.preco, i:r.juros.i, total:r.juros.total, b1:r.cen.estavel.meses[1].bruto, d2:r.cen.devagar.meses[2].bruto, n:r.cen.rapido.meses.length}}; }})()")
  checa("2× RTX 5070 com o empréstimo do Alex", R["ok"] and R["preco"] == 10318 and abs(R["i"] - 0.030401) < 5e-6 and round(R["total"]) == 3493 and R["n"] == 21, R)
  checa("bruto = estimativa sem margem × correção, e o cenário cai", abs(R["b1"] - 1295.7633 * 0.74) < 0.01 and abs(R["d2"] - R["b1"] * 0.985) < 1e-6)
  r = js(pg, "[{valor:0, parcelas:20, parcela:674.65}, {valor:10000, parcelas:20, parcela:0}, {valor:10000, parcelas:20, parcela:400}].map(d => simularOpcao({...%s, dinheiro:{tipo:'emprestimo', ...d}}, fatorSim(), 20).texto)" % OP)
  checa("empréstimo pela metade ou impossível: diz o que falta", r[0].startswith("Preencha") and r[1].startswith("Preencha") and "somam menos" in r[2], r)
  checa("sem placa", js(pg, "simularOpcao({...%s, placas:[{modelo:'', qtd:1, preco:null, maq:'novo'}]}, fatorSim(), 12).motivo" % OP) == "placa")
  checa("modelo fora do catálogo é ignorado; o PC novo entra no preço", js(pg, "simularOpcao({...%s, placas:[{modelo:'placa-que-nao-existe', qtd:1, preco:900, maq:'novo'}, {modelo:'rtx-5060', qtd:1, preco:2665, maq:'novo'}], pcNovo:{custo:1500}}, fatorSim(), 20).preco" % OP) == 4165)
  checa("aviso da máquina que sumiu", "não existe mais" in js(pg, "simularOpcao({...%s, placas:[{modelo:'rtx-5060', qtd:1, preco:2665, maq:'m-apagada'}]}, fatorSim(), 20).avisos.map(a => a.t).join(' ')" % OP))
  ```
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador.py` → as checagens de `opcoes` falham (`simCfg is not defined`).
- [ ] **Step 3: Implementar** o Produces. `simularOpcao` confere o empréstimo antes de chamar `fluxoSim` para dar o texto certo.
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador (1.9.0): cfg.sim arrumado ao ler e a conta de cada opção"`

### Task 4: A tela Simulador

**Files:**
- Modify: `mineracao.html` — tokens `--viz-a/b/c` nos dois blocos de tema (linhas ~272 e ~286); CSS novo do simulador perto do CSS do setup (`.maqs`, linha ~518); menu do PC (item depois de "Todas as placas", linha ~1087); folha Mais (item depois de "Todas as placas", linha ~1596); `<section class="view" id="v-sim">` depois de `#v-placas`; `VIEWS` e `NA_FOLHA` (linha ~6629) com `"sim"` depois de `"placas"`; `render()` (linha ~2099) chama `renderSim()`; `irPara` chama `gravarSimJa()`; `visibilitychange`/`pagehide` chamam `gravarSimJa()` quando a página fica escondida.
- Test: `testes/simulador.py` (`tela`, `guardar`, `celular`), `testes/visual.py` (linhas 30-31: ordem do menu e `VIEWS` com `"sim"` depois de `"placas"`), `testes/celular.py` (`TITULOS` ganha `"sim": "Simulador"`).

**Interfaces:**
- Consumes: Tarefas 1 a 3.
- Produces (ids e atributos de que os testes e a Tarefa 5 dependem): `#v-sim`, `#t-sim` ("Simulador"; subtítulo curto: "Quanto as placas rendem, quanto custam e quando se pagam, à vista, no cartão ou com empréstimo."), `#sim-fator`, `#sim-ops` com um `.sim-op[data-op=letra]` por opção e o botão `[data-sim="add-op"]` ("+ Opção", some com 3), `[data-sim="del-op"]` (só com mais de uma opção), `[data-sim="add-linha"]`, `[data-sim="del-linha"][data-i]`; campos com `data-op`, `data-i` (linhas) e `data-campo` (`modelo` select do catálogo com "Escolha a placa", `qtd`, `preco` mostrando o preço que vale e "sugerido: usada/nova/loja" quando vazio, `maq` select com as máquinas e "Um PC novo", `pcNovo.custo` só quando alguma linha usa o PC novo, `pagamento.parcelas`, `dinheiro.valor`, `dinheiro.parcelas`, `dinheiro.parcela`); rádios `name="sim-pag-{letra}"` (`avista`/`cartao`) e `name="sim-din-{letra}"` (`meu`/`emprestimo`) no estilo `.seg.radios`; dentro de cada opção, `.sim-juros` ("Juros de 3,04% ao mês (43,2% ao ano): R$ 3.493 no total.") e `.sim-res` com o preço total, o lucro do 1º mês (bruto − luz) e um `.sim-cen[data-cen]` por cenário: "Se paga em jun/2027 (mês 8)" ou "Não se paga em N meses"; "No fim (N meses): sobram/faltam R$ … · com a revenda: R$ …"; "A mineração paga as parcelas." ou "Em mar/2027 faltam R$ 820: você precisaria pôr esse dinheiro." (só quando a pior conta < −0,5); `.avisos li.w` com os avisos; `#sim-prazo` (select: "Até o fim das parcelas (N meses)", 12, 24, 36), `details#sim-ajuste` ("Ajustar cenários") com `input[data-cen]` (% ao mês), `#sim-pe` (rodapé). `mesSim(m)` = `mesAnoIso` do mês atual + m. `renderSim(forcar)` monta a estrutura e chama `renderSimRes()` (resultados, e o gráfico da Tarefa 5); quando o foco está num campo de `#sim-ops` e não é `forcar`, só chama `renderSimRes()`. Eventos delegados em `#sim-ops`: `input` → `mudarSim` + `renderSimRes()`; `change` de select, rádio e dos botões → `mudarSim` + `renderSim(true)`, devolvendo o foco ao campo com os mesmos `data-*`. Texto do `#sim-fator`: real → "Rendimento corrigido pelo real: a sua RX 9070 XT está rendendo 87% da estimativa da Kryptex." (várias placas: "as suas … e … estão rendendo"); estimativa → "Rendimento pela estimativa da Kryptex, com a sua margem de segurança de 20%: o painel ainda não tem leitura do app da Kryptex para corrigir pelo real."
- Layout: no PC, as opções lado a lado (grade `repeat(auto-fit, minmax(min(100%, 300px), 1fr))`); abaixo de 900 px, uma embaixo da outra; nenhuma rolagem lateral em 390 px; campos com pelo menos 44 px de altura no celular.

- [ ] **Step 1: Escrever os testes.** Ajudantes copiados de `celular.py` (`texto`, `clica`, `preenche`, `valor`) e `escolhe(pg, sel, v)` (põe `value` e dispara `change`). Script `CONTA_CFG` (vai no `extra` do `abrir`) que conta `Storage.prototype.setItem` com a chave `"min-cfg"` em `window.__gravouCfg`.
  - `tela(p)` (PC, `pc=True`, `hash="sim"`): `#v-sim` visível e `#t-sim` = "Simulador"; uma `.sim-op` e o "+ Opção"; escolher `rtx-5070` na linha 0 de A → `preco` mostra "5159"; `qtd` 2; cartão com 12; empréstimo digitado aos poucos: só `dinheiro.valor` 10000 → `.sim-op[data-op=A] .sim-res` começa com "Preencha", depois `dinheiro.parcela` 400 → "somam menos", depois parcela 674,65 e 20 parcelas → `.sim-juros` tem "3,04% ao mês", "43,2% ao ano" e "R$ 3.493"; três `.sim-cen`, cada um com "Se paga" ou "Não se paga"; "+ Opção" → B com `rtx-5060` × 3 em "Um PC novo" → o campo `pcNovo.custo` aparece; custo 1500 → o texto de B tem "R$ 9.300"; C com `rtx-5070` × 3 em `m-pc` → aviso com "113%"; `innerText` de `#v-sim` sem "NaN", "Infinity" e "undefined"; `pg.fill` de "12000" no `dinheiro.valor` de A (o foco fica nele) e `render()` → o foco continua nesse campo e o valor é "12000"; apagar A (`del-op`) → B e C continuam com as letras e o "+ Opção" volta; `setup.maquinas = []; render()` → a linha de C mostra o aviso "não existe mais" e nada quebra; sem erros na página.
  - `guardar(p)` (`extra=CONTA_CFG`; as contas são a partir de `n0`, o que a página gravou ao abrir no Resumo e esperar 1 s): `irPara('sim')` e esperar 1 s → `n0` (só abrir não grava); escolher um modelo e esperar 1,5 s → ainda `n0`; `irPara('resumo')` → `n0 + 1`; abrir de novo com `min-cfg` = o gravado → a linha 0 de A tem o mesmo modelo e quantidade; mudar a quantidade e chamar `salvarPendentes()` → mais 1; mudar de novo, forçar `document.visibilityState` = `"hidden"` e disparar `visibilitychange` → mais 1.
  - `celular(p)` (390×844, `celular=True`, `min-cfg` com 3 opções prontas e `min-kx-app` com `fatorKx: 0.74` e a placa "RX 9070 XT"): `irPara('sim')` → `#topo-t` = "Simulador"; a folha Mais tem `.mais-item[data-view="sim"]`; as 3 `.sim-op` uma embaixo da outra (cada uma dentro de 0..390 px e a de baixo começa depois do fim da de cima); `scrollWidth <= innerWidth`; `#sim-fator` com "74%" e "RX 9070 XT"; sem erros.
  - `visual.py` e `celular.py`: as listas novas (o passeio pelas telas já cobre contraste, rolagem e temas da tela nova).
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador.py` (tela não existe), `python3 testes/visual.py` (ordem do menu), `python3 testes/celular.py` (título "sim").
- [ ] **Step 3: Implementar** a tela, o CSS, os menus, `VIEWS`/`NA_FOLHA`, `renderSim`/`renderSimRes`, os eventos e as gravações. O ícone do menu: `<svg viewBox="0 0 24 24"><path d="M4 19h16"/><path d="M5 15l4-4 3 3 6-7"/><path d="M15 7h3v3"/></svg>`.
- [ ] **Step 4: Rodar e ver passar:** os três arquivos → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador (1.9.0): a tela, no menu do PC e na folha Mais do celular"`

### Task 5: Gráfico e tabela mês a mês

**Files:**
- Modify: `mineracao.html` (dentro de `#v-sim`: um `article.painel` com `#sim-cen`, `#sim-leg`, `#sim-graf`, a nota do resultado e `details#sim-tab-d` com `#sim-tab-op` e `#sim-tab`; `desenharSim(T)` chamado por `renderSimRes()`; CSS das linhas e da legenda)
- Test: `testes/simulador.py` (função `grafico(p)`)

**Interfaces:**
- Consumes: `simularTudo()` (Tarefa 3), `cfg.sim.cenarioGrafico` via `mudarSim`, os tokens `--viz-a/b/c`.
- Produces: `desenharSim(T)` no padrão de `desenharRetorno`: SVG com `role="img"`, `tabindex="0"`, grade em `--viz-grid`, a linha do zero `line.sim-zero` em `--viz-axis`, eixo x em meses (`out/26`, com um rótulo a cada ~64 px) e y em R$ (passo como em `desenharRetorno`, com o fundo abaixo de zero quando há negativo), um `path.sim-l[data-op]` por opção que deu conta (`stroke="var(--viz-a|b|c)"` pela letra, 2 px, o traço das Global Constraints), um `circle.sim-paga` no mês em que se paga (8 px, anel de 2 px na cor do fundo) e, no fim de cada linha, o rótulo "A +R$ 600" em `--fg` (rótulos afastados pelo menos 14 px na vertical). Cruz e `.tip` com "mês 8 · jun/2027" e o valor de cada opção (mouse, setas ±1 mês, Home e End). `aria-label`: "Resultado acumulado mês a mês, cenário {estável (0% ao mês)}: Opção A se paga no mês 8 e termina com R$ 600; Opção B não se paga em 20 meses e termina com −R$ 1.800." `#sim-cen`: "Estável", "Caindo devagar", "Caindo rápido" (grava em `cenarioGrafico`). Legenda `#sim-leg`: "Opção A — 2× RTX 5070" com a amostra `.k-sim.a|b|c` (cor e traço). Nota: "Resultado: o dinheiro na conta, menos o que ainda deve (empréstimo e cartão) e o dinheiro seu que foi para a compra. Zero é quando a compra se pagou." `#sim-tab` (num `.tw.scroll`): Mês ("8 · jun/2027") | Lucro da mineração | Parcelas | Rendimento | Na conta | Resultado, m = 0..prazo, da opção em `#sim-tab-op` no cenário do gráfico, com a nota "O lucro da mineração entra na conta no mês em que é minerado; na vida real ele fica no saldo da Kryptex, em bitcoin, até o saque."

- [ ] **Step 1: Escrever o teste** `grafico(p)` (PC, `min-cfg` com A = 2× RTX 5070 em `m-pc` com o empréstimo do Alex no cartão 12×, B = 3× RTX 5060 em "Um PC novo" à vista com dinheiro seu, C sem placa; `hash="sim"`):
  ```python
  checa("uma linha por opção que deu conta, com a cor da letra", js(pg, "[...document.querySelectorAll('#sim-graf path.sim-l')].map(e => [e.dataset.op, e.getAttribute('stroke')])") == [["A", "var(--viz-a)"], ["B", "var(--viz-b)"]])
  checa("linha do zero e descrição", pg.evaluate("!!document.querySelector('#sim-graf line.sim-zero')") and "cenário estável" in js(pg, "document.querySelector('#sim-graf svg').getAttribute('aria-label')"))
  escolhe(pg, "#sim-cen", "rapido")
  checa("trocar o cenário do gráfico", js(pg, "simCfg().cenarioGrafico") == "rapido" and "caindo rápido" in js(pg, "document.querySelector('#sim-graf svg').getAttribute('aria-label')"))
  pg.focus("#sim-graf svg"); pg.keyboard.press("ArrowRight")
  dica = texto(pg, "#sim-graf .tip"); checa("dica com o mês e as duas opções", "mês 1" in dica and "Opção A" in dica and "Opção B" in dica, dica)
  clica(pg, "#sim-tab-d summary"); escolhe(pg, "#sim-tab-op", "B")
  checa("tabela mês a mês da opção B", js(pg, "document.querySelectorAll('#sim-tab tbody tr').length") == js(pg, "simularTudo().prazo") + 1)
  checa("legenda com as opções", texto(pg, "#sim-leg").count("Opção") == 2)
  clica(pg, ".sim-op[data-op='A'] [data-sim='del-op']")
  checa("apagar A não troca a cor de B", js(pg, "[...document.querySelectorAll('#sim-graf path.sim-l')].map(e => [e.dataset.op, e.getAttribute('stroke')])") == [["B", "var(--viz-b)"]])
  pg.evaluate("cfg.tarifa = 5; render()")   # luz cara: B (3× RTX 5060 num PC novo, pela estimativa) dá prejuízo
  rot = js(pg, "document.querySelector('#sim-graf svg').getAttribute('aria-label')")
  checa("prejuízo: B não se paga, sem NaN no gráfico", "Opção B não se paga" in rot and "NaN" not in js(pg, "document.getElementById('sim-graf').innerHTML"), rot)
  ```
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador.py` → as checagens de `grafico` falham (`#sim-graf` vazio).
- [ ] **Step 3: Implementar** `desenharSim`, a legenda, a dica, a tabela e o CSS (`.k-sim` como `.k-lin`, com `border-top` em `solid`/`dashed`/`dotted`).
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador.py` e `python3 testes/visual.py --fotos <pasta>`; olhar as fotos do Simulador (PC e celular, escuro e claro): rótulos sem encostar, linhas e legenda legíveis.
- [ ] **Step 5: Commit:** `git commit -am "Simulador (1.9.0): gráfico do resultado por opção e a tabela mês a mês"`

### Task 6: Versão 1.9.0, novidades e documentação

**Files:**
- Modify: `mineracao.html` (`NOVIDADES`), `desktop/package.json` e o topo de `desktop/package-lock.json` (1.9.0), `CLAUDE.md`, `testes/visual.py`
- Create: `notas/v1.9.0.md`

**Interfaces:**
- Produces: `NOVIDADES[0] = {v:"1.9.0", itens:["Simulador de compra: monte até 3 opções de placas, com o pagamento à vista, no cartão ou com empréstimo, e veja mês a mês quando elas se pagam em 3 cenários de mercado, com a revenda no fim."]}`.

- [ ] **Step 1: Teste:** em `visual.py`, a checagem da 1.8.2 passa a procurar por versão (`NOVIDADES.find(n => n.v === '1.8.2')`), e entra `checa("novidades da 1.9.0 (simulador) no começo", pg.evaluate("NOVIDADES[0].v === '1.9.0' && /Simulador de compra/.test(NOVIDADES[0].itens[0])"))`.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/visual.py` → falha a da 1.9.0.
- [ ] **Step 3:** Novidades; versões; `notas/v1.9.0.md` no formato de `notas/v1.8.2.md` (novidades em negrito, "Esta versão não muda a parte do Android do app: com o app 1.8.0, o celular recebe o painel novo sozinho.", Como instalar com 1.9.0, rodapé igual); em `CLAUDE.md`, um item "Simulador (1.9.0)" com `cfg.sim`, as funções, a correção (`fatorKx` no retrato, no lugar da margem), `SIM_GRAVA` e `testes/simulador.py` na lista de testes.
- [ ] **Step 4: Rodar tudo:** o `tudo.sh` da 1.8.2 com `simulador` na lista (todos os `testes/*.py`, os testes Node, JUnit, lint e `conferir-nativo.py`) → tudo verde; o teste do aplicativo inteiro (`scratchpad/e2e.sh t190`) comparado com a última rodada (`comparar_e2e.py`): só as diferenças de tempo já conhecidas.
- [ ] **Step 5: Commit e push do branch:** `git commit -am "Versão 1.9.0: simulador de compra" && git push origin simulador-1.9.0`. O `main` só com o OK do Alex.
