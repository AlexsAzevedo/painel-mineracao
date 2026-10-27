# Simulador de compra de placas (versão 1.9.0)

Data: 26/10/2026 · Pedido do Alex: "quero comprar algumas placas, quero ver quando elas vão render, quanto vão gastar, o custo que terei por comprar essas placas, a projeção de mercado". Na mesma mensagem, a dúvida que o simulador precisa responder: pegar R$ 10.000 emprestados em 20 × R$ 674,65 e comprar 2 RTX 5070, ou 3 RTX 5060, pondo a compra no cartão e deixando o dinheiro rendendo (como ele fez com a RX 9070 XT).

## O que o Alex escolheu

- **Projeção de mercado: os dois.** O rendimento da mineração em 3 cenários (estável, caindo devagar, caindo rápido) e quanto as placas valem para revender no fim.
- **Rendimento: o real, corrigido.** A estimativa da Kryptex de cada placa, corrigida pelo que a RX 9070 XT dele rende de verdade.
- **Tela (parte 1) e contas (parte 2)** como apresentadas e resumidas abaixo.

## Critérios de pronto

1. Em Simulador, o Alex monta até 3 opções de compra e vê as 3 lado a lado (no celular, uma embaixo da outra).
2. Cada opção diz, em cada cenário: em que mês se paga; quanto sobra ou falta no fim do prazo, sem e com a revenda das placas; e se a mineração dá conta das parcelas todo mês ou em que mês ele precisaria pôr dinheiro, e quanto.
3. O empréstimo do Alex (R$ 10.000 em 20 × R$ 674,65) aparece com 3,04% ao mês e 43,2% ao ano, R$ 3.493 de juros.
4. O rendimento usa a correção pelo real quando o painel tem leitura do app da Kryptex, e diz qual correção usou; sem leitura, usa a estimativa e avisa.
5. O que o Alex monta fica guardado e aparece igual no PC, no celular e no painel online (na configuração, que já sincroniza).
6. Nada do que existe muda: as telas, as contas e os testes de hoje continuam passando.

## Fora desta versão

- Monitorar os PCs extras pelo painel (as leituras de cada PC indo para o principal).
- Recomendar compra: o simulador mostra as contas; o rodapé diz que é estimativa e não recomendação.
- Imposto sobre o ganho da mineração, e o preço do bitcoin separado do rendimento (o cenário já junta preço e dificuldade numa taxa só).
- Guardar várias simulações com nome: ficam as 3 opções da tela.

## 1. Onde fica e como é a tela

- Tela nova "Simulador" (`v-sim`). No PC, no grupo "Comprar" do menu, depois de "Todas as placas" (é uma decisão de compra; o "Montar setup" fica em "Ajustes"). No celular, na folha Mais, junto do "Montar setup".
- Até 3 opções (A, B e C), cada uma num quadro, lado a lado no PC e uma embaixo da outra no celular. Cada opção tem:
  - **Placas**: uma ou mais linhas com modelo (o catálogo), quantidade, preço por placa (sugerido pelo `melhorPreco`, o mesmo da lista de placas; dá para mudar) e em qual PC vai (as máquinas do "Montar setup" ou "Um PC novo"). Aviso se a fonte daquele PC passar de 80% de carga com as placas da opção.
  - **Um PC novo**: fonte de 650 W Gold, 30 W para o resto do PC e processador parado, com um campo para o custo do PC, que entra no preço da compra (pago do mesmo jeito que as placas).
  - **Como paga as placas**: à vista, ou no cartão em N vezes sem juros (1 a 24).
  - **De onde vem o dinheiro**: dinheiro seu, ou empréstimo (valor recebido, número de parcelas e valor de cada parcela). Do empréstimo, o painel mostra os juros ao mês e ao ano e o total de juros.
- **Resultado de cada opção**, nos 3 cenários: mês em que se paga ("não se paga no prazo", se for o caso); quanto sobra ou falta no fim do prazo, sem e com a revenda; e o pior mês da conta ("a mineração paga as parcelas" ou "em março/2027 faltam R$ 820: você precisaria pôr esse dinheiro").
- **Gráfico**: o resultado acumulado mês a mês das opções (uma linha por opção), no cenário escolhido (estável, devagar ou rápido), com a linha do zero. Mesmo jeito do gráfico de retorno de Minhas placas (`desenharRetorno`): SVG, legenda, dica ao passar o mouse e resumo para leitor de tela.
- **Tabela mês a mês** (abre num `details`): por opção e cenário escolhido, mês, lucro da mineração, parcelas, rendimento, dinheiro na conta e resultado acumulado.
- **Prazo**: até o fim das parcelas (das placas e do empréstimo), no mínimo 12 meses; dá para escolher 12, 24 ou 36.
- **Cenários**: estável 0% ao mês, caindo devagar −1,5% ao mês (uns −17% em um ano) e caindo rápido −4% ao mês (uns −39% em um ano), num quadro "Ajustar cenários" que dá para mudar.
- **Rodapé**: "Conta com estimativas: o rendimento da mineração e o preço das placas mudam. Não é recomendação de compra nem de empréstimo."

## 2. As contas

Para cada opção, cenário e mês `m` (1 até o prazo):

- **Rendimento**: para cada PC usado pela opção, `Δbruto` = o ganho bruto por mês daquele PC com as placas da opção menos sem elas (`calcMaq` com `extra`, as contas do "Montar setup": catálogo da Kryptex, dólar, horas por dia e margem das Premissas). Bruto do mês = `Δbruto × correção × (1 + taxa do cenário)^(m−1)`.
- **Correção pelo real**: o ritmo que o app da Kryptex mostra para as placas que estão minerando neste PC (`rendimentoUsd` de cada uma, o mesmo do `ritmoKxa`) dividido pela estimativa do catálogo para os mesmos modelos (achados pelo nome, como o `maqDestePc`). Fica entre 20% e 200%. O PC calcula na hora; o celular recebe no retrato do app da Kryptex (`min-kx-app`, campo novo `fatorKx`). Sem leitura (ou sem placa do catálogo minerando), a correção é 100% e o simulador avisa "pela estimativa da Kryptex".
- **Luz**: `Δluz` = a luz por mês daquele PC com as placas da opção menos sem elas (`calcMaq`): placas, processador, o resto do PC e a perda da fonte, na tarifa e bandeira das Premissas. Um PC que estava desligado (sem placa minerando) passa a contar inteiro. Fica igual todos os meses.
- **Lucro da mineração no mês** = bruto do mês − `Δluz` (pode ser negativo).
- **Empréstimo** (tabela Price): taxa ao mês achada pelo valor recebido, número de parcelas e valor da parcela (bisseção); saldo devedor `S_m = S_{m−1} × (1 + i) − parcela`.
- **Dinheiro na conta**: começa com o dinheiro da compra (o seu, separado para ela, ou o do empréstimo). Todo mês: rende o seu % do CDI das Premissas (mesma taxa do `rendimentoParcelado`, com o imposto da tabela regressiva pelo tempo: 22,5% até 6 meses, 20% até 12, 17,5% até 24 e 15% depois), sai a parcela das placas (o preço inteiro no mês 0, à vista; ou preço ÷ N nos meses 1 a N, no cartão), sai a parcela do empréstimo e entra o lucro da mineração (simplificação: na vida real ele fica no saldo da Kryptex, em bitcoin, até o saque; a tabela diz isso). Conta negativa = dinheiro que o Alex precisaria pôr.
- **Resultado acumulado** no mês `m` = dinheiro na conta − saldo devedor do empréstimo − parcelas do cartão que faltam − dinheiro seu separado no começo. No mês 0 ele é −(preço das placas e do PC novo); depois cresce com o lucro da mineração e o rendimento e cai com os juros do empréstimo.
- **Se paga** no primeiro mês com resultado acumulado ≥ 0 (sem a revenda).
- **Revenda no fim**: para cada placa, preço × (1 − desvalorização por ano)^(meses/12), com a desvalorização de `deprecModelo` (o histórico de preços com 60 dias ou mais, senão a das Premissas). O PC novo não entra na revenda.

## 3. Dados

- Tudo em `cfg.sim` (a configuração, `min-cfg`, que já sincroniza entre PC, celular e painel online): `{opcoes: [até 3 × {nome, placas: [{modelo, qtd, preco, maq}], pcNovo: {custo}, pagamento: {tipo: "avista"|"cartao", parcelas}, dinheiro: {tipo: "meu"|"emprestimo", valor, parcelas, parcela}}], prazo: 0|12|24|36, cenarios: {estavel, devagar, rapido}, cenarioGrafico}`. `migrar` completa o que faltar.
- Na primeira vez, a tela começa com a opção A vazia e um botão "+ Opção".
- `maq` guarda o id da máquina do setup; se a máquina sumir, a linha passa para "Um PC novo" e avisa.

## 4. Testes

- `testes/simulador.py` (Playwright, dados inventados): as contas puras (a taxa do empréstimo do Alex dá 3,04% ao mês e R$ 3.493 de juros; o mês em que se paga, à vista e no cartão, com e sem empréstimo; os cenários; a revenda; o pior mês da conta; a correção limitada a 20–200%), a tela (montar duas opções, trocar o cenário do gráfico, o aviso de fonte acima de 80%, o PC novo, guardar e abrir de novo) e o celular (as opções uma embaixo da outra, sem rolagem para o lado).
- `testes/kryptex_app.py`: o retrato leva `fatorKx` (a correção) calculado pelo `rendimentoUsd` e pelo catálogo.
- `testes/visual.py`: a tela nova no passeio pelas telas (temas claro e escuro, PC e celular) e a novidade 1.9.0.
- Os testes de hoje, o teste do aplicativo inteiro e uma revisão independente antes de pedir para publicar.

## 5. Versão

- 1.9.0 no PC (`desktop/package.json`). A parte Android não muda: o app continua 1.8.0 e o celular recebe a página nova sozinho.
- Novidades: "Simulador de compra: monte até 3 opções de placas, com o pagamento à vista, no cartão ou com empréstimo, e veja mês a mês quando elas se pagam em 3 cenários de mercado, com a revenda no fim."
