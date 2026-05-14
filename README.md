# Paper Reader Agent — 时间序列论文阅读 Agent

一个最小化的 AI Agent，用于阅读时间序列预测相关论文、梳理模型结构、复现代码。

不依赖任何 Agent 框架，核心就是一个 while 循环 + 工具调用。

## 架构

```
用户输入
   ↓
┌─────────────────────────────┐
│         Agent Loop          │
│                             │
│  messages → LLM API call    │
│       ↓                     │
│  有 tool_calls?             │
│    是 → 执行工具 → 结果     │
│         塞回 messages       │
│         → 继续循环          │
│    否 → 输出文本，结束      │
└─────────────────────────────┘
   ↓
输出结构化论文分析 / 代码 / 图表
```

## 支持的功能

### 工具列表

| 工具 | 功能 | 用途 |
|------|------|------|
| `read_pdf` | 读取本地 PDF 文件 | 解析本地下载的论文 |
| `fetch_arxiv` | 从 arXiv 下载论文 | 输入 arXiv ID 或 URL 自动下载并解析 |
| `web_search` | 网页搜索 | 搜索论文信息、代码仓库、相关资料 |
| `write_file` | 写文件 | 保存笔记、代码、分析报告到 output/ |
| `run_python` | 执行 Python 代码 | 数据处理、模型实现、可视化 |
| `read_file` | 读取文本文件 | 查看已有代码或笔记 |
| `list_files` | 列出目录内容 | 浏览文件结构 |
| `save_paper_index` | 保存论文到知识库 | 读完论文后结构化存储，跨会话记忆 |
| `query_paper_index` | 搜索知识库 | 按关键词查找已读论文 |
| `git_clone` | 克隆 Git 仓库 | 下载论文代码仓库到本地，配合 read_file 分析源码 |
| `generate_diagram` | 生成 Mermaid 流程图 | 可视化模型架构、数据流程、论文方法 |

### 论文分析能力

- 提取论文元信息（标题、作者、会议、年份）
- 梳理论文结构和核心方法
- 提取关键公式（LaTeX）
- 分析与 baseline 的差异
- 识别开源代码仓库
- 提取实验设置和结果

### 内置领域知识

System prompt 中包含时间序列预测领域常识：

- **模型族**：Transformer 系列、Linear 系列、CNN、MLP、Foundation Model、Diffusion、State-space
- **常用数据集**：ETT、Weather、Traffic、Electricity、Exchange-Rate、M4/M5 等
- **评估指标**：MSE、MAE、RMSE、MAPE、SMAPE、CRPS 等
- **时序特征**：趋势、季节性、频域特征、滞后特征、日历特征

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API（编辑 config.py）
#    填入你的 API_KEY、BASE_URL、MODEL

# 3. 运行
python agent.py
```

## 配置说明

编辑 `config.py`：

```python
API_KEY = "sk-your-key-here"
BASE_URL = "https://api.openai.com/v1"  # 或任何 OpenAI 兼容接口
MODEL = "gpt-4o"                         # 你使用的模型名称
```

常见配置示例：

| Provider | BASE_URL | MODEL |
|----------|----------|-------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| OpenRouter | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:72b` |

## 使用示例

```
📝 You: 帮我读一下 arXiv 2310.06625

🤖 Agent:
  🔧 [fetch_arxiv] arxiv_id=2310.06625
  🔧 [write_file] filename=patchtst_analysis.md
  
  ## PatchTST 论文分析
  ...
```

```
📝 You: 用 PyTorch 实现 PatchTST 的核心 patch embedding 模块

🤖 Agent:
  🔧 [run_python] code=import torch...
  🔧 [write_file] filename=patch_embedding.py
  
  已实现并保存到 output/patch_embedding.py
```

### 流式输出（Streaming）

Agent 回复时逐字输出，不需要等整个回答生成完毕。实现方式：

- `client.chat.completions.create(stream=True)` 返回一个迭代器
- 每收到一个 chunk 立刻 `print(delta.content, end="", flush=True)`
- 工具调用也是流式累积拼接的（参数 JSON 分多个 chunk 到达）

### 对话历史持久化

每次对话自动保存到 `output/sessions/`，下次可恢复继续。

会话命令：
- `sessions` — 列出所有已保存的会话
- `resume` — 选择一个历史会话恢复
- `new` — 保存当前会话并开始新的
- `quit` — 保存并退出

### 论文知识库（Learning Loop）

Agent 读过的论文会结构化存储在 `knowledge/papers.json`，实现跨会话记忆。

**工作流程**：

```
                    ┌──────────────────────────┐
                    │    knowledge/papers.json  │
                    │                          │
                    │  [{title, category,      │
                    │    innovation, ...}, ...] │
                    └────┬────────────────▲────┘
                         │                │
              启动时加载到               读完论文后
              system prompt            save_paper_index
                         │                │
                         ▼                │
┌─────────┐     ┌───────────────┐     ┌──────────┐
│  用户    │────▶│   Agent Loop  │────▶│ 分析论文  │
│  提问    │     │               │     │ 输出笔记  │
└─────────┘     └───────────────┘     └──────────┘
```

**存储格式**（每篇论文一条记录）：

```json
{
  "arxiv_id": "2310.06625",
  "title": "PatchTST",
  "authors": "Nie et al.",
  "year": 2023,
  "category": "Transformer-based",
  "innovation": "将时间序列分割为固定长度的patch作为Transformer的输入token",
  "datasets": ["ETTh1", "ETTh2", "Weather", "Traffic"],
  "metrics": {"ETTh1_MSE": 0.370, "Weather_MAE": 0.166},
  "has_code": true,
  "repo_url": "https://github.com/yuqinie98/PatchTST"
}
```

**自动行为**：
- 每次启动时，已有论文列表自动注入 system prompt（Agent 知道自己读过什么）
- System prompt 规则要求 Agent 读完论文后必须调用 `save_paper_index` 保存
- 读论文前先 `query_paper_index` 检查是否已读过，避免重复

**使用示例**：

```
📝 You: 我之前读过哪些 Transformer 类的论文？

🤖 Agent:
  🔧 [query_paper_index] keyword=Transformer
  
  根据知识库，你已读过以下 Transformer 类论文：
  - PatchTST (2023): 将时间序列分patch输入Transformer
  - iTransformer (2023): 对变量维度而非时间维度做注意力
  ...
```

**与 RAG 的区别**：
- 当前方案是"全量注入"——所有论文索引直接放进 prompt
- 适合 <100 篇论文的规模（几千 token）
- 超过 100 篇后可升级为 RAG（向量检索，只取最相关的几篇注入）

### Git Clone 工具

搜索到论文的开源代码后，Agent 可以自动克隆仓库并分析源码。

- 使用 `--depth 1` 浅克隆，只拉最新代码快照，节省空间和时间
- 仓库存放在 `output/repos/{repo_name}/`
- 重复克隆同一仓库会跳过，直接提示浏览
- 支持指定分支

**典型流程**：

```
📝 You: 帮我找到 PatchTST 的代码仓库，分析一下模型结构

🤖 Agent:
  🔧 [web_search] query=PatchTST github repository
  🔧 [git_clone] repo_url=https://github.com/yuqinie98/PatchTST
  🔧 [list_files] directory=output/repos/PatchTST
  🔧 [read_file] filepath=output/repos/PatchTST/models/PatchTST.py
  
  PatchTST 的模型结构如下：
  ...
```

Agent 会根据情况自动选择路径：已有知识库记录时直接用 `repo_url`，没有时先 `web_search` 搜索。

### 流程图生成（Mermaid）

Agent 分析模型架构时会自动生成 Mermaid 流程图，保存到 `output/diagrams/`。

**使用示例**：

```
📝 You: 画一下 PatchTST 的模型架构图

🤖 Agent:
  🔧 [generate_diagram] title=PatchTST_architecture, mermaid_code=graph TD...
  
  已保存到 output/diagrams/PatchTST_architecture.md
```

生成的文件内容：

```markdown
# PatchTST_architecture

Patch-based Transformer for time series forecasting

​```mermaid
graph TD
    A[Input Time Series] --> B[Patch Embedding]
    B --> C[Transformer Encoder]
    C --> D[Flatten Head]
    D --> E[Prediction]
​```
```

在 VSCode 中安装 Mermaid 预览插件即可直接查看渲染效果。

**实现方案对比**：

实现流程图生成有两种思路，当前采用方案 C：

| | 方案 B：保存 + 渲染 PNG | 方案 C：只保存 Markdown（当前） |
|---|---|---|
| 输出 | `.md` + `.png` 图片 | 仅 `.md` |
| 外部依赖 | Node.js + mermaid-cli（`npm install -g @mermaid-js/mermaid-cli`） | 无 |
| 渲染方式 | 工具内调用 `mmdc` 命令渲染 | VSCode/GitHub 自动渲染 |
| 适合场景 | 需要导出图片、生成报告、分享给非技术人员 | 本地开发分析，VSCode 中查看 |

选择方案 C 的原因：
1. 零外部依赖，不需要安装 Node.js 和 mermaid-cli
2. VSCode Mermaid 插件预览效果完全够用
3. 升级到方案 B 只需加一行 `subprocess.run(["mmdc", ...])` 即可

**设计决策：为什么不直接用 `write_file`？**

给模型一个专门的 `generate_diagram` 工具，比靠 prompt 引导用 `write_file` 更可靠。模型看到有"画图"工具，就更倾向于在分析架构时主动画图——工具名本身就是对模型行为的暗示。

## 项目结构

```
Paper-reader-agent/
├── agent.py              # Agent 主循环 + 流式输出 + 会话管理
├── config.py             # API 配置
├── tools/                # 11 个工具（自动发现，新建文件即注册）
├── prompts/
│   └── system.md         # System prompt（领域知识 + 行为规则）
├── knowledge/
│   └── papers.json       # 论文知识库（自动生成）
├── output/
│   ├── sessions/         # 会话历史存储
│   ├── repos/            # git_clone 下载的代码仓库
│   └── diagrams/         # generate_diagram 生成的流程图
├── notes/                # 学习笔记
├── requirements.txt      # Python 依赖
├── TODO.md               # 待实现功能
└── README.md             # 本文件
```

## 设计原则

1. **无框架** — 不依赖 LangChain/LangGraph，核心逻辑一目了然
2. **OpenAI 兼容** — 可接任何 OpenAI-compatible API，随时换模型
3. **Prompt 驱动** — 领域知识在 system prompt 里，修改 prompt 即可调整行为
4. **工具可扩展** — 在 tools.py 中添加函数 + schema 即可注册新工具
5. **跨会话记忆** — 论文知识库 + 会话持久化，越用越聪明
