package br.alex.painelmineracao.celular.atualizacao;

import java.nio.charset.StandardCharsets;
import java.security.PublicKey;
import java.security.Signature;
import java.util.List;
import java.util.regex.Pattern;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * O manifesto de uma release (painel-celular.json): a versão da página, a do app que ela precisa (appMin) e o SHA-256 e
 * o tamanho do zip da página e do .apk. Vem num envelope {"manifesto": "<texto>", "assinatura": "<base64>"}, assinado
 * com a chave do app (celular/scripts/AssinarPainel.java); só vale se a assinatura confere com uma das chaves dadas
 * (as do certificado com que o próprio app foi assinado).
 */
public final class Manifesto {
    public static final int MAX_ENVELOPE = 64 * 1024;
    public static final long MAX_PAINEL = 20L << 20, MAX_APK = 100L << 20;
    public static final String TIPO = "painel-mineracao/painel-celular";
    private static final Pattern SHA = Pattern.compile("[0-9a-f]{64}");

    public final String texto, versao, appMin, painelSha256, appVersao, appSha256;
    public final long painelTamanho, appCodigo, appTamanho;

    private Manifesto(String texto, String versao, String appMin, String painelSha256, long painelTamanho,
                      String appVersao, long appCodigo, String appSha256, long appTamanho) {
        this.texto = texto;
        this.versao = versao;
        this.appMin = appMin;
        this.painelSha256 = painelSha256;
        this.painelTamanho = painelTamanho;
        this.appVersao = appVersao;
        this.appCodigo = appCodigo;
        this.appSha256 = appSha256;
        this.appTamanho = appTamanho;
    }

    private static ProblemaAtualizacao formato(String detalhe) { return new ProblemaAtualizacao("formato", detalhe); }

    public static Manifesto conferir(byte[] envelope, List<PublicKey> chaves) throws ProblemaAtualizacao {
        if (envelope == null || envelope.length > MAX_ENVELOPE) throw formato("envelope ausente ou grande demais");
        String texto, assinatura;
        try {
            JSONObject e = new JSONObject(new String(envelope, StandardCharsets.UTF_8));
            texto = e.getString("manifesto");
            assinatura = e.getString("assinatura");
        } catch (JSONException e) {
            throw formato("envelope ilegível: " + e.getMessage());
        }
        byte[] sig = Base64Simples.decodificar(assinatura);
        if (sig == null) throw new ProblemaAtualizacao("assinatura", "assinatura ilegível");
        byte[] dados = texto.getBytes(StandardCharsets.UTF_8);
        boolean confere = false;
        if (chaves != null) {
            for (PublicKey k : chaves) {
                try {
                    Signature s = Signature.getInstance("EC".equals(k.getAlgorithm()) ? "SHA256withECDSA" : "SHA256withRSA");
                    s.initVerify(k);
                    s.update(dados);
                    if (s.verify(sig)) { confere = true; break; }
                } catch (Exception ignorada) {
                    /* chave de outro tipo ou assinatura malformada: não confere com esta chave */
                }
            }
        }
        if (!confere) throw new ProblemaAtualizacao("assinatura", "a assinatura não confere com a chave do app");
        return doTexto(texto);
    }

    /** lê um manifesto já conferido (o guardado no estado) e valida tudo menos a assinatura */
    public static Manifesto doTexto(String texto) throws ProblemaAtualizacao {
        try {
            JSONObject m = new JSONObject(texto);
            if (m.getInt("formato") != 1) throw formato("formato " + m.get("formato"));
            if (!TIPO.equals(m.getString("tipo"))) throw formato("tipo " + m.getString("tipo"));
            String versao = m.getString("versao"), appMin = m.getString("appMin");
            JSONObject p = m.getJSONObject("painel"), a = m.getJSONObject("app");
            String appVersao = a.getString("versao");
            if (!Versao.valida(versao) || !Versao.valida(appMin) || !Versao.valida(appVersao)) throw formato("versão inválida");
            String painelSha = p.getString("sha256"), appSha = a.getString("sha256");
            if (!SHA.matcher(painelSha).matches() || !SHA.matcher(appSha).matches()) throw formato("SHA-256 inválido");
            long painelTam = p.getLong("tamanho"), appTam = a.getLong("tamanho"), appCodigo = a.getLong("codigo");
            if (painelTam < 1 || painelTam > MAX_PAINEL || appTam < 1 || appTam > MAX_APK) throw formato("tamanho fora do limite");
            if (appCodigo != Versao.codigo(appVersao)) throw formato("código do app não bate com a versão");
            return new Manifesto(texto, versao, appMin, painelSha, painelTam, appVersao, appCodigo, appSha, appTam);
        } catch (JSONException e) {
            throw formato("manifesto ilegível: " + e.getMessage());
        }
    }
}
