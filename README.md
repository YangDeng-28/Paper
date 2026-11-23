# SE Figure Atlas · 软件工程论文图谱

公开的软件工程论文图表参考库，收录 2025–2026 年 CCF「软件工程 / 系统软件 / 程序设计语言」A 类来源的论文元数据、框架图与实验图。

网站：https://yangdeng-28.github.io/Paper/

仓库：`YangDeng-28/Paper`

## 数据库与访问速度

`data/catalog.sqlite3` 是唯一主数据库。论文标题、作者、DOI、会议期刊、年份、来源链接、图表信息、审核状态和采集进度均存入 SQLite。数据库使用事务、DOI 唯一索引、来源年份索引和图表外键约束；旧 JSON 仅作为首次迁移输入，迁移后不再读取。

网站使用 **数据库 → 构建静态文件 → GitHub Pages** 的发布方式：

- 浏览网站不连接数据库，不依赖在线 Python 服务。
- 首页只加载最多 24 张图表及其关联论文，不下载全库；论文数量增加不会使首页携带全部元数据。
- 搜索索引在搜索、筛选、浏览论文或收藏时才加载，完整记录按每 100 条一个文件分片加载。
- 列表使用 WebP 缩略图与图片懒加载，打开详情才获取原尺寸图。
- SQLite、原始 PDF 和未审核候选图不会进入 Pages 发布包。数据库本身在公开 GitHub 仓库中可见。

图片文件放在 `site/assets/figures/`，数据库保存关联和出处，不将图片二进制或 PDF 塞入数据库。可下载的原始 PDF 放在本地 `.cache/pdf/`，不提交到 GitHub。收藏仍保存在访问者自己的浏览器，可导出备份。

## 当前数据与范围

首轮已索引 **5,604 条论文元数据**，发布 **8 张图表**：RepairAgent（ICSE 2025）4 张、Agentless（FSE 2025）2 张、Reachability Gap（ICSE 2026）2 张。包括 3 张框架/流程图和 5 张实验图。图表已核对出处和公开版本；这些参考图尚未标为人工精选。自动提取的候选与公开图表分开存储。

配置的 14 个来源：ICSE、FSE、ASE、ISSTA、FM、PLDI、POPL、OOPSLA、SOSP、OSDI；TOSEM、TSE、TOPLAS、TSC。分级依据 [CCF 官方目录](https://www.ccf.org.cn/Academic_Evaluation/TCSE_SS_PDL/)，不是发表当年的历史评级。

首轮使用 Crossref 官方索引和 USENIX 官网。DBLP 在当前采集环境返回人机验证，因此使用这些公开来源；不绕过访问限制。会议检索最多取每个年份的 1,000 条相关结果，再按来源筛选；期刊使用游标分页。元数据索引不等于全部属于正式研究论文，自动条目标记待核验；不会据此声称全量覆盖。FM 2025 当前没有匹配记录，不代表该年没有论文。2026 年缺失记录同样不能推断为未发表。

年份优先按正式出版年份归档，预印本年份另存。Journal-first 展示不重复算作会议新论文。全文无法获取或公开展示依据不明时，仅保留论文来源，不伪造图表。

来源证据：

- RepairAgent 正式版本：https://software-lab.org/publications/icse2025_RepairAgent.pdf
- RepairAgent 图表版本与许可：https://arxiv.org/html/2403.17134v2
- Agentless 作者公开正式版本（第 1 页 CC BY 4.0）：https://lingming.cs.illinois.edu/publications/fse2025.pdf
- Reachability Gap 作者公开正式版本（第 1 页 CC BY 4.0）：https://mpi-softsec.github.io/papers/ICSE26-reachabilityGap.pdf

论文图片归原作者或权利人所有，代码许可不覆盖论文图片。每张公开图表保存作者、图号、图注、来源版本、展示依据和处理说明。

## 本地运行

Python 3.10+；前端无需 Node.js 或第三方 CDN。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/database.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/build.py
.venv/bin/python -m http.server 8000 --directory dist --bind 127.0.0.1
```

访问 `http://127.0.0.1:8000`。请通过 HTTP 服务预览；直接双击 HTML 的 `file://` 模式无法可靠加载分页文件。

## 发布与自动更新

运行 `bash DEPLOY.sh` 验证、构建、提交并推送现有 `origin`；不会强制推送或修改远程地址。仓库 Settings → Pages → Source 使用 **GitHub Actions**。

推送 main 时发布。每周一、周四北京时间 06:23 计划采集并更新（GitHub 调度可能延迟）；也可以在 Actions → Collect and publish figure atlas → Run workflow 勾选 `collect`。Actions 将更新后的数据库和图片提交到仓库，随后生成静态网站。访问者持续读取已发布页面，采集任务不参与页面请求。

自动更新需要 `contents: write`。如果分支保护禁止机器人推送，应配置 PR 工作流，不会强推绕过保护。所有数据库写入工具应顺序运行；SQLite 事务保护单次写入，但多个独立采集进程不应同时读改写同一目录。

## 采集与核验

```bash
# 支持 --venue ICSE --year 2025
.venv/bin/python scripts/collect.py
# 每次处理最多 20 篇；未尝试条目优先，失败至少 7 天后重试
.venv/bin/python scripts/harvest.py --limit 20
# 缓存已经核验并发布的外部图表
.venv/bin/python scripts/cache_assets.py
# 本地候选审核页，不进入公开网站
.venv/bin/python scripts/preview_review.py
```

自动提取只生成 `candidate`，不会自动发布或变成人工精选。按图注和矢量/位图区域裁剪的算法可能误判，须逐张检查复杂跨栏、密集图表等情况。`ATLAS_DIRECT=1` 可在本地代理故障时让采集工具直接联网；默认尊重系统代理配置。

使用 JSON 文件作为数据库的维护接口：

```bash
# 导出备份或编辑参考；不改变数据库
.venv/bin/python scripts/catalog.py export papers /tmp/papers-export.json
# 输入为 JSON 数组，按 id 新增或更新指定字段，未提供的记录不会删除
.venv/bin/python scripts/catalog.py upsert papers /path/to/paper-updates.json
.venv/bin/python scripts/catalog.py upsert figures /path/to/figure-updates.json
```

手动补充论文时填写正式年份、作者、来源、`pdf_url`、许可和展示依据；确认正式研究论文资格后设置 `verification: research_track_verified`，保留核验来源。然后提取与审核：

```bash
.venv/bin/python scripts/extract.py --paper '论文ID' --pdf /path/to/paper.pdf
.venv/bin/python scripts/review.py list
.venv/bin/python scripts/review.py crop 图表ID --pdf /path/to/paper.pdf --bbox 40 80 550 320
.venv/bin/python scripts/review.py approve 图表ID --kind framework --chart-type '模块架构图' --note '三层布局区分输入、处理和输出，模块边界清晰。' --license CC-BY-4.0 --rights-url https://example.org/verified-license
.venv/bin/python scripts/build.py
```

`--bbox` 使用 PDF 点坐标。`publication_verified` 表示核对出处和图片；`reviewed` 表示人工精选，必须填写参考理由。`approve` 表示维护者已核验裁剪、图注、展示依据和视觉效果。`reject 图表ID` 撤下图片，重建发布后公开网站才更新；公开仓库历史中的文件仍存在。

## 目录

- `data/catalog.sqlite3`：论文、图表、采集与提取状态的主数据库。
- `data/scope.json`：收录来源和年份配置。
- `site/`：静态前端及图表资源。
- `scripts/`：采集、数据库维护、提取、核验与构建。
- `tests/`：数据库事务、去重、来源筛选、发布边界和首页数据体积测试。
- `.github/workflows/publish.yml`：定时更新与 Pages 发布。
- `dist/`：构建产物，不提交 Git。

规模测试将论文从 11 条增加到 5,001 条，首页目录仅增加 4 字节（统计数字变化）；全量数据放在独立分片。后续达到数万或更多条时，搜索索引本身也应拆分或引入搜索服务。当前方案减少首屏负载，但实际访问时间仍受访客网络和 GitHub Pages 服务影响。
