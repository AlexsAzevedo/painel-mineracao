# Simulador de placas na web (página própria)

Data: 27/10/2026 · Pedido do Alex: "uma versão web só pra eu fazer essas simulações, verificar os valores… não precisa ser tudo que tem no app, só a parte de orçamento e custos". Sobre o que conferir: "similar ao que temos atualmente no software".

## O que o Alex escolheu

- **Página própria**, e não o link do painel online abrindo no Simulador.
- **A tela é a do Simulador do programa (1.9.0)**, com "Seus números" e "Seus PCs" no lugar dos dados que o programa tira do PC.
- Parte 1 (a tela e o que fica guardado) e Parte 2 (as contas e os testes) aprovadas como resumidas abaixo.

## Critérios de pronto

1. Um link novo e privado abre só o Simulador, no navegador do PC e do celular.
2. A tela é a do Simulador do programa: até 3 opções, os 3 cenários, o aviso da fonte, o gráfico, a tabela mês a mês, o ajuste dos cenários e o rodapé.
3. "Seus números" e "Seus PCs" começam com os números do Alex e dá para mudar; as contas mudam na hora.
4. Para a mesma opção e os mesmos números, a página e o programa dão os mesmos resultados (há um teste que compara).
5. O que o Alex monta fica guardado e abre igual no PC e no celular.
6. O programa, o app do celular e o painel online não mudam.

## Fora desta versão

- Ler o app da Kryptex ou os dados do PC, e sincronizar com o programa.
- Buscar preços nas lojas.
- Contar as vagas da placa-mãe (x16 e x1) e os risers (o Simulador do programa também não conta).

## 1. A página

- Título "Simulador de placas". Três partes, nesta ordem: **Seus números**, **Seus PCs** e a tela do Simulador.
- **Seus números** (valores iniciais): dólar R$ 5,42; luz R$ 0,96 por kWh, já com a bandeira; 24 horas por dia; rendimento real 74% da estimativa da Kryptex (a RX 9070 XT do Alex); CDI 13,65% ao ano; 120% do CDI (PicPay); desvalorização das placas 25% ao ano (a das Premissas, usada na revenda).
- **Seus PCs**: nome, fonte (watts e selo) e quanto o PC já gasta hoje, em watts (0 = desligado). Começa com:
  - "PC pessoal": fonte de 1000 W Platinum; 360 W hoje (a RX 9070 XT, 320 W no catálogo, e 40 W do resto do PC);
  - "PC extra (i5-13400)": fonte de 500 W Bronze; desligado;
  - "PC extra (i7-8700)": fonte de 500 W Bronze; desligado.
  Dá para mudar, acrescentar e remover PCs. "Um PC novo" fica como no programa (650 W Gold, com o custo do PC no preço).
- Uma opção cuja linha aponta para um PC removido usa "Um PC novo" e avisa, como no programa.
- Tema: o do claude.ai (claro ou escuro), com as cores do painel. No celular, uma coluna e nenhuma rolagem para o lado.

## 2. As contas

As do Simulador do programa (spec de 26/10, seção 2), com duas trocas:

- **Correção pelo real**: o rendimento real digitado (entre 20% e 200%), no lugar da leitura do app da Kryptex. A margem de segurança não entra, como no programa com leitura.
- **Os PCs**: um PC que gasta mais de 0 W hoje soma as placas novas ao que já gasta; um desligado passa a gastar as placas e mais 40 W (30 W do resto do PC e 10 W do processador parado). A luz passa pela eficiência da fonte (selo e carga, tomada de 220 V), a mesma curva do Montar setup. O ganho bruto é o das placas novas pelo catálogo, em dólar, pelas horas por dia, vezes a correção.
- **Preços sugeridos**: o menor entre usada e nova da pesquisa do painel (22/10/2026).

## 3. Uma fonte só para as contas e a tela

A página é gerada a partir do `mineracao.html` por um script (`web/gerar-simulador.py`), como o `gerar-index.py` faz para o programa. Do painel vêm o catálogo, os preços, a curva da fonte, os formatos de número e data, a seção `#v-sim` e o bloco inteiro do simulador (contas e tela). A página acrescenta só a casca: "Seus números", "Seus PCs", o jeito de guardar e as peças do painel que o simulador usa (como `calcMaq` e `maqsReais`), adaptadas aos PCs da página. Uma correção no simulador do programa chega à página quando ela é gerada e publicada de novo. O arquivo gerado não vai para o repositório (`web/dist/`).

## 4. Dados

`{numeros, pcs, sim}`, guardado no banco da própria página (o mesmo jeito do painel online), com o navegador como reserva. Grava 2 s depois da última mudança e ao sair da página (aqui não há o limite de mensagens do celular).

## 5. Testes

- `testes/simulador_web.py`: gera a página e testa as peças da casca (PC ligado, desligado e novo; correção; preço sugerido), a tela no PC e no celular (sem rolagem para o lado, sem erros), "Seus números" e "Seus PCs" mudando as contas, guardar e abrir de novo, e a comparação com o programa: a mesma opção no `mineracao.html` e na página dá os mesmos resultados nos 3 cenários.
- Os testes do painel continuam passando.

## 6. Publicação

- Um artifact novo e privado, publicado do arquivo gerado. Sem versão nova do programa: nada muda no PC nem no celular.
- O `CLAUDE.md` ganha um item sobre a página, com o link e como gerar e publicar de novo.
