# Simulador de placas na web: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** uma página própria (artifact novo e privado) só com o Simulador do programa, com "Seus números" e "Seus PCs" no lugar dos dados do PC, dando os mesmos resultados que o programa.

**Arquitetura:** `web/gerar-simulador.py` monta `web/dist/simulador.html` juntando a casca `web/simulador-casca.html` com peças tiradas do `mineracao.html` (catálogo, preços, curva da fonte, formatos, cores, o CSS e o bloco JS do simulador e a seção `#v-sim`). A casca define o que o bloco do simulador espera do painel (`cfg`, `calcMaq`, `maqsReais`…), adaptado aos PCs digitados, e guarda o estado. Nenhuma conta é reescrita: as do programa são as mesmas, por construção.

**Tecnologia:** Python 3 (gerador), HTML/CSS/JS sem biblioteca, testes com Playwright e `testes/apoio.py`.

**Especificação:** `docs/superpowers/specs/2026-10-27-simulador-web-design.md` (e, para as contas, `docs/superpowers/specs/2026-10-26-simulador-de-compra-design.md`).

## Global Constraints

- Textos em português do Brasil. Título da página: "Simulador de placas". Rodapé e textos do simulador: os do programa.
- Valores iniciais exatos: dólar 5,42; luz 0,96 R$/kWh; 24 h; rendimento real 74%; CDI 13,65%; 120% do CDI; desvalorização 25% ao ano. PCs: `{id:"pc-pessoal", nome:"PC pessoal", fonteW:1000, selo:"Platinum", jaGasta:360}`, `{id:"pc-i5", nome:"PC extra (i5-13400)", fonteW:500, selo:"Bronze", jaGasta:0}`, `{id:"pc-i7", nome:"PC extra (i7-8700)", fonteW:500, selo:"Bronze", jaGasta:0}`.
- Limites: dólar 0,5 a 50; luz 0 a 10; horas 0 a 24; rendimento real 20 a 200; CDI 0 a 100; % do CDI 0 a 300; desvalorização 0 a 90; fonte 100 a 5000 W; já gasta 0 a 5000 W; nome até 40 caracteres. Vazio ou inválido = o valor de antes.
- PC: `jaGasta > 0` = ligado (soma as placas novas); `0` = desligado (placas + 40 W). Tomada de 220 V. "Um PC novo" é o `maqNovaSim` do bloco.
- Contrato do artifact: o arquivo gerado não tem `<!doctype>`, `<html>`, `<head>` nem `<body>`; `<title>` e `<style>` no começo; `<meta name="claude:viewport-fit-sides" content="cover">` com `padding-left/right: max(16px, env(safe-area-inset-left/right, 0px))` no `body`; cores só por variáveis: as do painel, claras no `:root`, escuras em `@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){…}}` e em `:root[data-theme="dark"]{…}`; `body` com fundo explícito; fontes só do Google Fonts (Sora, Inter, JetBrains Mono), com fallback.
- Guardar: o estado `{v:1, numeros, pcs, sim}` no banco da página (capacidade `db`, conforme a skill `artifact-capabilities`), com o `localStorage` (`"sim-web"`) como reserva; todo acesso a armazenamento em try/catch. `SIM_GRAVA = 2e3`.
- Não mexer nas contas nem na tela do simulador do programa. A única mudança no `mineracao.html` é o comentário `/* fim do simulador de compra */` fechando o CSS do simulador. `web/dist/` vai para o `.gitignore`.
- Lição da revisão da 1.9.0: um campo que perde o foco não pode montar de novo a parte da tela onde está o próximo clique.

## Review Focus

1. **O painel mudou de lugar uma peça** (marcador, função ou `const` renomeados): o gerador tem de parar com "não achei <peça> no painel", nunca gerar meia página. Teste na Tarefa 1.
2. **Número digitado pela metade ou estranho** em "Seus números" e "Seus PCs" (vazio, "5,42" com vírgula, negativo, letras): nada de NaN; ao sair do campo, ele mostra o valor que vale. Testes nas Tarefas 2 e 3.
3. **PC removido ou renomeado** que uma opção usa: a opção passa a "Um PC novo" com o aviso do programa; o nome novo aparece na lista "Em qual PC". Teste na Tarefa 3.
4. **Sem onde guardar** (sem o banco da página, navegador bloqueando o armazenamento): a página abre com os valores iniciais, funciona e não mostra erro. Teste na Tarefa 3.
5. **Programa e página se afastando** (alguém muda as contas do simulador do programa): o teste de comparação pega. Teste na Tarefa 2.

---

### Task 1: Gerador e casca mínima

**Files:**
- Create: `web/gerar-simulador.py`, `web/simulador-casca.html`, `testes/simulador_web.py`
- Modify: `mineracao.html` (comentário de fim no CSS do simulador), `.gitignore` (`web/dist/`)

**Interfaces:**
- Produces: `python3 web/gerar-simulador.py [--painel <mineracao.html>] [--saida <arquivo>]` (padrões: o `mineracao.html` do repositório e `web/dist/simulador.html`); imprime `gerado: <saída> (<N> KB)`; sai com 1 e `não achei <peça> no painel` se faltar qualquer peça. Peças: `const` de uma linha `CATALOGO_RAW, marcaDe, nomeCompleto, slug, CATALOGO, LEGADO, novoId, byId, brl, brl0, n1, $, isoLocal, hojeISO, sinal, esc, SELOS, CARGAS, CPU_PARADO`; `const MERCADO` (várias linhas, até `}};`); funções `eficiencia, somaMesesIso, mesAnoIso, mercado, melhorPreco` (uma linha, ou até a linha `}`); o JS entre `/* ---------- simulador de compra ----------` e `/* ---------- carga inicial ---------- */`; o CSS entre `/* simulador de compra: as opções lado a lado` e `/* fim do simulador de compra */`; a `<section class="view" id="v-sim"` até o `</section>` dela; e as declarações dos blocos `:root{` (escuro) e `:root[data-tema="claro"]{` (claro), postas no formato do contrato (o `:root` leva as escuras e por cima as claras, para ter também as fontes). Marcadores na casca: `/*@@CORES@@*/`, `/*@@CSS_SIM@@*/`, `<!--@@TELA@@-->`, `/*@@PAINEL@@*/`, `/*@@SIMULADOR@@*/`, nesta ordem no arquivo (o script vai no fim, depois do HTML).
- Testes: `rodar_gerador(painel=None, saida=SAIDA) -> subprocess.CompletedProcess`; `copia_sem(trecho) -> str` (uma cópia temporária do `mineracao.html` sem o `trecho`); um servidor local da pasta de `SAIDA`, no padrão de `testes/mensagens_app.py`; `abrir_web(p, largura=1366, altura=900, estado=None, sem_storage=False) -> Page` (semeia `localStorage["sim-web"]` com `estado`; relógio e erros como no `abrir` do `apoio.py`); e os ajudantes `js`, `campo`, `perto`, `texto`, `visivel`, `existe`, `clica`, `preenche`, `escolhe`, `valor` iguais aos de `testes/simulador.py`.

- [ ] **Step 1: Antes de escrever a página**, chamar `Artifact` com `action:"quickstart"`, `intent:"other"`, e ler a orientação de página que ele devolve; carregar a skill `artifact-capabilities` (para o `db` da Tarefa 3).
- [ ] **Step 2: Escrever o teste** `gerar(p)`:
  ```python
  checa("gera a página", os.path.exists(SAIDA) and "gerado:" in r.stdout)
  html = open(SAIDA, encoding="utf-8").read()
  checa("leva o simulador do painel", all(x in html for x in ['id="v-sim"', "function fluxoSim", "const CATALOGO_RAW", "--viz-a", ".sim-op{"]))
  checa("contrato do artifact", not re.search(r"<!doctype|<html|<head|<body", html, re.I) and html.lstrip().startswith("<title>Simulador de placas</title>"))
  pg = abrir_web(p); checa("abre sem erros, com o simulador à mostra", visivel(pg, "#v-sim") and not erros(pg), erros(pg)[:3])
  # o painel sem o marcador do bloco JS: o gerador para e diz o que faltou
  r = rodar_gerador(painel=copia_sem("/* ---------- simulador de compra ----------"))
  checa("peça faltando: para com aviso", r.returncode == 1 and "não achei" in r.stdout + r.stderr)
  ```
- [ ] **Step 3: Rodar e ver falhar:** `python3 testes/simulador_web.py` → falha (o gerador não existe).
- [ ] **Step 4: Implementar** o gerador, a casca mínima (as peças que o bloco precisa existindo como na Tarefa 2, mesmo que simples) e o comentário de fim no CSS do simulador.
- [ ] **Step 5: Rodar e ver passar:** `python3 testes/simulador_web.py` e `python3 testes/visual.py` (o comentário no painel não muda nada) → `"falhas": []`.
- [ ] **Step 6: Commit:** `git add web testes/simulador_web.py mineracao.html .gitignore && git commit -m "Simulador na web: gerador e casca"`

### Task 2: O que o simulador espera do painel, e a comparação com o programa

**Files:**
- Modify: `web/simulador-casca.html`
- Test: `testes/simulador_web.py` (`contas(p)`, `paridade(p)`)

**Interfaces:**
- Consumes: o bloco do simulador (`simularTudo`, `simularOpcao`, `maqNovaSim`, `fatorSim`, `SIM_GRAVA`…).
- Produces (na casca, antes do bloco): `NUMEROS_PADRAO`, `PCS_PADRAO` (Global Constraints); `var numeros`, `var pcs`; `numerosOk(o) -> numeros` e `pcsOk(l) -> pcs` (convertem, limitam, guardam o anterior quando inválido; `pcsOk` sem PC devolve `[]`, ids repetidos ficam só o primeiro); `aplicarNumeros()` (põe em `cfg`: `dolar`, `tarifa = luz`, `bandeira: 0`, `horas`, `margem: 0`, `cdi`, `pctCdi`, `deprec`, e `kxaSnap = {v:1, fatorKx: real/100, placas:[]}`); `var cfg = {…, cotacoes:{}, precosAtual:{}, historico:{}, sim:{}}`; `var anuncios = []`; `PODE_KXA = () => false`; `kxa = {leitura:null}`; `nomePlaca = p => p && p.nome || "a placa"`; `acharModelo = () => null`; `dados = c => c`; `maqBase(o) -> {...o}`; `maqsReais() -> pcs` como máquinas `{id, nome, fonteW, selo, jaGasta}`; `deprecModelo(id) -> {d: deprec/100, fonte:"premissa", dias:0}`; `calcMaq(m, {extra}) -> {gpus, n, dc, carga, ef, tomada, kwh, luz, brutoGpu, bruto, ligada, fonte:{w, selo}}`: `dc` = (`jaGasta > 0` ? `jaGasta` : 40) + Σ `c.w × q` das extras, 0 se desligado e sem extras; `ef = eficiencia(selo, dc/fonteW, 220)`; `luz = dc/ef × horas × 30/1000 × tarifa`; `brutoGpu` = Σ `c.rec × q` das extras × 30/365 × dólar × horas/24 (as placas que o PC já tem não entram: o simulador usa a diferença); `gravarCfg()` (aqui só chama `salvarEstado`, da Tarefa 3; até lá, nada).

- [ ] **Step 1: Escrever os testes.** `contas(p)`, com a página nos valores iniciais:
  ```python
  ef = lambda selo, carga: js(pg, f"eficiencia('{selo}', {carga}, 220)")
  r = js(pg, "calcMaq(maqsReais()[0], {extra:[{tipo:'plano', c:byId['rtx-5070'], q:2, preco:5159}]})")
  checa("PC ligado: soma as placas ao que já gasta", r["dc"] == 680 and abs(r["luz"] - 680/ef("Platinum", 0.68)*24*30/1000*0.96) < 1e-9)
  r = js(pg, "calcMaq(maqsReais()[1], {extra:[{tipo:'plano', c:byId['rtx-5060'], q:2, preco:2600}]})")
  checa("PC desligado: placas + 40 W", r["dc"] == 240 and r["ligada"])
  checa("desligado e sem placas: não gasta", js(pg, "calcMaq(maqsReais()[1]).luz") == 0)
  checa("bruto das placas novas (sem margem)", abs(js(pg, "calcMaq(maqsReais()[0], {extra:[{tipo:'plano', c:byId['rtx-5070'], q:2, preco:5159}]}).brutoGpu") - 2*1564*30/365*5.42) < 1e-9)
  checa("correção pelo real digitado", js(pg, "fatorSim()") == {"f": 0.74, "fonte": "real", "placas": []})
  checa("revenda com 25% ao ano", js(pg, "deprecModelo('rtx-5060').d") == 0.25)
  r = js(pg, "numerosOk({dolar:'abc', luz:-1, real:500, horas:30, cdi:'', pctCdi:120})")
  checa("números estranhos: limita ou guarda o anterior", r["dolar"] == 5.42 and r["luz"] == 0 and r["real"] == 200 and r["horas"] == 24 and r["cdi"] == 13.65)
  ```
  `paridade(p)`: o mesmo `cfg.sim` (A: 2× `rtx-5070` a 5159 no PC ligado, cartão 12×, empréstimo 10000/20/674,65; B: 3× `rtx-5060` sem preço no "Um PC novo", custo 1500; C: 2× `rtx-5060` a 2600 no PC desligado) no programa, com `abrir(p, dados=…)`: `cfg` com dólar 5,42, tarifa 0,96, bandeira 0, 24 h, `margem: 26` (sem leitura, o programa usa 1 − 26% = 74%), CDI 13,65, 120%, `deprec: 25`; `min-setup` com `m-pc` (1000 W Platinum, base 30, `cpu:"outro"`, a RX 9070 XT de `PLACAS` nele: 360 W) e `m-ext` (500 W Bronze, base 30, sem placa); e na página, com `pcs` `m-pc` (1000 W Platinum, 360 W) e `m-ext` (500 W Bronze, 0 W). Para cada opção: `ok`, `preco`, `bruto1`, `min.luz`, os textos de `avisos`, os juros, e em cada cenário `sePaga`, `fim.resultado`, `fim.comRevenda`, `pior.m`, `pior.conta`: iguais (números com diferença < 1e-6).
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador_web.py` → as checagens de `contas` e `paridade` falham.
- [ ] **Step 3: Implementar** o Produces na casca.
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador_web.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador na web: as peças do painel adaptadas aos PCs digitados, iguais ao programa"`

### Task 3: Seus números, Seus PCs e guardar

**Files:**
- Modify: `web/simulador-casca.html`
- Test: `testes/simulador_web.py` (`tela`, `guardar`, `celular`, `sem_armazenamento`, `foco_real`)

**Interfaces:**
- Consumes: Tarefa 2 (`numeros`, `pcs`, `numerosOk`, `pcsOk`, `aplicarNumeros`), o bloco (`renderSim`, `renderSimRes`, `simCfg`).
- Produces: cabeçalho da casca (`h1` "Simulador de placas" e um subtítulo curto; o cabeçalho `.vh` da seção `#v-sim` fica escondido) e, antes da seção, `#web-numeros` (campos `input[data-num=dolar|luz|horas|real|cdi|pctCdi|deprec]`, com rótulos e unidade: "Dólar (R$)", "Luz (R$ por kWh, com a bandeira)", "Horas por dia", "Rendimento real (% da estimativa da Kryptex)", "CDI (% ao ano)", "% do CDI", "Desvalorização das placas (% ao ano)") e `#web-pcs` (uma linha por PC com `[data-pc=<id>][data-campo=nome|fonteW|selo|jaGasta]`, `selo` com as chaves de `SELOS`, o botão `[data-pc-del=<id>]` e `#web-pc-add` "+ PC"; a dica "0 W = desligado"). `input` → muda `numeros`/`pcs` → `aplicarNumeros()` → `renderSimRes()` (números) ou `renderSim()` (PCs) → agenda guardar; `change` → só arruma o próprio campo (o valor que vale), sem montar de novo. `carregarEstado() -> Promise<{numeros, pcs, sim}>` e `salvarEstado() -> Promise<void>` (Global Constraints); `gravarCfg = salvarEstado`; `SIM_GRAVA = 2e3` depois do bloco; as mudanças em "Seus números" e "Seus PCs" gravam 2 s depois da última, e ao esconder a página (`visibilitychange` e `pagehide`) grava já o que estava esperando; ao abrir, `$("v-sim").hidden = false` e `renderSim()`.

- [ ] **Step 1: Escrever os testes** (página servida pelo teste; sem banco, vale o `localStorage`):
  - `tela(p)`: os campos de `#web-numeros` mostram 5.42, 0.96, 24, 74, 13.65, 120, 25; `#web-pcs` tem os 3 PCs; a lista "Em qual PC" da opção A tem os 3 nomes e "Um PC novo"; escolher `rtx-5070` × 2 no "PC pessoal" → o texto da opção tem "Lucro da mineração no 1º mês"; mudar o rendimento real para 50 → o `bruto1` de A cai para 50/74 do de antes; mudar a luz para 1,2 → a luz de A sobe 1,2/0,96; renomear o PC pessoal para "Gamer" → a lista da opção mostra "Gamer"; remover o "Gamer" → a opção A avisa "não existe mais"; "+ PC" → aparece uma linha nova e o PC entra na lista; `innerText` sem "NaN", "Infinity" nem "undefined"; sem erros.
  - `foco_real(p)` (cliques e teclas de verdade): clicar no dólar, digitar "5,6" e clicar na luz → o foco está na luz e `numeros.dolar == 5.6`; digitar "-3" na luz e apertar Tab → o campo mostra "0"; digitar no "já gasta" de um PC e clicar no `select` de placa da opção A → o foco está no `select`.
  - `guardar(p)`: mudar o rendimento real e esperar 2,5 s → `localStorage["sim-web"]` tem `numeros.real` novo; abrir de novo com esse estado → o campo e a conta vêm iguais; a opção montada também volta.
  - `celular(p)` (390×844): sem rolagem para o lado; `#web-numeros`, `#web-pcs` e as opções uma embaixo da outra; campos com 44 px de altura.
  - `sem_armazenamento(p)` (o `Storage` lançando erro, como em `apoio._SEM_STORAGE`): abre com os valores iniciais, monta uma opção e não mostra erro.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador_web.py` → as checagens novas falham.
- [ ] **Step 3: Implementar** o Produces (o `db` conforme a skill `artifact-capabilities`).
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador_web.py` → `"falhas": []`; fotos da página (PC e celular, claro e escuro) conferidas a olho.
- [ ] **Step 5: Commit:** `git commit -am "Simulador na web: Seus números, Seus PCs e guardar"`

### Task 4: Documentação e publicação

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1:** No `CLAUDE.md`, um item "Simulador na web": o que é, `python3 web/gerar-simulador.py`, `python3 testes/simulador_web.py`, e que se publica de novo no mesmo artifact (com a `url` dele) depois de mudar o simulador do programa. Na lista de testes, `testes/simulador_web.py`.
- [ ] **Step 2: Rodar:** `python3 web/gerar-simulador.py`, `python3 testes/simulador_web.py`, `python3 testes/simulador.py`, `python3 testes/visual.py` → tudo verde.
- [ ] **Step 3: Publicar** `web/dist/simulador.html` como artifact novo (`icon: "calculator"`, descrição de uma frase) e anotar a `url` no item do `CLAUDE.md`.
- [ ] **Step 4: Commit e push do branch:** `git commit -am "Simulador na web: documentação e link" && git push origin simulador-web`. Juntar no `main` só com o OK do Alex (não publica versão: o `desktop/package.json` não muda).
