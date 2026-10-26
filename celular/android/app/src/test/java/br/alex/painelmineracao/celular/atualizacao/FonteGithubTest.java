package br.alex.painelmineracao.celular.atualizacao;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.junit.Test;

public class FonteGithubTest {
    private static final byte[] ENV = "{\"manifesto\":\"x\",\"assinatura\":\"y\"}".getBytes(StandardCharsets.UTF_8);
    private static final byte[] ZIP = {1, 2, 3, 4};

    @Test public void enderecoDeVerdade() { assertEquals("https://github.com/AlexsAzevedo/painel-mineracao/releases", FonteGithub.BASE); }

    @Test public void pedeManifestoDoLatest() throws Exception {
        try (Servidor s = new Servidor().em("/rel/latest/download/painel-celular.json", Servidor.bytes(ENV))) {
            assertArrayEquals(ENV, new FonteGithub(s.url("/rel"), new Baixador(false)).manifesto());
            assertEquals("/rel/latest/download/painel-celular.json", s.pedidos.get(0));
        }
    }

    @Test public void pedeArquivoDaVersao() throws Exception {
        try (Servidor s = new Servidor().em("/rel/download/v1.8.1/painel-celular.zip", Servidor.bytes(ZIP))
                 .em("/rel/download/v1.8.1/Painel-de-Mineracao.apk", Servidor.bytes(ZIP))) {
            File d = Files.createTempFile("zip", ".part").toFile();
            FonteGithub f = new FonteGithub(s.url("/rel"), new Baixador(false));
            f.baixar("1.8.1", "painel-celular.zip", d, 100, ZIP.length, p -> {});
            assertArrayEquals(ZIP, Files.readAllBytes(d.toPath()));
            f.baixar("1.8.1", "Painel-de-Mineracao.apk", d, 100, ZIP.length, p -> {});
            assertEquals("/rel/download/v1.8.1/painel-celular.zip", s.pedidos.get(0));
            assertEquals("/rel/download/v1.8.1/Painel-de-Mineracao.apk", s.pedidos.get(1));
        }
    }

    @Test(expected = IllegalArgumentException.class)
    public void recusaArquivoDesconhecido() throws Exception {
        new FonteGithub("http://127.0.0.1:1/rel", new Baixador(false)).baixar("1.8.1", "../outro.txt", new File("x"), 10, 10, p -> {});
    }

    @Test(expected = IllegalArgumentException.class)
    public void recusaVersaoInvalida() throws Exception {
        new FonteGithub("http://127.0.0.1:1/rel", new Baixador(false)).baixar("1.8.1/../x", "painel-celular.zip", new File("x"), 10, 10, p -> {});
    }
}
