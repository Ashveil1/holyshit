// holyshit VS Code client — zero npm dependencies.
// Spawns the language server that lives in the repo (../.. from this file).
// VS Code ships `vscode-languageclient`, so we borrow its module if present;
// otherwise fall back to a minimal JSON-RPC client over stdio.

const path = require('path');
const vscode = require('vscode');
const { spawn } = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const SERVER = path.join(REPO, 'lsp.py');
const PY = process.env.HS_PYTHON || 'python3';

let client = null;

function serverOptions() {
  return {
    run: { command: PY, args: [SERVER] },
    debug: { command: PY, args: [SERVER] }
  };
}

function start() {
  try {
    const lc = require('vscode-languageclient/node');
    client = new lc.LanguageClient(
      'holyshit',
      'holyshit',
      serverOptions(),
      {
        documentSelector: [{ scheme: 'file', language: 'holyshit' }],
        outputChannelName: 'holyshit',
        synchronize: { fileEvents: null },
        initializationOptions: { repo: REPO }
      }
    );
    client.start();
  } catch (e) {
    // no vscode-languageclient available: fall back to raw stdio client
    client = rawClient();
  }
}

function rawClient() {
  const proc = spawn(PY, [SERVER], { stdio: ['pipe', 'pipe', 'inherit'] });
  let seq = 0;
  const pending = new Map();
  let buf = Buffer.alloc(0);
  proc.stdout.on('data', chunk => {
    buf = Buffer.concat([buf, chunk]);
    for (;;) {
      const sep = buf.indexOf('\r\n\r\n');
      if (sep < 0) return;
      const header = buf.slice(0, sep).toString();
      const m = /content-length:\s*(\d+)/i.exec(header);
      if (!m) { buf = buf.slice(sep + 4); continue; }
      const n = parseInt(m[1], 10);
      if (buf.length < sep + 4 + n) return;
      const body = buf.slice(sep + 4, sep + 4 + n).toString();
      buf = buf.slice(sep + 4 + n);
      const msg = JSON.parse(body);
      if (msg.id && pending.has(msg.id)) {
        pending.get(msg.id)(msg.result);
        pending.delete(msg.id);
      }
    }
  });
  function send(obj) {
    const body = Buffer.from(JSON.stringify(obj), 'utf8');
    proc.stdin.write(`Content-Length: ${body.length}\r\n\r\n`);
    proc.stdin.write(body);
  }
  function request(method, params) {
    return new Promise(resolve => {
      const id = ++seq;
      pending.set(id, resolve);
      send({ jsonrpc: '2.0', id, method, params });
    });
  }
  send({ jsonrpc: '2.0', id: ++seq, method: 'initialize', params: { capabilities: {} } });
  send({ jsonrpc: '2.0', method: 'initialized', params: {} });
  return {
    dispose() { try { proc.kill(); } catch (e) {} }
  };
}

function activate(context) {
  start();
  context.subscriptions.push({
    dispose() {
      if (client && client.stop) { client.stop(); } else if (client) { client.dispose(); }
    }
  });
  context.subscriptions.push(
    vscode.commands.registerCommand('holyshit.restartServer', async () => {
      if (client && client.stop) { client.stop(); }
      start();
      vscode.window.showInformationMessage('holyshit: language server restarted');
    }),
    vscode.commands.registerCommand('holyshit.check', async () => {
      const py = require('child_process').spawnSync(PY,
        [path.join(REPO, 'hs.py'), 'check',
         vscode.window.activeTextEditor.document.fileName],
        { encoding: 'utf8' });
      const out = (py.stdout || '') + (py.stderr || '');
      vscode.window.showInformationMessage(out.trim() || 'ok');
    })
  );
}

function deactivate() {
  if (client && client.stop) { client.stop(); }
}

module.exports = { activate, deactivate };
