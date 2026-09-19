<div align="center">

# codeguard-skills

**Codeguard quality-gate knowledge for Codex, ZCode, Kimi, and other Agent Skills clients**

[简体中文](./README.zh-CN.md) | English

</div>

## Status

This repository is the standalone package extracted from `codeguard-plugin/skills`. It contains **68 skills**: 11 core governance skills and 57 language/file-type skills. The package structure, deeper content, generators, lint gate, TRACE evaluation, immutable `v0.1.0` tag, and plugin vendor integration are complete.

Repository: [full-stack-skills/codeguard-skills](https://github.com/full-stack-skills/codeguard-skills). `codeguard-plugin` v0.4.0 pins `v0.1.0` and commit `d6f2ee3c7b67ef037082212ca13a4bda758eefe0` through a per-skill checksummed vendor lock. A tag, plugin publication, Marketplace update, and fresh host installation remain distinct proof levels; fresh host installation has not yet been claimed here.

## Responsibility split

- `codeguard-skills`: portable operational knowledge, boundaries, workflows, failure semantics, examples, and references.
- `codeguard-plugin`: executable CLI, hooks, linters, runtime registry, retries, and host integration.

The plugin vendors a versioned and checksummed snapshot from this package instead of maintaining an independent handwritten copy. Only plugin-specific skills intentionally absent from its lock may be authored inside the plugin repository.

## Package contents

| Layer | Count | Scope |
|---|---:|---|
| Entry and commands | 6 | route, detect, check, fix, CVE, init |
| Git governance | 2 | branch model and commit-message governance |
| Security governance | 3 | code, API, and data security |
| Language/file profiles | 57 | 53 stable gates and 4 planned profiles |

Every generated language skill provides trigger guidance, capability boundaries, security declarations, a seven-step workflow, failure classification, output contract, gotchas, FAQ, two reference groups, and four scenario examples.

## Local validation

```bash
python3 scripts/lint_skills.py
python3 scripts/generate_language_skills.py --check --format json
python3 scripts/generate_core_resources.py --check --format json
```

Both generators default to check-only behavior and require an explicit `--write` to modify files. They never delete unknown files.

The expected generic Skills CLI installation shape is:

```bash
npx skills add full-stack-skills/codeguard-skills
npx skills add full-stack-skills/codeguard-skills --skill codeguard-check
```

These commands describe the host-side contract. Plugin publication, Marketplace installation, and real host loading still require separate evidence.

## Repository layout

```text
codeguard-skills/
├── .claude-plugin/plugin.json
├── skills/
├── references/languages.json
├── scripts/
├── MIGRATION.md
├── TRACE_EVALUATION.md
├── README.md
└── README.zh-CN.md
```

## License

Apache License 2.0. See [LICENSE](./LICENSE).
