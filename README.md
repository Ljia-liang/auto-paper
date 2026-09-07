# Auto Paper

面向研究方向的证据优先型文献综述工具。当前预置领域是无监督可见光-红外跨模态行人重识别（USL-VI-ReID），数据集包括 `SYSU-MM01` 和 `RegDB`。

流程固定为四个分析模块，并生成两个面向阅读的 PDF：

1. 领域综述报告
2. 论文清单和筛选理由
3. 方法演化
4. 创新方向

PDF 输出：

- `综述及方法论.pdf`：领域问题、常见方法、筛选论文表、统一流程和逐篇方法论
- `创新方向.pdf`：候选创新方向及文献依据

论文筛选要求公开访问，并在下载后的论文 PDF 第 1 页（标题/摘要页）检测公开代码链接；PDF 文本换行和页面超链接均会核验。

## CLI

```powershell
pip install -e ".[export,dev]"
auto-paper "visible infrared cross-modal person re-identification" --limit 50 --out artifacts
```

如果直接运行 CLI，需要一个 OpenAI-compatible API：

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
$env:OPENAI_MODEL = "codex-auto-review"
$env:GITHUB_TOKEN = "optional-github-token"
auto-paper "visible infrared cross-modal person re-identification" --limit 50 --out artifacts
```

没有 `OPENAI_API_KEY` 时，流程仍可检索、筛选和解析 PDF，但会输出明确的待分析草稿。

## Agent 模式

Codex 或其他 Agent 用自己的当前模型完成分析，不需要额外的模型 key。

```powershell
pip install -e ".[export,agent]"
auto-paper-mcp
```


## Codex 插件

仓库包含一个可从 Git marketplace 安装的自包含插件。使用者需要准备 Python 3.10+。可用下面两条命令注册 marketplace 并安装插件：

```text
codex plugin marketplace add Ljia-liang/auto-paper
codex plugin add auto-paper-review@auto-paper
```
marketplace 注册后，`auto-paper-review` 会出现在 Codex 插件界面中，之后可直接点击安装。安装完成后新建一个 Codex 任务，让新任务加载插件的 Skill 和 MCP 工具。
