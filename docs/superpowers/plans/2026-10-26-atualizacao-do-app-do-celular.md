# App do celular que se atualiza sozinho (1.8.0): plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** o app Android passa a trocar a página (o painel) sozinho, assinada com a chave do app, e a baixar o .apk novo para instalar com um toque; a publicação monta e assina o pacote da página. Sai como 1.8.0 (PC e app).

**Arquitetura:** a lógica do atualizador fica em Java puro (`…/celular/atualizacao/`: versões, manifesto assinado, download, descompactar, máquina de estados), testada no JVM com JUnit. Um plugin Capacitor fino (`AtualizadorPlugin`) liga essa lógica ao Android: escolhe a pasta da página antes de ela carregar (`CapWebViewSettings.serverBasePath`), troca com `bridge.setServerBasePath`, vigia a página nova por 30 s e instala o .apk pelo `PackageInstaller`. A página (`ponte-app.js`) decide a hora da troca e mostra os avisos; o painel (`mineracao.html`) desenha o estado em Este celular e na faixa `#app-nova`. A publicação ganha `montar-pacote.py` (zip + manifesto) e `AssinarPainel.java` (assina com o keystore do .apk).

**Tecnologia:** Java 17+ (Android, AGP 8.13, compileSdk 36, minSdk 24), JUnit 4.13.2 e `org.json:json:20250517` só nos testes do JVM; Capacitor 8.5.3 (`Plugin`, `Bridge.setServerBasePath`); Python 3 + Playwright (testes da página); Java 21 `java Arquivo.java` (assinar na publicação); GitHub Actions.

**Especificação:** `docs/superpowers/specs/2026-10-26-atualizacao-do-app-do-celular-design.md`.

## Global Constraints

- Textos da tela em português do Brasil, frases curtas, sem jargão.
- Nada vai para o `main` sem o OK do Alex: o push no `main` publica a release. Trabalho no branch `atualizacao-celular-1.8.0`.
- A chave de assinatura nunca vai para o repositório nem para um arquivo fora do keystore; os testes usam keystores gerados na hora, numa pasta temporária.
- Nunca `--com-dados`. Testes só com dados inventados.
- Pacote do app: `br.alex.painelmineracao.celular`. Código novo: `celular/android/app/src/main/java/br/alex/painelmineracao/celular/` (plugin e adaptadores) e `…/celular/atualizacao/` (Java puro, sem `android.*`).
- Endereços fixos: base `https://github.com/AlexsAzevedo/painel-mineracao/releases`; manifesto `…/latest/download/painel-celular.json`; arquivos `…/download/v<versao>/painel-celular.zip` e `…/download/v<versao>/Painel-de-Mineracao.apk`.
- Manifesto: `{"formato":1,"tipo":"painel-mineracao/painel-celular","versao":"X.Y.Z","appMin":"X.Y.Z","painel":{"sha256":"<64 hex>","tamanho":N},"app":{"versao":"X.Y.Z","codigo":N,"sha256":"<64 hex>","tamanho":N}}`; envelope `{"manifesto":"<texto>","assinatura":"<base64>"}`; assinatura `SHA256withRSA` sobre os bytes UTF-8 de `manifesto`.
- Limites: envelope até 64 KB; zip até 20 MB; .apk até 100 MB; descompactar até 500 arquivos, 40 MB no total, 20 MB por arquivo.
- Tempos: procurar sem forçar só depois de 30 min da última; ao abrir o app, procura se a última foi há mais de 6 h; com o app aberto, a página pede a cada 6 h; vigia de 30 s com o app na tela; a página confere a cada 2 s se já pode trocar.
- Prazos de rede: 15 s para conectar, 30 s sem receber; no máximo 5 redirecionamentos, todos em HTTPS.
- A versão do app (`celular/package.json`) só sobe quando a parte Android muda; `celular/scripts/conferir-nativo.py` garante. A versão da página é a de `desktop/package.json`.
- Sem emulador (não há `/dev/kvm`): nenhuma tarefa depende de rodar o app num Android.
- Ids e funções de que `desktop/scripts/teste.js` e os testes dependem continuam: `#estecel-p`, `#estecel-versao`, `#estecel-info`, `#estecel-atualizar`, `#estecel-baixar`, `#estecel-desvincular`, `#estecel-status`, `#app-nova`, `#appcel-lista`, `renderAppCel`, `renderAppNova`, `toast`, `abrirFolha`, `fecharFolha`, `irPara`.

## Review Focus

1. **Relógio do celular errado** (a última procura fica "no futuro"): a pessoa espera que o app continue procurando. Uma última procura com hora maior que agora conta como vencida (teste na Tarefa 6).
2. **App fechado no meio de um download ou de descompactar** (sobram `.part` e `.tmp-*`): a pessoa espera que na próxima vez tudo funcione normal. `aoAbrir` apaga as sobras e a próxima procura baixa de novo (teste na Tarefa 6).
3. **Celular sem espaço ao descompactar**: nada pela metade entra; fica a página de antes e o erro "falta espaço no celular" (testes na Tarefa 4 e na Tarefa 6).
4. **Release com o manifesto mas sem o zip ou o .apk** (upload que falhou no meio): mostra que a versão ainda não está completa, não trava e tenta de novo na próxima procura (teste na Tarefa 6).
5. **Dois toques rápidos** em Atualizar o app ou em Procurar agora: uma instalação e uma procura só (testes na Tarefa 6 e na Tarefa 10).

---

### Task 1: Conferência da parte Android (`conferir-nativo.py`)

**Files:**
- Create: `celular/scripts/conferir-nativo.py`, `celular/nativo.json`
- Test: `testes/conferir_nativo.py`

**Interfaces:**
- Produces: `python3 celular/scripts/conferir-nativo.py [--gravar] [--raiz <pasta>]`. Sai com 0 e "parte Android conferida: app X.Y.Z" quando bate; com 1 e uma frase dizendo o que fazer quando não bate. `--raiz` é a pasta do repositório (padrão: a deste script, dois níveis acima). `celular/nativo.json`: `{"app": "<versão de celular/package.json>", "resumo": "<sha256 hex>"}`.
- Resumo: SHA-256 de, em ordem de caminho: cada arquivo de `git ls-files celular/android` (caminho relativo + `\0` + bytes + `\0`), `celular/capacitor.config.json` (idem) e o texto `json.dumps` (chaves em ordem) das entradas `@capacitor/*` de `dependencies` e `devDependencies` de `celular/package.json`.

- [ ] **Step 1: Escrever o teste** `testes/conferir_nativo.py` (padrão dos testes: `checa`/`fim` de `apoio.py`, sem Playwright). Monta numa pasta temporária um repositório git mínimo (`celular/android/app/build.gradle`, `celular/capacitor.config.json`, `celular/package.json` com `"version": "1.0.0"` e `@capacitor/core`), e checa:
  ```python
  r = rodar("--gravar"); checa("grava o resumo", r.returncode == 0 and json.load(open(nativo))["app"] == "1.0.0")
  checa("confere sem mudança", rodar().returncode == 0)
  escrever("celular/android/app/build.gradle", "mudou"); git("add", "-A")
  r = rodar(); checa("parte Android mudou sem subir a versão: falha", r.returncode == 1 and "suba a versão do app" in r.stdout)
  versao("1.1.0"); r = rodar(); checa("versão subiu sem gravar: falha", r.returncode == 1 and "--gravar" in r.stdout)
  checa("depois de gravar, passa", rodar("--gravar").returncode == 0 and rodar().returncode == 0)
  escrever("celular/package.json", ...jsqr mudou...); checa("pacote que não é @capacitor não conta", rodar().returncode == 0)
  escrever("celular/src/ponte-app.js", "x"); git("add", "-A"); checa("página não conta", rodar().returncode == 0)
  ```
- [ ] **Step 2: Rodar e ver falhar:** `python3 testes/conferir_nativo.py` → falha (script não existe).
- [ ] **Step 3: Escrever `conferir-nativo.py`** com as mensagens: mudança sem versão nova → "A parte Android do app mudou (…). Suba a versão do app em celular/package.json e rode conferir-nativo.py --gravar."; versão nova sem gravar → "A versão do app subiu para X.Y.Z: rode celular/scripts/conferir-nativo.py --gravar."
- [ ] **Step 4: Rodar o teste e ver passar;** depois `python3 celular/scripts/conferir-nativo.py --gravar` no repositório (grava `1.7.1` e o resumo de hoje) e `python3 celular/scripts/conferir-nativo.py` → "parte Android conferida: app 1.7.1".
- [ ] **Step 5: Commit** `celular/scripts/conferir-nativo.py celular/nativo.json testes/conferir_nativo.py`.

### Task 2: A página do app sabe a versão do painel (`montar-www.py`)

**Files:**
- Modify: `celular/scripts/montar-www.py`, `celular/src/ponte-app.js:11` (só a constante nova)
- Test: `testes/pacote_celular.py` (novo; a Tarefa 3 acrescenta mais)

**Interfaces:**
- Produces: `celular/www/painel.json` = `{"versao": <desktop/package.json version>, "app": <celular/package.json version>}`; em `ponte-app.js`, `const PAINEL = "__PAINEL__";` trocado pela versão do painel (exatamente uma ocorrência, como `__VERSAO__`); a política de segurança da página sem `https://api.github.com`.

- [ ] **Step 1: Escrever o teste** em `testes/pacote_celular.py`: roda `montar-www.py --saida <tmp>/www` e checa `json.load(painel.json) == {"versao": versão do desktop, "app": versão do celular}`, `'const PAINEL = "' + versão do desktop + '"' in ponte-app.js`, `"__PAINEL__" not in ponte-app.js`, `"api.github.com" not in index.html` e `"https://ntfy.sh" in index.html`.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Mudar `montar-www.py`** (lê `REPO / "desktop" / "package.json"`, confere `X.Y.Z`, troca `__PAINEL__`, grava `painel.json`, tira `https://api.github.com` de `conexoes`) e pôr `const PAINEL = "__PAINEL__";` logo abaixo de `VERSAO` em `ponte-app.js` (o uso vem na Tarefa 9).
- [ ] **Step 4: Rodar o teste e ver passar.**
- [ ] **Step 5: Commit.**

### Task 3: Pacote da página e assinatura (`montar-pacote.py`, `AssinarPainel.java`)

**Files:**
- Create: `celular/scripts/montar-pacote.py`, `celular/scripts/AssinarPainel.java`
- Test: `testes/pacote_celular.py`

**Interfaces:**
- Consumes: `www/painel.json` (Tarefa 2).
- Produces:
  - `python3 celular/scripts/montar-pacote.py --www <pasta> --apk <arquivo.apk> --saida <pasta>` → `<saida>/painel-celular.zip` e `<saida>/manifesto.json` (o texto do manifesto, JSON compacto `separators=(",", ":")`, chaves na ordem da Global Constraints). Zip: arquivos de `--www` em ordem de caminho, data `(1980,1,1,0,0,0)`, `ZIP_DEFLATED`, permissão `0o644 << 16`; o mesmo `www` dá o mesmo zip byte a byte. `versao` e `appMin` vêm de `painel.json`; `app.versao`/`app.codigo` de `celular/package.json` (código = X·10000 + Y·100 + Z); SHA-256 e tamanhos dos arquivos.
  - `PAINEL_KEYSTORE_SENHA=… [PAINEL_KEYSTORE_ALIAS=painel] java celular/scripts/AssinarPainel.java <keystore> <manifesto.json> <saida.json>` → grava o envelope; antes de gravar, confere a própria assinatura com o certificado do apelido e sai com 1 se não bater. Lê o keystore com `KeyStore.getInstance(File, char[])` (JKS ou PKCS12). Algoritmo pela chave: RSA → `SHA256withRSA`, EC → `SHA256withECDSA`. O texto do manifesto vai para o JSON escapado à mão (`"`, `\`, controles como `\uXXXX`).

- [ ] **Step 1: Escrever os testes** em `testes/pacote_celular.py` (gera um keystore RSA 2048 com `keytool -genkeypair -alias painel -keystore <tmp>/teste.p12 -storetype PKCS12 -storepass senha123 -keypass senha123 -dname CN=Teste` e um ".apk" de mentira com bytes conhecidos):
  ```python
  checa("zip igual nas duas montagens", sha(zip1) == sha(zip2))
  checa("zip com os arquivos da página", sorted(zipfile.ZipFile(zip1).namelist()) == sorted(arquivos_www))
  m = json.loads(open(manifesto).read())
  checa("manifesto", m["formato"] == 1 and m["tipo"] == "painel-mineracao/painel-celular" and m["versao"] == VERSAO_PC and m["appMin"] == VERSAO_APP
        and m["painel"] == {"sha256": sha(zip1), "tamanho": os.path.getsize(zip1)} and m["app"]["codigo"] == codigo(VERSAO_APP) and m["app"]["sha256"] == sha(apk))
  r = assinar(); env = json.load(open(saida))
  checa("envelope guarda o texto exato", r.returncode == 0 and env["manifesto"] == open(manifesto, encoding="utf-8").read())
  checa("assinatura confere com o certificado (openssl)", verifica_openssl(env, certificado_pem) is True)
  checa("manifesto mexido não confere", verifica_openssl({**env, "manifesto": env["manifesto"].replace(VERSAO_PC, "9.9.9")}, certificado_pem) is False)
  checa("senha errada: falha sem gravar", assinar(senha="errada").returncode != 0 and not os.path.exists(saida2))
  checa("texto com aspas e acentos sobrevive", assinar_texto('{"a":"é \\"x\\""}') == '{"a":"é \\"x\\""}')
  ```
  (`verifica_openssl`: `keytool -exportcert -rfc` → `openssl x509 -pubkey -noout` → `openssl dgst -sha256 -verify pub.pem -signature sig.bin manifesto.txt`.)
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Escrever `montar-pacote.py` e `AssinarPainel.java`.**
- [ ] **Step 4: Rodar `python3 testes/pacote_celular.py` e ver passar.**
- [ ] **Step 5: Commit.**

### Task 4: Java puro — versões, manifesto e pacote

**Files:**
- Modify: `celular/android/app/build.gradle` (dependências de teste)
- Create: `…/celular/atualizacao/Versao.java`, `Manifesto.java`, `Pacote.java`, `ProblemaAtualizacao.java`
- Test: `celular/android/app/src/test/java/br/alex/painelmineracao/celular/atualizacao/VersaoTest.java`, `ManifestoTest.java`, `PacoteTest.java`

**Interfaces:**
- Produces:
  - `final class ProblemaAtualizacao extends Exception { final String codigo; ProblemaAtualizacao(String codigo, String detalhe) }`; códigos: `rede`, `nao-achou`, `assinatura`, `formato`, `tamanho`, `sha256`, `pacote`, `espaco`, `apk`, `endereco`, `erro`.
  - `final class Versao { static boolean valida(String v); static int comparar(String a, String b); static long codigo(String v) }` — `valida`: `\d{1,4}\.\d{1,2}\.\d{1,2}`; `comparar` lança `IllegalArgumentException` para inválida; `codigo("1.8.0") == 10800`.
  - `final class Manifesto { final String texto, versao, appMin, painelSha256, appVersao, appSha256; final long painelTamanho, appCodigo, appTamanho; static Manifesto conferir(byte[] envelope, List<PublicKey> chaves) throws ProblemaAtualizacao; static Manifesto doTexto(String texto) throws ProblemaAtualizacao }` — `conferir`: envelope até 64 KB, assinatura base64 válida com alguma das chaves (algoritmo pela chave), depois `doTexto`; `doTexto` valida formato, tipo, versões, sha (`[0-9a-f]{64}`), tamanhos (página 1..20 MB, .apk 1..100 MB) e `app.codigo == Versao.codigo(app.versao)`. Assinatura que não bate → `assinatura`; o resto → `formato`.
  - `final class Pacote { static final int MAX_ARQUIVOS = 500; static final long MAX_TOTAL = 40L << 20, MAX_ARQUIVO = 20L << 20; static String sha256(File f) throws IOException; static void extrair(File zip, File destino) throws ProblemaAtualizacao; static void conferirPagina(File pasta, String versao) throws ProblemaAtualizacao; static ProblemaAtualizacao traduzir(IOException e); static void apagar(File f) }` — `extrair` exige que `destino` não exista, recusa (`pacote`) nome vazio, com `..`, começando por `/`, com `\` ou `:`, mais arquivos ou bytes que os limites (contando os bytes lidos, não o tamanho declarado); erro de disco passa por `traduzir` (mensagem com "ENOSPC" ou "No space" → `espaco`; outra → `pacote`); qualquer falha apaga `destino`. `conferirPagina` exige `index.html` e `painel.json` com `versao` igual.

- [ ] **Step 1: Pôr no `app/build.gradle`** `testImplementation "junit:junit:$junitVersion"` e `testImplementation "org.json:json:20250517"`.
- [ ] **Step 2: Escrever os testes JUnit** (nomes e o que cada um afirma):
  - `VersaoTest`: `compara("1.10.0" > "1.9.9")`, `igual("1.8.0","1.8.0") == 0`, `invalidaLanca("1.8")`, `codigo("1.8.0") == 10800`, `codigo("2.0.12") == 20012`.
  - `ManifestoTest` (par RSA gerado no teste com `KeyPairGenerator`, envelope montado no teste): `aceitaAssinado`, `recusaOutraChave` (código `assinatura`), `recusaTextoMexido` (`assinatura`), `recusaEnvelopeGrande` (65 KB → `formato`), `recusaTipoErrado`, `recusaFormato2`, `recusaVersaoRuim` ("1.8"), `recusaShaCurto`, `recusaTamanhoZero`, `recusaPainelGrande` (20 MB + 1), `recusaCodigoQueNaoBateComVersao`, `doTextoLeOQueFoiConferido`, e `assinadoPeloScript`: gera keystore com `keytool` (de `java.home`), monta um `manifesto.json`, roda `java …/celular/scripts/AssinarPainel.java` por `ProcessBuilder` (caminho a partir de `System.getProperty("user.dir")`, que é `celular/android/app`), e `Manifesto.conferir` aceita com a chave pública do certificado do keystore.
  - `PacoteTest` (zips montados no teste): `extraiPagina`, `recusaPontoPonto` (`../x`), `recusaAbsoluto` (`/x`), `recusaContraBarra` (`a\\b`), `recusaMuitosArquivos` (501), `recusaArquivoGrande` (entrada que descompacta para 20 MB + 1 com tamanho declarado falso), `recusaDestinoExistente`, `falhaApagaDestino` (destino dentro de um arquivo comum, que não pode ter pastas: falha com `pacote` e nada fica para trás), `conferirPaginaSemIndex`, `conferirPaginaVersaoDiferente`, `traduzEspaco` (`traduzir(new IOException("write failed: ENOSPC (No space left on device)")).codigo == "espaco"`; outra mensagem → `pacote`).
- [ ] **Step 3: Rodar e ver falhar:** `cd celular/android && ANDROID_HOME=/home/claude/android-sdk ./gradlew --no-daemon -q testDebugUnitTest` → falha de compilação (classes não existem).
- [ ] **Step 4: Escrever as quatro classes.**
- [ ] **Step 5: Rodar os testes e ver passar.**
- [ ] **Step 6: Commit.**

### Task 5: Java puro — download e endereços (`Baixador`, `FonteGithub`)

**Files:**
- Create: `…/celular/atualizacao/Baixador.java`, `Fonte.java`, `FonteGithub.java`
- Test: `…/test/…/atualizacao/BaixadorTest.java`, `FonteGithubTest.java`

**Interfaces:**
- Consumes: `ProblemaAtualizacao` (Tarefa 4).
- Produces:
  - `final class Baixador { interface Progresso { void pct(int pct); } Baixador(boolean soHttps); byte[] ler(String url, int max) throws ProblemaAtualizacao; void baixar(String url, File destino, long max, long esperado, Progresso p) throws ProblemaAtualizacao }` — `HttpURLConnection`, sem seguir redirecionamento sozinho; até 5 (301, 302, 303, 307, 308; `Location` relativo resolvido); com `soHttps`, todo endereço (o primeiro e os redirecionamentos) precisa ser `https` (senão `endereco`); 404 → `nao-achou`; outro código fora de 2xx, falha de conexão, prazo (15 s conectar, 30 s leitura) ou mais de 5 redirecionamentos → `rede`; passar de `max` (pelo `Content-Length` ou contando) → `tamanho` e apaga `destino`; `IOException` de disco passa por `Pacote.traduzir`. `pct` vai de 0 a 100 pelo `esperado`. Cabeçalho `User-Agent: PainelMineracao-App`.
  - `interface Fonte { byte[] manifesto() throws ProblemaAtualizacao; void baixar(String versao, String arquivo, File destino, long max, long esperado, Baixador.Progresso p) throws ProblemaAtualizacao; }`
  - `final class FonteGithub implements Fonte { static final String BASE = "https://github.com/AlexsAzevedo/painel-mineracao/releases"; FonteGithub(String base, Baixador b) }` — manifesto: `base + "/latest/download/painel-celular.json"` (máx. 65 536); arquivo: `base + "/download/v" + versao + "/" + arquivo`, com `arquivo` só `painel-celular.zip` ou `Painel-de-Mineracao.apk` (outro → `IllegalArgumentException`).

- [ ] **Step 1: Escrever os testes** (servidor local `com.sun.net.httpserver.HttpServer` na porta 0, `new Baixador(false)`):
  - `BaixadorTest`: `baixaComProgresso` (pct chega a 100, bytes iguais), `segueRedirecionamentos` (3 saltos), `seisRedirecionamentosFalha` (`rede`), `notFound` (`nao-achou`), `erro500` (`rede`), `contentLengthMaiorQueMax` (`tamanho`, sem arquivo), `corpoMaiorQueMaxSemContentLength` (`tamanho`, arquivo apagado), `soHttpsRecusaHttp` (`new Baixador(true).ler("http://127.0.0.1:…")` → `endereco`), `lerRespeitaMax`.
  - `FonteGithubTest` (servidor local como `base`): `pedeManifestoDoLatest` (caminho `/latest/download/painel-celular.json`), `pedeArquivoDaVersao` (caminho `/download/v1.8.1/painel-celular.zip`), `recusaArquivoDesconhecido`.
- [ ] **Step 2: Rodar e ver falhar** (`testDebugUnitTest`).
- [ ] **Step 3: Escrever as classes.**
- [ ] **Step 4: Rodar e ver passar.**
- [ ] **Step 5: Commit.**

### Task 6: Java puro — a máquina de estados (`Atualizador`)

**Files:**
- Create: `…/celular/atualizacao/Atualizador.java`, `Armazem.java`, `Relogio.java`, `App.java`
- Test: `…/test/…/atualizacao/AtualizadorTest.java` (com `ArmazemMemoria`, `RelogioFalso`, `FonteFalsa`, `AppFalso` no próprio teste)

**Interfaces:**
- Consumes: Tarefas 4 e 5.
- Produces:
  - `interface Armazem { String ler(String chave); void gravar(String chave, String valor); }` (gravar `null` apaga; grava na hora, de forma síncrona).
  - `interface Relogio { long agora(); }`
  - `interface App { String versao(); long codigo(); String painelEmbutido(); List<PublicKey> chaves(); void conferirApk(File apk, Manifesto m) throws ProblemaAtualizacao; }`
  - `final class Atualizador` com `interface Ouvinte { void mudou(JSONObject estado); }`, constantes `PROCURA_MIN = 30 * 60_000L`, `PROCURA_AUTO = 6 * 3_600_000L`, `VIGIA = 30_000L`, e:
    - `Atualizador(File raiz, Armazem a, Relogio r, Fonte f, App app, Ouvinte o)` — pastas `raiz/painel/<versao>/`, temporárias `raiz/painel/.tmp-<versao>/`, downloads `raiz/atualizacao/` (`painel-<v>.zip.part`, `app-<codigo>.apk.part`, `app-<codigo>.apk`).
    - `String aoAbrir()` — passos 1 a 4 da especificação §3.2; devolve a pasta (absoluta) ou `""` (a do .apk); `null` só se um erro inesperado aconteceu (o plugin então não mexe em nada). Nunca lança.
    - `boolean procuraVencida()` — última procura há mais de `PROCURA_AUTO`, ou "no futuro".
    - `void procurar(boolean forcar)` — §3.3 inteira, inclusive baixar página e .apk; síncrono; uma de cada vez (`synchronized`; se já está procurando, volta na hora); sem `forcar`, só depois de `PROCURA_MIN` (ou se a última está "no futuro"). Manifesto que não existe (`nao-achou`) = "nada novo", sem erro. Nunca lança.
    - `String usarPainel()`, `boolean emProva()`, `String vigiaVenceu()`, `JSONObject painelOk(String versao)`, `void visto(String qual)` (`trocou`, `voltou`, `falhaApk`), `File apkPronto()` (confere de novo o SHA-256; se não bate, apaga e devolve `null`), `void instalando(boolean sim)`, `void falhaInstalacao(String motivo)`, `JSONObject estado()`.
  - Estado guardado: uma chave `estado` no `Armazem`, com JSON: `codigoApp`, `atual {versao,pasta}`, `emProva {versao,pasta,vezes}`, `pronta {versao,pasta}`, `ruins [..]`, `trocou {de,para}`, `voltou {de,para}`, `manifesto` (texto), `ultimaProcura`, `erro {codigo,versao,quando}`, `apk {versao,codigo,arquivo,sha256}`, `falhaApk`.
  - `estado()` para a página: `app {versao, codigo}`, `painel {versao, origem: "apk"|"baixado", embutido}`, `pronta`, `emProva`, `apk {versao}`, `precisaApp {versao}`, `procurando`, `baixando {qual: "painel"|"app", versao, pct}`, `ultimaProcura`, `erro {codigo, msg}`, `trocou`, `voltou`, `falhaApk`, `instalando`. Frases de `erro.msg`: `rede` "sem internet agora"; `nao-achou` "a versão X ainda não está completa no GitHub"; `assinatura` "a versão nova não veio com a assinatura certa"; `formato` "o arquivo da versão nova veio diferente do esperado"; `tamanho`/`sha256`/`pacote` "o arquivo baixado veio com defeito"; `espaco` "falta espaço no celular"; `apk` "o arquivo do app não é o esperado"; `endereco` "o GitHub mandou para um endereço inesperado"; `erro` "erro inesperado".

- [ ] **Step 1: Escrever os testes** (`AtualizadorTest`, raiz numa pasta temporária, manifestos assinados com um par RSA do teste; `FonteFalsa` serve o envelope e os arquivos de um mapa e registra os pedidos):
  - abrir: `primeiraVezDevolvePaginaDoApk` (`""`), `apkNovoApagaTudo` (codigo do `AppFalso` muda → pastas `painel/` e `atualizacao/` somem, `""`), `abrirApagaSobras` (`.tmp-1.8.1/` e `painel-1.8.1.zip.part` somem — Review Focus 2), `abrirComProntaEntraEmProva` (devolve a pasta, `emProva.vezes == 1`, `pronta` vazia), `duasAberturasSemConfirmarVoltam` (terceira chamada a `aoAbrir` → `""`, versão em `ruins`, pasta apagada, `voltou == {de:"1.8.1", para:"1.8.0"}` com embutido 1.8.0), `abrirComErroDevolveNull` (`Armazem` que lança → `null`, sem exceção).
  - troca e prova: `usarPainelSemProntaDevolveNull`, `vigiaVenceuVolta` (`""` ou a pasta de `atual`, `ruins`, `voltou`), `painelOkConfirma` (`atual` = a nova, `trocou`, pasta antiga apagada, devolve estado com `trocou`), `painelOkDeOutraVersaoNaoMuda`, `vistoLimpaAviso`.
  - procurar: `procuraBaixaPaginaNova` (`pronta == 1.8.1`, pasta com `index.html`), `naoBaixaVersaoRuim`, `naoBaixaMaisVelhaOuIgual` (1.8.0 com embutido 1.8.0), `precisaAppNovo` (`appMin` 1.9.0 → nada de página, `precisaApp == 1.9.0`), `baixaApkNovo` (`codigo` maior → `apk`; `AppFalso.conferirApk` chamado), `apkQueNaoConfereApaga` (`conferirApk` lança `apk` → arquivo apagado, `erro.codigo == "apk"`), `shaErradoNaoEntra` (`erro.codigo == "sha256"`, nada em `pronta`, sem `.part`), `manifestoInexistenteNaoEhErro` (`nao-achou` no manifesto → `erro` vazio), `zipFaltandoMostraErro` (manifesto ok, zip `nao-achou` → `erro.msg == "a versão 1.8.1 ainda não está completa no GitHub"` — Review Focus 4), `semEspacoNaoDeixaMetade` (`FonteFalsa` entrega um zip cuja extração falha → nenhuma pasta nova, `erro` de pacote; e `Pacote.traduzir` cobre `espaco` — Review Focus 3), `procuraRespeita30Min` (segunda procura sem forçar em 10 min não pede nada; com `forcar`, pede), `relogioNoFuturoContaComoVencida` (`ultimaProcura` = agora + 1 dia → `procuraVencida()` e a procura sem forçar acontece — Review Focus 1), `procurarDuasVezesAoMesmoTempo` (duas threads → um pedido de manifesto — Review Focus 5), `apkProntoConfereDeNovo` (arquivo mexido → `null`), `estadoParaAPagina` (campos e frases acima).
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Escrever as classes.**
- [ ] **Step 4: Rodar e ver passar** (todos os testes do JVM: `testDebugUnitTest`).
- [ ] **Step 5: Commit.**

### Task 7: Plugin Android, troca da página e vigia

**Files:**
- Create: `…/celular/AtualizadorPlugin.java`, `…/celular/PreferenciasAndroid.java` (`Armazem`), `…/celular/AppAndroid.java` (`App`)
- Modify: `…/celular/MainActivity.java`
- Test: `…/test/…/atualizacao/VigiaTest.java` (a conta do tempo na tela, em Java puro: `final class Vigia` em `…/atualizacao/`)

**Interfaces:**
- Consumes: `Atualizador` (Tarefa 6), `FonteGithub` (Tarefa 5).
- Produces:
  - `MainActivity.onCreate`: `registerPlugin(AtualizadorPlugin.class)` antes de `super.onCreate`.
  - `@CapacitorPlugin(name = "Atualizador") public class AtualizadorPlugin extends Plugin` com `load()`, `handleOnResume()`, `handleOnPause()` e os `@PluginMethod`: `estado`, `procurar({forcar})`, `usarPainel`, `painelOk({versao})`, `instalarApp` (Tarefa 8), `visto({qual})`; evento `estado` (o mesmo JSON de `estado()`, mais `podeInstalar` — `canRequestPackageInstalls()` no Android 8+, `true` antes — e `android` = `Build.VERSION.SDK_INT`).
  - `load()`: monta o `Atualizador` (`getContext().getFilesDir()`, `PreferenciasAndroid` "atualizador", `FonteGithub(FonteGithub.BASE, new Baixador(true))`, `AppAndroid`), chama `aoAbrir()` e, se não for `null`, grava o caminho em `getContext().getSharedPreferences("CapWebViewSettings", MODE_PRIVATE)` chave `serverBasePath` com `commit()`; se `procuraVencida()`, procura numa `ExecutorService` de uma thread só. Tudo dentro de `try { … } catch (Throwable t) { }`.
  - Trocar: `trocarPara(String pasta)` na thread principal: grava `serverBasePath` e chama `getBridge().setServerBasePath(pasta)` ou, com `""`, `getBridge().setServerAssetPath("public")`.
  - `final class Vigia { Vigia(long limite); void naFrente(long agora); void atras(long agora); void zerar(long agora, boolean naFrente); long falta(long agora); boolean venceu(long agora) }` — soma só o tempo com o app na frente.
  - `PreferenciasAndroid implements Armazem` (`commit()`); `AppAndroid implements App`: `versao`/`codigo` por `PackageInfo` (`PackageInfoCompat.getLongVersionCode`), `painelEmbutido` lendo `public/painel.json` dos assets (sem o arquivo: `"0.0.0"`), `chaves()` pelos certificados do próprio pacote (`GET_SIGNING_CERTIFICATES` e `signingInfo.getApkContentsSigners()` no Android 9+; `GET_SIGNATURES` antes) convertidos com `CertificateFactory.getInstance("X.509")`; `conferirApk` com `getPackageArchiveInfo(caminho, flags)` (nome do pacote igual; `getLongVersionCode` igual a `m.appCodigo` e maior que o instalado; certificado igual quando o Android consegue ler; sem leitura de certificado, vale o SHA-256 do manifesto) → `ProblemaAtualizacao("apk", …)`.

- [ ] **Step 1: Escrever `VigiaTest`:** `contaSoNaFrente` (na frente 10 s, atrás 1 h, na frente 15 s → `falta == 5 s`), `venceEm30s`, `zerarRecomeca`.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Escrever `Vigia`, o plugin, `PreferenciasAndroid`, `AppAndroid` e mudar `MainActivity`.** No plugin: vigia ligada quando `emProva()` (em `load`, ao receber `usarPainel` e em `handleOnResume`), `Handler(Looper.getMainLooper()).postDelayed(…, falta)`; parada em `handleOnPause` e em `painelOk`; ao vencer, `trocarPara(nucleo.vigiaVenceu())` e evento `estado`. `procurar` e `instalarApp` respondem na hora (`call.resolve(estado)`) e o andamento vai pelo evento.
- [ ] **Step 4: Rodar `testDebugUnitTest` e ver passar; `./gradlew --no-daemon assembleDebug`** compila.
- [ ] **Step 5: Commit.**

### Task 8: Instalar o .apk (`InstaladorApk`, `InstalacaoReceiver`)

**Files:**
- Create: `…/celular/InstaladorApk.java`, `…/celular/InstalacaoReceiver.java`, `…/celular/atualizacao/Instalacao.java` (decisões em Java puro)
- Modify: `celular/android/app/src/main/AndroidManifest.xml`, `AtualizadorPlugin.java` (`instalarApp`)
- Test: `…/test/…/atualizacao/InstalacaoTest.java`

**Interfaces:**
- Consumes: `Atualizador.apkPronto()`, `instalando()`, `falhaInstalacao()` (Tarefa 6); o plugin (Tarefa 7).
- Produces:
  - `final class Instalacao { enum Acao { CONFIRMAR, NADA, FALHOU } static Acao decidir(int status); static String motivo(int status, String msgDoAndroid); static boolean semPerguntar(int sdk) }` — `STATUS_PENDING_USER_ACTION` (-1) → `CONFIRMAR`; `STATUS_SUCCESS` (0) → `NADA`; o resto → `FALHOU`. `motivo`: abortada (3) → "a atualização foi cancelada"; incompatível (7) → "o app instalado foi assinado com outra chave: baixe pelo navegador"; armazenamento (6) → "falta espaço no celular"; bloqueada (2) → "o Android bloqueou a instalação"; inválido (4) → "o arquivo do app veio com defeito"; conflito (5) → "outra instalação está em andamento"; outros → "o Android não instalou (" + msg + ")". `semPerguntar(sdk) == sdk >= 31`.
  - `final class InstaladorApk { static void instalar(Context ctx, File apk) throws IOException }` — sessão `MODE_FULL_INSTALL`, `setAppPackageName`, `setSize`, `setInstallReason(INSTALL_REASON_USER)` no Android 8+, `setRequireUserAction(USER_ACTION_NOT_REQUIRED)` quando `semPerguntar`; grava com `openWrite("app.apk", 0, tamanho)` e `fsync`; `commit` com `PendingIntent.getBroadcast(ctx, 7, new Intent(ctx, InstalacaoReceiver.class).setAction(ACAO), FLAG_UPDATE_CURRENT | (sdk >= 31 ? FLAG_MUTABLE : 0))`. Em erro, `abandonSession`.
  - `public class InstalacaoReceiver extends BroadcastReceiver` (ação `br.alex.painelmineracao.celular.INSTALACAO`) — `CONFIRMAR`: abre `EXTRA_INTENT` com `FLAG_ACTIVITY_NEW_TASK`; `FALHOU`: chama o ouvinte estático (`static volatile Consumer<String> aoFalhar`, posto pelo plugin) com o motivo. 
  - Manifesto do Android: `<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>`, `<uses-permission android:name="android.permission.UPDATE_PACKAGES_WITHOUT_USER_ACTION"/>`, `<receiver android:name=".InstalacaoReceiver" android:exported="false"/>`.
  - `instalarApp` no plugin: se já `instalando`, só devolve o estado (Review Focus 5); senão `apkPronto()` (sem arquivo → `falhaInstalacao("o arquivo do app sumiu; ele é baixado de novo na próxima procura")`), `instalando(true)`, `InstaladorApk.instalar` numa thread; erro → `instalando(false)` e `falhaInstalacao`. O ouvinte do receptor faz `instalando(false)` + `falhaInstalacao(motivo)` + evento.

- [ ] **Step 1: Escrever `InstalacaoTest`:** `pendenteConfirma`, `sucessoNadaFaz`, `falhaFalha`, `motivos` (cada status → a frase acima), `semPerguntarSoNo12` (30 → false, 31 → true, 36 → true).
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Escrever as classes, o receptor, as permissões e `instalarApp`.**
- [ ] **Step 4: Rodar `testDebugUnitTest`, `assembleDebug` e `./gradlew --no-daemon lintDebug`;** conferir em `app/build/reports/lint-results-debug.txt` que não há `NewApi` nem `UnspecifiedRegisterReceiverFlag`/`UnsafeImplicitIntentLaunch` nos arquivos novos.
- [ ] **Step 5: Commit.**

### Task 9: A ponte do app (`ponte-app.js`)

**Files:**
- Modify: `celular/src/ponte-app.js`
- Test: `testes/atualizador.py` (novo)

**Interfaces:**
- Consumes: os métodos e o evento do plugin (Tarefas 7 e 8); `PAINEL` (Tarefa 2); `toast`, `irPara` (do painel).
- Produces:
  - `window.desktop.versao = PAINEL`; `quem()` → `{id, nome, app: <versão do app instalado (estado().app.versao) ou VERSAO>, painel: PAINEL}`; a tela de vincular mostra "versão ${PAINEL}".
  - `window.desktop.atualizador` (só com o plugin; senão `null`) = `Object.freeze({ estado: () => atuEst, procurar: () => …procurar({forcar:true}), instalarApp: () => …, aoMudar: (fn) => … })`; `estado()` devolve o último estado recebido (ou `null` antes do primeiro).
  - Some: `API_VERSAO`, `conferirVersaoApp`, `est.versaoNova`, `est.conferiuVersao` e `versaoNova` em `info()` (`urlApk` continua).
  - Ao começar: lê `estado()`, ouve o evento `estado`, chama `procurar({forcar:false})`; a cada 6 h com o app aberto e em `voltou()` (o plugin decide se já é hora).
  - Confirma que abriu: um ouvinte de `error` posto no começo da ponte conta erros; no `load` da janela, se `typeof window.irPara === "function"` e nenhum erro, chama `painelOk({versao: PAINEL})` e, com o estado devolvido, mostra os avisos.
  - `podeTrocar()`: `document.visibilityState === "visible"`, nenhuma `.folha-m.aberta`, `#mais` escondido, `#bv` escondido (ou inexistente), sem a tela de vincular, e o foco não está num campo de texto (`input` que não seja `button`/`checkbox`/`radio`/`range`/`submit`/`reset`/`file`, `textarea`, `select` ou `[contenteditable]`). Com `pronta`: troca se `podeTrocar()`; senão confere a cada 2 s e em `visibilitychange`.
  - Avisos, uma vez cada (depois `visto`): `trocou` → `toast("Painel atualizado: versão " + para)`; `voltou` → `toast("O painel " + de + " não abriu direito; voltei para o " + para + ".")`.

- [ ] **Step 1: Escrever `testes/atualizador.py` (parte da ponte):** monta `www` com `montar-www.py --saida <tmp> --ntfy http://127.0.0.1:<porta>/ntfy` (o mesmo servidor local responde 404 no ntfy), serve por HTTP, troca `capacitor.js` por um de mentira (`window.Capacitor = {isNativePlatform: () => true, registerPlugin: …}`) com o `Atualizador` de mentira (`window.__atu = {estado, chamadas: [], mudar(e)}`, que chama os ouvintes), põe no localStorage um `pm-codigo` válido (`PM1-` + 43 caracteres base64url) e um `pm-sinc` com `pronto: true`; tela de 390 × 844. Checagens:
  ```python
  checa("confirma que abriu", ["painelOk", {"versao": VERSAO_PC}] in chamadas(pg))
  checa("procura ao abrir", ["procurar", {"forcar": False}] in chamadas(pg))
  checa("versão da página", pg.evaluate("window.desktop.versao") == VERSAO_PC)
  pg.evaluate("__atu.mudar({...estadoBase, pronta:{versao:'9.9.9'}})"); pg.wait_for_timeout(300)
  checa("painel novo na hora", ["usarPainel"] in chamadas(pg))
  # com folha aberta: espera; ao fechar, troca em até 2,5 s
  # com o cursor num campo de texto: espera; ao sair do campo, troca
  # escondido (visibilityState = 'hidden'): espera; ao voltar ('visible' + visibilitychange), troca
  checa("aviso de troca", "Painel atualizado: versão 9.9.9" in toast_de(pg_trocou) and ["visto", {"qual": "trocou"}] in chamadas(pg_trocou))
  checa("aviso de volta", "O painel 9.9.9 não abriu direito; voltei para o 1.8.0." in toast_de(pg_voltou))
  checa("sem confirmação quando o painel quebra", not any(c[0] == "painelOk" for c in chamadas(pg_quebrado)))   # index.html servido com <script>throw new Error("teste")</script> antes de </body>
  checa("nenhum pedido à API do GitHub", not pedidos_para("api.github.com"))
  checa("sem erros", not erros_da_pagina(pg))
  ```
- [ ] **Step 2: Rodar `python3 testes/atualizador.py` e ver falhar.**
- [ ] **Step 3: Mudar `ponte-app.js`.**
- [ ] **Step 4: Rodar e ver passar; rodar `python3 testes/celular.py`** (sem mudança esperada).
- [ ] **Step 5: Commit.**

### Task 10: O painel e o PC (`mineracao.html`, `desktop/main.js`)

**Files:**
- Modify: `mineracao.html` (Este celular `#estecel-p` em ~1317, `renderAppCel`/`renderAppNova` em ~6079-6104, lista de celulares em ~6032), `desktop/main.js:703` e `:925`
- Test: `testes/atualizador.py` (parte do painel)

**Interfaces:**
- Consumes: `window.desktop.atualizador` (Tarefa 9).
- Produces:
  - Este celular: `#estecel-versao` = "painel X · app Y" (sem atualizador: "versão X"); linha "Atualização" em `#estecel-info` com `textoAtualizacaoApp(e)`; botões novos `#estecel-procurar` ("Procurar agora") e `#estecel-instalar` ("Atualizar o app", só com `apk`); `#estecel-baixar` vira "Baixar o app pelo navegador" e aparece com `falhaApk` (com o motivo em `#estecel-status`).
  - `textoAtualizacaoApp(e)` (em ordem): `instalando` → "instalando a versão Y do app…"; `baixando` → "baixando a versão V… P%"; `pronta` → "versão V pronta: entra assim que você fechar o formulário"; `apk` → "versão Y do app pronta"; `precisaApp` → "a versão V precisa do app novo"; `procurando` → "procurando versão nova…"; `erro` → "não deu para atualizar agora: " + msg; senão "em dia" + (`ultimaProcura` ? ", conferido " + `quandoVisto(ultimaProcura)` : "").
  - `#app-nova`: com `e.apk` (e fora de `remotoInfo.aviso`): "Atualização do app pronta (versão Y)." + botão "Atualizar o app" (desabilitado com `instalando`) + × (fecha até a próxima versão, `sessionStorage` `min-app-nova-fechada`); com `podeInstalar === false` e `android >= 26`, mais uma linha: "Na primeira vez, o Android pede para deixar o Mineração instalar apps: toque em Configurações, ligue a opção e volte."; com `falhaApk`, a linha do motivo e o link "Baixar pelo navegador".
  - `window.desktop.atualizador.aoMudar(renderAppCel)`.
  - PC: `main.js` guarda `a.painel = String(c.aparelho.painel).slice(0, 20)` e manda `painel` em `aparelhos`; a lista mostra "painel X · app Y · …" (sem `painel`: "app Y · …", como hoje).

- [ ] **Step 1: Escrever os testes** em `testes/atualizador.py` (parte do painel, com a mesma montagem da Tarefa 9 e, para o PC, `abrir(p, pc=True, extra=…)` de `apoio.py` com `appCelular.config` devolvendo dois aparelhos):
  ```python
  checa("versões no Este celular", texto(pg, "#estecel-versao") == f"painel {VERSAO_PC} · app {VERSAO_APP}")
  checa("em dia", "em dia, conferido" in texto(pg, "#estecel-info"))
  clica(pg, "#estecel-procurar"); checa("procurar agora força", ["procurar", {"forcar": True}] in chamadas(pg))
  mudar(apk={"versao": "1.9.0"}, podeInstalar=False, android=34)
  checa("faixa do app", "Atualização do app pronta (versão 1.9.0)." in texto(pg, "#app-nova") and "Na primeira vez, o Android pede" in texto(pg, "#app-nova"))
  clica(pg, "#app-nova .pri"); clica(pg, "#app-nova .pri")
  checa("um toque instala uma vez", [c[0] for c in chamadas(pg)].count("instalarApp") == 1)   # Review Focus 5: o botão fica desabilitado com instalando
  mudar(falhaApk="a atualização foi cancelada", apk=None)
  checa("falha com link", visivel(pg, "#estecel-baixar") and "a atualização foi cancelada" in texto(pg, "#estecel-p"))
  mudar(baixando={"qual": "painel", "versao": "1.8.1", "pct": 40}); checa("baixando", "baixando a versão 1.8.1… 40%" in texto(pg, "#estecel-info"))
  checa("lista do PC", "painel 1.8.0 · app 1.8.0" in texto(pc, "#appcel-lista") and "app 1.7.1" in texto(pc, "#appcel-lista"))
  ```
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Mudar `mineracao.html` e `desktop/main.js`.**
- [ ] **Step 4: Rodar `testes/atualizador.py`, `testes/visual.py`, `testes/celular.py`, `testes/kryptex_app.py` e ver passar.**
- [ ] **Step 5: Commit.**

### Task 11: Publicação, versão 1.8.0 e documentação

**Files:**
- Modify: `.github/workflows/publicar.yml`, `desktop/package.json`, `desktop/package-lock.json`, `celular/package.json`, `celular/package-lock.json`, `celular/nativo.json`, `mineracao.html` (`NOVIDADES`), `CLAUDE.md`, `testes/visual.py` (checagem da 1.8.0)
- Create: `notas/v1.8.0.md`
- Test: `testes/pacote_celular.py` (ensaio da publicação)

**Interfaces:**
- Consumes: tudo acima.
- Produces:
  - `publicar.yml`: depois de "Conferir a versão", passo "Conferir a parte Android do app" (`python3 celular/scripts/conferir-nativo.py`, quando `apk == 'sim'`); no passo do app, depois de conferir o .apk: `montar-pacote.py --www www --apk "$GITHUB_WORKSPACE/Painel-de-Mineracao.apk" --saida "$RUNNER_TEMP/pacote"`, `java scripts/AssinarPainel.java "$RUNNER_TEMP/painel.jks" "$RUNNER_TEMP/pacote/manifesto.json" "$GITHUB_WORKSPACE/painel-celular.json"`, cópia do zip para `$GITHUB_WORKSPACE`, e só então `rm -f "$RUNNER_TEMP/painel.jks"`; os dois arquivos vão em "Publicar a release" e em "Acrescentar o app do celular à release" (quando existem).
  - Versões 1.8.0 (desktop e celular) e `conferir-nativo.py --gravar`.
  - `NOVIDADES` 1.8.0: "O app do celular passa a se atualizar sozinho: o painel novo entra assim que é baixado, e quando a parte do Android muda ele baixa a versão nova e instala com um toque em Atualizar o app." `testes/visual.py` checa `NOVIDADES[0].v === '1.8.0'` com /atualizar sozinho/.
  - `notas/v1.8.0.md` no formato das anteriores, dizendo que esta é a última vez que o app do celular é baixado pelo navegador.
  - `CLAUDE.md`: regra nova de versão do app (sobe só com a parte Android; `conferir-nativo.py --gravar`), o pacote da página e o envelope assinado, o plugin `Atualizador` (estado, prova de 30 s, `ruins`), os testes novos (`testes/atualizador.py`, `testes/pacote_celular.py`, `testes/conferir_nativo.py`, `testDebugUnitTest`) e o passo 1 de "Publicar uma versão" reescrito.

- [ ] **Step 1: Escrever o ensaio da publicação** em `testes/pacote_celular.py` (`ensaio()`), pelo texto do `publicar.yml`: no passo "Gerar o app do celular", `montar-pacote.py` e `AssinarPainel.java` aparecem antes de `rm -f "$RUNNER_TEMP/painel.jks"`; "Publicar a release" e "Acrescentar o app do celular à release" mencionam `painel-celular.zip` e `painel-celular.json`; há o passo com `conferir-nativo.py`. Depois roda os dois comandos do passo (com o keystore de teste, um `www` montado e um .apk de mentira) e checa que o `painel-celular.json` confere com `openssl`.
- [ ] **Step 2: Rodar e ver falhar.**
- [ ] **Step 3: Mudar o `publicar.yml`, subir as versões, `--gravar`, NOVIDADES, notas, CLAUDE.md.**
- [ ] **Step 4: Rodar tudo:** `python3 testes/conferir_nativo.py`, `python3 testes/pacote_celular.py`, `python3 testes/atualizador.py`, `python3 testes/visual.py`, `python3 testes/kryptex_app.py`, `python3 testes/celular.py`, `python3 testes/rolagem_fb.py`, `node desktop/scripts/teste-sincronia.js`, `node desktop/scripts/teste-kryptex-app.js`, `node desktop/scripts/teste-sensores-amd.js`, `testDebugUnitTest`, `lintDebug`, `python3 celular/scripts/conferir-nativo.py`, o teste do aplicativo (Electron, com `PAINEL_TESTE=1`, como em `CLAUDE.md`, comparando com a última rodada: só mudam as versões e a lista de celulares com "painel 1.8.0") e uma montagem de release local (`montar-www.py`, `npx cap sync android`, `assembleRelease` com um keystore de teste, `montar-pacote.py`, `AssinarPainel.java`; o zip tem os mesmos arquivos de `android/app/src/main/assets/public` menos `cordova.js` e `cordova_plugins.js`).
- [ ] **Step 5: Commit** (sem push no `main`: publicar só com o OK do Alex).
