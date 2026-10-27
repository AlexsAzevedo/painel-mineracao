# Simulador na web, visual novo e aba Placas: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** a página "Simulador de placas" ganha um resumo no topo, três abas (Simular, Placas, Meus dados), a aba Placas com os preços da pesquisa e links de busca, e o botão Simular que leva a placa para o simulador.

**Arquitetura:** só a casca (`web/simulador-casca.html`) e o gerador (`web/gerar-simulador.py`) mudam. O bloco do simulador continua vindo do `mineracao.html`, sem mudança. O resumo lê `simularTudo()` e é redesenhado depois de cada `renderSimRes` (por um invólucro, como o de `simularOpcao`). A aba Placas usa peças puras do painel que o gerador copia (`OFERTAS`, `lojasBusca`, `urlBuscaFb`...).

**Tecnologia:** HTML, CSS e JS sem biblioteca; Python 3 no gerador; testes com Playwright (Python) em `testes/simulador_web.py`.

**Spec:** `docs/superpowers/specs/2026-10-27-simulador-web-visual-design.md`

## Global Constraints

- **Só a página web muda.** O bloco do simulador no `mineracao.html` fica intocado. O teste `paridade` continua passando. O programa, o app do celular e o painel online não mudam.
- **Tema:** as mesmas variáveis de cor e fontes do painel, no claro e no escuro.
- **Celular** (menos de 900 px): uma coluna, gutter de 16 px, nenhuma rolagem para o lado, abas e botões com pelo menos 44 px de altura.
- **Textos fixos:**
  - abas: "Simular", "Placas", "Meus dados";
  - resumo: "Se paga em {mesSim(m)} (mês {m})", "Não se paga em {P} meses", "No fim ({P} meses): sobram {brl0}" ou "faltam {brl0}", "Lucro no 1º mês: {sinal(lucro1)}";
  - etiquetas: "Se paga primeiro", "Sobra mais no fim";
  - botões e títulos: "+ Opção", "Melhores compras", "Mostrar todas", "Procurar agora", "Nova opção", "Cancelar", "Busca de usadas";
  - avisos: "A luz come o lucro", "Sem preço no Brasil na pesquisa".
- **Conta de uma placa:** ganho = `rec ÷ 365 × 30 × dólar × horas ÷ 24 × real ÷ 100`; luz = `W × horas × 30 ÷ 1000 × luz`; lucro = ganho − luz; se paga em = preço ÷ lucro meses, só com lucro > 0 e preço > 0.
- **Busca de usadas:** `uf` é uma chave de `UF_NOMES` (padrão "SC"); `raio` é inteiro de 10 a 500 km (padrão 100). Valor inválido fica com o anterior; fora da faixa vai para o limite.
- **Termo dos links:** `c.curto` sem "AMD ", "Intel " ou "Huawei " na frente. Todo link externo tem `target="_blank" rel="noopener noreferrer"`.
- **Estado guardado:** `{v:1, t, numeros, pcs, sim, busca:{uf, raio}}`. A aba aberta fica em `localStorage["sim-web-aba"]`, só deste aparelho, com try/catch; a primeira vez é "simular".
- **Publicação:** o mesmo artifact, https://claude.ai/artifact/FTKLDXgvCpffmd7YxNJF5T.

## Review Focus

1. **Gráfico desenhado com a aba escondida** (Simular pela lista no celular): ao abrir a aba Simular, o gráfico tem a largura da tela, sem rolagem para o lado. Teste na Tarefa 4.
2. **Resumo com opções estranhas:** sem placa, sem preço, empréstimo errado, só uma opção com conta (sem etiquetas) ou um empate. Cada quadro diz o que o simulador diz, sem NaN. Teste na Tarefa 2.
3. **Simular pela lista com as 3 opções ocupadas, sem nenhum PC ou numa placa sem preço:** a escolha não oferece "Nova opção"; sem PC a linha vai para "Um PC novo"; sem preço a placa vai sem preço. Teste na Tarefa 4.
4. **Busca de usadas com valores estranhos** ("abc", 5, 9999, estado inexistente): fica o anterior ou o limite, e os links acompanham. Teste na Tarefa 3.
5. **Estado guardado pela versão de antes** (sem `busca`) **e navegador que bloqueia o armazenamento:** abre com os padrões, a aba Simular e nenhum erro. Testes nas Tarefas 1 e 3.

---

### Task 1: Abas, topo e Meus dados

**Files:**
- Modify: `web/simulador-casca.html`
- Test: `testes/simulador_web.py` (`abas(p)` nova; `tela`, `foco_real`, `guardar`, `celular`, `sem_armazenamento` passam a abrir a aba certa antes de ver ou clicar)

**Interfaces:**
- Produces:
  - `ABAS = ["simular", "placas", "dados"]`;
  - `abrirAba(nome: string, foco = false) -> void`: marca `aria-selected`, faz o `tabIndex` andar entre as abas, esconde e mostra os painéis e guarda em `sim-web-aba`; nome inválido vira "simular";
  - abas `#aba-simular`, `#aba-placas`, `#aba-dados` (`role="tab"`, dentro de `.web-abas[role=tablist]`);
  - painéis `#painel-simular` (com a seção `#v-sim`), `#painel-placas` (com `<div id="web-placas"></div>`, vazio até a Tarefa 3) e `#painel-dados` (com `#web-numeros` e `#web-pcs`, classe `web-dados`);
  - um `<section id="web-resumo">` vazio entre o topo e as abas (a Tarefa 2 preenche).

- [ ] **Step 1: Escrever o teste `abas(p)`**
  ```python
  pg = abrir_web(p)
  r = js(pg, "[...document.querySelectorAll('.web-abas [role=tab]')].map(t => [t.id, t.getAttribute('aria-selected'), t.getAttribute('aria-controls'), t.tabIndex])")
  checa("três abas, Simular aberta", r == [["aba-simular", "true", "painel-simular", 0], ["aba-placas", "false", "painel-placas", -1], ["aba-dados", "false", "painel-dados", -1]], r)
  checa("só o painel da aba aberta aparece", visivel(pg, "#v-sim") and not visivel(pg, "#painel-placas") and not visivel(pg, "#web-numeros"))
  pg.focus("#aba-simular"); pg.keyboard.press("ArrowRight")    # → placas
  pg.keyboard.press("End")                                     # → dados
  pg.keyboard.press("ArrowRight")                              # volta para simular
  pg.keyboard.press("ArrowLeft")                               # → dados
  checa("setas, Home e End trocam de aba", js(pg, "document.activeElement.id") == "aba-dados" and visivel(pg, "#web-numeros") and visivel(pg, "#web-pcs"))
  checa("a aba fica guardada neste aparelho", js(pg, "localStorage.getItem('sim-web-aba')") == "dados")
  checa("barra das abas presa no alto", js(pg, "getComputedStyle(document.querySelector('.web-abas')).position") == "sticky")
  pg2 = abrir_web(p, extra="try{ if(!sessionStorage.getItem('__aba')){ localStorage.setItem('sim-web-aba', 'placas'); sessionStorage.setItem('__aba', '1'); } }catch(e){}")
  checa("abre na aba guardada", visivel(pg2, "#painel-placas") and js(pg2, "document.getElementById('aba-placas').getAttribute('aria-selected')") == "true")
  pg3 = abrir_web(p, sem_storage=True)
  checa("sem armazenamento: abre em Simular, sem erro", visivel(pg3, "#v-sim") and not erros(pg3), erros(pg3)[:3])
  ```
  Ajuste os testes de antes: abra Meus dados (`clica(pg, "#aba-dados")`) antes de cliques de verdade e de `visivel` em `#web-numeros`/`#web-pcs`. No `celular`, troque a checagem "um embaixo do outro" por: em cada aba, `document.documentElement.scrollWidth <= innerWidth`; em Meus dados, `#web-numeros` acima de `#web-pcs`; em Simular, as opções A e B uma embaixo da outra; e as abas com 44 px de altura.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador_web.py` → as checagens de `abas` falham.
- [ ] **Step 3: Implementar** a estrutura (topo, `#web-resumo`, `.web-abas`, os três painéis), `abrirAba`, o clique, o teclado (setas com volta, Home, End: movem o foco e abrem a aba) e a aba guardada ao abrir. CSS: as abas como botões de um grupo (o estilo da `.seg` do painel), `position:sticky; top:0` com o fundo `var(--bg)`, 44 px no celular.
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador_web.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador na web: abas Simular, Placas e Meus dados"`

### Task 2: Resumo no topo e o Simular mais caprichado

**Files:**
- Modify: `web/simulador-casca.html`
- Test: `testes/simulador_web.py` (`resumo(p)`)

**Interfaces:**
- Consumes: `abrirAba` (Tarefa 1). Do bloco: `simularTudo`, `renderSimRes`, `mudarSim`, `opcaoVazia`, `SIM_LETRAS`, `SIM_NOMES`, `SIM_CENARIOS`, `mesSim`, `pctSim`, `placasSimTxt`.
- Produces:
  - `renderResumo() -> void`, chamado depois de cada `renderSimRes` (invólucro `renderSimRes = function(){ ...; renderResumo(); }`, como o de `simularOpcao`);
  - `irParaOpcao(L: string, campo = "modelo", i = "0") -> void`: abre Simular e põe o foco em `.sim-op[data-op=L] [data-campo=campo][data-i=i]`, rolando até ele;
  - quadros `#web-quadros .web-quadro[data-op=L]` (botões), `.web-quadro-mais` e as etiquetas `.web-etq`;
  - botões de cenário `[data-cen-res=estavel|devagar|rapido]` com `aria-pressed`.

- [ ] **Step 1: Escrever o teste `resumo(p)`**, com o estado `{v:1, t:1, pcs: PCS_PAR, sim: SIM_PAR}`. O texto esperado vem de `simularTudo()` na própria página: os números são do simulador, e o teste confere o que o resumo escreve.
  ```python
  pg = abrir_web(p, estado={"v": 1, "t": 1, "pcs": PCS_PAR, "sim": SIM_PAR})
  esperado = js(pg, """(() => { const T = simularTudo(), k = T.s.cenarioGrafico; return T.ops.map(r => { const f = r.cen[k];
      return [r.nome, placasSimTxt(r), f.sePaga != null ? `Se paga em ${mesSim(f.sePaga)} (mês ${f.sePaga})` : `Não se paga em ${T.prazo} meses`,
        `No fim (${T.prazo} meses): ${f.fim.resultado >= 0 ? 'sobram' : 'faltam'} ${brl0(Math.abs(f.fim.resultado))}`, `Lucro no 1º mês: ${sinal(r.bruto1 - r.min.luz)}`]; }); })()""")
  quadros = js(pg, "[...document.querySelectorAll('#web-quadros .web-quadro')].map(e => [e.dataset.op, e.innerText])")
  checa("um quadro por opção, com a resposta do simulador", [q[0] for q in quadros] == ["A", "B", "C"] and all(all(x in q[1] for x in e[1:]) for q, e in zip(quadros, esperado)), [quadros, esperado])
  ```
  E as outras checagens:
  - as etiquetas: "Se paga primeiro" no quadro com o menor `sePaga` e "Sobra mais no fim" no de maior `fim.resultado`, calculados na página como acima;
  - num empate (A e B iguais), as duas etiquetas nos dois;
  - com uma opção só com conta, nenhuma etiqueta;
  - uma opção sem placa mostra "Escolha uma placa para ver as contas.";
  - o botão `[data-cen-res=rapido]`: `cfg.sim.cenarioGrafico == "rapido"`, o botão com `aria-pressed="true"`, `#sim-cen` com o valor "rapido", os quadros com os números do cenário rápido e, 2,5 s depois, o `sim-web` guardado com `cenarioGrafico` "rapido";
  - com 2 opções aparece `.web-quadro-mais`; tocar nele dá 3 opções, a aba Simular aberta e o foco em `.sim-op[data-op="C"] [data-campo="modelo"]`;
  - tocar no quadro B estando em Placas abre Simular com o foco no modelo da primeira placa de B;
  - mudar o rendimento real em Meus dados muda o "Lucro no 1º mês" do quadro;
  - nenhum NaN, Infinity ou undefined em `#web-resumo`.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador_web.py` → as checagens de `resumo` falham.
- [ ] **Step 3: Implementar** o resumo, os botões de cenário (pelo `mudarSim(s => { s.cenarioGrafico = k; })`), as etiquetas, o "+ Opção" (como o `add-op` do bloco) e `irParaOpcao`.
  - CSS do resumo: quadros com a faixa na cor da opção, a resposta em Sora grande e as etiquetas em pílula.
  - CSS do Simular, só na casca: "Compra" e "Lucro no 1º mês" (`.sim-resumo span`) como dois números em destaque; cada `.sim-cen` como bloco com borda e fundo `var(--sunk)`, com o "Se paga em…" (`.sim-cen p:nth-child(2) b`) maior.
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador_web.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador na web: resumo das opções no topo e o resultado mais caprichado"`
- [ ] **Step 6: Fotos para o Alex** (pedido dele, antes de seguir): Simular e Meus dados, no PC (1366×900) e no celular (390×844), no claro e no escuro, com as três opções do `SIM_PAR`.
  - Conferir a olho e mandar com `SendUserFile`.
  - **Esperar o OK dele antes da Tarefa 3.** Ajustes que ele pedir entram aqui, com teste quando mudam comportamento.

### Task 3: Aba Placas: lista, preços, links e busca de usadas

**Files:**
- Modify: `web/gerar-simulador.py`, `web/simulador-casca.html`
- Test: `testes/simulador_web.py` (`placas(p)` nova; `gerar(p)` com as peças novas)

**Interfaces:**
- Consumes: `abrirAba` (Tarefa 1). Do painel: `mercado`, `byId`, `CATALOGO`, `MERCADO`, `brl0`, `n1`, `esc`.
- Produces:
  - no gerador:
    - `const_linha` para `UF_NOMES`, `semAcento`, `soMineracao`, `NOTEBOOK`, `deNotebook`, `buscaShopping` e `urlBuscaOlx`;
    - `const_bloco("OFERTAS")` e `funcao("lojasBusca")`;
    - um extrator novo, `const_ate_pv(t, nome) -> str`: do `^const nome =` até a primeira linha que termina em `;` (com comentário depois ou não), usado para `urlBuscaFb`. Falta → `Falta`.
  - na casca:
    - `contaPlaca(c) -> {ganho, luz, lucro, usado, n, novo, loja, menor, meses:{usado, novo, menor}}`, com `null` onde não tem;
    - `termoBusca(c) -> string`;
    - `linksPlaca(c) -> {usadas: [[nome, url]...], novas: [[nome, url]...], oferta: [onde, url] | null}`, com as usadas na ordem Marketplace, OLX e as novas na ordem Kabum, Pichau, Terabyte, Mercado Livre, Google Shopping;
    - `var busca = {uf:"SC", raio:100}` e `buscaOk(o) -> {uf, raio}`;
    - `renderPlacas() -> void`;
    - os filtros `#pl-busca`, `#pl-marca`, `#pl-teto`, `#pl-ordem` (`retorno|lucro|preco|consumo`) e `#pl-todas` (checkbox "Mostrar todas");
    - `#web-melhores li[data-id]` e `#web-lista .web-placa[data-id]` (cada um com `[data-simular]` e `details.web-procurar`);
    - em Meus dados, `#web-busca` com `[data-busca=uf]` (select) e `[data-busca=raio]` (número).
  - `busca` entra em `estadoJson`, `conteudo`, `estadoOk` (`buscaOk(e.busca)`) e `aplicarEstado`. Mudar a busca chama `marcarMudanca()` e `agendarSalvar()`.

- [ ] **Step 1: Escrever os testes.** Em `gerar(p)`: o HTML leva `const OFERTAS`, `function lojasBusca`, `const urlBuscaFb`, `const UF_NOMES`. Com `copia_sem("function lojasBusca(")`, o gerador sai com 1 e diz "não achei". Em `placas(p)`, com os números iniciais:
  ```python
  pg = abrir_web(p); clica(pg, "#aba-placas")
  g = 1564/365*30*5.42*24/24*74/100; l = 160*24*30/1000*0.96
  c = js(pg, "contaPlaca(byId['rtx-5070'])")
  checa("conta da placa", perto(campo(c, "ganho"), g, 1e-9) and perto(campo(c, "luz"), l, 1e-9) and perto(campo(c, "lucro"), g - l, 1e-9)
        and campo(c, "usado") == 5600 and campo(c, "n") == 2 and campo(c, "novo") == 5159 and campo(c, "loja") == "Guerra Digital"
        and perto(campo(c, "meses", "menor"), 5159/(g - l), 1e-9), c)
  dados = js(pg, "CATALOGO.map(c => [c.id, c.curto, c.marca, c.w, c.rec, (MERCADO.precos[c.id] || {}).usado || 0, (MERCADO.precos[c.id] || {}).novo || 0, soMineracao(c) || deNotebook(c)])")
  ```
  A partir de `dados`, o Python calcula o esperado e confere:
  - as 5 `#web-melhores li` (ids na ordem);
  - quantos itens a lista mostra no padrão; com `#pl-todas`, 102, com as etiquetas "notebook" e "só mineração";
  - a busca "5070" (só nomes com 5070), a marca AMD, o "preço até" 3000 (menor preço ≤ 3000);
  - cada ordem: lucro decrescente, menor preço crescente, menor consumo crescente e o padrão em meses crescentes, com sem preço e sem lucro no fim.

  O texto da RTX 5070 traz "Usada R$ 5.600 (2 anúncios)", "Nova R$ 5.159 (Guerra Digital)" e "se paga em {n1(meses)} meses". Uma placa de lucro ≤ 0 diz "A luz come o lucro"; uma sem preço, com "Mostrar todas", diz "Sem preço no Brasil na pesquisa". Os links da RTX 5070 (os `href` em `details.web-procurar`, todos com `target="_blank"` e `rel="noopener noreferrer"`):
  ```python
  ["https://www.facebook.com/marketplace/category/search/?query=RTX%205070&exact=false&radius=100", "https://www.olx.com.br/estado-sc?q=RTX%205070",
   "https://www.kabum.com.br/busca/rtx-5070", "https://www.pichau.com.br/search?q=RTX%205070", "https://www.terabyteshop.com.br/busca?str=RTX+5070",
   "https://lista.mercadolivre.com.br/rtx-5070", "https://www.google.com/search?tbm=shop&q=placa%20de%20v%C3%ADdeo%20RTX%205070",
   "https://promotech.app.br/comparar/placa-de-video/rtx-5070-vs-rtx-5090"]
  ```
  Mais:
  - `termoBusca(byId['amd-rx-9070-xt']) == "RX 9070 XT"`;
  - em Meus dados, estado "PR" e raio "50": os links passam a `estado-pr` e `radius=50`, e o `sim-web` guardado traz `busca == {"uf": "PR", "raio": 50}`;
  - raio "abc", ao sair do campo, mostra o anterior; "5" vira 10; "9999" vira 500; `buscaOk({uf:"XX"}).uf` é o anterior;
  - um estado guardado sem `busca` abre com SC e 100, sem erro;
  - a nota da aba traz "22/10/2026" e "no Simular entram a fonte e o resto do PC";
  - nenhum NaN, Infinity ou undefined na aba.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador_web.py` → as checagens novas falham.
- [ ] **Step 3: Implementar** as peças no gerador, as funções da casca, a lista, as Melhores compras, os filtros e a ordem (só nesta visita, não guardados), os links e a Busca de usadas.
  - CSS: no PC, cada placa numa linha em grade (nome e consumo | ganho, luz e lucro | usada | nova | Simular); no celular, um cartão por placa.
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador_web.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador na web: aba Placas com os preços da pesquisa, links de busca e a busca de usadas"`

### Task 4: Simular pela lista

**Files:**
- Modify: `web/simulador-casca.html`
- Test: `testes/simulador_web.py` (`simular_lista(p)`)

**Interfaces:**
- Consumes: `abrirAba`, `irParaOpcao` (Tarefas 1 e 2), `contaPlaca`, `renderPlacas` (Tarefa 3). Do bloco: `mudarSim`, `opcaoVazia`, `simCfg`, `renderSim`, `SIM_LETRAS`.
- Produces:
  - `simularPlaca(id: string, onde: "A"|"B"|"C"|"nova", preco: number|null) -> string` (a letra usada);
  - a escolha `.web-escolha` dentro da placa, com os rádios `[data-esc-preco]` (o valor é o preço; "" quando não tem) e os botões `[data-esc-op=A|B|C|nova]` e `[data-esc-cancelar]`.

- [ ] **Step 1: Escrever o teste `simular_lista(p)`**:
  - tocar em `[data-simular]` da RTX 5060 abre `.web-escolha` com os rádios Usada R$ 2.600 (marcado: o menor) e Nova R$ 2.665, e os botões "Opção A" e "Nova opção";
  - marcar Nova e tocar em "Opção A" (que só tem a linha vazia) dá `simCfg().opcoes[0].placas == [{modelo:"rtx-5060", qtd:1, preco:2665, maq:"pc-pessoal"}]`, com a aba Simular aberta e o foco em `.sim-op[data-op="A"] [data-campo="qtd"][data-i="0"]`;
  - a RTX 5070 na Opção A vira a 2ª linha, com o mesmo PC da 1ª e o preço 5159;
  - "Nova opção" cria a B com a placa;
  - com 3 opções, a escolha não tem "Nova opção";
  - Cancelar fecha sem mudar `cfg.sim`;
  - uma placa sem preço (com "Mostrar todas") entra com `preco` null;
  - com `pcs = []` (todos os PCs removidos em Meus dados), a linha nova vai para "novo";
  - 2,5 s depois, o `sim-web` guardado tem as linhas;
  - no celular (390×844), Simular pela lista e depois `document.documentElement.scrollWidth <= innerWidth`, com a largura do `#sim-graf svg` até a do `#sim-graf`.
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/simulador_web.py` → as checagens de `simular_lista` falham.
- [ ] **Step 3: Implementar** `simularPlaca` dentro de um `mudarSim`, seguindo a regra da spec (só a linha vazia → entra nela; senão mais uma linha com o PC da última; opção nova pela `opcaoVazia` da letra livre).
  - Depois: `abrirAba("simular")` antes de `renderSim(true)`, para o gráfico já sair com a largura certa, e `irParaOpcao(L, "qtd", i)`.
  - A escolha abre e fecha dentro da placa, e Esc também fecha.
- [ ] **Step 4: Rodar e ver passar:** `python3 testes/simulador_web.py` → `"falhas": []`.
- [ ] **Step 5: Commit:** `git commit -am "Simulador na web: Simular pela lista de placas"`

### Task 5: Fotos, documentação e publicação

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1:** No item "Simulador na web" do `CLAUDE.md`: o resumo, as abas (`sim-web-aba`), a aba Placas (a conta rápida, os preços da pesquisa, os links e `busca`) e as peças novas que o gerador copia.
- [ ] **Step 2: Rodar:** `python3 web/gerar-simulador.py`, `python3 testes/simulador_web.py`, `python3 testes/simulador.py` e `python3 testes/visual.py` → todos com `"falhas": []`.
- [ ] **Step 3: Fotos:** as três abas, no PC e no celular, no claro e no escuro. Conferir a olho.
- [ ] **Step 4: Publicar** `web/dist/simulador.html` no mesmo artifact (o mesmo `file_path` desta conversa, ou a `url` dele) e mandar as fotos ao Alex.
- [ ] **Step 5: Commit e push do branch:** `git commit -am "Simulador na web: documentação do visual novo e da aba Placas" && git push origin simulador-web-2`. Juntar no `main` só com o OK do Alex.
