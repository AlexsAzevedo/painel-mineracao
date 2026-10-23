"use strict";
/* Depois de empacotar para Windows: põe o ícone e o nome do painel dentro do .exe (sem precisar do Windows). */
const path = require("path");
const fs = require("fs");

module.exports = async function (context) {
  if (context.electronPlatformName !== "win32") return;
  const ResEdit = await import("resedit");
  const nome = context.packager.config.executableName || context.packager.appInfo.productFilename;
  const exe = path.join(context.appOutDir, `${nome}.exe`);
  const ico = path.join(context.packager.projectDir, "build", "icon.ico");

  const binario = ResEdit.NtExecutable.from(fs.readFileSync(exe), { ignoreCert: true });
  const recursos = ResEdit.NtExecutableResource.from(binario);

  const grupos = ResEdit.Resource.IconGroupEntry.fromEntries(recursos.entries);
  const alvo = grupos[0] || { id: 1, lang: 1033 };
  const icone = ResEdit.Data.IconFile.from(fs.readFileSync(ico));
  ResEdit.Resource.IconGroupEntry.replaceIconsForResource(recursos.entries, alvo.id, alvo.lang, icone.icons.map((i) => i.data));

  const versao = String(context.packager.appInfo.version).split(".").map(Number).concat([0, 0, 0]).slice(0, 4);
  const vi = ResEdit.Resource.VersionInfo.fromEntries(recursos.entries)[0];
  if (vi) {
    const idioma = vi.getAllLanguagesForStringValues()[0] || { lang: 1033, codepage: 1200 };
    vi.setStringValues(idioma, {
      ProductName: "Painel de Mineração", FileDescription: "Painel de Mineração", CompanyName: "Uso pessoal",
      LegalCopyright: "Uso pessoal", OriginalFilename: `${nome}.exe`, InternalName: nome,
      FileVersion: versao.join("."), ProductVersion: versao.join(".")
    });
    vi.setFileVersion(...versao, idioma.lang);
    vi.setProductVersion(...versao, idioma.lang);
    vi.outputToResourceEntries(recursos.entries);
  }
  recursos.outputResource(binario);
  fs.writeFileSync(exe, Buffer.from(binario.generate()));
  console.log(`  • ícone e versão gravados em ${path.basename(exe)}`);
};
