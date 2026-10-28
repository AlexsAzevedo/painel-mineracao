"""Teste do C# do leitor da placa (desktop/placa-amd.ps1) sem Windows: tira o C# de dentro do .ps1, compila com o mcs do
Mono no modo C# 5 (o do Windows PowerShell 5.1) e roda contra o ADL de mentira (desktop/scripts/adl-falso.c), mandando os
pedidos pela entrada, como o programa faz.
Precisa de gcc e mono-mcs. Uso: python3 desktop/scripts/teste-placa-amd-cs.py"""
import json, os, re, subprocess, sys, tempfile, time

AQUI = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.dirname(AQUI)
PS1 = os.path.join(DESKTOP, "placa-amd.ps1")
falhas = []


def ok(cond, msg):
    if not cond:
        falhas.append(msg)
        print("FALHOU:", msg)


LEITURA = {"ADL2_Main_Control_Create", "ADL2_Main_Control_Destroy", "ADL2_Adapter_NumberOfAdapters_Get", "ADL2_Adapter_AdapterInfo_Get",
           "ADL2_Overdrive_Caps", "ADL2_Overdrive8_Init_Setting_Get", "ADL2_Overdrive8_Current_Setting_Get",
           "ADL2_Overdrive8_Init_SettingX2_Get", "ADL2_Overdrive8_Current_SettingX2_Get", "ADL2_New_QueryPMLogData_Get"}
ESCRITA = {"ADL2_Overdrive8_Setting_Set"}

MAIN = """using System;
public static class TesteMain {
    public static int Main(string[] a) { PlacaAmd.Rodar(Console.In, Console.Out, a.Length > 0 ? int.Parse(a[0]) : 0); return 0; }
}
"""


def extrair_cs():
    if not os.path.exists(PS1):
        raise SystemExit("FALHOU: desktop/placa-amd.ps1 não existe")
    txt = open(PS1, encoding="utf-8-sig").read()
    m = re.search(r"\$codigo = @'\r?\n(.*?)\r?\n'@", txt, re.S)
    if not m:
        raise SystemExit("FALHOU: não achei o C# entre $codigo = @' e '@ no placa-amd.ps1")
    return m.group(1)


def preparar(pasta):
    cs = extrair_cs()
    open(os.path.join(pasta, "placa.cs"), "w", encoding="utf-8").write(cs)
    open(os.path.join(pasta, "main.cs"), "w", encoding="utf-8").write(MAIN)
    for so, extra in (("libadl.so", []), ("libadl_sox2.so", ["-DSO_X2"])):
        r = subprocess.run(["gcc", "-std=c99", "-Wall", "-Werror", "-shared", "-fPIC", *extra, "-o", os.path.join(pasta, so),
                            os.path.join(AQUI, "adl-falso.c")], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("FALHOU: o ADL de mentira não compilou:\n" + r.stderr)
    r = subprocess.run(["mcs", "-langversion:5", "-warnaserror-", "-out:" + os.path.join(pasta, "placa.exe"),
                        os.path.join(pasta, "placa.cs"), os.path.join(pasta, "main.cs")], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("FALHOU: o C# não compilou no modo C# 5:\n" + r.stdout + r.stderr)
    r = subprocess.run(["mcs", "-langversion:5", "-warn:4", "-warnaserror+", "-target:library", "-out:/dev/null",
                        os.path.join(pasta, "placa.cs")], capture_output=True, text=True)
    ok(r.returncode == 0, "o C# compila sem avisos: " + r.stdout[-1500:])
    declaradas = set(re.findall(r"static\s+extern\s+int\s+(ADL2_\w+)", cs))
    ok(declaradas <= LEITURA | ESCRITA, "funções do ADL fora da lista: %s" % (declaradas - LEITURA - ESCRITA))
    return cs


def rodar(pasta, cen, pedidos, so="libadl.so", args=(), esperar=20):
    """Roda o leitor com os pedidos na entrada (que fecha no fim). Devolve (respostas, erro, chamadas, código, segundos)."""
    with open(os.path.join(pasta, "placa.exe.config"), "w") as f:
        f.write('<configuration><dllmap dll="atiadlxx.dll" target="%s"/></configuration>' % os.path.join(pasta, so))
    log = os.path.join(pasta, "falso-%s.log" % cen)
    if os.path.exists(log):
        os.remove(log)
    env = dict(os.environ, FALSO_CENARIO=cen, FALSO_LOG=log)
    entrada = "".join((p if isinstance(p, str) else json.dumps(p)) + "\n" for p in pedidos)
    t0 = time.time()
    r = subprocess.run(["mono", os.path.join(pasta, "placa.exe"), *args], input=entrada, capture_output=True, text=True, env=env, timeout=esperar)
    dt = time.time() - t0
    respostas = []
    for linha in r.stdout.splitlines():
        try:
            respostas.append(json.loads(linha))
        except Exception:
            ok(False, "%s: resposta que não é JSON: %r" % (cen, linha[:300]))
    chamadas = open(log).read().split() if os.path.exists(log) else []
    ok("PROIBIDO" not in r.stderr and "ERRADA" not in r.stderr, "%s: chamada errada ou proibida: %s" % (cen, r.stderr[-1500:]))
    ok(len(respostas) == len(pedidos), "%s: %d pedidos e %d respostas: %s" % (cen, len(pedidos), len(respostas), r.stdout[-800:]))
    return respostas, r.stderr, chamadas, r.returncode, dt


NUM = lambda atual, mn, mx, pd, **x: {"suporta": True, "min": mn, "max": mx, "passo": 1, "atual": atual, "padrao": pd, **x}
PNP1 = "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&2B6F2D5B&0&00000019"
PNP2 = "PCI\\VEN_1002&DEV_7550&SUBSYS_E4931EAE&REV_C0\\6&1A0C77E2&0&00080019"


def confere_9070(nome, p):
    ok(p.get("chave") == PNP1 and p.get("bus") == 3 and p.get("indice") == 0 and p.get("nome") == "AMD Radeon RX 9070 XT", "%s: placa %s" % (nome, {k: p.get(k) for k in ("chave", "bus", "indice", "nome")}))
    ok(p.get("deFabrica") is False and p.get("modo") == 3, "%s: deFabrica/modo %s %s" % (nome, p.get("deFabrica"), p.get("modo")))
    ok(p.get("potencia") == NUM(-20, -30, 10, 0), "%s: potência %s" % (nome, p.get("potencia")))
    ok(p.get("tensao") == NUM(-75, -200, 0, 0, offset=True), "%s: tensão %s" % (nome, p.get("tensao")))
    ok(p.get("clock") == NUM(0, -500, 1000, 0, offset=True), "%s: clock %s" % (nome, p.get("clock")))
    ok(p.get("memoria") == NUM(2518, 2518, 3000, 2518), "%s: memória %s" % (nome, p.get("memoria")))
    ok(p.get("temporizacao") == {"suporta": True, "atual": 0, "padrao": 0, "opcoes": [0, 1]}, "%s: temporização %s" % (nome, p.get("temporizacao")))
    v = p.get("ventoinha") or {}
    ok(v == {"suporta": True, "velMin": 15, "velMax": 100, "tempMin": 25, "tempMax": 100,
             "curva": [[30, 74], [50, 74], [61, 74], [72, 74], [80, 74]],
             "curvaPadrao": [[30, 15], [50, 32], [61, 49], [72, 66], [80, 100]],
             "zeroRpm": {"suporta": True, "atual": 0, "padrao": 1}}, "%s: ventoinha %s" % (nome, v))
    a = p.get("agora") or {}
    ok(a == {"clockMHz": 2950, "memoriaMHz": 2518, "tensaoMv": 850, "watts": 301, "tempC": 44, "quenteC": 61, "memoriaC": 60,
             "ventoinhaRpm": 2552, "ventoinhaPct": 74, "usoPct": 99}, "%s: agora %s" % (nome, a))


def main():
    with tempfile.TemporaryDirectory() as pasta:
        preparar(pasta)

        # a placa do Alex
        rs, err, ch, cod, dt = rodar(pasta, "9070xt", [{"id": 1, "op": "ler"}])
        if rs:
            r = rs[0]
            ok(r.get("id") == 1 and r.get("ok") is True and r.get("afterburner") is False and len(r.get("placas") or []) == 1, "9070xt: resposta %s" % json.dumps(r)[:400])
            if r.get("placas"):
                confere_9070("9070xt", r["placas"][0])
        ok(set(ch) <= LEITURA, "9070xt: chamou função que não é de leitura: %s" % (set(ch) - LEITURA))
        ok(cod == 0 and dt < 5, "9070xt: saiu com %s em %.1f s" % (cod, dt))
        ok(ch and ch[-1] == "ADL2_Main_Control_Destroy", "9070xt: o ADL não foi fechado no fim: %s" % ch[-3:])

        # só as funções X2 (driver sem as antigas)
        rs, err, ch, cod, dt = rodar(pasta, "9070xt", [{"id": 2, "op": "ler"}], so="libadl_sox2.so")
        if rs and rs[0].get("placas"):
            confere_9070("so-x2", rs[0]["placas"][0])
            ok("ADL2_Overdrive8_Init_SettingX2_Get" in ch and "ADL2_Overdrive8_Current_SettingX2_Get" in ch, "so-x2: não leu pelas X2: %s" % ch)
        else:
            ok(False, "so-x2: sem placa: %s" % rs)

        # placa sem Overdrive8, só Intel, sem o ADL
        rs, *_ = rodar(pasta, "od7", [{"id": 3, "op": "ler"}])
        ok(rs and rs[0] == {"id": 3, "ok": True, "afterburner": False, "placas": []}, "od7: %s" % rs)
        rs, *_ = rodar(pasta, "sem-amd", [{"id": 4, "op": "ler"}])
        ok(rs and rs[0].get("ok") is False and rs[0].get("erro") == "sem-amd" and rs[0].get("id") == 4, "sem-amd: %s" % rs)
        rs, err, ch, *_ = rodar(pasta, "sem-adl", [{"id": 5, "op": "ler"}])
        ok(rs and rs[0].get("ok") is False and rs[0].get("erro") == "sem-adl", "sem-adl: %s" % rs)

        # duas placas iguais em barramentos diferentes (Review Focus 3)
        rs, *_ = rodar(pasta, "duas", [{"id": 6, "op": "ler"}])
        ps = (rs[0].get("placas") if rs else None) or []
        ok([(p.get("chave"), p.get("bus"), p.get("indice")) for p in ps] == [(PNP1, 3, 0), (PNP2, 7, 4)], "duas: %s" % [(p.get("chave"), p.get("bus"), p.get("indice")) for p in ps])

        # o driver reiniciou entre duas leituras: o leitor abre o ADL de novo e responde bem
        rs, err, ch, cod, dt = rodar(pasta, "reinicia", [{"id": 7, "op": "ler"}, {"id": 8, "op": "ler"}])
        ok(len(rs) == 2 and all(r.get("ok") is True and len(r.get("placas") or []) == 1 for r in rs), "reinicia: %s" % [json.dumps(r)[:160] for r in rs])
        idx = [i for i, c in enumerate(ch) if c == "ADL2_Overdrive8_Current_Setting_Get"]
        entre = ch[idx[1]:idx[2]] if len(idx) >= 3 else []
        ok("ADL2_Main_Control_Destroy" in entre and "ADL2_Main_Control_Create" in entre
           and entre.index("ADL2_Main_Control_Destroy") < entre.index("ADL2_Main_Control_Create"),
           "reinicia: não fechou e abriu o ADL de novo entre a leitura que falhou e a nova: %s" % ch)

        # pedidos ruins, e um texto com escapes (o leitor de JSON)
        rs, *_ = rodar(pasta, "9070xt", ["x", {"id": 5, "op": "voar"}, '{"id":9,"op":"ler","nota":"caf\\u00e9 \\"aspas\\" \\\\ \\/ \\n","n":[1,2.5,-3e2,true,false,null]}', {"id": "a1", "op": "ler"}])
        if len(rs) == 4:
            ok(rs[0].get("id") is None and rs[0].get("ok") is False and rs[0].get("erro") == "pedido", "pedido x: %s" % rs[0])
            ok(rs[1].get("id") == 5 and rs[1].get("erro") == "pedido", "op voar: %s" % rs[1])
            ok(rs[2].get("id") == 9 and rs[2].get("ok") is True, "JSON com escapes: %s" % json.dumps(rs[2])[:200])
            ok(rs[3].get("id") == "a1" and rs[3].get("ok") is True, "id de texto: %s" % json.dumps(rs[3])[:200])

        # a vigia do processo pai: com a entrada aberta, o leitor sai quando o pai acaba
        pai = subprocess.Popen(["sleep", "1"])
        with open(os.path.join(pasta, "placa.exe.config"), "w") as f:
            f.write('<configuration><dllmap dll="atiadlxx.dll" target="%s"/></configuration>' % os.path.join(pasta, "libadl.so"))
        t0 = time.time()
        p = subprocess.Popen(["mono", os.path.join(pasta, "placa.exe"), str(pai.pid)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=dict(os.environ, FALSO_CENARIO="9070xt"))
        pai.wait()
        try:
            cod = p.wait(timeout=12)
            ok(cod == 0 and time.time() - t0 < 12, "pai: saiu com %s" % cod)
        except subprocess.TimeoutExpired:
            p.kill()
            ok(False, "pai: o leitor continuou rodando depois que o pai acabou")
        finally:
            p.stdin.close(); p.stdout.close(); p.stderr.close()

    print("tudo certo" if not falhas else "%d falha(s)" % len(falhas))
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
