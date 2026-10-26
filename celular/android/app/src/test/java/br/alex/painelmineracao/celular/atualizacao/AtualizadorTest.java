package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.KeyPair;
import java.security.MessageDigest;
import java.security.PublicKey;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;

public class AtualizadorTest {
    private static final KeyPair PAR = Assinador.par();
    private static final long T0 = 1_793_000_000_000L;

    /* ---------- dublês ---------- */
    static final class ArmazemMemoria implements Armazem {
        final Map<String, String> m = new HashMap<>();
        boolean falhar;
        @Override public String ler(String k) { if (falhar) throw new IllegalStateException("armazém quebrado"); return m.get(k); }
        @Override public void gravar(String k, String v) { if (falhar) throw new IllegalStateException("armazém quebrado"); if (v == null) m.remove(k); else m.put(k, v); }
    }

    static final class RelogioFalso implements Relogio {
        long t = T0;
        @Override public long agora() { return t; }
    }

    static final class FonteFalsa implements Fonte {
        byte[] envelope;
        ProblemaAtualizacao manifestoFalha;
        RuntimeException quebra;
        ProblemaAtualizacao baixarFalha;
        final Map<String, byte[]> arquivos = new HashMap<>();
        final List<String> pedidos = Collections.synchronizedList(new ArrayList<>());
        CountDownLatch segurar;          /* segura o pedido do manifesto até liberar */
        final CountDownLatch entrou = new CountDownLatch(1);

        @Override public byte[] manifesto() throws ProblemaAtualizacao {
            pedidos.add("manifesto");
            entrou.countDown();
            if (segurar != null) try { segurar.await(5, TimeUnit.SECONDS); } catch (InterruptedException e) { throw new RuntimeException(e); }
            if (quebra != null) throw quebra;
            if (manifestoFalha != null) throw manifestoFalha;
            return envelope;
        }

        @Override public void baixar(String versao, String arquivo, File destino, long max, long esperado, Baixador.Progresso p) throws ProblemaAtualizacao {
            pedidos.add(versao + "/" + arquivo);
            if (baixarFalha != null) throw baixarFalha;
            byte[] b = arquivos.get(versao + "/" + arquivo);
            if (b == null) throw new ProblemaAtualizacao("nao-achou", arquivo);
            if (b.length > max) throw new ProblemaAtualizacao("tamanho", arquivo);
            try { Files.write(destino.toPath(), b); } catch (IOException e) { throw Pacote.traduzir(e); }
            p.pct(100);
        }
    }

    static final class AppFalso implements App {
        String versao = "1.8.0", embutido = "1.8.0";
        long codigo = 10800;
        final List<File> conferidos = new ArrayList<>();
        ProblemaAtualizacao falhaConferir;
        @Override public String versao() { return versao; }
        @Override public long codigo() { return codigo; }
        @Override public String painelEmbutido() { return embutido; }
        @Override public List<PublicKey> chaves() { return Collections.singletonList(PAR.getPublic()); }
        @Override public void conferirApk(File apk, Manifesto m) throws ProblemaAtualizacao {
            conferidos.add(apk);
            if (falhaConferir != null) throw falhaConferir;
        }
    }

    private File raiz;
    private ArmazemMemoria armazem;
    private RelogioFalso relogio;
    private FonteFalsa fonte;
    private AppFalso app;
    private Atualizador a;
    private final List<JSONObject> avisos = new ArrayList<>();

    @Before public void comecar() throws IOException {
        raiz = Files.createTempDirectory("atualizador").toFile();
        armazem = new ArmazemMemoria();
        relogio = new RelogioFalso();
        fonte = new FonteFalsa();
        app = new AppFalso();
        a = novo();
    }

    /** um Atualizador novo sobre o mesmo armazém e a mesma pasta (o app abrindo de novo) */
    private Atualizador novo() { return new Atualizador(raiz, armazem, relogio, fonte, app, avisos::add); }

    /* ---------- ajuda ---------- */
    static byte[] zipPagina(String versao) {
        try {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            try (ZipOutputStream z = new ZipOutputStream(b)) {
                z.putNextEntry(new ZipEntry("index.html"));
                z.write("<!doctype html><title>Painel</title>".getBytes(StandardCharsets.UTF_8));
                z.closeEntry();
                z.putNextEntry(new ZipEntry("painel.json"));
                z.write(("{\"versao\":\"" + versao + "\",\"app\":\"1.8.0\"}").getBytes(StandardCharsets.UTF_8));
                z.closeEntry();
            }
            return b.toByteArray();
        } catch (IOException e) { throw new RuntimeException(e); }
    }

    static String sha(byte[] b) {
        try {
            StringBuilder s = new StringBuilder();
            for (byte x : MessageDigest.getInstance("SHA-256").digest(b)) s.append(String.format("%02x", x & 0xff));
            return s.toString();
        } catch (Exception e) { throw new RuntimeException(e); }
    }

    static final byte[] APK = "APK de mentira".getBytes(StandardCharsets.UTF_8);

    /** publica uma release: o zip da página e o .apk na fonte, e o manifesto assinado */
    private void publicar(String versao, String appMin, byte[] zip, String appVersao, byte[] apk) {
        String texto = Assinador.manifesto(versao, appMin, sha(zip), zip.length, appVersao, sha(apk), apk.length).toString();
        fonte.envelope = Assinador.envelope(texto, PAR.getPrivate());
        fonte.arquivos.put(versao + "/painel-celular.zip", zip);
        fonte.arquivos.put(versao + "/Painel-de-Mineracao.apk", apk);
    }

    private void publicar(String versao) { publicar(versao, "1.8.0", zipPagina(versao), "1.8.0", APK); }

    private JSONObject guardado() throws Exception { return new JSONObject(armazem.m.get("estado")); }

    private File pasta(String versao) { return new File(new File(raiz, "painel"), versao); }

    /** 1.8.1 baixada e pronta (o app abriu, procurou e baixou) */
    private void comPronta() {
        a.aoAbrir();
        publicar("1.8.1");
        a.procurar(true);
    }

    /* ---------- abrir ---------- */
    @Test public void primeiraVezDevolvePaginaDoApk() { assertEquals("", a.aoAbrir()); }

    @Test public void apkNovoApagaTudo() throws Exception {
        comPronta();
        assertTrue(pasta("1.8.1").isDirectory());
        assertTrue(new File(raiz, "atualizacao").mkdirs() || new File(raiz, "atualizacao").isDirectory());
        app.codigo = 10900; app.versao = "1.9.0"; app.embutido = "1.9.0";
        assertEquals("", novo().aoAbrir());
        assertFalse(new File(raiz, "painel").exists());
        assertFalse(new File(raiz, "atualizacao").exists());
        assertFalse(guardado().has("pronta"));
    }

    @Test public void abrirApagaSobras() throws Exception {
        a.aoAbrir();
        File tmp = new File(new File(raiz, "painel"), ".tmp-1.8.1"), part = new File(new File(raiz, "atualizacao"), "painel-1.8.1.zip.part");
        assertTrue(tmp.mkdirs());
        assertTrue(part.getParentFile().mkdirs());
        Files.write(part.toPath(), new byte[] {1});
        novo().aoAbrir();
        assertFalse(tmp.exists());
        assertFalse(part.exists());
    }

    @Test public void abrirComProntaEntraEmProva() throws Exception {
        comPronta();
        String p = novo().aoAbrir();
        assertEquals(pasta("1.8.1").getAbsolutePath(), p);
        JSONObject g = guardado();
        assertEquals(1, g.getJSONObject("emProva").getInt("vezes"));
        assertFalse(g.has("pronta"));
    }

    @Test public void duasAberturasSemConfirmarVoltam() throws Exception {
        comPronta();
        assertEquals(pasta("1.8.1").getAbsolutePath(), novo().aoAbrir());   /* vezes 1 */
        assertEquals(pasta("1.8.1").getAbsolutePath(), novo().aoAbrir());   /* vezes 2 */
        Atualizador b = novo();
        assertEquals("", b.aoAbrir());                                        /* vezes 3: volta */
        assertFalse(pasta("1.8.1").exists());
        assertEquals("1.8.1", guardado().getJSONArray("ruins").getString(0));
        JSONObject v = b.estado().getJSONObject("voltou");
        assertEquals("1.8.1", v.getString("de"));
        assertEquals("1.8.0", v.getString("para"));
    }

    @Test public void abrirComErroDevolveNull() {
        armazem.falhar = true;
        assertNull(a.aoAbrir());
    }

    /* ---------- troca e prova ---------- */
    @Test public void usarPainelSemProntaDevolveNull() {
        a.aoAbrir();
        assertNull(a.usarPainel());
        assertFalse(a.emProva());
    }

    @Test public void vigiaVenceuVolta() throws Exception {
        comPronta();
        assertEquals(pasta("1.8.1").getAbsolutePath(), a.usarPainel());
        assertTrue(a.emProva());
        assertEquals("", a.vigiaVenceu());
        assertFalse(a.emProva());
        assertFalse(pasta("1.8.1").exists());
        assertEquals("1.8.1", guardado().getJSONArray("ruins").getString(0));
        assertEquals("1.8.1", a.estado().getJSONObject("voltou").getString("de"));
        assertNull("sem prova, a vigia não faz nada", a.vigiaVenceu());
    }

    @Test public void vigiaVenceuVoltaParaAAtual() throws Exception {
        comPronta();
        a.usarPainel();
        a.painelOk("1.8.1");
        publicar("1.8.2");
        a.procurar(true);
        a.usarPainel();
        assertEquals(pasta("1.8.1").getAbsolutePath(), a.vigiaVenceu());
        JSONObject v = a.estado().getJSONObject("voltou");
        assertEquals("1.8.2", v.getString("de"));
        assertEquals("1.8.1", v.getString("para"));
    }

    @Test public void painelOkConfirma() throws Exception {
        comPronta();
        a.usarPainel();
        JSONObject e = a.painelOk("1.8.1");
        assertEquals("1.8.0", e.getJSONObject("trocou").getString("de"));
        assertEquals("1.8.1", e.getJSONObject("trocou").getString("para"));
        assertEquals("1.8.1", e.getJSONObject("painel").getString("versao"));
        assertEquals("baixado", e.getJSONObject("painel").getString("origem"));
        assertFalse(a.emProva());
        publicar("1.8.2");
        a.procurar(true);
        a.usarPainel();
        a.painelOk("1.8.2");
        assertFalse("a página de antes é apagada", pasta("1.8.1").exists());
        assertTrue(pasta("1.8.2").isDirectory());
        assertEquals(pasta("1.8.2").getAbsolutePath(), novo().aoAbrir());
    }

    @Test public void painelOkDeOutraVersaoNaoMuda() {
        comPronta();
        a.usarPainel();
        a.painelOk("9.9.9");
        assertTrue(a.emProva());
    }

    @Test public void vistoLimpaAviso() throws Exception {
        comPronta();
        a.usarPainel();
        a.painelOk("1.8.1");
        a.visto("trocou");
        assertFalse(a.estado().has("trocou"));
    }

    /* ---------- procurar ---------- */
    @Test public void procuraBaixaPaginaNova() throws Exception {
        comPronta();
        assertEquals("1.8.1", a.estado().getJSONObject("pronta").getString("versao"));
        assertTrue(new File(pasta("1.8.1"), "index.html").isFile());
        assertEquals(java.util.Arrays.asList("manifesto", "1.8.1/painel-celular.zip"), fonte.pedidos);
        assertFalse("sem erro", a.estado().has("erro"));
    }

    @Test public void naoBaixaVersaoRuim() {
        comPronta();
        a.usarPainel();
        a.vigiaVenceu();
        fonte.pedidos.clear();
        a.procurar(true);
        assertEquals(Collections.singletonList("manifesto"), fonte.pedidos);
    }

    @Test public void naoBaixaMaisVelhaOuIgual() {
        a.aoAbrir();
        publicar("1.8.0");
        a.procurar(true);
        publicar("1.7.9");
        a.procurar(true);
        assertEquals(java.util.Arrays.asList("manifesto", "manifesto"), fonte.pedidos);
    }

    @Test public void precisaAppNovo() throws Exception {
        a.aoAbrir();
        publicar("1.9.0", "1.9.0", zipPagina("1.9.0"), "1.9.0", APK);
        a.procurar(true);
        assertFalse(fonte.pedidos.contains("1.9.0/painel-celular.zip"));
        JSONObject e = a.estado();
        assertEquals("1.9.0", e.getJSONObject("precisaApp").getString("versao"));
        assertEquals("1.9.0", e.getJSONObject("apk").getString("versao"));
    }

    @Test public void baixaApkNovo() throws Exception {
        a.aoAbrir();
        publicar("1.8.1", "1.8.0", zipPagina("1.8.1"), "1.8.1", APK);
        a.procurar(true);
        assertEquals("1.8.1", a.estado().getJSONObject("apk").getString("versao"));
        assertEquals(1, app.conferidos.size());
        File f = a.apkPronto();
        assertNotNull(f);
        assertArrayEquals(APK, Files.readAllBytes(f.toPath()));
        fonte.pedidos.clear();
        a.procurar(true);
        assertFalse("não baixa de novo o mesmo .apk", fonte.pedidos.contains("1.8.1/Painel-de-Mineracao.apk"));
    }

    @Test public void apkQueNaoConfereApaga() throws Exception {
        app.falhaConferir = new ProblemaAtualizacao("apk", "outro pacote");
        a.aoAbrir();
        publicar("1.8.1", "1.8.0", zipPagina("1.8.1"), "1.8.1", APK);
        a.procurar(true);
        JSONObject e = a.estado();
        assertEquals("apk", e.getJSONObject("erro").getString("codigo"));
        assertEquals("o arquivo do app não é o esperado", e.getJSONObject("erro").getString("msg"));
        assertFalse(e.has("apk"));
        File[] sobra = new File(raiz, "atualizacao").listFiles((d, n) -> n.endsWith(".apk") || n.endsWith(".part"));
        assertTrue(sobra == null || sobra.length == 0);
    }

    @Test public void shaErradoNaoEntra() throws Exception {
        a.aoAbrir();
        byte[] zip = zipPagina("1.8.1"), outro = zip.clone();
        outro[outro.length - 1] ^= 1;
        publicar("1.8.1", "1.8.0", zip, "1.8.0", APK);
        fonte.arquivos.put("1.8.1/painel-celular.zip", outro);   /* mesmo tamanho, outro conteúdo */
        a.procurar(true);
        JSONObject e = a.estado();
        assertEquals("sha256", e.getJSONObject("erro").getString("codigo"));
        assertEquals("o arquivo baixado veio com defeito", e.getJSONObject("erro").getString("msg"));
        assertFalse(e.has("pronta"));
        assertFalse(pasta("1.8.1").exists());
        String[] sobra = new File(raiz, "atualizacao").list();
        assertTrue(sobra == null || sobra.length == 0);
    }

    @Test public void manifestoInexistenteNaoEhErro() throws Exception {
        a.aoAbrir();
        fonte.manifestoFalha = new ProblemaAtualizacao("nao-achou", "sem manifesto");
        a.procurar(true);
        JSONObject e = a.estado();
        assertFalse(e.has("erro"));
        assertEquals(T0, e.getLong("ultimaProcura"));
    }

    @Test public void semInternet() throws Exception {
        a.aoAbrir();
        fonte.manifestoFalha = new ProblemaAtualizacao("rede", "sem conexão");
        a.procurar(true);
        assertEquals("sem internet agora", a.estado().getJSONObject("erro").getString("msg"));
    }

    @Test public void zipFaltandoMostraErro() throws Exception {
        a.aoAbrir();
        publicar("1.8.1");
        fonte.arquivos.remove("1.8.1/painel-celular.zip");
        a.procurar(true);
        JSONObject erro = a.estado().getJSONObject("erro");
        assertEquals("nao-achou", erro.getString("codigo"));
        assertEquals("a versão 1.8.1 ainda não está completa no GitHub", erro.getString("msg"));
        publicar("1.8.1");
        a.procurar(true);
        assertFalse("na próxima procura, baixa", a.estado().has("erro"));
        assertEquals("1.8.1", a.estado().getJSONObject("pronta").getString("versao"));
    }

    @Test public void semEspacoNaoDeixaMetade() throws Exception {
        a.aoAbrir();
        byte[] naoZip = "isto não é um zip".getBytes(StandardCharsets.UTF_8);
        publicar("1.8.1", "1.8.0", naoZip, "1.8.0", APK);
        a.procurar(true);
        assertEquals("pacote", a.estado().getJSONObject("erro").getString("codigo"));
        String[] paginas = new File(raiz, "painel").list();
        assertTrue("nenhuma pasta pela metade", paginas == null || paginas.length == 0);
        fonte.baixarFalha = new ProblemaAtualizacao("espaco", "ENOSPC");
        a.procurar(true);
        assertEquals("falta espaço no celular", a.estado().getJSONObject("erro").getString("msg"));
    }

    @Test public void procuraRespeita30Min() {
        a.aoAbrir();
        publicar("1.8.0");
        a.procurar(false);
        relogio.t += 10 * 60_000L;
        a.procurar(false);
        assertEquals(1, fonte.pedidos.size());
        a.procurar(true);
        assertEquals(2, fonte.pedidos.size());
        relogio.t += 31 * 60_000L;
        a.procurar(false);
        assertEquals(3, fonte.pedidos.size());
    }

    @Test public void relogioNoFuturoContaComoVencida() throws Exception {
        a.aoAbrir();
        publicar("1.8.0");
        relogio.t = T0 + 24 * 3_600_000L;
        a.procurar(true);                 /* a última procura fica "amanhã" */
        relogio.t = T0;                   /* o relógio do celular voltou */
        assertTrue(a.procuraVencida());
        a.procurar(false);
        assertEquals(2, fonte.pedidos.size());
    }

    @Test public void procuraVencidaDepoisDe6Horas() {
        a.aoAbrir();
        assertTrue("nunca procurou", a.procuraVencida());
        publicar("1.8.0");
        a.procurar(true);
        assertFalse(a.procuraVencida());
        relogio.t += 6 * 3_600_000L + 1;
        assertTrue(a.procuraVencida());
    }

    @Test public void procurarDuasVezesAoMesmoTempo() throws Exception {
        a.aoAbrir();
        publicar("1.8.0");
        fonte.segurar = new CountDownLatch(1);
        Thread t = new Thread(() -> a.procurar(true));
        t.start();
        assertTrue(fonte.entrou.await(5, TimeUnit.SECONDS));
        a.procurar(true);                 /* a primeira ainda está no meio: esta volta na hora */
        assertTrue(a.estado().getBoolean("procurando"));
        fonte.segurar.countDown();
        t.join(5000);
        assertEquals(1, fonte.pedidos.size());
        assertFalse(a.estado().getBoolean("procurando"));
    }

    @Test public void procurarNuncaLanca() throws Exception {
        a.aoAbrir();
        fonte.quebra = new IllegalStateException("bug");
        a.procurar(true);
        assertEquals("erro", a.estado().getJSONObject("erro").getString("codigo"));
        assertEquals("erro inesperado", a.estado().getJSONObject("erro").getString("msg"));
    }

    @Test public void apkProntoConfereDeNovo() throws Exception {
        a.aoAbrir();
        publicar("1.8.1", "1.8.0", zipPagina("1.8.1"), "1.8.1", APK);
        a.procurar(true);
        File f = a.apkPronto();
        Files.write(f.toPath(), "mexido".getBytes(StandardCharsets.UTF_8));
        assertNull(a.apkPronto());
        assertFalse(a.estado().has("apk"));
        assertFalse(f.exists());
    }

    @Test public void estadoParaAPagina() throws Exception {
        a.aoAbrir();
        JSONObject e = a.estado();
        assertEquals("1.8.0", e.getJSONObject("app").getString("versao"));
        assertEquals(10800, e.getJSONObject("app").getLong("codigo"));
        assertEquals("1.8.0", e.getJSONObject("painel").getString("versao"));
        assertEquals("apk", e.getJSONObject("painel").getString("origem"));
        assertEquals("1.8.0", e.getJSONObject("painel").getString("embutido"));
        assertFalse(e.getBoolean("procurando"));
        assertFalse(e.getBoolean("instalando"));
        assertEquals(0, e.getLong("ultimaProcura"));
        a.instalando(true);
        assertTrue(a.estado().getBoolean("instalando"));
        a.falhaInstalacao("a atualização foi cancelada");
        assertFalse(a.estado().getBoolean("instalando"));
        assertEquals("a atualização foi cancelada", a.estado().getString("falhaApk"));
        a.visto("falhaApk");
        assertFalse(a.estado().has("falhaApk"));
        assertFalse("avisa a página quando muda", avisos.isEmpty());
    }

    @Test public void frases() {
        assertEquals("sem internet agora", Atualizador.frase("rede", null));
        assertEquals("a versão 1.8.1 ainda não está completa no GitHub", Atualizador.frase("nao-achou", "1.8.1"));
        assertEquals("a versão nova não veio com a assinatura certa", Atualizador.frase("assinatura", null));
        assertEquals("o arquivo da versão nova veio diferente do esperado", Atualizador.frase("formato", null));
        assertEquals("o arquivo baixado veio com defeito", Atualizador.frase("tamanho", null));
        assertEquals("o arquivo baixado veio com defeito", Atualizador.frase("sha256", null));
        assertEquals("o arquivo baixado veio com defeito", Atualizador.frase("pacote", null));
        assertEquals("falta espaço no celular", Atualizador.frase("espaco", null));
        assertEquals("o arquivo do app não é o esperado", Atualizador.frase("apk", null));
        assertEquals("o GitHub mandou para um endereço inesperado", Atualizador.frase("endereco", null));
        assertEquals("erro inesperado", Atualizador.frase("erro", null));
        assertEquals("erro inesperado", Atualizador.frase("outra-coisa", null));
    }
}
