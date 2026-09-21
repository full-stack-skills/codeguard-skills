#!/usr/bin/env python3
"""Generate the language-specific Codeguard skills from the capability snapshot.

The generator is intentionally conservative:
- default mode is read-only ``--check``;
- ``--write`` is required to change files;
- it never deletes unknown files;
- output can be emitted as text or JSON;
- all generated commands come from ``references/languages.json``.

The runtime registry remains authoritative for what the Codeguard plugin can
execute. This package turns that verified registry into standalone, installable
Agent Skills without claiming that planned integrations are already available.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references" / "languages.json"
SKILLS = ROOT / "skills"
MANIFEST = ROOT / ".claude-plugin" / "plugin.json"


SPECIAL_NOTES: dict[str, list[str]] = {
    "java": [
        "`mvn compile` 不执行 Javadoc 门禁；发布链失败时必须单独运行 `mvn javadoc:jar`。",
        "JDK 版本会改变 doclint 严格度；本地和 CI 必须使用同一主版本。",
    ],
    "rust": [
        "`cargo fmt` 通过不代表 Clippy 通过；格式和语义 lint 是两条独立门禁。",
        "Workspace 必须从根 `Cargo.toml` 执行，否则可能漏掉成员 crate。",
    ],
    "typescript": [
        "坚持 `npx --no-install`，避免检查过程静默下载与改变依赖树。",
        "ESLint flat config 与旧 `.eslintrc` 的解析规则不同，先确认项目实际采用哪一套。",
    ],
    "python": [
        "Ruff 的 `check --fix` 与 `format` 职责不同；需要格式化时两者应分别执行。",
        "先读取 `pyproject.toml` 的 target-version 与 per-file-ignores，不能用全局默认覆盖项目契约。",
    ],
    "go": [
        "`gofmt` 只处理格式；`go vet` 与 `go test` 仍需独立运行。",
        "多模块仓库可能包含多个 `go.mod`，从错误根目录执行会漏检。",
    ],
    "c": ["clang-tidy 需要可靠的编译参数；复杂项目优先提供 `compile_commands.json`。"],
    "cpp": ["模板、宏和条件编译高度依赖真实编译数据库；不要凭单文件默认参数宣布通过。"],
    "objc": ["Objective-C++ 的 `.mm` 文件必须使用匹配的 SDK 与编译参数，单独 clang-tidy 结果可能失真。"],
    "cuda": ["CUDA 文件同时受主机编译器与 nvcc 约束；clang-tidy 不能替代真实 CUDA 构建。"],
    "kotlin": ["Detekt 与 ktlint 是不同门禁；Gradle wrapper 版本和插件配置必须以项目为准。"],
    "swift": ["SwiftLint 的规则来自仓库配置；不得用个人全局配置覆盖团队 `.swiftlint.yml`。"],
    "php": ["`php -l` 只验证语法，不覆盖类型、风格或框架规则；不要把语法通过写成质量全绿。"],
    "shell": ["ShellCheck 必须匹配脚本 shebang；bash、sh、zsh 的语义不能混用。"],
    "dockerfile": ["Hadolint 通过不证明镜像安全；仍需检查基础镜像摘要、SBOM 与漏洞扫描结果。"],
    "yaml": ["YAML 语法正确不等于 Kubernetes、Compose 或 CI schema 正确；需要对应 schema 校验。"],
    "css": ["Stylelint glob 必须覆盖 SCSS/Sass/LESS 时显式扩展，默认 `**/*.css` 不会自动覆盖全部预处理器。"],
    "dart": ["`dart analyze` 与 Flutter widget/integration tests 是不同证据层级。"],
    "vue": ["Vue SFC 需要匹配 Vue 版本的 parser/plugin；普通 ESLint 配置可能跳过 `<template>`。"],
    "svelte": ["Svelte parser 与 ESLint 主版本需要兼容；解析失败不能降级为跳过。"],
    "astro": ["Astro 文件需要专用 parser；只检查脚本区不能代表整个组件通过。"],
    "solidity": ["Solhint 是风格/静态检查，不替代 Slither、Foundry 测试或合约审计。"],
    "terraform": ["`terraform fmt`、`terraform validate` 与 TFLint 是三类门禁，不能互相替代。"],
    "nix": ["deadnix 发现未使用表达式，nixpkgs-fmt 只格式化；仍需执行 flake/check 或真实构建。"],
    "html": ["模板文件可能包含服务端语法；HTMLHint 解析失败时先确认是否应交给模板专用工具。"],
    "sql": ["SQLFluff 必须设置正确 dialect；未指定方言的通过结果不能用于数据库兼容性结论。"],
    "graphql": ["GraphQL lint 依赖 schema；无 schema 时只能验证有限的文档规则。"],
    "protobuf": ["Buf lint 通过后仍应检查 breaking changes；风格合规不等于 wire compatibility。"],
    "markdown": ["Markdown 方言和文档生成器规则不同；先读取 `.markdownlint*` 与站点配置。"],
    "toml": ["Taplo 格式化会重排布局；先确认生成文件和锁文件是否允许修改。"],
    "haskell": ["HLint 建议不总是语义等价；涉及 strictness 或性能时禁止盲目批量应用。"],
    "ocaml": ["ocamlformat 版本是格式契约的一部分；不同版本可能产生大面积无意义 diff。"],
    "fsharp": ["Fantomas 主要处理格式，不替代编译器、测试与 analyzers。"],
    "perl": ["Perl::Critic profile 决定严重级别；必须读取项目 `.perlcriticrc`。"],
    "groovy": ["Groovy 动态特性使静态 lint 覆盖有限；Gradle/Jenkins DSL 需结合宿主验证。"],
    "clojure": ["clj-kondo cache 与 classpath 会影响宏分析；宏项目需提供导出配置。"],
    "powershell": ["Windows PowerShell 与 PowerShell 7 规则/模块不同，先确认目标运行时。"],
    "zig": ["`zig fmt --check` 只验证格式；必须结合目标 Zig 版本的 build/test 结果。"],
    "nim": ["`nim check` 仍依赖项目 defines 与搜索路径；单文件默认上下文可能误报。"],
    "crystal": ["Ameba 配置和 Crystal 版本需匹配；格式化不替代 `crystal spec`。"],
    "julia": ["只有 formatter 时必须明确标为 format-only，不能把它当作语义 lint 通过。"],
    "elm": ["elm-review 依赖项目 review 配置；未初始化时应报告不可验证。"],
    "lua": ["Lua 版本和宿主环境差异大；Luacheck globals 必须与运行时一致。"],
    "luau": ["Luau 与标准 Lua 类型/语法不同，禁止用普通 Lua linter 代替。"],
    "pascal": ["只有格式化能力时不得声称完成静态检查；仍需编译器或 IDE 诊断。"],
    "r": ["R 包项目与普通脚本目录的 lint 范围不同；包项目还需 R CMD check。"],
    "cfml": ["CFML 方言与引擎差异会影响 CFLint 结果；需注明 Adobe CF 或 Lucee。"],
    "vbnet": ["dotnet format 需要解析 solution/project；只有散落 `.vb` 文件时不可宣布通过。"],
    "erlang": ["Elvis 与 erlfmt 依赖 rebar 项目上下文；OTP 版本也会改变可用语法。"],
    "liquid": ["Shopify Theme Check 面向 Shopify Liquid；其他 Liquid 方言需单独确认。"],
    "ansible": ["当前条目标记为 planned；不得把 YAML 通道的结果冒充 Ansible 语义门禁。"],
    "arkts": ["当前条目标记为 planned；需要 HarmonyOS/DevEco 官方诊断证据后才能升级。"],
    "metal": ["当前条目标记为 planned；需要 Xcode/metal 编译链证据后才能升级。"],
    "cobol": ["当前条目标记为 planned；依赖具体编译器/IDE，不能虚构通用 CLI。"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate detailed Codeguard language skills from references/languages.json."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write generated files")
    mode.add_argument("--check", action="store_true", help="check without writing (default)")
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="result output format"
    )
    return parser.parse_args()


def shell_join(parts: list[str] | None) -> str:
    if not parts:
        return ""
    return shlex.join(parts)


def as_list(value: Any) -> list[str]:
    return value if isinstance(value, list) else []


def scalar(value: Any, fallback: str = "无") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def render_skill(lang: dict[str, Any]) -> str:
    lang_id = lang["id"]
    name = lang["name"]
    status = lang["status"]
    stable = status in {"stable", "beta"}
    lint = shell_join(lang.get("lint"))
    fmt = shell_join(lang.get("format"))
    gate = shell_join(lang.get("gate"))
    probe = shell_join(lang.get("probe"))
    extensions = ", ".join(f"`{item}`" for item in as_list(lang.get("extensions"))) or "无固定扩展名"
    markers = ", ".join(f"`{item}`" for item in as_list(lang.get("markers"))) or "无专用标记文件"
    configs = ", ".join(f"`{item}`" for item in as_list(lang.get("requiresConfig"))) or "以仓库现有配置为准"
    desc_status = "执行并诊断" if stable else "识别但不冒充已执行"
    description = (
        f"使用 Codeguard 对 {name} 项目{desc_status}代码规范门禁；当用户要求 lint、格式检查、"
        f"自动修复、提交前质量验证，或出现 {lint or '尚未接入的检查链'} 相关失败时使用。"
        "先确认仓库配置和工具可用性，区分通过、失败、无法验证与 planned，修复后必须复跑。"
    )
    notes = SPECIAL_NOTES.get(lang_id, [])
    note_lines = "\n".join(f"{index}. **领域陷阱** — {note}" for index, note in enumerate(notes, 1))
    if not note_lines:
        note_lines = "1. **项目配置优先** — 工具默认值不能覆盖仓库已提交的规则和版本约束。"
    execution = f"""## 执行契约

| 项目 | 当前事实 |
|---|---|
| 状态 | `{status}`（自 Codeguard {scalar(lang.get('since'))}） |
| 文件扩展名 | {extensions} |
| 项目标记 | {markers} |
| 接入配置 | {configs} |
| 工具准备 | {scalar(lang.get('install_hint'), '工具链内置或由项目声明')} |
| 探测命令 | `{probe or '使用命令查找与项目配置检查'}` |
| lint | `{lint or '未接入'}` |
| format/fix | `{fmt or '未接入'}` |
| 项目级 gate | `{(gate or lint or "未接入").replace("|", "\\|")}` |
"""
    if stable:
        quick = f"""## 30 秒开始

1. 在仓库根确认 `{markers}` 或目标文件存在。
2. 探测工具：`{probe or (lang.get('lint') or ['command', '-v'])[0] + ' --version'}`。
3. 先只读检查：`{gate or lint}`。
4. 将结果分为：代码违规、配置缺失、工具缺失、工具内部错误。
5. 只对可安全修复项执行：`{fmt or '手工最小修复'}`。
6. 复跑 lint，并执行项目已有测试/构建门禁。

可直接提出：

- “检查这个 {name} 项目，先不要修改，给我 lint 失败分类。”
- “只修复 {name} 的格式问题，语义问题先列清单。”
- “提交前验证 {name} lint、测试和构建证据。”
"""
        strengths = f"""### ✅ 擅长处理

1. 根据 {extensions} 与项目标记识别 {name} 工作区。
2. 执行 `{lint}` 并保留退出码、作用域和工具版本。
3. 区分格式、静态规则、配置、依赖和环境类失败。
4. 使用 `{fmt or '人工最小修复'}` 处理可逆问题并复扫。
5. 把本地结果与 CI/构建/测试证据分层汇报。
"""
        conditions = """### ⚠️ 需要条件

1. 目标工具必须已安装且版本与项目约束兼容。
2. 必须从正确仓库或模块根目录执行。
3. 项目若有自定义配置，以已提交配置为准。
4. 生成代码、vendor、缓存目录是否扫描必须遵循仓库规则。
"""
        out_scope = """### ❌ 不适用范围

1. 不把 formatter 通过当作编译、测试或安全审计通过。
2. 不静默安装工具、升级依赖或修改团队规则。
3. 不用 suppress/ignore/调高阈值掩盖真实问题。
4. 不在缺少工具或配置时声称“检查通过”。
"""
    else:
        quick = f"""## 30 秒开始

当前 `{status}` 只表示 Codeguard 能识别 {extensions}，不表示存在可执行门禁。

1. 明确报告“已识别，但当前无法由 Codeguard 验证”。
2. 保留项目已有 IDE、编译器或平台诊断结果，不伪造通用命令。
3. 若必须检查，使用目标平台官方工具，并把结果标为外部证据。
4. 只有补齐探测、lint、失败样例和回归测试后，才能把注册表升级为 stable/beta。
"""
        strengths = f"""### ✅ 擅长处理

1. 识别 {name} 文件和相关用户意图。
2. 明确说明当前 Codeguard 支持状态与缺口。
3. 为未来接入定义可验证的验收条件。
"""
        conditions = """### ⚠️ 需要条件

1. 真实目标工具或平台诊断输出。
2. 至少一个失败样例和一个通过样例。
3. 可重复的非交互命令或明确的宿主边界。
"""
        out_scope = """### ❌ 不适用范围

1. 不执行不存在的通用 linter 命令。
2. 不把扩展名识别写成质量门禁通过。
3. 不在没有运行证据时升级支持状态。
"""

    return f"""---
name: codeguard-{lang_id}
description: {description}
license: Apache-2.0
compatibility: 需要本地项目、对应语言工具链和仓库既有 lint 配置；默认只读检查，不自动安装依赖。
---

# {name} Codeguard 门禁

> 目标：把“看起来没问题”变成可重复的工具证据，并且诚实区分通过、失败、无法验证和 planned。

{quick}

## 能力边界

{strengths}
{conditions}
{out_scope}

## 什么时候使用

- 用户要求检查或修复 {name} 代码规范。
- AI 修改了 {extensions}，需要提交前验证。
- CI 出现与 `{lint or name + ' 工具链'}` 相关的失败。
- 需要判断某个问题能否自动修复，或必须人工处理。

## 什么时候不该使用

- 主要任务是学习语言语法、框架设计或业务建模，应改用对应语言专业技能。
- 主要任务是依赖漏洞、安全审计或许可证治理，应使用专门安全技能。
- 用户只要求解释一条报错且没有项目上下文时，先做局部解释，不宣称仓库全绿。

## 数据与安全

本技能不收集、上传、发送或存储用户代码和凭据。默认只读取本地仓库配置并运行本地工具；不联网安装依赖，不记录 token、密码或私有源码。任何自动修复前先检查 diff，破坏性或大范围修改必须由用户明确确认。

{execution}

## 标准 Workflow

### Step 1：确定真实作用域

确认仓库根、模块根、生成目录、vendor 目录和用户指定文件。多模块项目先列出将被扫描的模块，禁止靠当前目录猜测。

### Step 2：读取项目契约

读取 {configs} 及 CI 中的实际命令。仓库配置优先于本技能示例；如果两者冲突，先报告差异。

### Step 3：探测工具与版本

运行 `{probe or '对应工具 --version'}`。工具缺失、版本不兼容或配置无法加载均记为“无法验证”，不是通过。

### Step 4：执行只读检查

运行 `{gate or lint or '目标平台官方诊断'}`，记录命令、工作目录、退出码、工具版本和首个可操作错误。

### Step 5：失败分型

| 类型 | 典型信号 | 处理 |
|---|---|---|
| 格式 | 缩进、空白、import 顺序 | 允许 formatter，随后检查 diff |
| 静态规则 | unused、复杂度、命名、危险 API | 最小语义修复，禁止批量猜测 |
| 配置 | parser/config/schema 找不到 | 修复接入或报告前置条件 |
| 环境 | command not found、版本冲突 | 报告安装/版本要求，不静默安装 |
| 工具内部错误 | crash、timeout、解析器异常 | 保留原始证据，缩小复现范围 |

### Step 6：受控修复

优先运行 `{fmt or '人工最小修复'}`。只处理确定可逆的问题；依赖升级、规则豁免、生成文件和业务语义改动必须单独说明。

### Step 7：验证闭环

复跑同一 lint 命令，再运行项目已有测试与构建。只有命令、范围和退出码都明确时才写“通过”；否则写“未运行”或“无法验证”。

## Rules

1. **同命令复验**：修复后必须复跑触发失败的原命令。
2. **证据分层**：lint、format、compile、test、security 分开报告。
3. **最小修改**：不顺手重构，不把风格修复扩大成业务改写。
4. **配置优先**：不覆盖项目已有 ignore、dialect、target 或版本约束。
5. **禁止胡编**：未运行的工具、未看到的配置和未验证的平台必须明确标注。

## 输出模板

```text
{name} Codeguard 结果
- 范围：<仓库/模块/文件>
- 工具：<名称与版本>
- 命令：<实际命令>
- 状态：PASS / FAIL / UNVERIFIED / PLANNED
- 发现：<按格式/规则/配置/环境分类>
- 修改：<文件与原因；无修改写 none>
- 复验：<命令、退出码>
- 未验证：<测试/构建/平台差异>
```

## Gotchas

1. **工具缺失不是通过** — 必须输出 `UNVERIFIED` 和明确的准备方式。
2. **formatter 不是 linter** — 格式全绿不能覆盖静态规则或编译错误。
3. **根目录决定结果** — 在错误模块运行可能漏检或加载错误配置。
4. **占位符不是字面参数** — `{{file}}` 必须替换为真实、已授权路径。
5. **自动修复可能扩大 diff** — 修复后先审查 diff，再运行回归门禁。
6. **生成与 vendor 目录需显式策略** — 不得随意全仓扫描或修改第三方内容。

### 领域陷阱与修复

{note_lines}

## 信息不足时

不要只说“请提供更多信息”。先给出安全的只读检查方案，并列出仍需确认的具体项：

1. 仓库/模块根目录；
2. 目标工具与版本；
3. 项目配置文件；
4. CI 中的权威命令；
5. 是否允许自动修复。

## FAQ

**Q1：工具没安装，可以判定代码没问题吗？** 不能。状态必须是 `UNVERIFIED`。

**Q2：可以自动加 ignore 或 suppression 吗？** 不可以。只有用户明确接受并记录理由时才能豁免。

**Q3：格式化后为什么还失败？** formatter 只覆盖格式；静态规则、配置、编译和测试仍需分别处理。

**Q4：是否应该扫描生成代码？** 默认遵循仓库配置；没有规则时先排除生成/vendor，再向用户说明。

**Q5：如何避免一次修改太多？** 先按失败类别和文件分批修复，每批都复跑原命令并审查 diff。

**Q6：本地通过就能说 CI 会通过吗？** 不能。还需对齐 CI 的版本、环境变量、操作系统和命令范围。

## 按需加载资源

- 遇到退出码、失败分类或豁免决策时，读取 `references/rules/gate-rules.md`。
- 需要核对本语言注册表、工具链和项目配置时，读取 `references/tooling/toolchain.md`。
- 需要可复制任务示例时，按场景读取 `examples/`，不必一次加载全部。
"""


def render_gate_rules(lang: dict[str, Any]) -> str:
    return f"""# {lang['name']} 门禁规则与失败语义

## 状态机

```text
DETECTED -> READY -> CHECKING -> PASS
                  |            -> FAIL -> FIXING -> RECHECK
                  -> UNVERIFIED
DETECTED -> PLANNED
```

- `PASS`：权威检查命令在明确范围内退出 0。
- `FAIL`：工具成功运行并发现违规。
- `UNVERIFIED`：工具、配置、权限、版本或环境不足。
- `PLANNED`：仅有识别能力，尚无可执行门禁。

## 修复优先级

1. 配置加载错误：先恢复工具可运行性。
2. 自动可逆格式问题：运行 formatter 并审查 diff。
3. 确定性静态规则：做最小代码修复。
4. 可能改变行为的问题：停止自动修复，解释取舍。
5. 规则争议：保留失败，等待用户决定，不静默豁免。

## 完成门禁

- [ ] 记录工具版本、命令、工作目录与扫描范围。
- [ ] 原失败命令复跑退出 0。
- [ ] 自动修复 diff 已审查。
- [ ] 项目已有测试/构建已运行或明确标为未运行。
- [ ] 没有新增 suppression、ignore 或规则降级。
- [ ] 报告区分 PASS、FAIL、UNVERIFIED、PLANNED。
"""


def render_toolchain(lang: dict[str, Any]) -> str:
    fields = {
        "id": lang["id"],
        "name": lang["name"],
        "status": lang["status"],
        "since": lang.get("since"),
        "extensions": lang.get("extensions", []),
        "file_names": lang.get("file_names", []),
        "markers": lang.get("markers", []),
        "requiresConfig": lang.get("requiresConfig", []),
        "probe": lang.get("probe", []),
        "lint": lang.get("lint", []),
        "gate": lang.get("gate", []),
        "format": lang.get("format", []),
        "install_hint": lang.get("install_hint"),
    }
    return """# 工具链快照\n\n该快照来自 Codeguard 运行时注册表。发布前应通过差分检查确认未漂移。\n\n```json\n""" + json.dumps(fields, ensure_ascii=False, indent=2) + "\n```\n"


def render_example(lang: dict[str, Any], kind: str) -> str:
    name = lang["name"]
    lint = shell_join(lang.get("gate") or lang.get("lint")) or "当前无可执行门禁"
    fmt = shell_join(lang.get("format")) or "人工最小修复"
    examples = {
        "01-detect-and-check.md": f"""# 只读检测与检查\n\n用户：检查这个 {name} 项目，但先不要修改。\n\n执行：确认根目录和配置 → 探测工具 → 运行 `{lint}`。\n\n输出必须包含范围、工具版本、退出码和 PASS/FAIL/UNVERIFIED/PLANNED。\n""",
        "02-fix-and-recheck.md": f"""# 受控修复与复验\n\n用户：修复 {name} lint，但不要改变业务逻辑。\n\n执行：先保存失败证据 → 仅对格式类问题运行 `{fmt}` → 审查 diff → 复跑 `{lint}` → 跑受影响测试。\n""",
        "03-missing-tool.md": f"""# 工具缺失降级\n\n用户：确认 {name} 代码是否全绿。\n\n如果工具或配置缺失：输出 `UNVERIFIED`，列出缺少的命令、版本和配置；不得静默安装，也不得写“通过”。\n""",
        "04-ci-gate.md": f"""# CI 门禁对齐\n\n用户：本地已经通过，为什么 CI 仍失败？\n\n对比本地与 CI 的工具版本、工作目录、配置、环境变量、扫描范围和实际命令；使用 CI 的 `{lint}` 形状复现，并分别报告 lint、test、build 证据。\n""",
    }
    return examples[kind]


def desired_files(languages: list[dict[str, Any]]) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for lang in languages:
        skill = SKILLS / f"codeguard-{lang['id']}"
        files[skill / "SKILL.md"] = render_skill(lang)
        files[skill / "references" / "rules" / "gate-rules.md"] = render_gate_rules(lang)
        files[skill / "references" / "tooling" / "toolchain.md"] = render_toolchain(lang)
        for example in (
            "01-detect-and-check.md",
            "02-fix-and-recheck.md",
            "03-missing-tool.md",
            "04-ci-gate.md",
        ):
            files[skill / "examples" / example] = render_example(lang, example)

    skill_paths = sorted(
        f"./skills/{path.name}" for path in SKILLS.iterdir() if path.is_dir()
    )
    manifest = {
        "name": "codeguard-skills",
        "version": "0.1.0",
        "description": "Codeguard quality-gate skills for lint, safe fixes, Git governance, CVE triage, and 57 language/toolchain profiles",
        "author": {"name": "PartMe.AI", "email": "partmeai@gmail.com"},
        "homepage": "https://github.com/full-stack-skills/codeguard-skills",
        "repository": "https://github.com/full-stack-skills/codeguard-skills",
        "source": "./",
        "skills": skill_paths,
    }
    files[MANIFEST] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return files


def main() -> int:
    args = parse_args()
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    languages = payload.get("languages", [])
    expected = desired_files(languages)
    changed: list[str] = []

    for path, content in expected.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        changed.append(str(path.relative_to(ROOT)))
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    result = {
        "mode": "write" if args.write else "check",
        "language_count": len(languages),
        "changed_count": len(changed),
        "changed": changed,
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        action = "updated" if args.write else "would change"
        print(f"generate_language_skills: {len(languages)} languages; {len(changed)} files {action}")
        for item in changed:
            print(f"  - {item}")
    return 0 if args.write or not changed else 1


if __name__ == "__main__":
    sys.exit(main())
