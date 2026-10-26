package br.alex.painelmineracao.celular.atualizacao;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.json.JSONException;
import org.json.JSONObject;

/** O zip da página: conferir, descompactar com cuidado (nada fora da pasta, limites de tamanho) e apagar. */
public final class Pacote {
    public static final int MAX_ARQUIVOS = 500;
    public static final long MAX_TOTAL = 40L << 20, MAX_ARQUIVO = 20L << 20;

    private static ProblemaAtualizacao pacote(String detalhe) { return new ProblemaAtualizacao("pacote", detalhe); }

    public static String sha256(File f) throws IOException {
        MessageDigest md;
        try { md = MessageDigest.getInstance("SHA-256"); } catch (NoSuchAlgorithmException e) { throw new IOException(e); }
        byte[] buf = new byte[64 * 1024];
        try (InputStream in = new FileInputStream(f)) {
            int r;
            while ((r = in.read(buf)) > 0) md.update(buf, 0, r);
        }
        StringBuilder hex = new StringBuilder(64);
        for (byte b : md.digest()) hex.append(String.format("%02x", b & 0xff));
        return hex.toString();
    }

    /** nome de arquivo dentro do zip que não sai da pasta: sem "..", "." ou vazio entre barras, sem "/" no começo, "\" ou ":" */
    static boolean nomeSeguro(String nome) {
        if (nome == null || nome.isEmpty() || nome.startsWith("/") || nome.indexOf('\\') >= 0 || nome.indexOf(':') >= 0 || nome.indexOf('\0') >= 0) return false;
        String[] partes = (nome.endsWith("/") ? nome.substring(0, nome.length() - 1) : nome).split("/", -1);
        for (String p : partes) if (p.isEmpty() || p.equals(".") || p.equals("..")) return false;
        return true;
    }

    /** descompacta o zip numa pasta nova (que ainda não existe); em qualquer falha, apaga o que já saiu */
    public static void extrair(File zip, File destino) throws ProblemaAtualizacao {
        if (destino.exists()) throw pacote("a pasta de destino já existe: " + destino);
        try {
            if (!destino.mkdirs()) throw pacote("não deu para criar " + destino);
            String base = destino.getCanonicalPath() + File.separator;
            int arquivos = 0;
            long total = 0;
            byte[] buf = new byte[64 * 1024];
            try (ZipInputStream zin = new ZipInputStream(new BufferedInputStream(new FileInputStream(zip)))) {
                ZipEntry e;
                while ((e = zin.getNextEntry()) != null) {
                    String nome = e.getName();
                    if (!nomeSeguro(nome)) throw pacote("nome de arquivo inválido no pacote: " + nome);
                    File alvo = new File(destino, nome);
                    if (!alvo.getCanonicalPath().startsWith(base)) throw pacote("arquivo fora da pasta: " + nome);
                    if (e.isDirectory()) {
                        if (!alvo.isDirectory() && !alvo.mkdirs()) throw pacote("não deu para criar " + nome);
                        continue;
                    }
                    if (++arquivos > MAX_ARQUIVOS) throw pacote("arquivos demais no pacote");
                    File pai = alvo.getParentFile();
                    if (pai != null && !pai.isDirectory() && !pai.mkdirs()) throw pacote("não deu para criar a pasta de " + nome);
                    long este = 0;
                    try (OutputStream out = new BufferedOutputStream(new FileOutputStream(alvo))) {
                        int r;
                        while ((r = zin.read(buf)) > 0) {
                            este += r;
                            total += r;
                            if (este > MAX_ARQUIVO || total > MAX_TOTAL) throw pacote("arquivo grande demais no pacote: " + nome);
                            out.write(buf, 0, r);
                        }
                    }
                }
            }
            if (arquivos == 0) throw pacote("pacote vazio");
        } catch (ProblemaAtualizacao p) {
            apagar(destino);
            throw p;
        } catch (IOException io) {
            apagar(destino);
            throw traduzir(io);
        } catch (RuntimeException r) {
            apagar(destino);
            throw pacote("pacote ilegível: " + r);
        }
    }

    /** a pasta tem a página certa: index.html e um painel.json com a versão esperada */
    public static void conferirPagina(File pasta, String versao) throws ProblemaAtualizacao {
        if (!new File(pasta, "index.html").isFile()) throw pacote("a página não tem index.html");
        File pj = new File(pasta, "painel.json");
        if (!pj.isFile() || pj.length() > 4096) throw pacote("a página não tem painel.json");
        try (InputStream in = new FileInputStream(pj)) {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int r;
            while ((r = in.read(buf)) > 0) b.write(buf, 0, r);
            String v = new JSONObject(new String(b.toByteArray(), StandardCharsets.UTF_8)).getString("versao");
            if (!v.equals(versao)) throw pacote("a página é a versão " + v + ", não a " + versao);
        } catch (IOException | JSONException e) {
            throw pacote("painel.json ilegível: " + e.getMessage());
        }
    }

    /** erro de disco: sem espaço vira "espaco"; o resto, "pacote" */
    public static ProblemaAtualizacao traduzir(IOException e) {
        String m = String.valueOf(e.getMessage());
        if (m.contains("ENOSPC") || m.contains("No space")) return new ProblemaAtualizacao("espaco", m);
        return new ProblemaAtualizacao("pacote", m);
    }

    /** apaga o arquivo ou a pasta inteira, sem reclamar */
    public static void apagar(File f) {
        if (f == null || !f.exists()) return;
        File[] filhos = f.isDirectory() ? f.listFiles() : null;
        if (filhos != null) for (File x : filhos) apagar(x);
        //noinspection ResultOfMethodCallIgnored
        f.delete();
    }

    private Pacote() {}
}
