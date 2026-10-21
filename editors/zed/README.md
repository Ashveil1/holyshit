# Zed - holyshit

Zed needs a separate extension, but the protocol is plain LSP,
so there are two ways to connect:

## 1. Use LSP directly (custom server)

`~/.config/zed/settings.json`:

```json
{
  "languages": {
    "Holyshit": {
      "extensions": ["holy", "hs"],
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

Note: Zed diagnostics need text edits that map back to lines - the server
returns whole lines, which Zed accepts.

## 2. Write your own Zed extension (cleaner)

Skeleton `extension.toml` + `src/holyshit.rs`:

```toml
# extension.toml
id = "holyshit"
name = "Holyshit"
description = "holyshit (.holy) support"
schema_version = 1
languages = ["Holyshit"]
language-servers = ["holyshit-lsp"]

[[grammar]]
name = "holyshit"
source = { path = "./grammar" }
file-types = ["holy", "hs"]
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

Zed's grammar is tree-sitter - until one exists, pointing at the grammar of
a language with similar indentation (Python) works; the LSP still works fully
