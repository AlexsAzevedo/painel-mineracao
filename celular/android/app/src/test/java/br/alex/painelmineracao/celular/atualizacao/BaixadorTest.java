package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

public class BaixadorTest {
    private static final byte[] CORPO = new byte[300 * 1024];
    static { new Random(7).nextBytes(CORPO); }

    private Servidor s;
    private File tmp;
    private final Baixador b = new Baixador(false);

    @Before public void comecar() throws IOException {
        s = new Servidor().em("/arq", Servidor.bytes(CORPO)).em("/partes", Servidor.emPartes(CORPO));
        tmp = Files.createTempDirectory("baixar").toFile();
    }

    @After public void parar() { s.close(); }

    private void falha(String codigo, Runnable r) {
        try { r.run(); fail("devia falhar com " + codigo); }
        catch (Falhou f) { assertEquals(codigo, f.p.codigo); }
    }

    /** para usar as chamadas que lançam ProblemaAtualizacao dentro de falha(...) */
    private static final class Falhou extends RuntimeException { final ProblemaAtualizacao p; Falhou(ProblemaAtualizacao p) { this.p = p; } }
    private interface Chamada { void rodar() throws ProblemaAtualizacao; }
    private static Runnable r(Chamada c) { return () -> { try { c.rodar(); } catch (ProblemaAtualizacao p) { throw new Falhou(p); } }; }

    @Test public void baixaComProgresso() throws Exception {
        File d = new File(tmp, "arq.bin");
        List<Integer> pcts = new ArrayList<>();
        b.baixar(s.url("/arq"), d, 1 << 20, CORPO.length, pcts::add);
        assertArrayEquals(CORPO, Files.readAllBytes(d.toPath()));
        assertEquals(100, (int) pcts.get(pcts.size() - 1));
        for (int i = 1; i < pcts.size(); i++) assertTrue("o progresso não volta", pcts.get(i) >= pcts.get(i - 1));
    }

    @Test public void segueRedirecionamentos() throws Exception {
        s.em("/r1", Servidor.redireciona(302, "/r2")).em("/r2", Servidor.redireciona(301, s.url("/r3"))).em("/r3", Servidor.redireciona(307, "arq"));
        File d = new File(tmp, "arq.bin");
        b.baixar(s.url("/r1"), d, 1 << 20, CORPO.length, p -> {});
        assertArrayEquals(CORPO, Files.readAllBytes(d.toPath()));
    }

    @Test public void cincoRedirecionamentosPassam() throws Exception {
        for (int i = 0; i < 5; i++) s.em("/c" + i, Servidor.redireciona(302, i == 4 ? "/arq" : "/c" + (i + 1)));
        assertArrayEquals(CORPO, b.ler(s.url("/c0"), 1 << 20));
    }

    @Test public void seisRedirecionamentosFalha() {
        for (int i = 0; i < 6; i++) s.em("/s" + i, Servidor.redireciona(302, i == 5 ? "/arq" : "/s" + (i + 1)));
        falha("rede", r(() -> b.ler(s.url("/s0"), 1 << 20)));
    }

    @Test public void notFound() {
        s.em("/nada", Servidor.codigo(404));
        falha("nao-achou", r(() -> b.baixar(s.url("/nada"), new File(tmp, "x"), 1 << 20, 10, p -> {})));
        assertFalse(new File(tmp, "x").exists());
    }

    @Test public void erro500() {
        s.em("/erro", Servidor.codigo(500));
        falha("rede", r(() -> b.ler(s.url("/erro"), 1000)));
    }

    @Test public void semConexao() throws Exception {
        String url = s.url("/arq");
        s.close();
        falha("rede", r(() -> b.ler(url, 1000)));
    }

    @Test public void contentLengthMaiorQueMax() {
        File d = new File(tmp, "grande.bin");
        falha("tamanho", r(() -> b.baixar(s.url("/arq"), d, 100 * 1024, 100 * 1024, p -> {})));
        assertFalse(d.exists());
    }

    @Test public void corpoMaiorQueMaxSemContentLength() {
        File d = new File(tmp, "grande.bin");
        falha("tamanho", r(() -> b.baixar(s.url("/partes"), d, 100 * 1024, 100 * 1024, p -> {})));
        assertFalse("o arquivo pela metade é apagado", d.exists());
    }

    @Test public void baixaSemContentLength() throws Exception {
        File d = new File(tmp, "partes.bin");
        b.baixar(s.url("/partes"), d, 1 << 20, CORPO.length, p -> {});
        assertArrayEquals(CORPO, Files.readAllBytes(d.toPath()));
    }

    @Test public void soHttpsRecusaHttp() {
        falha("endereco", r(() -> new Baixador(true).ler(s.url("/arq"), 1 << 20)));
        assertTrue("nem chega a pedir", s.pedidos.isEmpty());
    }

    @Test public void enderecoInvalido() { falha("endereco", r(() -> b.ler("ftp://127.0.0.1/x", 10))); }

    @Test public void lerRespeitaMax() {
        falha("tamanho", r(() -> b.ler(s.url("/arq"), 1000)));
        falha("tamanho", r(() -> b.ler(s.url("/partes"), 1000)));
    }

    @Test public void lerDevolveOsBytes() throws Exception { assertArrayEquals(CORPO, b.ler(s.url("/arq"), 1 << 20)); }

    @Test public void discoQueNaoGravaNaoViraRede() {
        File arquivo = new File(tmp, "comum.txt");
        falha("pacote", r(() -> { try { Files.write(arquivo.toPath(), new byte[] {1}); } catch (IOException e) { throw new RuntimeException(e); }
            b.baixar(s.url("/arq"), new File(arquivo, "dentro.bin"), 1 << 20, CORPO.length, p -> {}); }));
    }
}
