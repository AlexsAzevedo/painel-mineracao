"""A página do app do celular e o pacote que vai em cada release: a versão do painel dentro da página (painel.json e
ponte-app.js), a política de segurança, o zip da página, o manifesto e a assinatura (com um keystore de teste, gerado
na hora; a chave de verdade nunca entra aqui).
Uso: python3 testes/pacote_celular.py"""
import base64, hashlib, json, os, subprocess, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import RAIZ, checa, fim

CELULAR = os.path.join(RAIZ, "celular")
VERSAO_PC = json.load(open(os.path.join(RAIZ, "desktop", "package.json"), encoding="utf-8"))["version"]
VERSAO_APP = json.load(open(os.path.join(CELULAR, "package.json"), encoding="utf-8"))["version"]
TMP = tempfile.mkdtemp(prefix="pacote-celular-")


def montar_www(saida):
    r = subprocess.run([sys.executable, os.path.join(CELULAR, "scripts", "montar-www.py"), "--saida", saida], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("montar-www.py falhou: " + r.stdout + r.stderr)
    return saida


def ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def montagem():
    www = montar_www(os.path.join(TMP, "www"))
    painel = os.path.join(www, "painel.json")
    checa("painel.json com as duas versões", os.path.exists(painel) and json.load(open(painel)) == {"versao": VERSAO_PC, "app": VERSAO_APP},
          ler(painel) if os.path.exists(painel) else "sem painel.json")
    ponte = ler(os.path.join(www, "ponte-app.js"))
    checa("a ponte sabe a versão do painel", f'const PAINEL = "{VERSAO_PC}";' in ponte)
    checa("sem marcador sobrando", "__PAINEL__" not in ponte and "__VERSAO__" not in ponte)
    pagina = ler(os.path.join(www, "index.html"))
    checa("a página não fala com a API do GitHub", "api.github.com" not in pagina)
    checa("a página fala com o ntfy.sh", "connect-src https://ntfy.sh" in pagina)
    return www


def sha(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def codigo(v):
    x, y, z = (int(n) for n in v.split("."))
    return x * 10000 + y * 100 + z


def rodar(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, **(env or {})})


KS = os.path.join(TMP, "teste.p12")
CERT = os.path.join(TMP, "cert.pem")


def keystore():
    r = rodar(["keytool", "-genkeypair", "-alias", "painel", "-keyalg", "RSA", "-keysize", "2048", "-validity", "365",
               "-keystore", KS, "-storetype", "PKCS12", "-storepass", "senha123", "-keypass", "senha123", "-dname", "CN=Teste", "-noprompt"])
    if r.returncode != 0:
        raise SystemExit("keytool falhou: " + r.stderr)
    rodar(["keytool", "-exportcert", "-rfc", "-alias", "painel", "-keystore", KS, "-storepass", "senha123", "-file", CERT])


def montar_pacote(www, apk, saida):
    return rodar([sys.executable, os.path.join(CELULAR, "scripts", "montar-pacote.py"), "--www", www, "--apk", apk, "--saida", saida])


def assinar(manifesto, saida, senha="senha123"):
    return rodar(["java", os.path.join(CELULAR, "scripts", "AssinarPainel.java"), KS, manifesto, saida], {"PAINEL_KEYSTORE_SENHA": senha})


def verifica_openssl(env, cert=CERT):
    """A assinatura do envelope confere com o certificado? (pelo openssl, sem o código do app)"""
    pasta = tempfile.mkdtemp(dir=TMP)
    pub, sig, txt = (os.path.join(pasta, n) for n in ("pub.pem", "sig.bin", "manifesto.txt"))
    with open(pub, "w") as f:
        f.write(rodar(["openssl", "x509", "-pubkey", "-noout", "-in", cert]).stdout)
    with open(sig, "wb") as f:
        f.write(base64.b64decode(env["assinatura"]))
    with open(txt, "wb") as f:
        f.write(env["manifesto"].encode("utf-8"))
    return rodar(["openssl", "dgst", "-sha256", "-verify", pub, "-signature", sig, txt]).returncode == 0


def assinar_texto(texto):
    m, s = os.path.join(TMP, "texto.json"), os.path.join(TMP, "texto-env.json")
    with open(m, "w", encoding="utf-8") as f:
        f.write(texto)
    r = assinar(m, s)
    return json.load(open(s, encoding="utf-8"))["manifesto"] if r.returncode == 0 else "falhou: " + r.stdout + r.stderr


def pacote(www):
    keystore()
    apk = os.path.join(TMP, "app.apk")
    with open(apk, "wb") as f:
        f.write(b"APK de mentira " * 1000)
    s1, s2 = os.path.join(TMP, "pacote1"), os.path.join(TMP, "pacote2")
    r1, r2 = montar_pacote(www, apk, s1), montar_pacote(www, apk, s2)
    checa("montar-pacote roda", r1.returncode == 0 and r2.returncode == 0, r1.stdout + r1.stderr)
    if r1.returncode != 0:
        return
    zip1, zip2, manifesto = os.path.join(s1, "painel-celular.zip"), os.path.join(s2, "painel-celular.zip"), os.path.join(s1, "manifesto.json")
    checa("zip igual nas duas montagens", sha(zip1) == sha(zip2))
    arquivos_www = [os.path.relpath(os.path.join(d, n), www).replace(os.sep, "/") for d, _, ns in os.walk(www) for n in ns]
    nomes = zipfile.ZipFile(zip1).namelist()
    checa("zip com os arquivos da página, em ordem", nomes == sorted(arquivos_www), nomes)
    texto = open(manifesto, encoding="utf-8").read()
    m = json.loads(texto)
    checa("manifesto compacto e na ordem", list(m) == ["formato", "tipo", "versao", "appMin", "painel", "app"] and ", " not in texto and ": " not in texto, texto)
    checa("manifesto", m["formato"] == 1 and m["tipo"] == "painel-mineracao/painel-celular" and m["versao"] == VERSAO_PC and m["appMin"] == VERSAO_APP
          and m["painel"] == {"sha256": sha(zip1), "tamanho": os.path.getsize(zip1)}
          and m["app"] == {"versao": VERSAO_APP, "codigo": codigo(VERSAO_APP), "sha256": sha(apk), "tamanho": os.path.getsize(apk)}, texto)
    saida = os.path.join(TMP, "painel-celular.json")
    r = assinar(manifesto, saida)
    env = json.load(open(saida, encoding="utf-8")) if r.returncode == 0 else {}
    checa("envelope guarda o texto exato", r.returncode == 0 and env.get("manifesto") == texto and list(env) == ["manifesto", "assinatura"], r.stdout + r.stderr)
    if env:
        checa("assinatura confere com o certificado (openssl)", verifica_openssl(env) is True)
        checa("manifesto mexido não confere", verifica_openssl({**env, "manifesto": env["manifesto"].replace(VERSAO_PC, "9.9.9")}) is False)
    saida2 = os.path.join(TMP, "senha-errada.json")
    r = assinar(manifesto, saida2, senha="errada")
    checa("senha errada: falha sem gravar", r.returncode != 0 and not os.path.exists(saida2))
    checa("texto com aspas e acentos sobrevive", assinar_texto('{"a":"é \\"x\\""}') == '{"a":"é \\"x\\""}')
    checa("texto com escapes e barra sobrevive", assinar_texto('{"a":"\\n\\t\\\\ / \\u0001"}') == '{"a":"\\n\\t\\\\ / \\u0001"}')
    checa("texto com caracteres de controle de verdade sobrevive", assinar_texto('linha1\nlinha2\t\x01\x1f\x7f') == 'linha1\nlinha2\t\x01\x1f\x7f')
    r = montar_pacote(www, os.path.join(TMP, "nao-existe.apk"), os.path.join(TMP, "pacote3"))
    checa("sem o .apk, montar-pacote falha", r.returncode != 0)


www = montagem()
pacote(www)
fim()
