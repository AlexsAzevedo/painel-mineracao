package br.alex.painelmineracao.celular.atualizacao;

import java.io.File;

/** As releases do repositório no GitHub: o manifesto da última e os arquivos da release de uma versão (a assinada). */
public final class FonteGithub implements Fonte {
    public static final String BASE = "https://github.com/AlexsAzevedo/painel-mineracao/releases";
    public static final String ZIP = "painel-celular.zip", APK = "Painel-de-Mineracao.apk";

    private final String base;
    private final Baixador baixador;

    public FonteGithub(String base, Baixador baixador) {
        this.base = base;
        this.baixador = baixador;
    }

    @Override public byte[] manifesto() throws ProblemaAtualizacao {
        return baixador.ler(base + "/latest/download/painel-celular.json", Manifesto.MAX_ENVELOPE);
    }

    @Override public void baixar(String versao, String arquivo, File destino, long max, long esperado, Baixador.Progresso p) throws ProblemaAtualizacao {
        if (!ZIP.equals(arquivo) && !APK.equals(arquivo)) throw new IllegalArgumentException("arquivo desconhecido: " + arquivo);
        if (!Versao.valida(versao)) throw new IllegalArgumentException("versão inválida: " + versao);
        baixador.baixar(base + "/download/v" + versao + "/" + arquivo, destino, max, esperado, p);
    }
}
