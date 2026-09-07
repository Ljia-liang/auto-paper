# Auto Paper

面向研究方向的证据优先型文献综述工具。当前预置领域是可见光-红外跨模态行人重识别（VI-ReID），数据集包括 `SYSU-MM01` 和 `RegDB`。

流程固定为四个分析模块，并生成两个面向阅读的 PDF：

1. 领域综述报告
2. 论文清单和筛选理由
3. 方法演化
4. 创新方向

PDF 输出：

- `综述及方法论.pdf`：领域问题、常见方法、筛选论文表、统一流程和逐篇方法论
- `创新方向.pdf`：候选创新方向及文献依据，不包含验证方案

论文筛选要求公开访问，并在下载后的论文 PDF 第 1 页（标题/摘要页）检测公开代码链接；PDF 文本换行和页面超链接均会核验。指标、趋势和创新候选必须通过 `Evidence` 记录回溯到论文原文。

## CLI

```powershell
pip install -e ".[export,dev]"
auto-paper "visible infrared cross-modal person re-identification" --limit 50 --out artifacts
```

如果直接运行 CLI，需要一个 OpenAI-compatible API：

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_BASE_URL = "https://xunsuan.online/v1"
$env:OPENAI_MODEL = "codex-auto-review"
$env:GITHUB_TOKEN = "optional-github-token"
auto-paper "visible infrared cross-modal person re-identification" --limit 50 --out artifacts
```

没有 `OPENAI_API_KEY` 时，流程仍可检索、筛选和解析 PDF，但会输出明确的待分析草稿。

## 为什么支持宿主 Agent 模式

CLI 是独立进程，不能继承 Codex 当前对话的模型权限，因此它需要 API key。MCP 模式不同：MCP 只负责检索、筛选和返回全文材料，Codex 或其他 Agent 用自己的当前模型完成分析，所以不需要额外的模型 key。

```powershell
pip install -e ".[export,agent]"
auto-paper-mcp
```

MCP 工具包括：

- `prepare_review_materials`：无模型调用，返回论文、代码链接、全文片段和排除理由
- `run_literature_review`：在 MCP 进程配置了 API key 时直接完成分析
- `export_agent_review`：把宿主 Agent 生成的 `ReviewResult` JSON 导出为 Markdown、JSON、Excel，以及“综述及方法论”和“创新方向”两个 PDF

因此，在 Codex 中推荐调用 `prepare_review_materials`，由当前 Codex Agent 分析，再调用 `export_agent_review`。

## Codex 插件

仓库包含一个可从 Git marketplace 安装的自包含插件：

```text
plugins/auto-paper-review/
  .codex-plugin/plugin.json
  .mcp.json
  scripts/launch_mcp.py
  requirements-runtime.txt
  runtime/src/auto_paper/
  config/domains/vit_reid.yaml
  skills/auto-paper-review/SKILL.md
```

使用者只需要准备 Python 3.10+。将仓库发布到 GitHub 后，可用下面两条命令注册 marketplace 并安装插件；把 `<owner>` 换成实际 GitHub 用户名或组织名：

```text
codex plugin marketplace add <owner>/auto-paper
codex plugin add auto-paper-review@auto-paper
```

也可以把完整的 HTTPS Git URL 传给第一条命令。marketplace 注册后，`auto-paper-review` 会出现在 Codex 插件界面中，之后可直接点击安装。安装完成后新建一个 Codex 任务，让新任务加载插件的 Skill 和 MCP 工具。

首次调用工具时，`scripts/launch_mcp.py` 会在用户缓存目录建立隔离的 Python 环境并自动安装依赖，可能需要几分钟和 PyPI 网络访问；后续启动直接复用。插件不再要求用户克隆仓库或执行 `pip install -e`。论文下载缓存位于用户缓存目录，最终报告由 Skill 指示写入当前工作区。

更新已发布插件时先修改 `.codex-plugin/plugin.json` 的语义化版本，再构建、提交并推送，然后让使用者执行：

```text
codex plugin marketplace upgrade auto-paper
codex plugin add auto-paper-review@auto-paper
```

维护者每次修改 `src/auto_paper/` 或 `config/domains/` 后，需要重新生成插件内的运行时副本：

```powershell
python scripts/build_plugin.py
python scripts/build_plugin.py --check
```

发布到 GitHub 前还应把插件 manifest 中的 `author`、`homepage` 和 `repository` 补成真实的发布者信息。当前目录尚未初始化为 Git 仓库，因此这些 URL 无法在本地自动推断。

## 其他 Agent 和 DeepSeek Harness

只要宿主支持标准 MCP，就可以直接配置 `auto-paper-mcp`，不需要理解 Codex 插件 manifest。DeepSeek Harness 如果支持 stdio MCP，可使用：

```json
{
  "command": "python",
  "args": ["-m", "auto_paper.mcp_server"],
  "env": {
    "AUTO_PAPER_DOMAIN": "config/domains/vit_reid.yaml"
  }
}
```

如果 Harness 只支持 OpenAI-compatible tools，则使用 CLI 或把 MCP server 转成它支持的工具协议；插件 manifest 本身不能跨宿主通用。

## 验证

```powershell
python scripts/build_plugin.py --check
python -m pytest -q
python "C:\Users\李佳亮\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" `
  plugins/auto-paper-review
```
