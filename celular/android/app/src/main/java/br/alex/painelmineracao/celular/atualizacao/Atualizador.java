package br.alex.painelmineracao.celular.atualizacao;

import java.io.File;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicBoolean;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * A máquina de estados do atualizador do app do celular (Java puro: o Android entra pelo Armazem, pela Fonte e pelo App).
 *
 * Páginas baixadas ficam em raiz/painel/<versao>/ (temporárias em raiz/painel/.tmp-<versao>/) e downloads em
 * raiz/atualizacao/. O estado guardado (chave "estado" do Armazem) diz qual página está em uso (atual), qual está em
 * prova (emProva: abriu, mas ainda não confirmou que funciona), qual está pronta para entrar, as que não abriram (ruins),
 * o .apk baixado e os avisos para a página (trocou, voltou, falhaApk). Downloads e conferências rodam fora da trava, para
 * a página poder perguntar o estado durante um download.
 */
public final class Atualizador {
    public interface Ouvinte { void mudou(JSONObject estado); }

    public static final long PROCURA_MIN = 30 * 60_000L, PROCURA_AUTO = 6 * 3_600_000L, VIGIA = 30_000L;
    private static final int VEZES_MAX = 2;

    private final File pastaPaginas, pastaDownloads;
    private final Armazem armazem;
    private final Relogio relogio;
    private final Fonte fonte;
    private final App app;
    private final Ouvinte ouvinte;

    private JSONObject est;                                    /* o estado guardado (sob a trava: this) */
    private final AtomicBoolean procurando = new AtomicBoolean(false);
    private volatile JSONObject baixando;                       /* {qual, versao, pct} durante um download */
    private volatile boolean instalando;

    public Atualizador(File raiz, Armazem armazem, Relogio relogio, Fonte fonte, App app, Ouvinte ouvinte) {
        this.pastaPaginas = new File(raiz, "painel");
        this.pastaDownloads = new File(raiz, "atualizacao");
        this.armazem = armazem;
        this.relogio = relogio;
        this.fonte = fonte;
        this.app = app;
        this.ouvinte = ouvinte;
    }

    /* ---------- JSON sem exceção verificada (o org.json do Android declara JSONException em tudo) ---------- */
    static JSONObject obj(Object... chaveValor) {
        JSONObject o = new JSONObject();
        for (int i = 0; i + 1 < chaveValor.length; i += 2) put(o, (String) chaveValor[i], chaveValor[i + 1]);
        return o;
    }

    static JSONObject put(JSONObject o, String k, Object v) {
        try { return o.put(k, v); } catch (JSONException e) { throw new IllegalStateException(e); }
    }

    private static String texto(JSONObject o, String k) { return o == null ? null : o.optString(k, null); }

    /* ---------- estado guardado ---------- */
    private JSONObject est() {
        if (est == null) {
            String s = armazem.ler("estado");
            try { est = s == null ? new JSONObject() : new JSONObject(s); } catch (JSONException e) { est = new JSONObject(); }
        }
        return est;
    }

    private void gravar() { armazem.gravar("estado", est().toString()); }

    private void avisar() {
        if (ouvinte == null) return;
        try { ouvinte.mudou(estado()); } catch (RuntimeException e) { /* quem ouve não derruba o atualizador */ }
    }

    private boolean ruim(String versao) {
        JSONArray r = est().optJSONArray("ruins");
        if (r != null) for (int i = 0; i < r.length(); i++) if (versao.equals(r.optString(i))) return true;
        return false;
    }

    private void marcarRuim(String versao) {
        JSONArray r = est().optJSONArray("ruins");
        if (r == null) { r = new JSONArray(); put(est(), "ruins", r); }
        if (!ruim(versao)) r.put(versao);
    }

    /** a página mais nova que o app já tem: a do .apk, a atual, a em prova ou a pronta */
    private String maiorPagina(String embutido) {
        String maior = Versao.valida(embutido) ? embutido : "0.0.0";
        for (String k : new String[] {"atual", "emProva", "pronta"}) {
            String v = texto(est().optJSONObject(k), "versao");
            if (Versao.valida(v) && Versao.comparar(v, maior) > 0) maior = v;
        }
        return maior;
    }

    private static boolean pastaExiste(JSONObject o) {
        String p = texto(o, "pasta");
        return p != null && new File(p).isDirectory();
    }

    /** volta da página em prova: ela vira ruim, a pasta some e a página fica sabendo (voltou) */
    private void voltarDaProva(JSONObject prova, String embutido) {
        String de = texto(prova, "versao");
        if (de != null) marcarRuim(de);
        String pasta = texto(prova, "pasta");
        if (pasta != null) Pacote.apagar(new File(pasta));
        String para = texto(est().optJSONObject("atual"), "versao");
        put(est(), "voltou", obj("de", de, "para", para != null ? para : embutido));
        est().remove("emProva");
    }

    private void limparSobras() {
        File[] ps = pastaPaginas.listFiles();
        if (ps != null) for (File f : ps) if (f.getName().startsWith(".tmp-")) Pacote.apagar(f);
        File[] ds = pastaDownloads.listFiles();
        if (ds != null) for (File f : ds) if (f.getName().endsWith(".part")) Pacote.apagar(f);
    }

    /* ---------- ao abrir o app (antes de a página carregar) ---------- */

    /** a pasta da página que deve abrir ("" = a do .apk); null se algo inesperado aconteceu (então não mexa em nada) */
    public String aoAbrir() {
        try {
            String caminho;
            synchronized (this) {
                est = null;
                long codigo = app.codigo();
                if (est().optLong("codigoApp", -1) != codigo) {
                    /* app novo (ou primeira vez): começa do zero, com a página que veio no .apk */
                    Pacote.apagar(pastaPaginas);
                    Pacote.apagar(pastaDownloads);
                    est = obj("codigoApp", codigo);
                    gravar();
                    return "";
                }
                if (!procurando.get()) limparSobras();   /* com um download no meio (atividade recriada), as sobras são dele */
                String embutido = app.painelEmbutido();
                JSONObject prova = est().optJSONObject("emProva");
                if (prova != null) {
                    int vezes = prova.optInt("vezes", 0) + 1;
                    if (vezes > VEZES_MAX || !pastaExiste(prova)) voltarDaProva(prova, embutido);
                    else put(prova, "vezes", vezes);
                }
                JSONObject pronta = est().optJSONObject("pronta");
                if (pronta != null && est().optJSONObject("emProva") == null) {
                    est().remove("pronta");
                    if (prontaValida(pronta, embutido)) put(est(), "emProva", obj("versao", texto(pronta, "versao"), "pasta", texto(pronta, "pasta"), "vezes", 1));
                }
                JSONObject atual = est().optJSONObject("atual");
                if (atual != null && (!pastaExiste(atual) || !Versao.valida(texto(atual, "versao")) || Versao.comparar(texto(atual, "versao"), Versao.valida(embutido) ? embutido : "0.0.0") <= 0)) {
                    if (texto(atual, "pasta") != null) Pacote.apagar(new File(texto(atual, "pasta")));
                    est().remove("atual");
                }
                gravar();
                JSONObject emUso = est().optJSONObject("emProva") != null ? est().optJSONObject("emProva") : est().optJSONObject("atual");
                caminho = emUso != null ? texto(emUso, "pasta") : "";
            }
            return caminho;
        } catch (Throwable t) {
            return null;
        }
    }

    /** a pronta ainda vale: a pasta existe, é mais nova que a do .apk e que a atual, e não é ruim */
    private boolean prontaValida(JSONObject pronta, String embutido) {
        String v = texto(pronta, "versao");
        if (!Versao.valida(v) || !pastaExiste(pronta) || ruim(v)) return false;
        if (Versao.valida(embutido) && Versao.comparar(v, embutido) <= 0) return false;
        String atual = texto(est().optJSONObject("atual"), "versao");
        return atual == null || !Versao.valida(atual) || Versao.comparar(v, atual) > 0;
    }

    /* ---------- procurar e baixar ---------- */

    /** a última procura foi há mais de 6 horas (ou "no futuro": o relógio do celular voltou) */
    public synchronized boolean procuraVencida() {
        long ultima = est().optLong("ultimaProcura", 0), agora = relogio.agora();
        return ultima <= 0 || ultima > agora || agora - ultima > PROCURA_AUTO;
    }

    /** procura versão nova e baixa o que precisar. Uma procura de cada vez; nunca lança. */
    public void procurar(boolean forcar) {
        if (!procurando.compareAndSet(false, true)) return;
        String versao = null;
        try {
            long agora = relogio.agora();
            synchronized (this) {
                long ultima = est().optLong("ultimaProcura", 0);
                if (!forcar && ultima > 0 && ultima <= agora && agora - ultima < PROCURA_MIN) return;
                put(est(), "ultimaProcura", agora);
                gravar();
            }
            avisar();
            Manifesto m;
            try {
                m = Manifesto.conferir(fonte.manifesto(), app.chaves());
            } catch (ProblemaAtualizacao p) {
                if (!"nao-achou".equals(p.codigo)) throw p;
                synchronized (this) { est().remove("erro"); gravar(); }   /* nenhuma release com o pacote: nada novo */
                return;
            }
            versao = m.versao;
            String embutido = app.painelEmbutido();
            boolean paginaNova, apkNovo;
            synchronized (this) {
                put(est(), "manifesto", m.texto);
                gravar();
                paginaNova = Versao.comparar(m.versao, maiorPagina(embutido)) > 0 && !ruim(m.versao) && Versao.comparar(m.appMin, app.versao()) <= 0;
                JSONObject apk = est().optJSONObject("apk");
                apkNovo = m.appCodigo > app.codigo() && !(apk != null && apk.optLong("codigo") == m.appCodigo && new File(apk.optString("arquivo")).isFile());
            }
            if (paginaNova) baixarPagina(m);
            if (apkNovo) baixarApk(m);
            synchronized (this) { est().remove("erro"); gravar(); }
        } catch (ProblemaAtualizacao p) {
            registrarErro(p.codigo, versao);
        } catch (Throwable t) {
            registrarErro("erro", versao);
        } finally {
            baixando = null;
            procurando.set(false);
            avisar();
        }
    }

    private void registrarErro(String codigo, String versao) {
        try {
            synchronized (this) {
                put(est(), "erro", obj("codigo", codigo, "versao", versao, "quando", relogio.agora()));
                gravar();
            }
        } catch (RuntimeException e) { /* sem onde guardar: fica sem o aviso */ }
    }

    private Baixador.Progresso progresso(String qual, String versao) {
        baixando = obj("qual", qual, "versao", versao, "pct", 0);
        avisar();
        return pct -> { baixando = obj("qual", qual, "versao", versao, "pct", pct); avisar(); };
    }

    private void baixarPagina(Manifesto m) throws ProblemaAtualizacao {
        File part = new File(pastaDownloads, "painel-" + m.versao + ".zip.part");
        File tmp = new File(pastaPaginas, ".tmp-" + m.versao), fim = new File(pastaPaginas, m.versao);
        try {
            if (!pastaDownloads.isDirectory() && !pastaDownloads.mkdirs()) throw new ProblemaAtualizacao("espaco", "não deu para criar " + pastaDownloads);
            if (!pastaPaginas.isDirectory() && !pastaPaginas.mkdirs()) throw new ProblemaAtualizacao("espaco", "não deu para criar " + pastaPaginas);
            Pacote.apagar(tmp);
            fonte.baixar(m.versao, FonteGithub.ZIP, part, m.painelTamanho, m.painelTamanho, progresso("painel", m.versao));
            if (part.length() != m.painelTamanho) throw new ProblemaAtualizacao("tamanho", "o zip veio com " + part.length() + " bytes");
            if (!Pacote.sha256(part).equals(m.painelSha256)) throw new ProblemaAtualizacao("sha256", "o zip não é o do manifesto");
            Pacote.extrair(part, tmp);
            Pacote.conferirPagina(tmp, m.versao);
            Pacote.apagar(fim);
            if (!tmp.renameTo(fim)) throw new ProblemaAtualizacao("espaco", "não deu para guardar a página");
            String antiga;
            synchronized (this) {
                antiga = texto(est().optJSONObject("pronta"), "pasta");
                put(est(), "pronta", obj("versao", m.versao, "pasta", fim.getAbsolutePath()));
                gravar();
            }
            if (antiga != null && !antiga.equals(fim.getAbsolutePath())) Pacote.apagar(new File(antiga));
        } catch (IOException e) {
            throw Pacote.traduzir(e);
        } finally {
            Pacote.apagar(part);
            Pacote.apagar(tmp);
        }
    }

    private void baixarApk(Manifesto m) throws ProblemaAtualizacao {
        File part = new File(pastaDownloads, "app-" + m.appCodigo + ".apk.part"), fim = new File(pastaDownloads, "app-" + m.appCodigo + ".apk");
        boolean ok = false;
        try {
            if (!pastaDownloads.isDirectory() && !pastaDownloads.mkdirs()) throw new ProblemaAtualizacao("espaco", "não deu para criar " + pastaDownloads);
            fonte.baixar(m.versao, FonteGithub.APK, part, m.appTamanho, m.appTamanho, progresso("app", m.appVersao));
            if (part.length() != m.appTamanho) throw new ProblemaAtualizacao("tamanho", "o .apk veio com " + part.length() + " bytes");
            if (!Pacote.sha256(part).equals(m.appSha256)) throw new ProblemaAtualizacao("sha256", "o .apk não é o do manifesto");
            Pacote.apagar(fim);
            if (!part.renameTo(fim)) throw new ProblemaAtualizacao("espaco", "não deu para guardar o .apk");
            app.conferirApk(fim, m);
            synchronized (this) {
                put(est(), "apk", obj("versao", m.appVersao, "codigo", m.appCodigo, "arquivo", fim.getAbsolutePath(), "sha256", m.appSha256));
                est().remove("falhaApk");
                gravar();
            }
            /* só fica o .apk desta versão */
            File[] outros = pastaDownloads.listFiles();
            if (outros != null) for (File f : outros) if (f.getName().endsWith(".apk") && !f.equals(fim)) Pacote.apagar(f);
            ok = true;
        } catch (IOException e) {
            throw Pacote.traduzir(e);
        } finally {
            Pacote.apagar(part);
            if (!ok) Pacote.apagar(fim);
        }
    }

    /* ---------- trocar de página ---------- */

    /** a pasta da página pronta, que agora entra em prova; null se não há uma que valha */
    public String usarPainel() {
        String pasta = null;
        synchronized (this) {
            JSONObject pronta = est().optJSONObject("pronta");
            if (pronta != null && est().optJSONObject("emProva") == null) {
                est().remove("pronta");
                if (prontaValida(pronta, app.painelEmbutido())) {
                    pasta = texto(pronta, "pasta");
                    put(est(), "emProva", obj("versao", texto(pronta, "versao"), "pasta", pasta, "vezes", 1));
                }
                gravar();
            }
        }
        if (pasta != null) avisar();
        return pasta;
    }

    public synchronized boolean emProva() { return est().optJSONObject("emProva") != null; }

    /** a página em prova não confirmou a tempo: volta; devolve a pasta para onde voltar ("" = a do .apk), ou null sem prova */
    public String vigiaVenceu() {
        String para;
        synchronized (this) {
            JSONObject prova = est().optJSONObject("emProva");
            if (prova == null) return null;
            voltarDaProva(prova, app.painelEmbutido());
            gravar();
            String atual = texto(est().optJSONObject("atual"), "pasta");
            para = atual != null ? atual : "";
        }
        avisar();
        return para;
    }

    /** a página da versão dada abriu direito: se estava em prova, vira a atual (e a pasta da atual de antes some) */
    public JSONObject painelOk(String versao) {
        boolean trocou = false;
        String velha = null;
        synchronized (this) {
            JSONObject prova = est().optJSONObject("emProva");
            if (prova != null && versao != null && versao.equals(texto(prova, "versao"))) {
                JSONObject antes = est().optJSONObject("atual");
                String de = texto(antes, "versao");
                velha = texto(antes, "pasta");
                put(est(), "atual", obj("versao", versao, "pasta", texto(prova, "pasta")));
                est().remove("emProva");
                put(est(), "trocou", obj("de", de != null ? de : app.painelEmbutido(), "para", versao));
                gravar();
                trocou = true;
            }
        }
        if (trocou) {
            if (velha != null) Pacote.apagar(new File(velha));
            avisar();
        }
        return estado();
    }

    /** a página já mostrou o aviso: trocou, voltou ou falhaApk */
    public void visto(String qual) {
        if (!"trocou".equals(qual) && !"voltou".equals(qual) && !"falhaApk".equals(qual)) return;
        synchronized (this) {
            if (est().remove(qual) == null) return;
            gravar();
        }
        avisar();
    }

    /* ---------- instalar o .apk ---------- */

    /** o .apk baixado, conferido de novo agora (se mudou no disco, some); null se não há */
    public File apkPronto() {
        JSONObject apk;
        synchronized (this) { apk = est().optJSONObject("apk"); }
        if (apk == null) return null;
        File f = new File(apk.optString("arquivo"));
        try {
            if (f.isFile() && apk.optLong("codigo") > app.codigo() && Pacote.sha256(f).equals(apk.optString("sha256"))) return f;
        } catch (IOException e) { /* não deu para ler: vale como mexido */ }
        synchronized (this) { est().remove("apk"); gravar(); }
        Pacote.apagar(f);
        avisar();
        return null;
    }

    /** começou (ou acabou) uma tentativa de instalar: uma tentativa nova apaga o motivo da falha anterior */
    public void instalando(boolean sim) {
        instalando = sim;
        if (sim) {
            synchronized (this) {
                if (est().remove("falhaApk") != null) gravar();
            }
        }
        avisar();
    }

    public void falhaInstalacao(String motivo) {
        instalando = false;
        synchronized (this) { put(est(), "falhaApk", motivo); gravar(); }
        avisar();
    }

    /* ---------- o estado para a página ---------- */

    static String frase(String codigo, String versao) {
        switch (codigo == null ? "" : codigo) {
            case "rede": return "sem internet agora";
            case "nao-achou": return "a versão " + (versao != null ? versao : "nova") + " ainda não está completa no GitHub";
            case "assinatura": return "a versão nova não veio com a assinatura certa";
            case "formato": return "o arquivo da versão nova veio diferente do esperado";
            case "tamanho": case "sha256": case "pacote": return "o arquivo baixado veio com defeito";
            case "espaco": return "falta espaço no celular";
            case "apk": return "o arquivo do app não é o esperado";
            case "endereco": return "o GitHub mandou para um endereço inesperado";
            default: return "erro inesperado";
        }
    }

    public synchronized JSONObject estado() {
        String embutido = app.painelEmbutido(), appVersao = app.versao();
        JSONObject e = obj("app", obj("versao", appVersao, "codigo", app.codigo()));
        JSONObject prova = est().optJSONObject("emProva"), atual = est().optJSONObject("atual");
        JSONObject emUso = prova != null ? prova : atual;
        put(e, "painel", obj("versao", emUso != null ? texto(emUso, "versao") : embutido, "origem", emUso != null ? "baixado" : "apk", "embutido", embutido));
        JSONObject pronta = est().optJSONObject("pronta");
        if (pronta != null) put(e, "pronta", obj("versao", texto(pronta, "versao")));
        if (prova != null) put(e, "emProva", obj("versao", texto(prova, "versao")));
        JSONObject apk = est().optJSONObject("apk");
        if (apk != null) put(e, "apk", obj("versao", texto(apk, "versao")));
        String mt = est().optString("manifesto", null);
        if (mt != null) {
            try {
                Manifesto m = Manifesto.doTexto(mt);
                if (Versao.comparar(m.versao, maiorPagina(embutido)) > 0 && !ruim(m.versao) && Versao.comparar(m.appMin, appVersao) > 0)
                    put(e, "precisaApp", obj("versao", m.versao));
            } catch (ProblemaAtualizacao | RuntimeException x) { /* manifesto guardado ilegível: sem esse aviso */ }
        }
        put(e, "procurando", procurando.get());
        JSONObject b = baixando;
        if (b != null) put(e, "baixando", b);
        put(e, "ultimaProcura", est().optLong("ultimaProcura", 0));
        JSONObject erro = est().optJSONObject("erro");
        if (erro != null) put(e, "erro", obj("codigo", texto(erro, "codigo"), "msg", frase(texto(erro, "codigo"), texto(erro, "versao"))));
        for (String k : new String[] {"trocou", "voltou"}) {
            JSONObject x = est().optJSONObject(k);
            if (x != null) put(e, k, obj("de", texto(x, "de"), "para", texto(x, "para")));
        }
        String falha = est().optString("falhaApk", null);
        if (falha != null) put(e, "falhaApk", falha);
        put(e, "instalando", instalando);
        return e;
    }
}
