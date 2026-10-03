# Zed — holyshit

Zed ต้องมี extension แยก แต่ตัวโปรโตคอลเป็น LSP ตรง ๆ เหมือนกัน
เลยต่อได้สองแบบ:

## 1. ใช้ LSP ตรง (มี custom server)

`~/.config/zed/settings.json`:

```json
{
  "languages": {
    "Holyshit": {
      "extensions": ["hs"],
      "language_servers": ["holyshit-lsp"]
    }
  },
  "language_servers": {
    "holyshit-lsp": {
      "binary": { "path": "python3", "args": ["/path/to/holyshit/lsp.py"] }
    }
  }
}
```

หมายเหตุ: diagnostics ของ Zed ต้องเป็น text-edit ที่แมปกลับบรรทัดได้ —
เซิร์ฟเวอร์คืนทั้งบรรทัด ซึ่ง Zed รับได้

## 2. เขียน Zed extension เอง (สะอาดกว่า)

โครง `extension.toml` + `src/holyshit.rs`:

```toml
# extension.toml
id = "holyshit"
name = "Holyshit"
description = "holyshit (.hs) support"
schema_version = 1
languages = ["Holyshit"]
language-servers = ["holyshit-lsp"]

[[grammar]]
name = "holyshit"
source = { path = "./grammar" }
file-types = ["hs"]
```

```rust
// src/holyshit.rs
use std::{env, sync::Arc};
use zed::{settings::LspSettings, LanguageServerConfig};

pub fn language_server(lsp_settings: &Arc<LspSettings>) -> anyhow::Result<LanguageServerConfig> {
    let server = LanguageServerConfig::new {
        name: "holyshit".into(),
        binary: lsp_settings
            .get("holyshit")?
            .and_then(|s| s.binary.clone())
            .unwrap_or_else(|| {
                let mut b = zed::settings::BinarySettings::default();
                b.path = Some(env::var("HS_PYTHON").unwrap_or("python3".into()).into());
                b.arguments = Some(vec!["lsp.py".into()]);
                b
            }),
        ..Default::default()
    };
    Ok(LanguageServerConfig { language_servers: vec![server], ..Default::default() })
}
```

grammar ของ Zed คือ tree-sitter — ถ้ายังไม่มี ชี้ไปที่ grammar
ของภาษาอื่นที่ indent ใกล้กัน (Python) ชั่วคราวก็ได้ LSP ยังทำงานครบ
