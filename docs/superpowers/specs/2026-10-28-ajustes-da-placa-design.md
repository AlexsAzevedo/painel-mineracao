# Ajustes da placa de vídeo no painel, no lugar do Afterburner (1.11.0)

Data: 28/10/2026 · Pedidos do Alex: "Existiria alguma forma de em outros computadores o sistema meio que ajustar o clock a energia essas coisas que foram feitas no meu computador para achar o melhor desempenho pelo nosso aplicativo?" e "conseguiriamos incrementar dentro do nosso app algo similar ao que o msi afterburner faz, pra não depender dele?"

## O que o Alex escolheu

- **Duas partes.** Esta é a primeira: os ajustes da placa feitos à mão no painel, no lugar do MSI Afterburner. A segunda vem depois, em cima desta: o "Ajustar desempenho" automático, em que o painel testa ajustes e fica com o que dá mais lucro.
- **Só no PC.** Os ajustes só mudam no PC; o celular mostra o ajuste aplicado. Eu recomendei assim e ele respondeu "Certo".
- **Ele abre o painel à mão.** Essa é uma escolha dele. O painel aplica o ajuste quando abre e confere a cada minuto. Para o ajuste valer assim que o Windows liga, existe a opção "Abrir o painel junto com o Windows" (Premissas › Este computador), e ela continua sendo dele.
- **Convivência com o Afterburner.** Até o Alex desligar, o Afterburner pode continuar aplicando o −20% e −75 mV quando o Windows liga; o painel convive com isso.
- **Testes no PC dele, passo a passo** ("vamos testando conforme").
- **Gosta do conjunto mais frio.** No dia dos testes, ele mexeu na ventoinha quando a placa chegou a 55 °C. Vale para os avisos desta parte e, principalmente, para o ajuste automático da segunda.

## O que os testes no PC do Alex mostraram (28/10/2026)

Rodaram quatro testes: um só de leitura; um que gravou de volta os mesmos valores que a placa já tinha; um que mudou um pouco a potência, a ventoinha e a tensão, uma de cada vez, e voltou cada uma; e um que observou a ventoinha depois de gravar a potência.

- **A placa e o acesso.** A placa é uma RX 9070 XT (XFX). Os quatro testes foram pelo ADLX do driver (`amdadlx64.dll`, versão 1.5), como usuário comum, sem administrador, e com o Afterburner aberto. Por causa da licença (veja "Licença"), o painel vai usar a outra biblioteca da AMD que vem com o driver, o ADL (`atiadlxx.dll`); os testes pelo ADL estão no fim desta seção.
- **O que dá para ajustar, e como estava:**
  - Potência: de −30% a +10%, padrão 0%; estava em −20%.
  - Tensão: em offset, de −200 a 0 mV; estava em −75 mV.
  - Clock máximo: em offset, de −500 a +1000 MHz; estava em 0.
  - Memória: de 2518 a 3000 MHz, de 2 em 2; estava em 2518.
  - Temporização rápida da memória: estava desligada.
  - Ventoinha: curva de 5 pontos, de 15% a 100%; estava reta em 75%, com o zero rpm desligado.
- **O que a placa não tem:** o undervolt automático da AMD.
- **A gravação.** Gravar os mesmos −20% e −75 mV deu certo (`ADLX_OK`), e a mineração não sentiu: uns 271 W e 2.220 MHz, antes e depois.
- **Mudar um pouco e voltar** (30 s cada, tudo `ADLX_OK`, tudo voltou):
  - potência de −20% para −21%: de 272 para 268 W, e o clock de 2.204 para 2.175 MHz, porque a placa trabalha no limite de potência;
  - ventoinha de 74% para 69%: de 2.551 para 2.430 rpm, com a mesma temperatura;
  - tensão de −75 para −80 mV: o clock subiu de 2.204 para 2.238 MHz, gastando o mesmo. A tensão ainda tem espaço para baixar, o que importa na segunda parte.
- **A ventoinha do Afterburner cai quando o painel grava a potência.** Com a ventoinha posta pelo Afterburner, depois de o painel gravar a potência as rotações começaram a cair (de 2.511 para 2.048 rpm em 30 s), embora a curva lida continuasse igual. Às 17:14, isso levou a placa a 55 °C, e o Alex refez a ventoinha à mão. Depois que o painel gravou a curva da ventoinha, gravar a potência não mexeu mais nela: 2.550 rpm durante 1 minuto inteiro.

## Critérios de pronto

1. **Ver.** Premissas › "Placa de vídeo deste PC" mostra, para cada placa AMD deste PC:
   - os ajustes de agora;
   - as faixas que o driver permite;
   - como a placa está: clock, consumo, temperatura e uso.
2. **Assumir sem mexer.** Na primeira vez que a pessoa marca "O painel cuida dos ajustes da placa", o painel guarda o que a placa já tem e não muda nenhum valor. No PC do Alex, isso é o −20%, −75 mV e ventoinha em 74% do Afterburner. O painel só grava de novo a mesma curva da ventoinha, para ela passar a ser do painel: com a curva posta pelo Afterburner, gravar a potência devolve a ventoinha ao automático.
3. **Mudar.** A pessoa muda um ou mais campos e clica em Aplicar. O painel confere as faixas, grava só o que mudou, lê a placa de volta e diz o resultado de cada item.
4. **Manter.** Com o painel cuidando da placa, ele confere ao abrir e a cada minuto. Se a placa não estiver com o ajuste guardado, ele aplica de novo. Isso acontece quando:
   - o PC reiniciou;
   - o driver reiniciou;
   - outro programa mudou o ajuste. Nesse caso o painel avisa, no máximo uma vez por hora, e diz como desligar o "aplicar ao iniciar" do Afterburner;
   - a ventoinha fixa foi para o automático sem a curva mudar: as rotações caíram mais de 15%. O painel grava a ventoinha de novo e avisa, no máximo uma vez por hora.
5. **Proteção contra travamento.** Um ajuste novo fica "em teste" até completar 15 minutos com a placa minerando.
   - **O que conta como travamento:** durante o teste, o driver de vídeo reiniciar (a placa volta ao de fábrica) ou o PC desligar sem o desligamento normal.
   - **O que o painel faz:** marca o ajuste como "travou", volta para o último ajuste bom e avisa no Windows e no celular.
   - **Depois:** o painel não aplica sozinho de novo um ajuste que travou. Para aplicar à mão, ele pede confirmação.
6. **De fábrica.** O botão "Voltar ao de fábrica" devolve a placa ao estado de fábrica, e esse passa a ser o ajuste que o painel guarda.
7. **Celular.** Mostra o ajuste aplicado e a situação (bom, em teste, travou), sem campos para mudar.
8. **Sem administrador e sem derrubar o painel.** Quem lê e grava é um processo separado. Se ele travar ou cair, o painel continua funcionando.
9. **Sem quebrar nada.**
   - O painel online e o celular sem o PC não mostram a seção.
   - Não aparece NaN, Infinity nem undefined.
   - Funciona no PC e no celular, no claro e no escuro, sem rolagem para o lado.
   - Os testes de antes continuam passando.

## Fora desta versão

- **A segunda parte:** o "Ajustar desempenho" automático e os ajustes por moeda.
- **Placas NVIDIA:** o próprio app da Kryptex já faz esses ajustes nelas.
- **Mudar os ajustes pelo celular.**
- **Curva de ventoinha personalizada.** Só existem "Automática (a da AMD)" e "Fixa em X%". Uma curva feita em outro programa aparece como "Personalizada" e fica como está enquanto a pessoa não mexer na ventoinha.
- **Placas AMD antigas (RX 6000 para trás).** O clock, a tensão e a memória dessas placas usam outro jeito de ajuste, por estados. Nelas o painel ajusta só a potência e a ventoinha e mostra o resto como "não ajustável pelo painel".
- **O que o Afterburner tem a mais:** os extras de jogo (contador na tela, gravação) e os perfis dele.

## Caminhos considerados

1. **Processo separado (o escolhido).** Um processo de PowerShell com C#, como o dos sensores da 1.7.0, que fala com o ADL (`atiadlxx.dll`), a mesma biblioteca dos sensores.
   - Já funcionou no PC do Alex, sem administrador.
   - Se o driver travar no meio de uma chamada, cai só esse processo.
2. **Chamar o ADL de dentro do programa,** pelo Node com uma biblioteca de FFI (como a koffi).
   - É mais rápido e dispensa o PowerShell.
   - Traz uma dependência nativa nova para o instalador.
   - Se o driver travar no meio de uma chamada, derruba o painel inteiro.
3. **Comandar o Afterburner,** escrevendo os perfis dele e chamando-o por linha de comando.
   - O painel continuaria dependendo do Afterburner.
   - Os perfis ficam em Arquivos de Programas, que pede administrador.
4. **O ADLX** (`amdadlx64.dll`), a biblioteca mais nova da AMD, que rodou os quatro primeiros testes: fica de fora pela licença (abaixo).

## Licença

O painel tem o código aberto no GitHub e leva o leitor da placa em texto dentro do instalador.

- **ADLX:** a licença do SDK ("ADLX SDK License Agreement", o PDF do repositório da AMD) só deixa usar o código feito a partir dele internamente, ou distribuí-lo compilado e com um contrato de usuário nos termos da AMD. Os cabeçalhos dizem "All rights reserved". Por isso o painel não usa o ADLX. As sondas de 28/10 feitas com ele ficam só no PC do Alex, uso interno que a licença permite. (A primeira versão deste desenho dizia, errado, que o ADLX era MIT.)
- **ADL:** os cabeçalhos do ADL SDK (github.com/GPUOpen-LibrariesAndSDKs/display-library) trazem a licença MIT no próprio texto. O painel usa deles só os nomes das funções, o formato das estruturas e os números dos ajustes, escritos à mão no C#, como o `sensores-amd.ps1` faz desde a 1.7.0, com o aviso de copyright da AMD no começo do arquivo. A pasta de documentos do SDK ainda cita um contrato antigo (EULA); o painel se apoia no texto MIT dos cabeçalhos, que é de onde vêm as declarações.

## 1. O leitor e gravador da placa (`desktop/placa-amd.ps1`)

### Como roda

- É Windows PowerShell 5.1 com o C# dentro (`Add-Type`), como o `sensores-amd.ps1`, e vai no instalador por `extraResources`.
- Ele fala com o ADLX por uma tabela que diz a posição de cada função de cada interface. A tabela vem dos cabeçalhos do ADLX SDK 2.0.0.125 (MIT): um script gera, e o teste confere. É a mesma tabela das sondas que rodaram no PC do Alex.
- Fica rodando escondido enquanto o painel precisa dele, e conversa por linhas de JSON:
  - cada pedido é uma linha na entrada;
  - cada resposta é uma linha na saída, com o mesmo `id` do pedido;
  - o laço que lê os pedidos fica no C#, para o teste sem Windows cobrir também essa parte.
- Ele termina quando a entrada fecha ou quando o painel (`-Pai`) acaba.

### Os pedidos

- **`ler`** devolve as placas que têm ajuste manual. Cada placa traz:
  - `chave`: tirada do `PNPString`, que identifica o slot e não muda quando o PC reinicia;
  - `nome` e `deFabrica`;
  - os ajustes `potencia`, `tensao`, `clock` e `memoria`, cada um com `{min, max, passo, atual, padrao}`. A tensão e o clock levam `offset: true` quando a faixa começa abaixo de zero;
  - `temporizacao`: `{suporta, atual, opcoes}`;
  - `ventoinha`: `{velMin, velMax, curva: [[°C, %] × 5], curvaPadrao, zeroRpm: {suporta, atual, padrao}}`;
  - `agora`: clock, memória, tensão, W da placa, °C da borda, do ponto quente e da memória, rpm e uso.

  A resposta também traz `afterburner`, que diz se o `MSIAfterburner.exe` está aberto.
- **`aplicar`** com `{chave, ajuste}`:
  - grava só os campos que vieram e que estão diferentes do valor atual;
  - grava na ordem: potência, tensão, clock, memória e, por último, a ventoinha. Quando o pedido traz a ventoinha, ela é gravada de novo no fim mesmo sem mudar, porque gravar os outros ajustes pode devolvê-la ao automático;
  - antes de gravar, confere cada valor na faixa e no passo; fora disso, responde "fora da faixa" e não grava;
  - responde o resultado de cada campo e a leitura da placa depois.
- **`fabrica`** com `{chave}` chama `ResetToFactory` e responde a leitura depois.

### Segurança e erros

- **Só estas gravações existem.** A lista fica no C#, como no teste de gravação: `SetPowerLimit`, `SetGPUVoltage`, `SetGPUMaxFrequency`, `SetMaxVRAMFrequency`, `SetMemoryTimingDescription`, `SetFanTuningStates` (mais os `SetFanSpeed` dos pontos da lista que vai ser gravada), `SetZeroRPMState` e `ResetToFactory`. Qualquer outra função de escrita é recusada antes de chegar ao driver.
- **Ventoinha.** "Fixa em X%" põe os 5 pontos da curva em X%, mantém as temperaturas dos pontos e desliga o zero rpm. "Automática" põe a curva padrão e o zero rpm padrão. Antes de gravar a curva, o leitor confere com `IsValidFanTuningStates`.
- **Erro de objeto do ADLX** (`INVALID_OBJECT`, `GPU_INACTIVE` ou `ORPHAN_OBJECTS`, que acontecem quando o driver reiniciou ou foi atualizado): o leitor reinicia o ADLX e tenta de novo uma vez.

## 2. O programa do PC

### `desktop/placa-amd.js`: o processo

- **Ligar e pedir.** O processo liga na primeira chamada e atende um pedido de cada vez, numa fila.
- **Prazos.** 60 s para o primeiro pedido, porque o C# compila; 20 s para cada pedido; 30 s para o de fábrica. Se um pedido não responde no prazo, o processo é encerrado e o pedido volta com erro.
- **Quedas.** Se o processo cai, liga de novo depois de 1, 5 e 30 minutos. Sem placa AMD ou sem o ADLX, confere de novo só depois de 1 hora.
- **Ocioso.** Sem nenhum pedido por 5 minutos, o processo encerra.
- **No teste.** `PAINEL_PLACA_CMD` troca o leitor por um de mentira, em Node, e os tempos vêm de variáveis, como nos sensores.

### `desktop/placa-regras.js`: as decisões

São funções puras. Recebem uma leitura, o estado guardado e as marcas de energia, e dizem o que fazer: aplicar, marcar como bom, marcar como travou ou avisar.

### `placa.json`: o estado, na pasta de dados

- **Formato:** `{v, cuidar, placas: {chave: {nome, salvo, bom, teste: {ajuste, desde, minutos}, travou: [{ajuste, quando, motivo}] (até 10), resetes: [t], rpm: {referencia, amostras}, avisos: {outro: t, ventoinha: t}}}}`.
- **Gravado antes de aplicar.** O arquivo é gravado inteiro, e já no disco, antes de cada aplicação, como o `app-celular.json`. Assim, se o PC travar logo depois, o painel sabe na volta que aquele ajuste estava em teste.

### A vigia, no `main.js`

Roda logo que o painel abre e depois a cada minuto, enquanto o painel cuida da placa:

1. **Lê a placa.**
2. **Se há um ajuste em teste,** vê o que aconteceu desde o começo do teste:
   - **O PC desligou sem o desligamento normal** (pelas marcas do `energia.js`): o ajuste travou, porque "o PC desligou de repente durante o teste".
   - **A placa está de fábrica:** o ajuste travou, porque "o driver de vídeo reiniciou durante o teste".
   - **O PC desligou normalmente:** o painel aplica o ajuste de novo e o teste recomeça, com os minutos de volta a zero.
   - **Nada disso:** se a placa estava minerando (uso de 80% ou mais), o minuto conta. Com 15 minutos contados, o ajuste vira bom.

   Quando um ajuste trava, o painel guarda ele na lista dos que travaram, troca o ajuste guardado pelo último bom (ou pelo de fábrica, se não houver um), aplica e avisa.
3. **A ventoinha fixa.** Com a ventoinha "Fixa em X%", depois de cada aplicação o painel guarda as rotações dela (a mediana dos 3 primeiros minutos). Se elas caírem mais de 15% sem a curva mudar, a ventoinha foi para o automático: o painel grava a curva de novo e avisa, no máximo uma vez por hora. Com a ventoinha "Automática", as rotações mudam com a temperatura, e essa conferência não vale.
4. **Se não há teste, mas a placa está diferente do ajuste guardado:**
   - **Está de fábrica:** aplica de novo, que é o normal depois de reiniciar. Se o driver reiniciou com o painel aberto, isso conta: com 2 vezes em 24 horas com o mesmo ajuste, esse ajuste vai para a lista dos que travaram, o painel passa a guardar o de fábrica e avisa.
   - **Está com outro valor** (outro programa mudou): aplica de novo e avisa, no máximo uma vez por hora.
5. **Gravação com erro:** o painel não tenta de novo mais que uma vez a cada 10 minutos.

### A ponte (`preload.js`): `window.desktop.placa`

- **Funções:** `estado()`, `ler()`, `aplicar(chave, ajuste, {mesmoQueTravou})`, `fabrica(chave)`, `cuidar(sim)` e `aoMudar(fn)`.
- **Eventos:** "travou", "driver reiniciou", "outro programa" e "parou de aplicar" chegam à página. A página avisa no Windows e no celular pelo mesmo caminho dos avisos do app da Kryptex (`avisoKx`).

### Segundo plano

- "O painel cuida dos ajustes da placa" entra nas funções que pedem o ícone perto do relógio e abrir junto com o Windows (`sincronizarSegundoPlano`). A escolha da pessoa em Este computador continua valendo.
- Sem abrir junto com o Windows, a seção avisa que o ajuste só é aplicado quando o painel abre.

## 3. Na tela

### PC: Premissas › "Placa de vídeo deste PC" (`#placa-p`)

- **Onde:** depois do "App da Kryptex neste PC". A seção aparece só no programa do PC e só com uma placa AMD que tenha ajuste manual.
- **"O painel cuida dos ajustes da placa"** é uma caixa de marcar. Na primeira vez, o painel guarda o que a placa já tem e diz isso.
- **Para cada placa:**
  - o nome e a linha "Agora: 2.220 MHz · 271 W · 44 °C · uso 100%";
  - os campos:
    - Limite de potência (%);
    - Tensão (mV; "ajuste" quando for offset);
    - Clock máximo (MHz; "ajuste" quando for offset);
    - Memória (MHz), com a caixa "Temporização rápida" quando a placa oferece (`MEMORYTIMING_FAST_TIMING`);
    - Ventoinha: Automática ou Fixa em X%;
  - embaixo de cada campo, a faixa e o padrão, por exemplo "de −30% a +10% · padrão 0%". Um campo fora da faixa fica marcado e o Aplicar não segue.
- **Botões:**
  - Aplicar;
  - Desfazer, que volta os campos para o ajuste guardado;
  - Voltar ao de fábrica, que pede confirmação;
  - Copiar o que o painel leu da placa.
- **A situação,** por exemplo:
  - "Em teste: faltam 12 minutos com a placa minerando. Se ela travar, o painel volta para o ajuste anterior."
  - "Ajuste bom desde 28/10 18:05."
  - "O ajuste de 28/10 17:40 travou a placa (o driver de vídeo reiniciou). O painel voltou para o anterior."
- **Com o Afterburner aberto:** "O MSI Afterburner também está aberto. Para os dois não brigarem, desligue nele o 'Aplicar overclock ao iniciar o sistema' (ou desinstale)."
- **Sem abrir junto com o Windows:** "O painel só aplica o ajuste quando está aberto. Para aplicar assim que o Windows ligar: Este computador › Abrir o painel junto com o Windows."

### Celular: a mesma seção, só para ver

- **Uma chave nova sincronizada, `min-placa`.** Só o PC grava, como a `min-paradas`, e ela entra na lista `SINCRONIZADAS` dos dois lados (`mineracao.html` e `desktop/sincronia.js`). Formato: `{v, quando, cuidar, placas: [{nome, ajuste, situacao, desde, testeAte, travou}]}`.
- O PC grava essa chave quando o ajuste ou a situação mudam.
- O celular mostra o ajuste e a situação, sem campos para mudar.

## 4. Riscos que o desenho cobre

- **Depois de reiniciar o PC.** Ainda não sabemos se o driver da AMD guarda o ajuste sozinho. A vigia funciona dos dois jeitos: se a placa voltar de fábrica, o painel aplica de novo quando abrir.
- **O AMD Adrenalin.** Ele pode reaplicar um perfil próprio quando o Windows entra. A vigia trata isso como "outro programa".
- **A ventoinha posta por outro programa.** Com a curva gravada pelo Afterburner, gravar a potência pelo painel devolveu a ventoinha ao automático. Por isso o painel grava a ventoinha por último em toda aplicação, assume a curva ao começar a cuidar da placa e vigia as rotações.
- **Um ajuste que trava a placa.** A proteção vale tanto para um travamento do driver (a placa volta ao de fábrica) quanto para o PC inteiro travar e ser desligado no botão (o PC liga sem o desligamento normal).

## 5. Testes

- **O C# do leitor, sem Windows.**
  - É compilado com o `mcs` do Mono no modo C# 5, o mesmo do Windows PowerShell 5.1.
  - Roda contra um ADLX de mentira, em C, com as vtables geradas dos mesmos cabeçalhos. Toda função de escrita fora da lista faz o processo abortar.
  - Cenários: a 9070 XT, interfaces antigas, placa sem suporte, gravação recusada, valor fora da faixa, driver reiniciado no meio, duas placas.
  - Arquivo novo: `desktop/scripts/teste-placa-amd-cs.py`. Precisa de `gcc` e `mono-mcs`.
- **O processo e as regras:** `desktop/scripts/teste-placa-amd.js`, com o leitor de mentira (`placa-falsa.js`). Cobre a fila, os prazos, as quedas e todas as decisões: teste, travou, de fábrica, outro programa e as esperas.
- **O programa inteiro:** um roteiro do Electron (`teste-placa-app.js`) com o leitor de mentira. Cobre o aplicar, a vigia, o PC reiniciando no meio do teste (com marcas de energia de mentira) e os avisos.
- **A página:** `testes/placa.py` (Playwright), com uma ponte de mentira.
  - A seção no PC e no celular.
  - Assumir, aplicar, valor fora da faixa e as situações.
  - O aviso do Afterburner.
  - Claro e escuro, com fotos.
- **O instalador:** o `teste-pacote.js` passa a conferir também os `extraResources` (o `placa-amd.ps1` e o `sensores-amd.ps1`) dentro do pacote montado.
- **No PC do Alex, com o OK dele em cada passo:**
  1. **Antes da versão nova (feito em 28/10):** pela pasta "mineração", os quatro testes do começo deste desenho: ler; gravar os mesmos valores; potência em −21%, ventoinha em 69% e tensão em −80 mV, voltando cada uma; e a ventoinha observada depois de gravar a potência. O leitor da versão nova roda de novo esses testes antes de entrar no instalador.
  2. **Com a 1.11.0 instalada:** nada muda na placa até ele marcar a caixa.
     - Assumir o ajuste de agora.
     - Mudar um pouco a potência e ver o teste virar bom depois de 15 minutos.
  3. **Reiniciar o PC** com o "aplicar ao iniciar" do Afterburner desligado:
     - ver se o driver da AMD guarda o ajuste sozinho;
     - ver se o painel aplica o ajuste quando abre.

## 6. Versão

- **1.11.0** do programa do PC. A página nova chega sozinha ao celular, e o app do celular não muda.
- Novidades, `notas/v1.11.0.md` e o `CLAUDE.md`.
- Publicar só com o OK do Alex.
