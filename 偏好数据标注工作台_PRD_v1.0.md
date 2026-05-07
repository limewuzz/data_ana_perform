# 偏好数据标注工作台 PRD

PRODUCT REQUIREMENTS DOCUMENT

偏好数据标注工作台

Preference Data Annotation Workbench

DPO / RLHF 偏好数据标注全流程解决方案

| Version | 1.0.0 |
| --- | --- |
| Date | 2026-05-06 |
| Author | Claude / Product Team |
| Status | Draft |

Table of Contents

## 1 项目概述

### 1.1 背景与动机

DPO（Direct Preference Optimization）和 RLHF（Reinforcement Learning from Human Feedback）是当前大模型对齐（Alignment）的核心技术。其训练效果的上限直接取决于偏好数据的质量：标注是否一致、偏好信号是否清晰、数据分布是否充分。

然而，目前行业内缺乏专业的偏好数据标注工具。大多数团队依赖 Excel 表格或简单的文本编辑器进行标注，存在流程碎片化、质量不可控、导出格式不统一等问题。

### 1.2 产品目标

构建一个 Web 端的偏好数据标注工作台，覆盖从数据生成到标注、审核、导出的全流程，具体包括：

多模型并行生成：输入 Prompt，调用后端配置的多个模型生成回复

Listwise 标注：支持拖拽排序、打分、编辑、Drop 功能

标注一致性：基于 Cohen’s Kappa 计算多标注者间的一致性

多格式导出：支持 DPO Format 和 Alpaca Format

数据质量看板：多维度评估数据可用性，辅助训练工程师决策

### 1.3 目标用户

| 角色 | 描述 | 核心诉求 |
| --- | --- | --- |
| 标注者 (Annotator) | 执行偏好标注的一线人员 | 高效、低认知负荷的标注界面 |
| 审核者 (Reviewer) | 检查标注质量，解决分歧 | 快速定位低质量标注 |
| 训练工程师 | 使用标注数据训练模型 | 数据质量可视化、灵活导出 |
| 管理员 (Admin) | 管理模型配置、用户权限 | 系统配置与监控 |

## 2 系统架构

### 2.1 整体架构

系统采用前后端分离架构，数据流向为：Prompt → 后端多模型生成 → 前端标注交互 → 后端持久化 → 看板聚合展示 → 导出。

> 核心设计原则：模型选择由前端提供 UI，但实际的 API Key 和调用逻辑完全由后端控制，前端不接触任何密钥。


### 2.2 技术栈建议

| 层 | 技术选型 | 说明 |
| --- | --- | --- |
| 前端 | React + TypeScript | 组件化开发，拖拽库生态成熟 |
| 拖拽排序 | dnd-kit 或 react-beautiful-dnd | 支持列表拖拽重排 |
| 图表 | Recharts 或 ECharts | 看板可视化 |
| 后端 | Python FastAPI / Node Express | 灵活选择，REST API |
| 数据库 | PostgreSQL + Redis | 结构化存储 + 缓存 |
| 模型调用 | 后端统一代理 | 支持 OpenAI / Anthropic / 自部署模型 |

## 3 数据模型

### 3.1 Task（标注任务）

每个 Task 代表一条待标注的 Prompt 及其生成的多条回复。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| prompt | string | 输入的提示词 |
| responses | Response[] | 模型生成的回复列表 |
| status | enum | pending \| annotating \| completed \| dropped |
| category | string? | 可选，Prompt 分类标签 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 最后更新时间 |

### 3.2 Response（模型回复）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| task_id | UUID | 关联 Task |
| model_id | string | 模型标识，如 claude-3.5-sonnet |
| content | string | 原始生成内容 |
| created_at | datetime | 生成时间 |

### 3.3 Annotation（标注记录）

每个标注者对每个 Task 产生一条 Annotation 记录。这是系统最核心的数据结构。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| task_id | UUID | 关联 Task |
| annotator_id | UUID | 关联标注者 |
| ranking | string[] | 有序数组，index 0 = 最优，元素为 response_id |
| ranking_groups | string[][]? | 可选，支持并列（Tie）的排序分组；外层数组有序，内层数组表示同一名次的并列 response_id |
| scores | Record<string, number> | 可选打分，key = response_id，value = 1-5 |
| edits | Record<string, string> | 编辑后快照，key = response_id |
| is_dropped | boolean | 标注者是否判定该条不可用 |
| drop_reason | string? | Drop 原因（预设 + 自定义） |
| duration_ms | number | 标注耗时（毫秒） |
| created_at | datetime | 提交时间 |

> 设计要点：ranking / ranking_groups 都是 Listwise 结构，不是 pairwise 对。导出与一致性计算时再转换为偏好对。若出现并列（Tie），使用 ranking_groups 表达；ranking 可作为兼容字段（例如将 groups 直接顺序拼接）。


### 3.4 Annotator（标注者）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | UUID | 主键 |
| name | string | 标注者名称 |
| role | enum | annotator \| reviewer \| admin |
| created_at | datetime | 创建时间 |

### 3.5 状态机

Task 的状态转换如下：

pending：初始状态，Prompt 已录入但还未生成回复，或回复已生成但无人标注

annotating：至少有一个标注者开始标注但未全部完成

completed：所有分配的标注者都已提交

dropped：任一标注者判定为 drop 后，Task 直接进入 dropped；或管理员手动标记

注意：dropped 状态的数据不删除，保留用于看板统计和回溯。

## 4 模块一：多模型生成

### 4.1 功能说明

用户输入 Prompt 并选择模型，系统并行调用多个模型生成回复。模型列表由后端配置提供，前端仅做选择展示。

### 4.2 前端交互

前端启动时调用 GET /api/models 获取可用模型列表

用户输入 Prompt，多选模型（至少勾选 2 个）

点击“生成”按钮，前端发送 POST /api/tasks 请求

后端并行调用各模型 API，返回结果后前端展示所有回复

回复展示顺序随机打乱，避免位置偏差

### 4.3 API 接口

GET /api/models

返回后端配置的可用模型列表。

| 字段 | 类型 | 示例 |
| --- | --- | --- |
| id | string | claude-3.5-sonnet |
| name | string | Claude 3.5 Sonnet |
| provider | string | anthropic |
| enabled | boolean | true |

POST /api/tasks

创建标注任务，触发多模型生成。

Request Body：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| prompt | string | 提示词文本 |
| model_ids | string[] | 选择的模型 ID 列表，最少 2 个 |
| category | string? | 可选分类标签 |

Response： 返回完整的 Task 对象，包含所有 responses。回复顺序已随机打乱。

> 安全要点：所有模型的 API Key 仅存储于后端环境变量，前端永不接触。后端应对模型调用失败做降级处理，单个模型失败不影响其他模型的结果返回。


## 5 模块二：标注工作区

### 5.1 核心交互

标注工作区是系统的核心页面，标注者在此对每个 Task 的多条回复进行偏好判定。

#### 5.1.1 Listwise 拖拽排序

所有回复以卡片形式垂直排列，每张卡片显示模型名称和回复内容

标注者通过拖拽手柄调整卡片顺序，最上方 = 最优

初始顺序随机打乱，避免位置偏差（Position Bias）

排序后自动显示排名编号（#1, #2, #3...）

#### 5.1.2 打分

每张卡片右上角提供 1-5 星打分组件

打分与排序独立：排序反映相对偏好，打分反映绝对质量

允许相同分数（两条回复都是 4 星但排序不同）

#### 5.1.3 内联编辑

每张卡片提供「编辑」按钮，点击后内容区域变为可编辑的 textarea

编辑保存后存入 Annotation.edits 字段，原始 Response.content 不变

编辑过的卡片显示「已编辑」标记，支持「还原」操作

#### 5.1.4 Drop 功能

Drop 功能允许标注者判定某条数据不适合用于训练，具体设计如下：

页面右上角提供「Drop」按钮，点击后弹出原因选择框

预设 Drop 原因：

Prompt 本身有问题（模糊 / 不合理 / 有害）

所有回复质量都太差，无法区分偏好

所有回复过于相似，无标注价值

其他（自定义填写）

Drop 后的行为： 该条 Task 跳过，自动进入下一条。数据保留不删除，看板中统计 Drop 率和原因分布。

### 5.2 导航与流程

标注者进入工作区后，系统自动加载下一条待标注任务

顶部显示进度条：「Task 3/47」

支持「上一条」「下一条」导航，可回看已标注的任务

标注提交时记录 duration_ms（从进入页面到点击提交的时间差）

提交后自动进入下一条

### 5.3 API 接口

POST /api/annotations

提交一条标注记录。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| task_id | UUID | 关联的 Task ID |
| annotator_id | UUID | 当前标注者 ID |
| ranking | string[] | 有序 response_id 数组 |
| ranking_groups | string[][]? | 可选，支持并列（Tie）的排序分组 |
| scores | object | 可选，{ response_id: score } |
| edits | object | 可选，{ response_id: edited_content } |
| is_dropped | boolean | 是否 Drop |
| drop_reason | string? | Drop 原因 |
| duration_ms | number | 标注耗时 |

## 6 模块三：标注一致性（Cohen’s Kappa）

### 6.1 计算方法

由于标注采用 Listwise 排序，而 Cohen’s Kappa 适用于分类任务，因此需要先将排序转换为 Pairwise 分类再计算。

Step 1：排序 → Pairwise 分类

将每个标注者的排序拆解为所有 C(N,2) 个偏好对。例如 3 条回复的排序 [A, B, C] 拆解为：A>B, A>C, B>C 三个分类判断。

若排序存在并列（Tie），推荐策略为：同一并列组内的 pairwise 不参与 Kappa（避免引入随机噪声）；不同组之间按组顺序生成偏好对。

Step 2：构建混淆矩阵

对两个标注者的所有 pairwise 判断构建 2×2 混淆矩阵，其中分类标签为 「A胜」或「B胜」。

Step 3：计算 Kappa

Kappa 公式：κ = (p_o - p_e) / (1 - p_e)，其中 p_o 为观察一致率，p_e 为随机一致率。

### 6.2 Kappa 值解释

| Kappa 范围 | 一致性等级 | 建议操作 |
| --- | --- | --- |
| 0.81 - 1.00 | 几乎完美 (Almost Perfect) | 数据可直接用于训练 |
| 0.61 - 0.80 | 显著一致 (Substantial) | 数据质量良好，建议抽检低 Kappa 子集 |
| 0.41 - 0.60 | 中等一致 (Moderate) | 需要审核，可能需要优化标注指南 |
| 0.21 - 0.40 | 较弱一致 (Fair) | 建议重新标注或引入第三个标注者 |
| < 0.20 | 差 / 随机 (Poor/Slight) | 数据不可用，需查找原因 |

### 6.3 计算粒度

全局 Kappa：汇总所有 Task 的 pairwise 对计算，体现整体一致性水平

分 Task Kappa：每个 Task 单独计算，用于定位分歧严重的具体 Prompt

分类别 Kappa：按 Prompt 类别分桶计算，发现某类任务是否特别难标注

### 6.4 边界情况处理

如果某条 Task 被任一标注者 Drop，该条不参与 Kappa 计算（并直接进入 dropped 状态）

Drop 一致性单独统计：两个标注者是否对同一条 Task 同时 Drop

如果只有一个标注者的数据，Kappa 无法计算，看板显示「N/A」

## 7 模块四：数据导出

### 7.1 导出格式

#### 7.1.1 DPO Format

每个偏好对生成一条记录，从 Listwise 排序自动拆解。一个长度为 N 的排序产生 C(N,2) 条记录。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| prompt | string | 提示词 |
| chosen | string | 排名较高的回复内容 |
| rejected | string | 排名较低的回复内容 |
| chosen_model | string | chosen 回复的模型 ID |
| rejected_model | string | rejected 回复的模型 ID |
| margin | number | 排名差值，可用于训练加权 |
| annotator | string | 标注者 ID |

#### 7.1.2 Alpaca Format

取每个 Task 排名第一的回复，生成 SFT 数据。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| instruction | string | 提示词 |
| input | string | 始终为空字符串 |
| output | string | 排名第一的回复内容 |

### 7.2 导出选项

导出时提供以下过滤选项，让训练工程师控制数据质量：

| 选项 | 默认值 | 说明 |
| --- | --- | --- |
| 排除 Dropped 数据 | ☑ 开启 | 不导出被 Drop 的 Task |
| Kappa 最低阈值 | 0.4 | 仅导出 Kappa 超过阈值的 Task |
| 使用编辑后内容 | ☑ 开启 | 优先使用标注者编辑后的内容 |
| 导出格式 | DPO | DPO Format / Alpaca Format |
| 文件格式 | JSONL | JSONL / JSON / CSV |

### 7.3 API 接口

POST /api/export

根据筛选条件导出数据，返回可下载的文件。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| format | enum | dpo \| alpaca |
| file_type | enum | jsonl \| json \| csv |
| exclude_dropped | boolean | 是否排除 Dropped |
| min_kappa | number? | Kappa 最低阈值 |
| use_edits | boolean | 是否使用编辑后内容 |
| tie_handling | enum? | tie 的处理策略：skip（跳过并列组内 pairwise）\| random（并列组内 pairwise 以确定性随机方式采样方向） |
| export_job_id | string? | 导出作业 ID（uuid/时间戳均可）；用于随机采样的可复现性控制 |
| tie_seed | string? | tie_handling=random 时的随机种子；为空则默认派生自 export_job_id（见 14.1），确保“同一导出作业稳定、不同导出作业可变化” |

## 8 模块五：数据质量看板

### 8.1 设计理念

看板的核心问题：训练工程师拿到这批数据后，如何判断能不能用？看板围绕五个维度设计，从宏观到微观透进式展示。

> 设计原则：看板不只是展示数字，每个维度都要给出可操作的建议。低一致性不只是红灯，还要告诉用户“建议回审这 12 条”。


### 8.2 维度一：健康度总览

页面顶部的概览卡片区，一粒握全局状态。

| 指标 | 计算方式 | 展示形式 |
| --- | --- | --- |
| 总任务数 | 所有 Task 计数 | 数字卡片 |
| 已完成 | status = completed 计数 | 数字卡片 + 进度条 |
| Drop 率 | dropped / total × 100% | 数字卡片，>15% 标红 |
| 平均标注耗时 | avg(duration_ms) | 数字卡片 |
| 可用数据比例 | 排除 dropped + 低 Kappa + 低区分度后的比例 | 大字比例 + 环形图 |

「可用数据比例」 是看板的灵魂指标。它综合了一致性、区分度、Drop 率三个因素，直接告诉训练工程师：这批数据能用多少。

### 8.3 维度二：标注一致性分布

Kappa 分布直方图： X 轴为 Kappa 值区间，Y 轴为 Task 数量。用颜色区分一致性等级（绿/黄/红）。

全局 Kappa 值： 醒目显示当前数据集的整体 Kappa，附带一致性等级标签。

低一致性任务列表： Kappa < 0.4 的 Task 单独列出，支持点击跳转回审。

### 8.4 维度三：Prompt 多样性覆盖

用 Treemap 或 Sunburst 图展示 Prompt 的分类分布。分类来源：

如果 Task 有 category 字段，直接使用

如果没有，可用关键词匹配或简单 NLP 自动分类

价值： 如果 80% 的 Prompt 都是代码题，训练工程师需要知道这个分布偏斜，以便决定是否需要补充其他类型的数据。

### 8.5 维度四：Response 区分度

衡量 chosen 和 rejected 之间的差异大小。差异太小意味着偏好信号弱，对训练价值低。

计算方式

文本相似度： 计算每个 Task 中排名第 1 与排名最后的回复的 Jaccard 相似度或余弦相似度

低区分度阈值： 相似度 > 0.85 则标记为「低区分度」，该偏好对的训练价值有限

展示形式

相似度分布直方图：展示所有偏好对的相似度分布

低区分度占比：用百分比醒目显示，超过 20% 标红

### 8.6 维度五：标注者行为分析

检测标注者的行为异常，识别潜在的低质量标注。

| 指标 | 计算方式 | 异常阈值 |
| --- | --- | --- |
| 平均标注耗时 | avg(duration_ms) per annotator | < 10s 标红（可能在划水） |
| 位置偏差 | 统计标注者将初始位置第 1 的回复排在最终第 1 的频率，减去随机基准 1/N | 偏差 > 0.3 标红 |
| 与他人一致性 | 该标注者与所有其他标注者的平均 Kappa | < 0.3 标红（Outlier） |
| Drop 率 | is_dropped / total_tasks per annotator | > 30% 标红 |

当标注者触发任意异常阈值时，对应行标记警告图标，并在底部给出具体的文字描述（如「Bob：标注速度异常快 + 位置偏差高」）。

## 9 API 接口汇总

以下是系统所有 API 接口的概览：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /api/models | 获取可用模型列表 |
| POST | /api/tasks | 创建任务，触发多模型生成 |
| GET | /api/tasks | 获取任务列表，支持状态筛选和分页 |
| GET | /api/tasks/:id | 获取单个任务详情（含 responses） |
| POST | /api/annotations | 提交标注记录 |
| GET | /api/annotations?task_id= | 获取某任务的所有标注 |
| GET | /api/stats/kappa | 获取全局和分 Task 的 Kappa 值 |
| GET | /api/stats/dashboard | 获取看板数据（健康度 + 分布） |
| GET | /api/stats/annotators | 获取标注者行为分析数据 |
| POST | /api/export | 根据筛选条件导出数据 |

## 10 页面结构与线框

### 10.1 全局导航

左侧边栏导航，包含三个主页面：

任务管理台：Prompt 录入、任务列表、状态管理

标注工作区：核心标注界面，排序 / 打分 / 编辑 / Drop

数据质量看板：五维度质量分析 + 导出入口

### 10.2 任务管理台线框

顶部操作栏：「新建任务」按钮、「批量导入 Prompts」按钮、「导出」按钮。主体为任务列表表格，列包括：Prompt 摘要、模型数、标注状态、Kappa 值、操作。支持按状态筛选和排序。

### 10.3 标注工作区线框

页面结构从上到下：

顶部导航栏：进度指示器「Task 3/47」 + 前后翻页 + Drop 按钮

Prompt 展示区：灰色背景卡片显示当前提示词

回复排序区：可拖拽卡片列表，每张卡片包含模型名称、回复内容、打分组件、编辑按钮、拖拽手柄

底部提交栏：「提交标注」按钮

### 10.4 看板线框

采用 2×2 + 1 的布局：

左上：健康度总览（5 个数字卡片）

右上：标注一致性分布（Kappa 直方图 + 低一致性列表）

左下：Prompt 类别分布（Treemap）

右下：Response 区分度（相似度直方图）

底部全宽：标注者行为分析表格

## 11 非功能性需求

### 11.1 性能

模型生成超时上限：单个模型 60 秒，超时后返回部分结果

标注提交响应：< 500ms

看板加载：< 3s（含所有图表渲染）

导出：10,000 条数据在 10s 内完成

### 11.2 安全

所有模型 API Key 仅存储于后端环境变量

API 接口需要身份验证（JWT 或 Session）

标注数据按用户角色做权限控制

### 11.3 可扩展性

模型接入：后端采用插件化设计，新增模型只需添加配置而非改代码

导出格式：可通过注册新的 Formatter 扩展导出格式

看板维度：预留自定义维度插槽

## 12 里程碑与优先级

### 12.1 开发阶段

| 阶段 | 内容 | 优先级 |
| --- | --- | --- |
| Phase 1 | 数据模型 + 多模型生成 + 基础 CRUD API | P0 - 核心 |
| Phase 2 | 标注工作区（拖拽排序 + 打分 + 编辑 + Drop） | P0 - 核心 |
| Phase 3 | Cohen’s Kappa 计算 + 多标注者支持 | P0 - 核心 |
| Phase 4 | 导出功能（DPO + Alpaca） | P0 - 核心 |
| Phase 5 | 数据质量看板（5 个维度） | P1 - 重要 |
| Phase 6 | 权限管理 + 审核流程 | P2 - 增强 |

### 12.2 Demo 范围建议

作为 Demo，建议 Phase 1-4 实现完整功能，Phase 5 实现核心 3 个维度（健康度总览 + Kappa 分布 + 标注者行为），Phase 6 可简化为单角色登录。

## 13 补充决策（2026-05-07）

1) 模型调用并发：API 可并发调用，多模型生成的并发策略不作为限制项。

2) 审核方式：审核者面向集合处理（例如低 Kappa 任务集合、低区分度集合、异常标注者关联集合），而非逐条流水式审核。

3) 排序允许并列（Tie）：导出与一致性计算的 pairwise 构造支持随机选择策略（用于从并列关系中采样生成训练对）。

4) margin 计算：结合标注分数计算（剔除 dropped 数据），用于训练加权信号。

5) Drop 判定：单人 Drop 即直接丢弃（进入 dropped，默认不参与 Kappa/导出），但保留记录用于 Drop 率与原因分布统计。

## 14 计算规则（Tie / Pairwise / Margin）

### 14.1 Listwise（含 Tie）→ Pairwise 的构造

数据结构约定：

- 若提供 ranking_groups：`[[A,B],[C],[D,E,F]]` 表示 A 与 B 并列第一，C 第二，D/E/F 并列第三
- 若仅提供 ranking：视为无并列（等价于每个元素单独成组）

规则：

- 不同组之间：高组内任意元素都优于低组内任意元素
- 同组内（Tie）：可选择跳过（skip）或用随机采样方向（random）生成可训练对

伪代码（用于导出与一致性计算的公共转换）：

```text
to_groups(annotation):
  if annotation.ranking_groups exists:
    return annotation.ranking_groups
  else:
    return [[id] for id in annotation.ranking]

pairwise_from_groups(groups, tie_handling, seed):
  pairs = []
  for i in range(len(groups)):
    for j in range(i + 1, len(groups)):
      for a in groups[i]:
        for b in groups[j]:
          pairs.append((chosen=a, rejected=b, rel='ordered'))

  if tie_handling == 'skip':
    return pairs

  if tie_handling == 'random':
    rng = DeterministicRng(seed)
    for g in groups:
      for each unordered pair (x, y) in g:
        if rng.flip(): pairs.append((chosen=x, rejected=y, rel='tie'))
        else:          pairs.append((chosen=y, rejected=x, rel='tie'))
    return pairs
```

推荐默认值：

- Kappa：`tie_handling=skip`
- 导出：`tie_handling=random`（与训练格式要求的 chosen/rejected 对齐）
  - export_job_id：由后端在每次导出请求开始时生成（建议 uuid），并用于默认 seed 派生

### 14.2 margin 计算（结合分数，剔除 dropped）

前置：Task 未进入 dropped（单人 Drop 直接 dropped 时，默认不参与导出；除非显式关闭 exclude_dropped）。

对每条 pairwise 记录 (chosen, rejected) 计算：

定义：

- `rank_group_index(x)`：x 所在的组序号（0=最优）
- `rank_gap = (rank_group_index(rejected) - rank_group_index(chosen)) / max(1, G-1)`，其中 G 为组数；若是 tie 产生的对，则 rank_gap=0
- `score(x)`：若 scores 缺失则视为 null；范围 1..5
- `score_gap = (score(chosen) - score(rejected)) / 4`（归一化到 [-1, 1]）

合成：

```text
margin = w_rank * rank_gap + w_score * score_gap
where:
  w_rank = 1.0
  w_score = 1.0
  if score(chosen) or score(rejected) is null:
    score_gap = 0
```

落地建议：

- 若你希望 margin 永远非负，可在导出时做 `margin = max(margin, 0)` 或直接改用 `abs(score_gap)`；当前默认保留符号，便于发现“分数与排序不一致”的异常标注。
- 为保证可复现性与可变性并存，推荐默认 seed 派生规则：
  - 若请求提供 tie_seed：直接使用
  - 否则要求存在 export_job_id，并对每条 Task/标注派生 `seed = hash(export_job_id + ':' + task_id + ':' + annotator_id)`，使得“同一 export_job_id 的导出结果稳定、不同 export_job_id 的导出结果可变化”

END OF DOCUMENT
