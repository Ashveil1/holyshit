#!/usr/bin/env node
// holyshit runtime: node run.js out.wasm
const fs = require("fs");
const path = process.argv[2];
if (!path) { console.error("usage: node run.js out.wasm"); process.exit(2); }
const bytes = fs.readFileSync(path);
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
WebAssembly.instantiate(bytes, imports).then(() => {}).catch((e) => {
  console.error("trap:", e.message);
  process.exit(1);
});
