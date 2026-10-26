package br.alex.painelmineracao.celular.atualizacao;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;

/**
 * Downloads do atualizador. Segue no máximo 5 redirecionamentos (o GitHub manda as releases para outro servidor) e, com
 * soHttps, só aceita HTTPS em todos os endereços. Quem garante que o arquivo é nosso é a assinatura do manifesto e o
 * SHA-256, não o endereço. Prazos: 15 s para conectar e 30 s sem receber nada.
 */
public final class Baixador {
    public interface Progresso { void pct(int pct); }

    static final int CONECTAR = 15_000, LER = 30_000, MAX_SALTOS = 5;
    private final boolean soHttps;

    public Baixador(boolean soHttps) { this.soHttps = soHttps; }

    private static ProblemaAtualizacao rede(String detalhe) { return new ProblemaAtualizacao("rede", detalhe); }
    private static ProblemaAtualizacao tamanho(long max) { return new ProblemaAtualizacao("tamanho", "maior que " + max + " bytes"); }

    /** abre o endereço, seguindo os redirecionamentos; devolve a conexão já com resposta 2xx */
    private HttpURLConnection abrir(String endereco) throws ProblemaAtualizacao {
        URL url;
        try { url = new URL(endereco); } catch (MalformedURLException e) { throw new ProblemaAtualizacao("endereco", "endereço inválido: " + endereco); }
        for (int saltos = 0; ; saltos++) {
            String protocolo = url.getProtocol();
            if (!"https".equals(protocolo) && (soHttps || !"http".equals(protocolo)))
                throw new ProblemaAtualizacao("endereco", "endereço sem HTTPS: " + url.getHost());
            HttpURLConnection c;
            int codigo;
            try {
                c = (HttpURLConnection) url.openConnection();
                c.setInstanceFollowRedirects(false);
                c.setConnectTimeout(CONECTAR);
                c.setReadTimeout(LER);
                c.setUseCaches(false);
                c.setRequestProperty("User-Agent", "PainelMineracao-App");
                codigo = c.getResponseCode();
            } catch (IOException e) {
                throw rede(e.toString());
            }
            if (codigo == 301 || codigo == 302 || codigo == 303 || codigo == 307 || codigo == 308) {
                String para = c.getHeaderField("Location");
                c.disconnect();
                if (para == null) throw rede("redirecionamento sem destino");
                if (saltos >= MAX_SALTOS) throw rede("redirecionamentos demais");
                try { url = new URL(url, para); } catch (MalformedURLException e) { throw new ProblemaAtualizacao("endereco", "redirecionamento inválido: " + para); }
                continue;
            }
            if (codigo == 404) { c.disconnect(); throw new ProblemaAtualizacao("nao-achou", url.getPath()); }
            if (codigo < 200 || codigo > 299) { c.disconnect(); throw rede("resposta " + codigo); }
            return c;
        }
    }

    /** lê tudo para a memória (o manifesto), até max bytes */
    public byte[] ler(String endereco, int max) throws ProblemaAtualizacao {
        HttpURLConnection c = abrir(endereco);
        try {
            if (c.getContentLengthLong() > max) throw tamanho(max);
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] buf = new byte[16 * 1024];
            try (InputStream in = c.getInputStream()) {
                int r;
                while ((r = in.read(buf)) > 0) {
                    if (b.size() + r > max) throw tamanho(max);
                    b.write(buf, 0, r);
                }
            } catch (IOException e) {
                throw rede(e.toString());
            }
            return b.toByteArray();
        } finally {
            c.disconnect();
        }
    }

    /** baixa para o arquivo (até max bytes), com o progresso pelo tamanho esperado; em qualquer falha, apaga o arquivo */
    public void baixar(String endereco, File destino, long max, long esperado, Progresso p) throws ProblemaAtualizacao {
        HttpURLConnection c = abrir(endereco);
        boolean ok = false;
        try {
            long declarado = c.getContentLengthLong();
            if (declarado > max) throw tamanho(max);
            long base = esperado > 0 ? esperado : declarado;
            InputStream in;
            try { in = c.getInputStream(); } catch (IOException e) { throw rede(e.toString()); }
            try (InputStream entrada = in) {
                OutputStream out;
                try { out = new FileOutputStream(destino); } catch (IOException e) { throw Pacote.traduzir(e); }
                try (OutputStream saida = out) {
                    byte[] buf = new byte[64 * 1024];
                    long total = 0;
                    int ultimo = -1;
                    while (true) {
                        int r;
                        try { r = entrada.read(buf); } catch (IOException e) { throw rede(e.toString()); }
                        if (r < 0) break;
                        total += r;
                        if (total > max) throw tamanho(max);
                        try { saida.write(buf, 0, r); } catch (IOException e) { throw Pacote.traduzir(e); }
                        int pct = base > 0 ? (int) Math.min(99, total * 100 / base) : 0;
                        if (pct != ultimo && p != null) { ultimo = pct; p.pct(pct); }
                    }
                } catch (IOException e) {
                    throw Pacote.traduzir(e);   /* ao fechar o arquivo (gravar o resto no disco) */
                }
            } catch (IOException e) {
                /* ao fechar a conexão: o arquivo já está inteiro */
            }
            if (p != null) p.pct(100);
            ok = true;
        } finally {
            c.disconnect();
            if (!ok) Pacote.apagar(destino);
        }
    }
}
