# SE Figure Atlas · 软件工程论文图谱

公开、可部署的软件工程论文图表参考库。首批收录范围为 2025–2026 年发表、属于 CCF「软件工程 / 系统软件 / 程序设计语言」A 类来源的正式研究论文。框架图与实验图并重。

## 产品范围

- 来源：ICSE、FSE、ASE、ISSTA、FM、PLDI、POPL、OOPSLA、SOSP、OSDI；TOSEM、TSE、TOPLAS、TSC。
- 分级以当前 CCF 目录为口径，不声称是论文发表当年的历史评级。来源：https://www.ccf.org.cn/Academic_Evaluation/TCSE_SS_PDL/
- 年份按正式发表年份；预印本年份另存。Journal-first 展示不重复算作会议新论文。
- 自动发现论文、定时增量更新、元数据去重；可获取且适合公开展示的图表进入提取和人工审核流程。
- 公开图库支持组合筛选、全文关键词检索、放大、原文追溯、分享直达链接和本地收藏。
- “精选”由人工审核决定，依据布局、可读性、配色及表达效果，必须填写参考理由；自动提取只产生候选。
- 无法下载或未确认可公开展示的图片保留原文链接，不伪造缩略图。

## 部署目标

目标仓库：`YangDeng-28/Paper`（`git@github.com:YangDeng-28/Paper.git`）。静态网页使用 GitHub Pages，采集和生成使用 GitHub Actions。SSH 推送和 Pages 启用是不同操作；SSH 只负责 Git 传输。

## 数据边界

首版是逐步建设的图表库，不声称已经覆盖全部来源。网站显示实际收录数量、采集状态和更新日期。2026 年缺失条目不能据此判定论文未发表。

论文图片归原作者或权利人所有，代码许可不覆盖论文图片。每张已发布图表记录来源、作者、图号、图注、版本和展示依据，支持撤下。

## 当前首版

包含 3 篇核实出处的论文、4 张 RepairAgent 图表（1 张框架图、3 张实验图）。图片来自标注 CC BY 4.0 的 arXiv:2403.17134v2，网页明确展示预印本版本；正式发表年份为 ICSE 2025。它们经过来源核对，但不标为人工精选。2026 年目前只有论文索引，尚无图表。14 个来源均已配置，不代表已完成全量收录。

来源证据：
- RepairAgent 正式版本：https://software-lab.org/publications/icse2025_RepairAgent.pdf
- RepairAgent 图片与许可：https://arxiv.org/html/2403.17134v2
- Agentless FSE 2025：https://conf.researchr.org/details/fse-2025/fse-2025-research-papers/85/Demystifying-LLM-based-Software-Engineering-Agents
- Reachability Gap ICSE 2026：https://mpi-softsec.github.io/papers/ICSE26-reachabilityGap.pdf

## 本地运行

前端无需 Node.js，无第三方 CDN、字体或前端依赖。Python 3.10+ 可直接构建。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 --directory dist --bind 127.0.0.1
```

打开 `http://127.0.0.1:8000`。也可直接打开 `dist/index.html`，搜索与收藏可运行；文件协议下收藏和剪贴板行为取决于浏览器。

## 发布到 GitHub

在普通终端运行 `bash DEPLOY.sh`。脚本验证数据、构建、提交并推送到现有 `origin`，不会强制推送或修改远程地址。

首次在仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。工作流部署成功后，预期网址为 `https://yangdeng-28.github.io/Paper/`；部署成功前不要把这个地址当作已上线链接。

工作流在推送 main 时构建并发布；每周一、周四北京时间 06:23 计划执行论文发现和候选提取（GitHub 调度可能延迟）。第一次希望立即采集时，在 Actions → Collect and publish figure atlas → Run workflow，保持 `collect` 勾选。定时任务仅更新索引与候选，不自动标记人工精选。

自动更新需要 Actions 的 `contents: write` 权限。若 main 分支受到保护而不允许机器人提交，采集任务会在推送时失败，须改成 PR 工作流或调整该仓库的自动更新策略；不会强推绕过保护。

## 采集与审核

```bash
# 按配置发现论文，支持 --venue ICSE --year 2025
python3 scripts/collect.py
# PDF 提取的唯一依赖，建议先建虚拟环境
python3 -m pip install -r requirements.txt
# 每次最多解析 20 篇；失败来源至少 7 天后自动重试
python3 scripts/harvest.py --limit 20
# 将已发布、已核验的外部图片缓存进仓库
python3 scripts/cache_assets.py
# 本地审核页，不会进入 dist 发布包
python3 scripts/preview_review.py
```

打开 `.cache/review/index.html` 逐张核对。提取算法按图注和矢量/位图区域生成候选，不保证裁剪正确；扫描版 PDF、复杂跨栏、多图密集页面需要手工处理。原始 PDF 缓存在 `.cache/pdf/`，不提交到 GitHub。

手动导入 PDF：先在 `data/papers.json` 添加来源、正式年份、作者和 PDF URL，再执行：

```bash
python3 scripts/extract.py --paper '论文ID' --pdf /path/to/paper.pdf
python3 scripts/review.py list
python3 scripts/review.py crop 图表ID --pdf /path/to/paper.pdf --bbox 40 80 550 320
python3 scripts/review.py approve 图表ID --kind framework --chart-type '模块架构图' --note '用三层布局区分输入、处理和输出，模块边界清晰。' --license CC-BY-4.0 --rights-url https://example.org/verified-license
python3 scripts/build.py
```

`--bbox` 使用 PDF 点坐标。批准前核实论文属于正式研究论文，把论文的 `verification` 设为 `research_track_verified` 并保留核实来源。`approve` 表示你已检查裁剪、授权与图注，并填写精选理由。`reject 图表ID` 撤下图片，重建并推送后公开网站才会生效。

可在 `data/figures.json` 直接添加已获取的图片。必要字段通过 `scripts/common.py` 校验；`publication_verified` 表示已核对来源和图片，`reviewed` 专门表示人工精选，两者分开。自动提取生成 `candidate`，不会进入公开网站。公开仓库中已提交的图片会保留 Git 历史，因此撤下历史文件需要另行处理。

## 目录与运行边界

- `site/`：网页、样式、交互和图片。
- `data/scope.json`：来源和年份配置。
- `data/papers.json`：论文索引，自动发现默认待核验。
- `data/figures.json`：图表元数据、状态、来源与精选理由。
- `data/status.json` / `harvest.json`：查询与提取进度、失败原因。
- `scripts/`：发现、下载、提取、审核、构建工具。
- `.github/workflows/publish.yml`：定时更新和 Pages 发布。

元数据按 DOI 和 DBLP key 去重，自动更新保留人工标签。Crossref 只采用许可版本与 PDF 版本匹配的下载链接；缺失开放全文时等待人工补充作者版本。公共网页不提供数据库写入入口，维护通过仓库完成。收藏只保存在当前浏览器，可导出 JSON；不跨设备同步。

搜索、分类、分享和收藏在浏览器本地运行。搜索与卡片采用分批显示；当图表规模增长至数万张时，建议将目录拆分为分页索引，图片迁移至对象存储。
