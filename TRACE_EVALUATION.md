# Codeguard Skills TRACE 评估报告

## 评估信息

- 评估对象：`codeguard-skills` 本地独立包候选，共 68 个技能。
- 评估日期：2026-09-19。
- 评估方法：`skill-trace-evaluation` 的确定性静态评分器 + 人工语义抽样校准。
- 基线来源：拆分前 `codeguard-plugin/skills` 的 68 个技能。
- 最终来源：当前 `codeguard-skills/skills`。
- 评分范围：1.0–5.0；4.5 及以上为优秀。

> 本报告评估技能质量。GitHub 远端与 `main` 已建立，但本报告不证明 Codeguard CLI、release/tag、插件发行物或真实宿主安装已经可用。

## 总体结果

| 阶段 | 技能数 | Overall | T Trust | R Reliability | A Adaptability | C Convention | E Effectiveness | 最低 / 最高 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 拆分前基线 | 68 | 3.931 | 4.441 | 3.631 | 3.958 | 3.820 | 3.803 | 3.84 / 4.12 |
| 当前确定性评分 | 68 | **4.643** | **4.950** | **4.577** | **4.462** | **4.649** | **4.561** | **4.56 / 4.73** |
| 提升 | — | **+0.712** | +0.509 | +0.946 | +0.504 | +0.829 | +0.758 | +0.72 / +0.61 |

结论：当前 68 个技能全部达到 4.5 以上的包级总体目标；确定性最低项为 `codeguard-security-code` 4.56，最高项为 4.73。没有技能仍低于 4.5。

## 基线问题

拆分前最弱的技能是 `codeguard-php`、`codeguard-python`、`codeguard-scala` 和 `codeguard-swift`（3.84），其次为 `codeguard-check` 与 `codeguard-detect`（3.86）。主要缺口不是语法错误，而是：

1. description 使用 YAML block scalar，部分宿主只能解析到 `|`；
2. 大量语言技能只有 34–39 行，缺少不适用范围、工具缺失降级、复验、gotchas 和 examples；
3. references 几乎为空，无法渐进式加载工具链与规则证据；
4. 技能状态与运行时注册表漂移，stable 能力仍被文档标为 planned；
5. 技能与插件运行时耦合，存在跨 sibling/插件文档的相对路径。

## 五维分析

### T · Trust：4.950

- 所有技能均使用中文主体、合法 kebab-case 名称和单行触发 description。
- 全部技能声明只读默认、安全/隐私边界与授权门禁。
- stable、planned、工具缺失和未验证状态被显式区分。
- 没有在技能文件中发现硬编码秘密。

### R · Reliability：4.577

- 语言技能统一为七步 Workflow，并要求原命令复验。
- 核心技能补齐失败分类、停止条件、Rules、Gotchas 与证据交接。
- 每个技能至少有 4 个 examples；每个语言技能有 2 个 reference 分组。
- 工具缺失、超时、配置失败均输出 `UNVERIFIED`，不再冒充 PASS。

### A · Adaptability：4.462

- 描述覆盖中文用户表达、CI 失败、提交前验证与领域触发词。
- stable 与 planned 采用不同工作流；planned 技能只给接入验收条件。
- monorepo、生成代码、vendor、CI/本地差异与多工具版本漂移都有降级策略。
- 该维度略低于 4.5 的原因是确定性评分器对中文可读性固定给 4.3，且文档型技能的通用化静态上限偏低；人工抽样未发现需要扣分的语义问题。

### C · Convention：4.649

- 68 个目录均有名称匹配的 `SKILL.md`，manifest 完整列出所有技能。
- description 单行、20–1024 字符；所有 `SKILL.md` 少于 500 行。
- references 使用两层分类，examples 使用编号场景名。
- 已清除 sibling skill 的 `../` 相对链接，交接改为技能名 + 安装命令。

### E · Effectiveness：4.561

- 每个语言技能包含 30 秒开始、执行契约、七步闭环、输出模板、FAQ 和按需资源路由。
- 核心命令技能给出实际命令形状、状态语义和复验策略。
- 安全技能从静态清单扩展为信任边界、失败路径、处置与剩余风险证据。
- 技能包明确不携带 CLI，避免“文档命令存在”被误读为“运行时已经安装”。

## 人工语义校准

抽样覆盖：

- 主入口：`codeguard`；
- 只读命令：`codeguard-check`；
- stable 语言：`codeguard-python`；
- planned 语言：`codeguard-ansible`；
- Git 治理：`codeguard-git-branch`；
- 安全治理：`codeguard-security-code`。

逐项阅读 SKILL、references 与 examples 后，未发现确定性评分与语义质量之间达到 ±0.1 以上的偏差，因此没有为了提高分数施加人工加分，也没有额外扣分。最终总体分沿用可复现的确定性分数 **4.643/5.0**。

### 语义抽样结论

- `codeguard-python`：命令、工具缺失、配置优先、修复复验和 CI 差异闭环一致。
- `codeguard-ansible`：虽然列出目标工具，但明确声明运行时状态为 planned，不将外部 `ansible-lint` 结果冒充 Codeguard 门禁。
- `codeguard-security-code`：明确“删除文件不等于撤销泄露”，包含凭据轮换、历史副本、日志排查和抑制到期边界。
- `codeguard`：清楚区分知识路由、CLI 执行、Git 写操作和发布授权。

## 无技能基线

这是结构化推演，不是在线 A/B 实验。若不加载任何 Codeguard 技能，通用模型通常缺少以下本地事实：57 个注册表条目、53/4 的 stable/planned 划分、真实命令形状、PASS/FAIL/UNVERIFIED 语义、插件与技能包的职责边界。因此估计只能达到约 **2.4/5.0**：可以给出通用 lint 建议，但容易猜测工具、遗漏仓库配置、把工具缺失当作未发现问题，或把格式通过扩张为完整质量证明。

当前技能包相对该推演基线的主要收益是：可路由、可执行、可降级、可复验、可交接。

## 官方规范与本仓库约束检查

| 检查项 | 结果 |
|---|---|
| 目录名与 `name` 一致 | 68/68 通过 |
| description 单行且含触发条件 | 68/68 通过 |
| `SKILL.md` 少于 500 行 | 68/68 通过 |
| 跨 sibling 的 `../` 链接 | 0 个 |
| references/examples 渐进式披露 | 68/68 具备 |
| 生成器默认只读检查 | 通过 |
| 生成器 `--help` | 通过 |
| Python 语法编译 | 通过 |
| manifest 技能数 | 68 |

## 改进优先级

### P1 · 发布与消费链

1. 等待并核对首次 GitHub Actions CI，再发布不可变 `v0.1.0`。
2. 从全新缓存验证完整安装和单技能安装。
3. 在 `codeguard-plugin` 增加带 commit、version、sha256 的 vendor lock/sync/check，而不是继续手工双写。

这些是迁移完成门禁，不是本地技能内容问题。

### P2 · 自动化评测

1. 为 11 个核心技能增加任务级 fixture，验证路由、状态语义和安全停止条件。
2. 为每个 planned → stable 变更建立失败样例、通过样例、工具版本与运行时回归测试。
3. 在 CI 中运行 TRACE 并设置 overall ≥4.5、单技能不得回退的门禁。

### P3 · 长期维护

1. 由插件 release/tag 自动生成并签名 `references/languages.json` 快照。
2. 增加 Codex、ZCode、Kimi、Claude Code 的真实安装/加载矩阵。
3. 记录每个语言工具链的最低/推荐版本和离线行为。

## 复现命令

```bash
python3 scripts/lint_skills.py
python3 scripts/generate_language_skills.py --check --format json
python3 scripts/generate_core_resources.py --check --format json

for skill in skills/*; do
  python3 /Users/wandl/.agents/skills/skill-trace-evaluation/scripts/trace_evaluate.py \
    --skill-dir "$skill" \
    --output "/tmp/$(basename "$skill").trace.json"
done
```

## 最终判定

技能内容质量：**通过**。68 个技能的确定性 TRACE 总体均分 4.643，最低 4.56，满足 4.5+ 目标。

独立仓库：**已创建并推送 main**。完整发布与插件迁移：**未完成**。tag/release、全新缓存安装、插件 vendor lock 和真实宿主验证仍属于后续发布动作，详见 `MIGRATION.md`。
