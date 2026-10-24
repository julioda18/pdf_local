// Proceso principal: arranca el servidor Python en un puerto libre y lo muestra en una ventana.
const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const PROJECT_DIR = path.resolve(__dirname, "..");
const STARTUP_TIMEOUT_MS = 60000;
const POLL_INTERVAL_MS = 300;

let server = null;

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
}

const IS_WINDOWS = process.platform === "win32";

// Empaquetado: ejecutable congelado + vendor/ en resources (vendor/ solo existe en Windows;
// en macOS/Linux los programas externos vienen del sistema). En desarrollo: Python del proyecto.
function serverCommand() {
  if (app.isPackaged) {
    return {
      command: path.join(process.resourcesPath, "backend", IS_WINDOWS ? "pdf_local_server.exe" : "pdf_local_server"),
      args: [],
      vendor: path.join(process.resourcesPath, "vendor"),
    };
  }
  const venvPython = IS_WINDOWS
    ? path.join(PROJECT_DIR, ".venv", "Scripts", "python.exe")
    : path.join(PROJECT_DIR, ".venv", "bin", "python");
  return {
    command: fs.existsSync(venvPython) ? venvPython : IS_WINDOWS ? "python" : "python3",
    args: [path.join(PROJECT_DIR, "app.py")],
    vendor: path.join(PROJECT_DIR, "vendor"),
  };
}

function startServer(port) {
  const { command, args, vendor } = serverCommand();
  server = spawn(command, args, {
    env: { ...process.env, PDF_LOCAL_PORT: String(port), PDF_LOCAL_VENDOR: vendor },
    windowsHide: true,
    stdio: "ignore",
  });
  server.once("exit", (code) => {
    server = null;
    if (!app.isQuitting) {
      dialog.showErrorBox("PDF Local", `El servidor se detuvo (código ${code}).`);
      app.quit();
    }
  });
}

function isReady(url) {
  return new Promise((resolve) => {
    http.get(url, (res) => resolve(res.statusCode === 200)).on("error", () => resolve(false));
  });
}

async function waitForServer(url) {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await isReady(url)) return;
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
  throw new Error("El servidor no respondió a tiempo");
}

async function createWindow() {
  const port = await freePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  startServer(port);
  await waitForServer(`${baseUrl}/api/tools`);
  const window = new BrowserWindow({
    width: 1200,
    height: 800,
    autoHideMenuBar: true,
    icon: path.join(__dirname, "resources", "icon.png"),
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  window.webContents.session.on("will-download", (_event, item) => {
    item.once("done", (_e, state) => state === "completed" && shell.openPath(item.getSavePath()));
  });
  window.loadURL(baseUrl);
}

app.on("before-quit", () => {
  app.isQuitting = true;
  server?.kill();
});
app.disableHardwareAcceleration();
app.on("window-all-closed", () => app.quit());
app.whenReady().then(createWindow).catch((error) => {
  dialog.showErrorBox("PDF Local", error.message);
  app.quit();
});
