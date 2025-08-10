# Review guidelines for scripts/ (R)

- Entry dispatcher is `entry/mcp_tools.R`; ensure relative `source()` paths to `../tools` and `../adapters`
- Adapters in `adapters/meta_adapter.R` choose methods per effect measure (`PROP/OR/RR/MD/SMD/MEAN`)
- Tools in `tools/` must return JSON lists with `status` and relevant fields; avoid interactive code
- Upload normalization in `tools/upload_data.R` must handle CSV/Excel, base64, column mapping, and limits
- Prefer `meta` functions (metabin, metacont, metaprop, metamean, metagen); use `metafor` where needed
- Add roxygen-style headers to exported functions (inputs/outputs)
