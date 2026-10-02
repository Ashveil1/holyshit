#!/usr/bin/env node
// holyshit JIT: node jit.js prog.HC [args...]
// compiles to WASM in memory (no .wasm file) and runs immediately.
const { spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const src = process.argv[2];
if (!src || !fs.existsSync(src)) {
  console.error("usage: node jit.js prog.HC");
  process.exit(2);
}

const r = spawnSync("python3", [path.join(__dirname, "compiler.py"), src, "-"], {
  maxBuffer: 64 * 1024 * 1024,
});
if (r.status !== 0) {
  process.stderr.write(r.stderr.length ? r.stderr : Buffer.from("compile failed\n"));
  process.exit(1);
}

const memory = new WebAssembly.Memory({ initial: 1 });
const dec = new TextDecoder();
const imports = {
  env: {
    memory,
    print_i64: (x) => process.stdout.write(x.toString()),
    print_str: (ptr, len) =>
      process.stdout.write(dec.decode(new Uint8Array(memory.buffer, ptr, len))),
    print_nl: () => process.stdout.write("\n"),
  },
};

WebAssembly.instantiate(r.stdout, imports).catch((e) => {
  console.error("trap:", e.message);
  process.exit(1);
});
