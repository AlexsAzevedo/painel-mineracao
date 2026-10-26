package br.alex.painelmineracao.celular.atualizacao;

/** Base64 padrão (com ou sem "="), para o Android 7 (java.util.Base64 só existe a partir do Android 8). */
final class Base64Simples {
    private static final String ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    /** devolve null se o texto não é base64 */
    static byte[] decodificar(String s) {
        if (s == null) return null;
        StringBuilder limpo = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '\n' || c == '\r' || c == ' ' || c == '\t') continue;
            limpo.append(c);
        }
        String t = limpo.toString();
        while (t.endsWith("=")) t = t.substring(0, t.length() - 1);
        if (t.isEmpty() || t.length() % 4 == 1) return null;
        byte[] saida = new byte[t.length() * 3 / 4];
        int bits = 0, n = 0, j = 0;
        for (int i = 0; i < t.length(); i++) {
            int v = ALFABETO.indexOf(t.charAt(i));
            if (v < 0) return null;
            bits = (bits << 6) | v;
            n += 6;
            if (n >= 8) {
                n -= 8;
                saida[j++] = (byte) ((bits >> n) & 0xff);
            }
        }
        return saida;
    }

    private Base64Simples() {}
}
