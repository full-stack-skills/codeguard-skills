# AGENTS.md

## Scope

This repository contains portable Agent Skills only. It does not contain the executable Codeguard CLI, hooks, linters, or release pipeline.

## Source of truth

- Skill content: `skills/<skill-name>/`
- Language capability snapshot: `references/languages.json`
- Generated language skills and manifest: `scripts/generate_language_skills.py`
- Generated core references/examples: `scripts/generate_core_resources.py`

Do not edit a generated language skill by hand unless the generator is updated in the same change. Core `SKILL.md` files are authored; their common references/examples are generated.

## Quality gates

Before completion, run:

```bash
python3 scripts/lint_skills.py
python3 scripts/generate_language_skills.py --check --format json
python3 scripts/generate_core_resources.py --check --format json
```

Run TRACE evaluation for changed skills. CI also executes `scripts/trace_gate.py` with the evaluator pinned in `.github/workflows/lint.yml` and rejects any skill below 4.5. Keep every `SKILL.md` below 500 lines and use progressive disclosure for reference material.

## Release and downstream synchronization

- Published `v*` tags are protected by an active GitHub tag ruleset and must never be moved or deleted.
- GitHub immutable releases are enabled for future releases.
- Publishing a release invokes `.github/workflows/dispatch-plugin-sync.yml`, which sends the immutable tag and peeled commit SHA to `full-stack-plugins/codeguard-plugin`.
- The dispatch workflow requires repository secret `SKILLS_SYNC_TOKEN`, scoped to Contents: write for the plugin repository only. Never use a broad personal token.

## Cross-skill references

Never link to a sibling skill using `../`. Granular installs do not include siblings. Hand off by skill name and installation command:

```markdown
交给 **`codeguard-fix`** 技能。安装：`npx skills add full-stack-skills/codeguard-skills --skill codeguard-fix`。
```

## Runtime synchronization

`references/languages.json` is a snapshot from the Codeguard plugin runtime registry, not an independently editable product contract. When the runtime changes:

1. update the snapshot from the released plugin source;
2. run the language generator with `--write`;
3. run all lint and TRACE gates;
4. record the source plugin version and commit in `references/source-provenance.json`;
5. release this package before updating the plugin vendor lock.

Do not claim a command is executable merely because a skill documents it. `planned` profiles remain non-executable until the runtime implements and tests their gates.
