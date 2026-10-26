package br.alex.painelmineracao.celular.atualizacao;

import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.Signature;
import java.util.Base64;
import org.json.JSONException;
import org.json.JSONObject;

/** Ajuda dos testes: chaves, manifestos e envelopes assinados como os da publicação (AssinarPainel.java). */
final class Assinador {
    static final String SHA_A = "a".repeat(64), SHA_B = "b".repeat(64);

    static KeyPair par() {
        try {
            KeyPairGenerator g = KeyPairGenerator.getInstance("RSA");
            g.initialize(2048);
            return g.generateKeyPair();
        } catch (Exception e) { throw new RuntimeException(e); }
    }

    /** um manifesto válido: página versao (appMin), zip com painelSha/painelTam, .apk appVersao */
    static JSONObject manifesto(String versao, String appMin, String painelSha, long painelTam, String appVersao, String appSha, long appTam) {
        try {
            return new JSONObject()
            .put("formato", 1).put("tipo", "painel-mineracao/painel-celular").put("versao", versao).put("appMin", appMin)
            .put("painel", new JSONObject().put("sha256", painelSha).put("tamanho", painelTam))
            .put("app", new JSONObject().put("versao", appVersao).put("codigo", Versao.codigo(appVersao)).put("sha256", appSha).put("tamanho", appTam));
        } catch (JSONException e) { throw new RuntimeException(e); }
    }

    static JSONObject manifesto() { return manifesto("1.8.1", "1.8.0", SHA_A, 1000, "1.8.0", SHA_B, 3_000_000); }

    static byte[] envelope(String texto, PrivateKey chave) {
        try {
            Signature s = Signature.getInstance("SHA256withRSA");
            s.initSign(chave);
            s.update(texto.getBytes(StandardCharsets.UTF_8));
            return envelope(texto, Base64.getEncoder().encodeToString(s.sign()));
        } catch (Exception e) { throw new RuntimeException(e); }
    }

    static byte[] envelope(String texto, String assinaturaBase64) {
        try {
            return new JSONObject().put("manifesto", texto).put("assinatura", assinaturaBase64).toString().getBytes(StandardCharsets.UTF_8);
        } catch (JSONException e) { throw new RuntimeException(e); }
    }

    private Assinador() {}
}
