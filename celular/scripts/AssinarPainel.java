/* Assina o manifesto do pacote da página do app do celular com a mesma chave que assina o .apk (o keystore dos segredos
   do GitHub). O app confere a assinatura com o certificado com que ele mesmo foi assinado: sem essa chave, ninguém
   consegue fazer o app aceitar uma página.

   Uso (Java 11 ou mais novo, sem compilar):
     PAINEL_KEYSTORE_SENHA=<senha> [PAINEL_KEYSTORE_ALIAS=painel] java AssinarPainel.java <keystore> <manifesto.json> <saida.json>
   Saída: {"manifesto": "<o texto de manifesto.json, igual>", "assinatura": "<base64>"}. Antes de gravar, confere a própria
   assinatura com o certificado do keystore; se não conferir (ou faltar senha, chave…), sai com 1 sem gravar nada.
   A chave não sai do keystore: nada é gravado além do envelope. */
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.Key;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.Signature;
import java.security.cert.Certificate;
import java.util.Arrays;
import java.util.Base64;

public class AssinarPainel {
    public static void main(String[] args) {
        if (args.length != 3) {
            System.err.println("uso: java AssinarPainel.java <keystore> <manifesto.json> <saida.json>");
            System.exit(2);
        }
        try {
            String senha = System.getenv("PAINEL_KEYSTORE_SENHA");
            if (senha == null || senha.isEmpty()) throw new IllegalStateException("falta PAINEL_KEYSTORE_SENHA");
            String apelido = System.getenv("PAINEL_KEYSTORE_ALIAS");
            if (apelido == null || apelido.isEmpty()) apelido = "painel";
            char[] s = senha.toCharArray();
            KeyStore ks = KeyStore.getInstance(new File(args[0]), s);
            Key chave = ks.getKey(apelido, s);
            Certificate cert = ks.getCertificate(apelido);
            if (!(chave instanceof PrivateKey) || cert == null) throw new IllegalStateException("o keystore não tem a chave \"" + apelido + "\"");

            byte[] texto = Files.readAllBytes(Path.of(args[1]));
            String manifesto = new String(texto, StandardCharsets.UTF_8);
            if (!Arrays.equals(manifesto.getBytes(StandardCharsets.UTF_8), texto)) throw new IllegalStateException("o manifesto não é UTF-8 válido");

            String algoritmo = algoritmo(chave.getAlgorithm());
            Signature assina = Signature.getInstance(algoritmo);
            assina.initSign((PrivateKey) chave);
            assina.update(texto);
            byte[] assinatura = assina.sign();
            Signature confere = Signature.getInstance(algoritmo);
            confere.initVerify(cert.getPublicKey());
            confere.update(texto);
            if (!confere.verify(assinatura)) throw new IllegalStateException("a assinatura não confere com o certificado do keystore");

            String envelope = "{\"manifesto\":" + textoJson(manifesto) + ",\"assinatura\":\"" + Base64.getEncoder().encodeToString(assinatura) + "\"}";
            Files.writeString(Path.of(args[2]), envelope, StandardCharsets.UTF_8);
            System.out.println("manifesto assinado (" + algoritmo + "): " + args[2]);
        } catch (Exception e) {
            System.err.println("não deu para assinar: " + e.getMessage());
            System.exit(1);
        }
    }

    static String algoritmo(String chave) {
        switch (chave) {
            case "RSA": return "SHA256withRSA";
            case "EC": return "SHA256withECDSA";
            default: throw new IllegalStateException("chave de tipo inesperado: " + chave);
        }
    }

    /* o texto como string JSON: aspas, barra invertida e caracteres de controle escapados; o resto igual (UTF-8) */
    static String textoJson(String t) {
        StringBuilder b = new StringBuilder(t.length() + 16).append('"');
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                case '\b': b.append("\\b"); break;
                case '\f': b.append("\\f"); break;
                default:
                    if (c < 0x20 || c == 0x7f || c == ' ' || c == ' ') b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        return b.append('"').toString();
    }
}
