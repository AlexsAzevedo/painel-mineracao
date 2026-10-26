package br.alex.painelmineracao.celular;

import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.content.pm.SigningInfo;
import android.os.Build;
import androidx.core.content.pm.PackageInfoCompat;
import br.alex.painelmineracao.celular.atualizacao.App;
import br.alex.painelmineracao.celular.atualizacao.Manifesto;
import br.alex.painelmineracao.celular.atualizacao.ProblemaAtualizacao;
import br.alex.painelmineracao.celular.atualizacao.Versao;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.PublicKey;
import java.security.cert.CertificateFactory;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import org.json.JSONObject;

/** O app instalado, pelo PackageManager: versão, a página que veio no .apk, as chaves da assinatura e a conferência do .apk novo. */
final class AppAndroid implements App {
    private final Context c;

    AppAndroid(Context c) { this.c = c.getApplicationContext(); }

    private PackageInfo info(int flags) {
        try { return c.getPackageManager().getPackageInfo(c.getPackageName(), flags); }
        catch (PackageManager.NameNotFoundException e) { throw new IllegalStateException(e); }
    }

    @Override public String versao() { return info(0).versionName; }

    @Override public long codigo() { return PackageInfoCompat.getLongVersionCode(info(0)); }

    @Override public String painelEmbutido() {
        try (InputStream in = c.getAssets().open("public/painel.json")) {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int r;
            while ((r = in.read(buf)) > 0 && b.size() < 8192) b.write(buf, 0, r);
            String v = new JSONObject(new String(b.toByteArray(), StandardCharsets.UTF_8)).getString("versao");
            return Versao.valida(v) ? v : "0.0.0";
        } catch (Exception e) {
            return "0.0.0";
        }
    }

    /** os certificados com que este app (o instalado) foi assinado */
    @SuppressWarnings("deprecation")
    private Signature[] assinaturas() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            SigningInfo s = info(PackageManager.GET_SIGNING_CERTIFICATES).signingInfo;
            return s == null ? new Signature[0] : s.getApkContentsSigners();
        }
        Signature[] s = info(PackageManager.GET_SIGNATURES).signatures;
        return s == null ? new Signature[0] : s;
    }

    @Override public List<PublicKey> chaves() {
        List<PublicKey> r = new ArrayList<>();
        try {
            CertificateFactory cf = CertificateFactory.getInstance("X.509");
            for (Signature s : assinaturas()) r.add(cf.generateCertificate(new ByteArrayInputStream(s.toByteArray())).getPublicKey());
        } catch (Exception e) {
            /* sem chaves, nenhum manifesto confere: o app só não se atualiza */
        }
        return r;
    }

    @SuppressWarnings("deprecation")
    @Override public void conferirApk(File apk, Manifesto m) throws ProblemaAtualizacao {
        int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P ? PackageManager.GET_SIGNING_CERTIFICATES : PackageManager.GET_SIGNATURES;
        PackageInfo i = c.getPackageManager().getPackageArchiveInfo(apk.getAbsolutePath(), flags);
        if (i == null) throw new ProblemaAtualizacao("apk", "o Android não conseguiu ler o .apk");
        if (!c.getPackageName().equals(i.packageName)) throw new ProblemaAtualizacao("apk", "o .apk é de outro app: " + i.packageName);
        long v = PackageInfoCompat.getLongVersionCode(i);
        if (v != m.appCodigo || v <= codigo()) throw new ProblemaAtualizacao("apk", "o .apk é da versão " + v + ", não da " + m.appCodigo);
        Signature[] deles = null;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            if (i.signingInfo != null) deles = i.signingInfo.getApkContentsSigners();
        } else {
            deles = i.signatures;
        }
        /* sem conseguir ler o certificado do arquivo, vale o SHA-256 do manifesto assinado (já conferido) */
        if (deles != null && deles.length > 0 && !new HashSet<>(Arrays.asList(deles)).equals(new HashSet<>(Arrays.asList(assinaturas()))))
            throw new ProblemaAtualizacao("apk", "o .apk foi assinado com outra chave");
    }
}
