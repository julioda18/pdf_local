// Incrusta icono y metadatos en el exe. Sustituye a signAndEditExecutable, desactivado porque
// winCodeSign no se extrae en Windows sin privilegio de symlinks (ver doc_errores.md).
const path = require("path");
const rcedit = require("rcedit");

exports.default = async function afterPack({ appOutDir, packager }) {
  const { productFilename, productName, buildVersion } = packager.appInfo;
  await rcedit(path.join(appOutDir, `${productFilename}.exe`), {
    icon: path.join(__dirname, "resources", "icon.ico"),
    "file-version": buildVersion,
    "product-version": buildVersion,
    "version-string": { ProductName: productName, FileDescription: productName },
  });
};
