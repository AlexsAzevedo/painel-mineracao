package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.FileInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.KeyPair;
import java.security.KeyStore;
import java.security.PublicKey;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;
import org.junit.Test;

public class ManifestoTest {
    private static final KeyPair PAR = Assinador.par(), OUTRO = Assinador.par();
    private static final List<PublicKey> CHAVES = Collections.singletonList(PAR.getPublic());

    private static void recusa(String codigo, byte[] envelope) {
        try {
            Manifesto.conferir(envelope, CHAVES);
            fail("devia recusar com " + codigo);
        } catch (ProblemaAtualizacao p) {
            assertEquals(codigo, p.codigo);
        }
    }

    private static byte[] assinado(JSONObject m) { return Assinador.envelope(m.toString(), PAR.getPrivate()); }

    @Test public void aceitaAssinado() throws Exception {
        Manifesto m = Manifesto.conferir(assinado(Assinador.manifesto()), CHAVES);
        assertEquals("1.8.1", m.versao);
        assertEquals("1.8.0", m.appMin);
        assertEquals(Assinador.SHA_A, m.painelSha256);
        assertEquals(1000, m.painelTamanho);
        assertEquals("1.8.0", m.appVersao);
        assertEquals(10800, m.appCodigo);
        assertEquals(Assinador.SHA_B, m.appSha256);
        assertEquals(3_000_000, m.appTamanho);
    }

    @Test public void recusaOutraChave() throws Exception { recusa("assinatura", Assinador.envelope(Assinador.manifesto().toString(), OUTRO.getPrivate())); }

    @Test public void recusaTextoMexido() throws Exception {
        JSONObject env = new JSONObject(new String(assinado(Assinador.manifesto()), StandardCharsets.UTF_8));
        env.put("manifesto", env.getString("manifesto").replace("1.8.1", "1.9.9"));
        recusa("assinatura", env.toString().getBytes(StandardCharsets.UTF_8));
    }

    @Test public void recusaAssinaturaQueNaoEhBase64() throws Exception { recusa("assinatura", Assinador.envelope(Assinador.manifesto().toString(), "@@@ não é base64 @@@")); }

    @Test public void recusaEnvelopeGrande() throws Exception {
        JSONObject m = Assinador.manifesto().put("enchimento", "x".repeat(65 * 1024));
        recusa("formato", assinado(m));
    }

    @Test public void recusaEnvelopeQueNaoEhJson() throws Exception { recusa("formato", "isto não é JSON".getBytes(StandardCharsets.UTF_8)); }

    @Test public void recusaTipoErrado() throws Exception { recusa("formato", assinado(Assinador.manifesto().put("tipo", "outra-coisa"))); }

    @Test public void recusaFormato2() throws Exception { recusa("formato", assinado(Assinador.manifesto().put("formato", 2))); }

    @Test public void recusaVersaoRuim() throws Exception { recusa("formato", assinado(Assinador.manifesto().put("versao", "1.8"))); }

    @Test public void recusaAppMinRuim() throws Exception { recusa("formato", assinado(Assinador.manifesto().put("appMin", "x"))); }

    @Test public void recusaShaCurto() throws Exception { recusa("formato", assinado(Assinador.manifesto("1.8.1", "1.8.0", "abc", 1000, "1.8.0", Assinador.SHA_B, 3_000_000))); }

    @Test public void recusaShaMaiusculo() throws Exception { recusa("formato", assinado(Assinador.manifesto("1.8.1", "1.8.0", "A".repeat(64), 1000, "1.8.0", Assinador.SHA_B, 3_000_000))); }

    @Test public void recusaTamanhoZero() throws Exception { recusa("formato", assinado(Assinador.manifesto("1.8.1", "1.8.0", Assinador.SHA_A, 0, "1.8.0", Assinador.SHA_B, 3_000_000))); }

    @Test public void recusaPainelGrande() throws Exception { recusa("formato", assinado(Assinador.manifesto("1.8.1", "1.8.0", Assinador.SHA_A, (20L << 20) + 1, "1.8.0", Assinador.SHA_B, 3_000_000))); }

    @Test public void recusaApkGrande() throws Exception { recusa("formato", assinado(Assinador.manifesto("1.8.1", "1.8.0", Assinador.SHA_A, 1000, "1.8.0", Assinador.SHA_B, (100L << 20) + 1))); }

    @Test public void recusaCodigoQueNaoBateComVersao() throws Exception {
        JSONObject m = Assinador.manifesto();
        m.getJSONObject("app").put("codigo", 10801);
        recusa("formato", assinado(m));
    }

    @Test public void recusaSemApp() throws Exception {
        JSONObject m = Assinador.manifesto();
        m.remove("app");
        recusa("formato", assinado(m));
    }

    @Test public void doTextoLeOQueFoiConferido() throws Exception {
        Manifesto m = Manifesto.conferir(assinado(Assinador.manifesto()), CHAVES);
        Manifesto d = Manifesto.doTexto(m.texto);
        assertEquals(m.versao, d.versao);
        assertEquals(m.appCodigo, d.appCodigo);
        assertEquals(m.painelSha256, d.painelSha256);
    }

    /** o envelope feito pelo script da publicação (celular/scripts/AssinarPainel.java) é aceito pelo app */
    @Test public void assinadoPeloScript() throws Exception {
        File tmp = Files.createTempDirectory("assinar").toFile();
        File ks = new File(tmp, "teste.p12"), manifesto = new File(tmp, "manifesto.json"), saida = new File(tmp, "painel-celular.json");
        String bin = System.getProperty("java.home") + File.separator + "bin" + File.separator;
        rodar(tmp, bin + "keytool", "-genkeypair", "-alias", "painel", "-keyalg", "RSA", "-keysize", "2048", "-validity", "30",
            "-keystore", ks.getPath(), "-storetype", "PKCS12", "-storepass", "senha123", "-keypass", "senha123", "-dname", "CN=Teste", "-noprompt");
        Files.write(manifesto.toPath(), Assinador.manifesto().toString().getBytes(StandardCharsets.UTF_8));
        File script = new File(System.getProperty("user.dir"), "../../scripts/AssinarPainel.java").getCanonicalFile();
        rodar(tmp, bin + "java", script.getPath(), ks.getPath(), manifesto.getPath(), saida.getPath());

        KeyStore k = KeyStore.getInstance("PKCS12");
        try (FileInputStream in = new FileInputStream(ks)) { k.load(in, "senha123".toCharArray()); }
        Manifesto m = Manifesto.conferir(Files.readAllBytes(saida.toPath()), Collections.singletonList(k.getCertificate("painel").getPublicKey()));
        assertEquals("1.8.1", m.versao);
    }

    private static void rodar(File pasta, String... cmd) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(cmd).directory(pasta).redirectErrorStream(true);
        pb.environment().put("PAINEL_KEYSTORE_SENHA", "senha123");
        Process p = pb.start();
        String saida = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        if (!p.waitFor(120, TimeUnit.SECONDS) || p.exitValue() != 0) fail(String.join(" ", cmd) + " falhou: " + saida);
    }
}
