#!/usr/bin/env python3
"""生成 Codeguard 核心技能的按需参考和场景示例。

默认仅检查差异；显式传入 --write 才会写入。脚本不删除未知文件。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CORE = {
    "codeguard": {
        "focus": "全局路由、能力状态、证据分层和跨技能交接",
        "rule": "先判定用户目标是 detect、check、fix、cve、git 还是 security，再路由到一个主技能。",
        "operation": "记录范围、状态、权威命令、退出码和未验证层，避免把局部成功扩大为整体成功。",
    },
    "codeguard-check": {
        "focus": "只读 lint 门禁、失败分类与 PASS/FAIL/UNVERIFIED/PLANNED 状态语义",
        "rule": "没有实际命令、扫描范围和退出码，不得声称门禁通过。",
        "operation": "按语言保留工具版本、命令、耗时、退出码和首个可操作错误。",
    },
    "codeguard-cve": {
        "focus": "依赖漏洞扫描、引入路径、修复版本、缓解与抑制证据",
        "rule": "工具或漏洞数据库不可用是 UNVERIFIED；不得用调高阈值代替修复。",
        "operation": "扫描后核对 CVE/GHSA、依赖路径、影响范围、修复版本和数据库新鲜度。",
    },
    "codeguard-detect": {
        "focus": "扩展名、文件名和项目标记的语言识别与歧义处理",
        "rule": "识别到语言不等于已实现门禁；planned 语言不得报告 PASS。",
        "operation": "先限定根目录和排除范围，再用标记文件与主要源文件交叉验证。",
    },
    "codeguard-fix": {
        "focus": "可逆自动修复、diff 审查、原命令复验与回归验证",
        "rule": "没有失败基线不修；不自动改业务语义、规则阈值、依赖版本或用户未提交改动。",
        "operation": "保存基线，dry-run，限定范围执行，审查 diff，复跑原 lint 并执行受影响测试。",
    },
    "codeguard-git-branch": {
        "focus": "分支模型识别、命名、合并方向、rebase 边界和发版分支生命周期",
        "rule": "不编造版本、作者、issue 或分支模型；不 rebase 已共享历史。",
        "operation": "读取远端分支、最近图形历史和仓库文档，输出模型、证据、命名与流向。",
    },
    "codeguard-git-commit": {
        "focus": "基于 staged diff 的提交信息起草、风格识别和 commit-msg 门禁",
        "rule": "不凭会话记忆编造改动，不用 --no-verify，不把未暂存改动写进 message。",
        "operation": "读取 git diff --cached 和最近提交风格，再校验 type、scope、subject、body 和 breaking change。",
    },
    "codeguard-init": {
        "focus": "已有仓库的 Codeguard 增量接入、配置合并、CI 验证和回退",
        "rule": "不覆盖既有配置，不自动安装 hook/全局工具，不把生成文件当成运行验证。",
        "operation": "先盘点 create/merge/skip，再执行最小配置变更，最后运行 parser、check 和 CI 等价门禁。",
    },
    "codeguard-security-api": {
        "focus": "身份、功能权限、对象层授权、文件上传和防重放",
        "rule": "不信任客户端 tenant/user/role 声明；资源归属必须在服务端从受信身份推导。",
        "operation": "沿路由、鉴权中间件、服务、查询和返回值跟踪一次请求，检查所有执行路径。",
    },
    "codeguard-security-code": {
        "focus": "凭据和配置泄露、源码暴露、依赖漏洞与修复证据",
        "rule": "已泄露密钥必须轮换；仅删除当前文件或添加 gitignore 不等于清除风险。",
        "operation": "分开处理当前工作树、Git 历史、远程系统、凭据轮换和依赖扫描证据。",
    },
    "codeguard-security-data": {
        "focus": "数据分级、加密、密钥托管、脱敏、审计和等保/密评证据",
        "rule": "加密方案必须包含密钥生命周期、轮换和授权边界；不使用真实个人数据做示例。",
        "operation": "按采集、传输、处理、存储、返回、日志、备份和销毁跟踪数据生命周期。",
    },
}


def files_for(name: str, meta: dict[str, str]) -> dict[Path, str]:
    base = ROOT / "skills" / name
    focus = meta["focus"]
    rule = meta["rule"]
    operation = meta["operation"]
    return {
        base / "references" / "rules" / "decision-contract.md": f"""# 决策契约

## 焦点

{focus}。

## 硬性规则

{rule}

## 通用证据要求

- 记录真实作用域、输入来源、工具/规则版本和时间。
- 区分已验证事实、基于上下文的推断、建议和未知项。
- 任何自动修复或抑制都要求原失败证据和复验证据。
- 缺少工具、配置、权限或环境时写 `UNVERIFIED`，不写 `PASS`。

## 停止条件

- 目标作用域不清晰。
- 操作将覆盖用户未提交改动。
- 需要安装、外部发布、凭据、付费或破坏性动作但未获授权。
""",
        base / "references" / "operations" / "evidence-playbook.md": f"""# 证据化操作手册

## 执行原则

{operation}

## 证据包

1. 目标：仓库、模块、文件或数据流。
2. 基线：执行前状态、现有配置和未提交改动。
3. 命令或检查点：实际输入、版本、作用域和结果。
4. 分类：PASS、FAIL、UNVERIFIED、PLANNED 或安全风险级别。
5. 变更：文件、规则、依赖或补偿措施。
6. 复验：原命令/原检查点与回归证据。
7. 剩余风险：未执行、不可到达和需用户决策的内容。

## 交付前检查

- [ ] 没有把未执行的步骤写成已通过。
- [ ] 没有依靠未经验证的猜测给出确定性结论。
- [ ] 没有回显凭据、秘密、真实个人数据或不必要的私有路径。
- [ ] 所有修复和例外都有责任人/跟踪条件或明确未完成。
""",
        base / "examples" / "01-read-only-assessment.md": f"""# 只读评估

用户：先检查 {name}，不要修改。

执行：确认作用域和现有规则 → 收集只读证据 → 按事实/推断/风险/未知分类。

重点：{focus}。
""",
        base / "examples" / "02-controlled-change.md": f"""# 受控变更

用户：根据发现做最小修复，不要扩大范围。

执行：保存基线 → 列出将变更的范围 → 只处理已授权项 → 审查差异 → 复验原检查。

约束：{rule}
""",
        base / "examples" / "03-unverified-input.md": f"""# 信息或工具不足

用户：请确认当前是否通过。

若缺少工具、配置、仓库上下文或权限，输出 `UNVERIFIED`，说明已确认的事实、缺口和安全的下一步。不静默安装，不冒充通过。
""",
        base / "examples" / "04-evidence-handoff.md": f"""# 证据交接

用户：把结果交给下一个处理人。

输出包含：目标范围、基线、真实命令/检查点、版本、退出码/风险、已做变更、复验、未完成与剩余风险。

执行原则：{operation}
""",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="检查是否需要重新生成（默认）")
    mode.add_argument("--write", action="store_true", help="写入生成的参考与示例")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed: list[str] = []
    for name, meta in CORE.items():
        for path, content in files_for(name, meta).items():
            normalized = content.rstrip() + "\n"
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current == normalized:
                continue
            changed.append(str(path.relative_to(ROOT)))
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(normalized, encoding="utf-8")
    payload = {"mode": "write" if args.write else "check", "changed_count": len(changed), "files": changed}
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"core_resources: {len(changed)} file(s) differ")
        for item in changed:
            print(item)
    return 0 if args.write or not changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
