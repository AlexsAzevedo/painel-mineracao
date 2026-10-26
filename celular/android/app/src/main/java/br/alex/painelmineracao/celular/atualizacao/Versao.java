package br.alex.painelmineracao.celular.atualizacao;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Versões do tipo X.Y.Z (Y e Z até 99, como o versionCode do app: X·10000 + Y·100 + Z). */
public final class Versao {
    private static final Pattern FORMA = Pattern.compile("(\\d{1,4})\\.(\\d{1,2})\\.(\\d{1,2})");

    public static boolean valida(String v) {
        return v != null && FORMA.matcher(v).matches();
    }

    private static int[] partes(String v) {
        Matcher m = FORMA.matcher(v == null ? "" : v);
        if (!m.matches()) throw new IllegalArgumentException("versão inválida: " + v);
        return new int[] {Integer.parseInt(m.group(1)), Integer.parseInt(m.group(2)), Integer.parseInt(m.group(3))};
    }

    /** menor que zero se a < b, zero se iguais, maior que zero se a > b */
    public static int comparar(String a, String b) {
        int[] x = partes(a), y = partes(b);
        for (int i = 0; i < 3; i++) if (x[i] != y[i]) return x[i] < y[i] ? -1 : 1;
        return 0;
    }

    public static long codigo(String v) {
        int[] p = partes(v);
        return p[0] * 10000L + p[1] * 100L + p[2];
    }

    private Versao() {}
}
