# Simulador de placas na web: visual novo e a aba Placas

Data: 27/10/2026 · Pedido do Alex: "melhorar o design da página, deixar mais apresentável; se puder também pôr a busca por placas de vídeo novas e usadas".

## O que o Alex escolheu

- **Busca:** a lista de placas com os preços da pesquisa e links que abrem a busca nos sites, e não anúncios de agora dentro da página.
- **Organização:** um resumo no topo e três abas.
- **Caminho:** só a página web muda. O simulador continua vindo do programa: as mesmas contas, com o teste que compara as duas.
- As Partes 1 (topo, abas e visual) e 2 (lista, links e Simular) foram aprovadas como estão abaixo.

## Critérios de pronto

1. No topo, um quadro por opção com a resposta no cenário escolhido: quando se paga, quanto sobra ou falta no fim e o lucro do 1º mês. Duas etiquetas: "Se paga primeiro" e "Sobra mais no fim".
2. Três abas: Simular, Placas e Meus dados. Funcionam com o teclado e o leitor de tela, e a página lembra a última aba em cada aparelho.
3. A aba Placas lista as placas com os preços da pesquisa (usada e nova), em quantos meses cada uma se paga, o botão Simular e os links de busca.
4. O botão Simular põe a placa na opção escolhida, com o preço escolhido, e abre a aba Simular nela.
5. As contas do simulador continuam iguais às do programa: o teste de comparação continua passando.
6. Funciona no PC e no celular, nos temas claro e escuro, sem rolagem para o lado e sem NaN, Infinity ou undefined na tela.
7. O programa, o app do celular e o painel online não mudam.

## Fora desta versão

- Anúncios de agora dentro da página: a página só abre a busca nos sites.
- Atualizar os preços da pesquisa: eles vêm do painel e mudam quando o painel muda e a página é gerada de novo.
- O veredito "vale a pena": o programa usa "recuperar em N meses", que a página não tem.

## 1. Topo e resumo

- Título "Simulador de placas", uma linha que explica a página e o aviso de onde fica guardado (o que já existe).
- **Resumo:** um quadro por opção, na ordem A, B, C, com a faixa de cima na cor da opção (`--viz-a/b/c`).
  - Cada quadro mostra as placas (por exemplo, "2× RTX 5070") e, em letra grande, "Se paga em mar/2028 (mês 17)" ou "Não se paga em 20 meses". Embaixo vêm "No fim (20 meses): sobram R$ 3.013" (ou "faltam") e "Lucro no 1º mês: +R$ 793".
  - Uma opção sem conta mostra o texto do simulador ("Escolha uma placa para ver as contas.", "Falta o preço da…", os do empréstimo).
- **Cenário:** acima dos quadros, três botões (Estável, Caindo devagar, Caindo rápido, cada um com o seu % ao mês). Eles mudam o mesmo cenário do gráfico (`cfg.sim.cenarioGrafico`), que fica guardado.
- **Etiquetas:** só com duas opções ou mais com conta. "Se paga primeiro" vai na que se paga no mês mais cedo e "Sobra mais no fim" na de maior resultado no fim. Num empate, a etiqueta vai para todas as empatadas.
- Tocar num quadro abre a aba Simular naquela opção, com o cursor na primeira placa dela.
- Com menos de 3 opções, aparece um quadro "+ Opção", que cria a próxima e abre a aba Simular nela.
- O resumo acompanha cada mudança no simulador, nos seus números e nos seus PCs.

## 2. Abas

- Três abas: **Simular**, **Placas** e **Meus dados**.
  - Seguem o padrão de abas para o leitor de tela (`tablist`, `tab`, `tabpanel`).
  - No teclado, as setas para a esquerda e para a direita, Home e End trocam de aba.
- A barra das abas fica presa no alto ao rolar a página.
- A aba aberta fica guardada só neste aparelho (`localStorage` `sim-web-aba`, que pode faltar sem dar erro). A primeira vez abre em Simular.
- Simular tem a seção do simulador do programa (`#v-sim`). Placas é nova. Meus dados tem Seus números, Seus PCs e a Busca de usadas.

## 3. Visual

- As mesmas cores e fontes do painel, no claro e no escuro: Sora nos títulos e números grandes, Inter no texto.
- Os quadros do resumo têm números grandes. As abas são botões grandes (44 px de altura no celular), com a aba aberta bem marcada.
- No Simular, só com CSS da página e sem mexer no programa:
  - "Compra" e "Lucro no 1º mês" viram dois números em destaque.
  - Cada cenário vira um bloco separado, com o "Se paga em…" maior.
- No celular, tudo numa coluna, com o gutter de 16 px e sem rolar para o lado.

## 4. Aba Placas

**A conta de cada placa** é a rápida, da placa sozinha, como em "Todas as placas" do programa, mas com o rendimento real no lugar da margem:

- ganho por mês = `rec ÷ 365 × 30 × dólar × horas ÷ 24 × real ÷ 100`;
- luz por mês = `W × horas × 30 ÷ 1000 × luz`;
- lucro = ganho − luz;
- se paga em = preço ÷ lucro meses, só com lucro maior que zero.

A página avisa que "no Simular entram a fonte e o resto do PC, e o número muda um pouco".

**Preços** (`mercado(id)`, a pesquisa de 22/10/2026):

- usada: o preço típico dos anúncios da região, com quantos anúncios (`n`);
- nova: o menor à vista, com a loja.

**Melhores compras:** as 5 placas com preço no Brasil e lucro, sem as de notebook e as só de mineração, que se pagam mais rápido pelo menor preço (usada ou nova). Cada uma mostra o preço, os meses, o lucro por mês e o botão Simular.

**A lista:**

- Filtros:
  - busca pelo nome: as palavras, sem acento, todas no nome;
  - marca: Todas, NVIDIA, AMD ou Intel;
  - "preço até": compara o menor preço, e sem preço a placa sai da lista;
  - ordenar: se paga mais rápido (padrão), lucro por mês, menor preço ou menor consumo. Sem preço ou sem lucro, a placa vai para o fim.
- Por padrão a lista mostra as placas com preço no Brasil, sem as de notebook e as só de mineração. "Mostrar todas" mostra as 102, com a etiqueta "notebook" ou "só mineração".
- Cada placa mostra:
  - o nome, a marca, o consumo, o ganho, a luz e o lucro por mês. Com lucro zero ou negativo, aparece "A luz come o lucro";
  - "Usada R$ 2.600 (3 anúncios) · se paga em 14 meses" e "Nova R$ 2.665 (Guerra Digital) · se paga em 15 meses", ou "Sem preço no Brasil na pesquisa";
  - o botão Simular;
  - "Procurar agora" (abre e fecha), com os links:
    - Usadas: Marketplace (`urlBuscaFb(termo, raio)`) e OLX (`urlBuscaOlx(termo, uf)`), com o termo = o nome curto sem "AMD", "Intel" ou "Huawei" na frente;
    - Novas: Kabum, Pichau, Terabyte e Mercado Livre (`lojasBusca`) e Google Shopping (`buscaShopping`);
    - a oferta que a pesquisa achou (`OFERTAS[id]`), quando tem.
  - Todo link abre numa aba nova (`target="_blank" rel="noopener noreferrer"`).
- Uma nota diz de onde vêm os preços e a data, e que o preço de agora se vê pelos links.

**Botão Simular:** abre, dentro da própria placa, uma escolha pequena.

- O preço: usada ou nova, já marcado o menor. Sem preço, a placa vai sem preço e você digita no Simular.
- Onde colocar: Opção A, B ou C (as que existem) ou "Nova opção" (até 3). Tem também Cancelar.
- Ao escolher:
  - se a opção só tem a linha vazia, a placa entra nela; senão, entra como mais uma linha, com 1 placa, no mesmo PC da última linha (sem linhas: o primeiro PC, ou Um PC novo);
  - a aba Simular abre nessa opção, com o cursor na quantidade da linha nova;
  - tudo passa pelo `mudarSim`, então grava como qualquer mudança.

## 5. Aba Meus dados

- Seus números e Seus PCs, como hoje.
- **Busca de usadas:** o estado da OLX (lista dos estados, padrão SC) e o raio do Marketplace (10 a 500 km, padrão 100). Valores fora disso ficam com o anterior. Os links usam esses dois.

## 6. O que fica guardado

- `{v:1, t, numeros, pcs, sim, busca:{uf, raio}}`, do mesmo jeito de hoje: no banco da página e no navegador, valendo o mais novo pelo `t`. Mudar a busca de usadas conta como mudança.
- A aba aberta fica só no `localStorage` deste aparelho.

## 7. De onde vem cada peça

- Do painel, pelo gerador: `OFERTAS`, `buscaShopping`, `lojasBusca`, `semAcento`, `urlBuscaFb` (duas linhas), `urlBuscaOlx`, `UF_NOMES`, `soMineracao`, `NOTEBOOK` e `deNotebook`. Se alguma mudar de nome ou de jeito, o gerador para com "não achei", como as outras peças.
- O resto é da casca: o resumo, as abas, a aba Placas, a escolha do Simular, a busca de usadas e o CSS novo.

## 8. Testes

Em `testes/simulador_web.py`, com dados inventados:

- **resumo:** os textos dos quadros, as etiquetas (também no empate), os botões de cenário (que mudam os quadros, o gráfico e o que fica guardado), o quadro "+ Opção" e o toque num quadro;
- **abas:** os papéis para o leitor de tela, o teclado e a aba lembrada;
- **placas:**
  - a conta de uma placa conferida com a fórmula;
  - as Melhores compras;
  - cada filtro e cada ordem, e o "Mostrar todas";
  - os links, com o estado e o raio de Meus dados;
- **simular pela lista:** na linha vazia, como mais uma linha, numa nova opção, o preço escolhido, a aba que abre e o cursor;
- **meus dados:** a busca de usadas guardada e limitada;
- **celular:** todas as abas sem rolagem para o lado e com botões de 44 px;
- os testes de antes continuam passando (com a comparação com o programa).

Mais as fotos das três abas no PC e no celular, claro e escuro, conferidas a olho e mandadas para o Alex.

## 9. Publicação

- O mesmo artifact (https://claude.ai/artifact/FTKLDXgvCpffmd7YxNJF5T), publicado de novo com a `url` dele, sem perder o que está guardado.
- Sem versão nova do programa.
- O `CLAUDE.md` ganha as abas e a lista no item do Simulador na web.
