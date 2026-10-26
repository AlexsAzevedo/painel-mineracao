# App do celular que se atualiza sozinho (versão 1.8.0)

Data: 26/10/2026 · Pedido do Alex: "em vez de toda vez eu ter que baixar o app, ser igual o PC: só atualiza" (print do Brave perguntando "Baixar o arquivo novamente? Painel-de-Mineracao.apk").

## O que o Alex escolheu

- **Os dois caminhos**: o painel do celular se atualiza sozinho, sem instalar nada; a parte Android do app (rara) se atualiza com um toque, dentro do app.
- **Painel novo na hora, sem perguntar**: assim que termina de baixar, o painel recarrega com a versão nova. Duas exceções combinadas: com um formulário aberto, espera fechar; com o app em segundo plano, entra quando ele voltar para a frente.
- Segurança e "se der errado" como apresentados (abaixo).

## Por que dá para fazer assim

- O Android não deixa um app de fora da Play Store se reinstalar sem nenhuma confirmação na primeira vez; no Android 12 ou mais novo, um app que **atualiza a si mesmo** pode instalar sem perguntar, se declarar `UPDATE_PACKAGES_WITHOUT_USER_ACTION`, pedir `USER_ACTION_NOT_REQUIRED` e mirar uma versão recente do Android (o nosso mira a 36). Sem isso, o Android mostra a tela de confirmação dele.
- Quase tudo que muda de uma versão para outra é a página (`celular/www`: o painel, a ponte, a sincronia). O Capacitor 8 já sabe servir a página de uma pasta do app em vez da que vem no .apk (`Bridge.setServerBasePath`, guardado em `CapWebViewSettings.serverBasePath`, lido antes de abrir a página; um .apk novo zera essa escolha, em `isNewBinary`). O endereço da página continua `https://localhost`, então os dados (localStorage) e o vínculo com o PC continuam os mesmos.
- O Google vai exigir, em 2027, desenvolvedor cadastrado para instalar e atualizar apps fora das lojas (no Brasil começou em 30/09/2026, por enquanto só para lojas). Trocar a página não instala nada, então não depende disso; atualizar o .apk depende (aí entra o cadastro gratuito de "distribuição limitada", até 20 aparelhos, quando chegar a hora: fora desta versão).

## Critérios de pronto

1. Com o app 1.8.0 instalado, uma versão nova publicada (por exemplo 1.8.1, só com mudança na página) chega ao celular sozinha: o app baixa, confere a assinatura e passa a mostrar a 1.8.1 sem o Alex baixar nem instalar nada.
2. Uma versão que muda a parte Android: o app baixa o .apk sozinho e mostra "Atualização do app pronta · Atualizar o app"; um toque instala (sem perguntar no Android 12+ quando o Android deixa; com a tela do Android nos outros casos).
3. O app só aceita página e .apk publicados por nós (assinatura com a chave do app); nunca volta para uma página mais velha; nunca usa uma página que precise de uma parte Android mais nova do que a instalada.
4. Uma página nova que não abre direito volta sozinha para a anterior em até 30 segundos com o app na tela, e aquela versão não é tentada de novo.
5. O app nunca fecha sozinho por causa do atualizador: qualquer erro do atualizador vira só "não atualizou agora".
6. Nada se perde: dados, vínculo, sincronia, avisos, a tela de vincular e os testes de hoje continuam passando.
7. A publicação (`publicar.yml`) monta, assina e publica o pacote da página junto com o .apk, sem nenhum segredo novo.

## Fora desta versão

- Atualizar com o app fechado (trabalho em segundo plano do Android). Procura só com o app aberto.
- Cadastro de desenvolvedor no Google (2027) e Play Store.
- Atualização parcial (só os arquivos que mudaram): o pacote inteiro tem menos de 1 MB compactado.
- Lista de novidades no celular (as `NOVIDADES` falam do PC). Só o aviso "Painel atualizado: versão X".
- O aviso "o PC voltou depois de desligar sem querer" (oferecido ao Alex em 26/10; decisão à parte).

## 1. Nomes e versões

- **Página do celular** (o "painel" para o Alex): o conteúdo de `celular/www` que `montar-www.py` monta (`index.html`, `ponte-app.js`, `sincronia.js`, `capacitor.js`, `jsQR.js`, `icone.png`, `fonts/`) mais um `painel.json` novo: `{"versao": "<versão da release>", "app": "<versão do app>"}`.
- **Versão da página** = versão da release (`desktop/package.json`), a mesma do PC. `montar-www.py` troca `__PAINEL__` em `ponte-app.js` por ela (como já faz com `__VERSAO__`).
- **Versão do app** = `celular/package.json` (versionName; versionCode = X·10000 + Y·100 + Z). A partir da 1.8.0, **sobe só quando a parte Android muda**: código em `celular/android`, plugins e versão do Capacitor, permissões, ícones, `celular/capacitor.config.json`.
- **appMin** de uma página = a versão do app em `celular/package.json` quando ela foi montada. Como a versão do app só sobe quando a parte Android muda, uma página só exige app novo quando depende de algo novo da parte Android.
- `celular/scripts/conferir-nativo.py` calcula um resumo (SHA-256) dos arquivos da parte Android (os arquivos de `celular/android` que estão no git, `celular/capacitor.config.json` e as versões dos pacotes `@capacitor/*` de `celular/package.json`) e compara com `celular/nativo.json` (`{"app": "1.8.0", "resumo": "…"}`). Se a parte Android mudou sem subir a versão do app, ou a versão subiu sem `--gravar`, ele falha com a explicação. Roda nos testes e no `publicar.yml`.
- `window.desktop.versao` no app passa a ser a versão da página. O app manda ao PC `{app, painel}` no `ola`; o PC guarda `painel` junto de `app` e a lista de celulares mostra "painel 1.8.1 · app 1.8.0".

## 2. O que vai em cada release (a partir da 1.8.0)

Além do que já vai (instalador, `.blockmap`, `latest.yml`, `Painel-de-Mineracao.apk`):

- `painel-celular.zip`: `celular/www` compactado (os arquivos na raiz do zip, em ordem, com data fixa).
- `painel-celular.json`: `{"manifesto": "<texto>", "assinatura": "<base64>"}`, em que `manifesto` é o texto JSON:
  ```json
  {"formato": 1, "tipo": "painel-mineracao/painel-celular", "versao": "1.8.1", "appMin": "1.8.0",
   "painel": {"sha256": "<64 hex>", "tamanho": 401234},
   "app": {"versao": "1.8.0", "codigo": 10800, "sha256": "<64 hex>", "tamanho": 3745000}}
  ```
  e `assinatura` é RSA com SHA-256 (PKCS#1 v1.5) sobre os bytes UTF-8 de `manifesto`, com a mesma chave que assina o .apk (`ANDROID_KEYSTORE_B64`, apelido `painel`, RSA 4096). O app confere com a chave pública do certificado com que **ele mesmo** foi assinado: quem não tem a chave do app não consegue fazer o app aceitar nada.
- Assinar: `celular/scripts/AssinarPainel.java` (Java 21, rodado com `java Arquivo.java`, sem compilar), que abre o keystore, assina, confere a própria assinatura com o certificado e grava `painel-celular.json`. Montar o zip e o manifesto: `celular/scripts/montar-pacote.py` (zip de `celular/www`, SHA-256 e tamanhos, a versão e o código do .apk pelo `package.json`). A chave nunca sai do keystore para um arquivo.
- Endereços (fixos no app): o manifesto em `https://github.com/AlexsAzevedo/painel-mineracao/releases/latest/download/painel-celular.json`; o zip e o .apk da **mesma** release, pela versão assinada: `…/releases/download/v<versao>/painel-celular.zip` e `…/releases/download/v<versao>/Painel-de-Mineracao.apk`.

## 3. A parte Android: o plugin `Atualizador`

Código Java novo em `celular/android/app/src/main/java/br/alex/painelmineracao/celular/`, registrado em `MainActivity` antes de `super.onCreate`. A lógica fica em classes de Java puro (testáveis fora do Android, com o tempo, os arquivos, a rede e as preferências passados de fora); o plugin só liga essas classes ao Android.

### 3.1 Estado guardado (SharedPreferences `atualizador`)
- `codigoApp`: o versionCode da última vez (para saber que o .apk mudou).
- `atual` `{versao, pasta}` e `anterior` `{versao, pasta}`: a página em uso e a de antes (vazios = a que vem no .apk). A versão da que vem no .apk sai de `assets/public/painel.json`.
- `emProva` `{versao, pasta, vezes}`: página nova em uso que ainda não confirmou que abriu.
- `pronta` `{versao, pasta}`: baixada e conferida, esperando a hora de entrar.
- `ruins`: versões que não abriram (não tenta de novo).
- `trocou` `{de, para}` e `voltou` `{de, para}`: para a página mostrar o aviso uma vez.
- `manifesto`: o último conferido; `ultimaProcura`, `erro` (o último, em palavras simples).
- `apk` `{versao, codigo, arquivo}`: .apk baixado e conferido; `falhaApk`.

### 3.2 Ao abrir (`load()`, antes de a página carregar)
Tudo dentro de um `try/catch (Throwable)`: se algo der errado aqui, o app abre com a página que o Capacitor escolheria sozinho.
1. Se o versionCode mudou (app atualizado): apaga as páginas e o .apk baixados, zera o estado (o Capacitor volta sozinho para a página do .apk).
2. Se há `emProva`: soma 1 em `vezes`. Com mais de 2, a página não confirmou em duas aberturas: volta para `anterior` (ou a do .apk), põe a versão em `ruins` e grava `voltou`.
3. Se há `pronta` e nada em prova: ela entra agora (o app está abrindo, não interrompe nada): sai de `pronta` e vira `emProva` com `vezes = 1`.
4. Grava em `CapWebViewSettings.serverBasePath` a pasta que deve abrir (ou vazio).
5. Se a última procura foi há mais de 6 horas, procura em segundo plano (mesmo que a página esteja com defeito no atualizador).

### 3.3 Procurar e baixar (uma tarefa de cada vez, numa linha de execução própria)
- `procurar` (sem `forcar`, só se a última procura foi há mais de 30 minutos; com `forcar`, quando a pessoa toca em Procurar agora, na hora; duas procuras ao mesmo tempo viram uma): baixa o manifesto (até 64 KB), confere a assinatura e o formato (`formato` 1, `tipo` certo, versões `X.Y.Z`, SHA-256 com 64 letras, tamanhos dentro do limite: página até 20 MB, .apk até 100 MB).
  - Página nova: `versao` maior que a atual e a do .apk, fora de `ruins`, e `appMin` até a versão do app instalado → baixa a página.
  - `appMin` maior que a versão do app instalado → a página espera; o que vale é o .apk.
  - `app.codigo` maior que o versionCode instalado → baixa o .apk.
- Baixar a página: só HTTPS, só `github.com` e endereços terminados em `.githubusercontent.com` (inclusive nos redirecionamentos, no máximo 5), prazos de 15 s para conectar e 30 s sem receber nada; confere tamanho e SHA-256 com o manifesto; descompacta numa pasta temporária recusando caminhos com `..`, absolutos ou com `\`, mais de 500 arquivos, mais de 40 MB no total ou mais de 20 MB num arquivo; exige `index.html` e um `painel.json` com a mesma versão; renomeia para `files/painel/<versao>/` e grava `pronta`.
- Baixar o .apk: o mesmo cuidado, para `files/atualizacao/`; confere tamanho e SHA-256 com o manifesto e, pelo Android (`getPackageArchiveInfo`), o pacote (`br.alex.painelmineracao.celular`), o versionCode (o do manifesto, maior que o instalado) e o certificado (o mesmo do app; se o Android não conseguir ler o certificado do arquivo, vale a conferência pelo manifesto assinado). Grava `apk`.
- Cada mudança de estado vai para a página pelo evento `estado`.

### 3.4 Trocar de página
- `usarPainel()` (a página pede, na hora combinada): só com `pronta` válida. Vira `emProva` (`vezes = 1`), grava a pasta em `serverBasePath` e chama `bridge.setServerBasePath(pasta)` (recarrega a página).
- Vigia de 30 segundos **com o app na tela** (para enquanto o app está em segundo plano e continua quando ele volta): se a página não confirmou, volta para `anterior` (ou a do .apk) na hora, com `setServerBasePath` ou `setServerAssetPath("public")`, põe a versão em `ruins` e grava `voltou`.
- `painelOk({versao})`: se é a versão em prova, ela vira `atual`, a de antes vira `anterior`, grava `trocou` e apaga as outras pastas de página.

### 3.5 Instalar o .apk
- `instalarApp()`: confere de novo o SHA-256 do arquivo e abre uma sessão do `PackageInstaller` (`MODE_FULL_INSTALL`, `setAppPackageName`, `setSize`; no Android 12+, `setRequireUserAction(USER_ACTION_NOT_REQUIRED)`), copia o .apk e confirma com um `PendingIntent` (mutável no Android 12+, com intenção explícita) para um receptor do próprio app (`exported="false"`).
- Receptor: `STATUS_PENDING_USER_ACTION` → abre a tela de confirmação do Android (que também cuida, na primeira vez, de pedir para o Mineração poder instalar apps); sucesso → nada (o Android fecha o app); falha ou cancelado → grava `falhaApk` com o motivo em palavras simples e avisa a página.
- Permissões novas no `AndroidManifest.xml`: `REQUEST_INSTALL_PACKAGES` e `UPDATE_PACKAGES_WITHOUT_USER_ACTION`. O receptor de instalação é declarado no manifesto.
- `estado()` também diz se o Android já deixa o app instalar apps (`canRequestPackageInstalls`, Android 8+), para a página avisar antes ("na primeira vez o Android pede…").

### 3.6 Métodos para a página
`estado()`, `procurar({forcar})`, `usarPainel()`, `painelOk({versao})`, `instalarApp()`, `visto({qual})` (limpa `trocou` ou `voltou` depois do aviso) e o evento `estado`. O estado tem: `app {versao, codigo}`, `painel {versao, origem: "apk" | "baixado", embutido}`, `pronta`, `emProva`, `apk`, `procurando`, `baixando {qual, pct}`, `ultimaProcura`, `erro`, `trocou`, `voltou`, `falhaApk`, `podeInstalar`, `android` (número da versão).

## 4. A página (`celular/src/ponte-app.js` e `mineracao.html`)

### 4.1 Ponte do app
- `PAINEL = "__PAINEL__"`; `window.desktop.versao = PAINEL`; `window.desktop.atualizador` com `estado`, `procurar`, `instalarApp` e `aoMudar(fn)`, para o painel desenhar.
- Ao abrir: `procurar()` (o plugin decide se já é hora) e, com o app aberto, a cada 6 horas.
- **Confirma que abriu**: no `load` da janela, se `window.irPara` existe (o script do painel rodou até o fim) e não houve nenhum erro não tratado (`error`) até ali, chama `painelOk({versao: PAINEL})`. Sem isso, o vigia da parte Android volta para a anterior.
- **Painel novo na hora**: quando o estado diz `pronta`, chama `usarPainel()` assim que (a) o app estiver na tela, (b) não houver folha aberta (`abrirFolha`: Diário, Minhas placas, ajustes da busca; Mais), nem campo de texto com o cursor, nem a configuração inicial (`#bv`), nem a tela de vincular. Confere de novo quando o app volta para a frente e a cada 2 segundos enquanto espera.
- Avisos (pelo `toast` do painel), uma vez cada: `trocou` → "Painel atualizado: versão 1.8.1"; `voltou` → "O painel 1.8.1 não abriu direito; voltei para o 1.8.0". Depois, `visto`.
- Sai a procura de versão pela API do GitHub (`conferirVersaoApp`) e `https://api.github.com` sai da política de segurança da página (`montar-www.py`): quem procura agora é a parte Android.

### 4.2 Painel (só no app: `APP`)
- Premissas › Este celular: "painel 1.8.1 · app 1.8.0"; uma linha "Atualização" com o estado em palavras ("em dia, conferido hoje às 12:40", "baixando a versão 1.8.1… 40%", "versão 1.8.1 pronta, entra quando você fechar o formulário", "sem internet agora; tenta de novo mais tarde"); botão **Procurar agora**; com .apk pronto, botão **Atualizar o app**; com falha na instalação, o motivo e o link "baixar pelo navegador" (o de hoje).
- Faixa `#app-nova` (no alto, como hoje): "Atualização do app pronta (versão 1.9.0)" com o botão **Atualizar o app**; se o Android ainda não deixa o app instalar apps, uma linha a mais: "Na primeira vez, o Android pede para deixar o Mineração instalar apps: toque em Configurações, ligue a opção e volte." O × some com a faixa até a próxima versão, como hoje.
- PC (Premissas › App do celular): cada celular mostra "painel X · app Y" (só "app Y" para os que ainda não mandam a versão da página).

## 5. Publicação (`publicar.yml`) e documentação

- Antes de montar: `python3 celular/scripts/conferir-nativo.py`.
- No passo do app do celular, depois do .apk: `montar-pacote.py` e `AssinarPainel.java` (com o keystore ainda no `RUNNER_TEMP`; ele é apagado só depois), e `painel-celular.zip` e `painel-celular.json` vão para a release junto com o .apk (também no caso "a release já existe sem o .apk").
- `CLAUDE.md`: a regra nova da versão do app (sobe só quando a parte Android muda; `conferir-nativo.py --gravar`), o pacote da página, o plugin `Atualizador` e os testes novos.
- `notas/v1.8.0.md`: "Esta é a última vez que o app do celular precisa ser baixado pelo navegador: daqui para frente ele se atualiza sozinho." Nas versões seguintes, só a página muda: "O app do celular recebe esta versão sozinho."

## 6. Testes

- **Java puro** (JUnit 4 pelo Gradle, `testReleaseUnitTest`, com `org.json` para fora do Android): conferência do manifesto (assinatura boa; assinatura de outra chave; manifesto mexido; formato, tipo, versões, SHA-256 e tamanhos inválidos), comparação de versões, regras de "página nova / precisa de app novo / .apk novo / versão ruim / mais velha", descompactar (caminhos com `..`, absolutos, `\`, limites de quantidade e tamanho, sem `index.html`, `painel.json` com outra versão), endereços permitidos nos redirecionamentos, e a máquina de estados (abrir com `pronta`, prova que confirma, prova que não confirma em 30 s, duas aberturas sem confirmar, .apk novo zera tudo, erro em qualquer passo não derruba o abrir).
- **Assinatura de ponta a ponta**: um keystore de teste (gerado com `keytool` numa pasta temporária) assina com `AssinarPainel.java`, e a mesma classe de conferência do app aceita; outra chave é recusada.
- **Página** (Playwright, `testes/atualizador.py`, com um plugin `Atualizador` de mentira): painel novo na hora; espera com folha aberta, com o cursor num campo e com o app em segundo plano; avisos de troca e de volta (uma vez); faixa e botão do .apk; texto da primeira vez; falha com o link; `painelOk` só quando a página abriu sem erro; Este celular com as duas versões; o PC mostrando "painel X · app Y".
- `conferir-nativo.py`: falha quando um arquivo da parte Android muda sem subir a versão, e passa depois de `--gravar`.
- Os de sempre: `testes/visual.py`, `testes/kryptex_app.py`, `testes/celular.py`, `testes/rolagem_fb.py`, o teste do aplicativo (Electron) e `node desktop/scripts/teste-sincronia.js`.
- **Android de verdade**: não há aceleração de emulador neste ambiente; tentar um emulador sem aceleração para um teste de ponta a ponta (página nova vinda de um servidor local, troca, volta, instalação do .apk). Para isso, só no build de teste (debug), o endereço base das releases pode ser trocado por uma variável na hora do build. Se o emulador não rodar, a primeira atualização de verdade acontece no celular do Alex, com a 1.8.1, e o desenho acima garante que o pior caso é "não atualizou".

## 7. Ordem de entrega

1. 1.8.0 (PC + app): o atualizador inteiro. O Alex instala o .apk 1.8.0 pelo navegador uma última vez (o app de hoje já avisa que existe a 1.8.0).
2. Na próxima versão do painel (1.8.1 ou a que vier), conferir com o Alex que a página chegou sozinha.
