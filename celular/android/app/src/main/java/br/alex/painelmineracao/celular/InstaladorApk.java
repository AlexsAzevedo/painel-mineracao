package br.alex.painelmineracao.celular;

import android.annotation.SuppressLint;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.content.pm.PackageManager;
import android.os.Build;
import br.alex.painelmineracao.celular.atualizacao.Instalacao;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Instala o .apk novo do próprio app pelo PackageInstaller. No Android 12+ pede para não mostrar a confirmação (o
 * Android deixa quando o app atualiza a si mesmo); senão, ou se o Android quiser perguntar, a resposta chega no
 * InstalacaoReceiver como "pendente", e ele abre a tela de confirmação do Android.
 */
final class InstaladorApk {
    static void instalar(Context ctx, File apk) throws IOException {
        PackageInstaller pi = ctx.getPackageManager().getPackageInstaller();
        PackageInstaller.SessionParams p = new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        p.setAppPackageName(ctx.getPackageName());
        p.setSize(apk.length());
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) p.setInstallReason(PackageManager.INSTALL_REASON_USER);
        semPerguntar(p);
        int id = pi.createSession(p);
        PackageInstaller.Session s = pi.openSession(id);
        try {
            try (InputStream in = new FileInputStream(apk); OutputStream out = s.openWrite("app.apk", 0, apk.length())) {
                byte[] buf = new byte[64 * 1024];
                int r;
                while ((r = in.read(buf)) > 0) out.write(buf, 0, r);
                s.fsync(out);
            }
            Intent i = new Intent(ctx, InstalacaoReceiver.class).setAction(InstalacaoReceiver.ACAO).setPackage(ctx.getPackageName());
            int flags = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ? PendingIntent.FLAG_MUTABLE : 0);
            s.commit(PendingIntent.getBroadcast(ctx, 7, i, flags).getIntentSender());
            s.close();
        } catch (IOException | RuntimeException e) {
            s.abandon();
            throw e;
        }
    }

    @SuppressLint("NewApi")   /* Instalacao.semPerguntar só é verdade do Android 12 (API 31) em diante */
    private static void semPerguntar(PackageInstaller.SessionParams p) {
        if (Instalacao.semPerguntar(Build.VERSION.SDK_INT)) p.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED);
    }

    private InstaladorApk() {}
}
