package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.junit.Before;
import org.junit.Test;

public class PacoteTest {
    private File tmp;

    @Before public void pasta() throws IOException { tmp = Files.createTempDirectory("pacote").toFile(); }

    /** um zip com os arquivos (nome → bytes), na ordem */
    private File zip(Map<String, byte[]> arquivos) throws IOException {
        File z = new File(tmp, "p" + System.nanoTime() + ".zip");
        try (ZipOutputStream out = new ZipOutputStream(new FileOutputStream(z))) {
            for (Map.Entry<String, byte[]> e : arquivos.entrySet()) {
                out.putNextEntry(new ZipEntry(e.getKey()));
                out.write(e.getValue());
                out.closeEntry();
            }
        }
        return z;
    }

    private static byte[] b(String s) { return s.getBytes(StandardCharsets.UTF_8); }

    private Map<String, byte[]> pagina(String versao) {
        Map<String, byte[]> m = new LinkedHashMap<>();
        m.put("index.html", b("<!doctype html><title>Painel</title>"));
        m.put("painel.json", b("{\"versao\":\"" + versao + "\",\"app\":\"1.8.0\"}"));
        m.put("fonts/inter.woff2", new byte[] {1, 2, 3});
        return m;
    }

    private void recusa(Map<String, byte[]> arquivos) throws IOException {
        File destino = new File(tmp, "pagina");
        try {
            Pacote.extrair(zip(arquivos), destino);
            fail("devia recusar");
        } catch (ProblemaAtualizacao p) {
            assertEquals("pacote", p.codigo);
            assertFalse("a pasta de destino não fica para trás", destino.exists());
        }
    }

    private Map<String, byte[]> comEntrada(String nome) {
        Map<String, byte[]> m = pagina("1.8.1");
        m.put(nome, b("x"));
        return m;
    }

    @Test public void extraiPagina() throws Exception {
        File destino = new File(tmp, "pagina");
        Pacote.extrair(zip(pagina("1.8.1")), destino);
        assertTrue(new File(destino, "index.html").isFile());
        assertEquals(3, Files.readAllBytes(new File(destino, "fonts/inter.woff2").toPath()).length);
        Pacote.conferirPagina(destino, "1.8.1");
    }

    @Test public void recusaPontoPonto() throws Exception { recusa(comEntrada("../x")); }

    @Test public void recusaPontoPontoNoMeio() throws Exception { recusa(comEntrada("fonts/../../x")); }

    @Test public void recusaAbsoluto() throws Exception { recusa(comEntrada("/x")); }

    @Test public void recusaContraBarra() throws Exception { recusa(comEntrada("a\\b")); }

    @Test public void recusaDoisPontos() throws Exception { recusa(comEntrada("c:x")); }

    @Test public void recusaMuitosArquivos() throws Exception {
        Map<String, byte[]> m = pagina("1.8.1");
        for (int i = 0; i < 500; i++) m.put("x/" + i + ".txt", b("x"));
        recusa(m);
    }

    /** o tamanho conta pelo que sai do zip (um arquivo de zeros comprime muito) */
    @Test public void recusaArquivoGrande() throws Exception {
        Map<String, byte[]> m = pagina("1.8.1");
        m.put("grande.bin", new byte[(int) Pacote.MAX_ARQUIVO + 1]);
        recusa(m);
    }

    @Test public void recusaTotalGrande() throws Exception {
        Map<String, byte[]> m = pagina("1.8.1");
        for (int i = 0; i < 3; i++) m.put("g" + i + ".bin", new byte[15 << 20]);
        recusa(m);
    }

    @Test public void recusaDestinoExistente() throws Exception {
        File destino = new File(tmp, "ja-existe");
        assertTrue(destino.mkdirs());
        try {
            Pacote.extrair(zip(pagina("1.8.1")), destino);
            fail("devia recusar");
        } catch (ProblemaAtualizacao p) {
            assertEquals("pacote", p.codigo);
            assertTrue("não apaga uma pasta que já existia", destino.isDirectory());
        }
    }

    /** a primeira entrada sai, a segunda é recusada: nada fica para trás */
    @Test public void falhaNoMeioApagaDestino() throws Exception { recusa(comEntrada("../depois.txt")); }

    @Test public void falhaAoCriarApagaDestino() throws Exception {
        File arquivo = new File(tmp, "comum.txt");
        Files.write(arquivo.toPath(), b("x"));
        File destino = new File(arquivo, "pagina");
        try {
            Pacote.extrair(zip(pagina("1.8.1")), destino);
            fail("devia recusar");
        } catch (ProblemaAtualizacao p) {
            assertEquals("pacote", p.codigo);
            assertFalse(destino.exists());
        }
    }

    @Test public void zipQuebrado() throws Exception {
        File z = new File(tmp, "quebrado.zip");
        Files.write(z.toPath(), b("isto não é um zip"));
        File destino = new File(tmp, "pagina");
        try {
            Pacote.extrair(z, destino);
            fail("devia recusar");
        } catch (ProblemaAtualizacao p) {
            assertEquals("pacote", p.codigo);
            assertFalse(destino.exists());
        }
    }

    @Test public void conferirPaginaSemIndex() throws Exception {
        Map<String, byte[]> m = pagina("1.8.1");
        m.remove("index.html");
        File destino = new File(tmp, "pagina");
        Pacote.extrair(zip(m), destino);
        try { Pacote.conferirPagina(destino, "1.8.1"); fail("devia recusar"); } catch (ProblemaAtualizacao p) { assertEquals("pacote", p.codigo); }
    }

    @Test public void conferirPaginaSemPainelJson() throws Exception {
        Map<String, byte[]> m = pagina("1.8.1");
        m.remove("painel.json");
        File destino = new File(tmp, "pagina");
        Pacote.extrair(zip(m), destino);
        try { Pacote.conferirPagina(destino, "1.8.1"); fail("devia recusar"); } catch (ProblemaAtualizacao p) { assertEquals("pacote", p.codigo); }
    }

    @Test public void conferirPaginaVersaoDiferente() throws Exception {
        File destino = new File(tmp, "pagina");
        Pacote.extrair(zip(pagina("1.0.0")), destino);
        try { Pacote.conferirPagina(destino, "1.8.1"); fail("devia recusar"); } catch (ProblemaAtualizacao p) { assertEquals("pacote", p.codigo); }
    }

    @Test public void traduzEspaco() {
        assertEquals("espaco", Pacote.traduzir(new IOException("write failed: ENOSPC (No space left on device)")).codigo);
        assertEquals("pacote", Pacote.traduzir(new IOException("invalid entry compressed size")).codigo);
    }

    @Test public void sha256() throws Exception {
        File f = new File(tmp, "abc.txt");
        Files.write(f.toPath(), b("abc"));
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", Pacote.sha256(f));
    }

    @Test public void apagarPastaInteira() throws Exception {
        File destino = new File(tmp, "pagina");
        Pacote.extrair(zip(pagina("1.8.1")), destino);
        Pacote.apagar(destino);
        assertFalse(destino.exists());
    }
}
