# TLE Aggregation Service

## 项目背景

卫星、火箭体和空间碎片的轨道数据通常以 TLE/GP 形式发布。Space-Track 提供基于账号的官方 GP 数据接口，CelesTrak 提供公开的分类和 GP 数据入口。实际下载过程中可能遇到认证失败、跨境网络不稳定、旧 URL、服务端限流、临时封禁以及返回 HTML 错误页等情况。

本项目当前实现了一个低频、可审计的 Space-Track GP 下载 MVP。它的目标是先可靠地完成一次受控下载：使用环境变量读取账号密码，建立登录会话，请求官方 GP JSON 接口，校验响应，并将原始响应按日期归档。项目默认不自动重试，不频繁访问服务，避免触发 Space-Track 限制。

## 当前使用的方案

当前版本使用以下方法：

- 使用 Space-Track `class/gp` 接口获取当前 GP 数据；
- 使用 JSON 格式，而不是固定宽度的 3LE/TLE，便于兼容 100000 以上的新目录号；
- 查询条件为 `DECAY_DATE/null-val` 和 `EPOCH/>now-10`，只获取最近 10 天内有较新轨道历元且尚未衰减的对象；
- 使用 `urllib` 建立 Cookie 会话，先登录再请求 GP 数据；
- 账号和密码只从环境变量读取，不写入 YAML、源代码、日志或归档；
- 对 HTTP 401、403、404、网络错误、空响应、HTML 响应和非法 JSON 直接失败；
- 下载成功后使用临时文件原子替换，避免中断时留下半个数据文件；
- 原始 JSON 保存到 `archive/raw/spacetrack/YYYY-MM-DD/`（按配置的本地时区命名）；每次成功下载的记录同时写入 SQLite 数据库。
- SQLite 保存下载运行信息和 GP 历史记录，可按 NORAD 目录号或每个对象的最新历元查询。

当前版本尚未实现：CelesTrak 适配器、SatNOGS 适配器、OMM 规范化、TLE 导出、manifest 和源间回退。已经提供的能力包括：基于 `min_interval_minutes` 的跨进程下载限频、用 SQLite 文件锁避免并发 `fetch`、`compact` 数据库维护命令，以及 systemd service/timer 每日调度（需要在部署主机上完成安装和凭据配置）。

## 实际表现

已完成的本地验证：

```text
11 个离线单元测试全部通过
Python compileall 编译检查通过
示例配置校验通过
缺少凭据时 fetch 安全退出，不发起请求、不重试
```

测试不会访问外网。真实 Space-Track 下载只有在用户主动设置环境变量并执行 `fetch` 时才会发生。

已在 nano72 上完成多次真实接口下载：单次归档约 36 MiB / 31,967 条 GP JSON 记录，首次快照约 47.0 MiB / 31,927 条，JSON 结构校验通过。该结果说明当前登录、接口请求、响应解析和原始文件归档链路可用；它不代表后续请求可以高频执行。

## 环境要求

- Linux/macOS；
- Python 3.10 或更高版本；
- PyYAML；
- 可访问 `https://www.space-track.org`；
- 已注册并可用的 Space-Track 账号。

安装依赖：

```bash
python3 -m pip install -e .
```

也可以直接使用当前工作区的源码模式，不安装项目：

```bash
export PYTHONPATH=src
```

## 配置文件

复制配置模板：

```bash
cp config.example.yaml config.yaml
```

配置中的关键项：

```yaml
timezone: Asia/Shanghai

storage:
  root: ./archive
  database: ./archive/tle.db

policy:
  max_attempts_per_source: 1
  min_interval_minutes: 300
  request_timeout_seconds: 60
  user_agent: tle-aggregation-service/0.1

sources:
  spacetrack:
    base_url: https://www.space-track.org
    username_env: SPACE_TRACK_USER
    password_env: SPACE_TRACK_PASSWORD
    query: /basicspacedata/query/class/gp/DECAY_DATE/null-val/EPOCH/%3Enow-10/ORDERBY/NORAD_CAT_ID/format/json
```

`min_interval_minutes` 默认值为 300 分钟（5 小时），模板 `config.example.yaml` 和代码兜底默认值保持一致。CLI 会根据数据库中的最近一次成功运行时间执行跨进程限频，并使用 SQLite 锁避免并发 `fetch`。需要人工强制执行时使用 `fetch --force`。

该值同时受两个约束，调整时要一起考虑：

1. **必须低于 systemd timer 的调度周期。** timer 为 24 小时（`RandomizedDelaySec=300`，即最多延后 5 分钟），因此两次计划运行的最小间隔可能只有 1435 分钟。若把该值设为 1440，随机延迟会让计划任务偶尔被判为“未到间隔”而跳过，表现为某天没有下载。
2. **要足够小，手动补跑才不会吞掉次日计划。** 下一次计划运行固定在 03:20，因此当间隔为 N 分钟时，只有 **03:20 + (1440 − N)** 之后启动的补跑才会与之冲突。默认 300 表示 `22:20` 之前的手动补跑都不影响次日凌晨的计划运行；若沿用 1200，则 `07:20` 之后补跑就会导致次日跳过。

> 代价是限频作为“重复下载保险”的力度变弱：两次运行间隔只要超过 5 小时就不会被拦。对每日一次的计划任务没有影响，但如果日后提高抓取频率，应重新评估该值。

```text
fetch skipped; last successful run was 2026-09-21T09:11:15.372058+00:00; minimum interval has 49825s remaining
```

上面是限频命中时的输出：`fetch` 以退出码 0 结束，不会发起任何请求，也不会重试。

## 凭据设置

不要把密码写入配置文件，也不要提交 `.env`。在执行下载的同一个终端中设置环境变量：

```bash
export SPACE_TRACK_USER='你的 Space-Track 账号'
export SPACE_TRACK_PASSWORD='你的 Space-Track 密码'
```

项目也提供 `.env.example` 作为变量名称参考，但当前程序不会自动读取 `.env` 文件。

## 启动和使用

### 1. 校验配置

不检查账号密码，只检查 YAML、HTTPS 地址和最低请求间隔：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml validate
```

成功输出：

```text
configuration valid; credentials are not checked
```

### 2. 执行一次下载

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml fetch
```

本项目使用 `src` 布局，直接手动运行 `python3 -m tle_aggregation.cli ...` 时必须设置 `PYTHONPATH=src`；systemd service 已经自动设置该环境变量。账号环境变量也需要先加载，例如：

```bash
set -a
. /home/lzk/.config/tle-aggregation/credentials.env
set +a
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml fetch --force
```

成功后会输出归档文件路径，例如：

```text
archive/raw/spacetrack/2026-09-21/gp-032000.json
```

本命令只执行一次登录和一次 GP 请求。成功下载后 SQLite 会自动压缩为每个卫星的最新记录，完整 JSON 仍保留在按日期归档的文件中。当前代码不做自动重试，因此遇到 401、403、404 或网络错误时会直接退出，避免重复请求导致账号或 IP 被限制。

### 3. 查看归档

```bash
find archive/raw/spacetrack -type f -name '*.json' -print
python3 -m json.tool archive/raw/spacetrack/YYYY-MM-DD/gp-HHMMSS.json >/dev/null
```

归档路径为 `archive/raw/spacetrack/<YYYY-MM-DD>/gp-<HHMMSS>.json`，目录名和文件名都按配置的 `timezone`（默认 `Asia/Shanghai`）生成，而数据库中的 `runs.retrieved_at` 始终是 UTC。例如 UTC `2026-09-20T19:21:27Z` 在上海时间是 09-21 03:21:27，归档为 `archive/raw/spacetrack/2026-09-21/gp-032127.json`。

> 历史数据说明：2026-09-21 08:13 UTC 之前部署的版本按 **UTC** 命名归档（例如 `archive/raw/spacetrack/2026-09-20/gp-192127.json`），之后的版本改为按配置时区命名。既有原始文件保持原样、未做重命名（原始归档视为不可变证据），因此早期目录中可能混有两种命名。需要定位某个批次时，请以数据库 `runs.payload_path` 为准，不要从文件名反推时间。

### 4. 查询 SQLite

查询每个 NORAD 号的最新记录：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml query
```

查询一个 NORAD 号的全部历史记录：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml --norad 25544 query
```

SQLite 文件默认是 `archive/tle.db`。表 `runs` 保存每次下载，表 `gp_records` 保存每个卫星最新的 GP 记录（每次 `fetch` 成功后会立刻执行一次 `compact --latest-only`）；原始 JSON 路径保存在 `runs.payload_path` 中。

### 5. 迁移和瘦身数据库

`fetch` 每次成功后都会自动执行等价的 `compact --latest-only`，因此日常运行不需要手动调用本命令。手动命令用于：迁移旧数据库结构、按保留窗口裁剪历史、或对已有数据库重新执行 `VACUUM` 回收空间。

新版数据库使用短 SHA-256 哈希去重，不再把完整 `raw_json` 放进唯一索引。对旧数据库执行迁移并只保留每个卫星最新记录：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml --latest-only compact
```

该命令会先迁移表结构，再删除历史记录并执行 SQLite `VACUUM`。执行前应备份 `archive/tle.db`。如果需要保留最近一段历史，可以改用：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml --keep-history-days 90 compact
```

## 运行测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.example.yaml validate
```

测试内容包括：

- 示例配置能够加载，且不需要读取真实凭据；
- HTTP 数据源被拒绝，未知时区被拒绝；
- `min_interval_minutes` 的默认值与模板一致，并低于 24 小时调度周期；
- 非法 JSON、HTML 响应等异常被拒绝且不重试；
- 合法 JSON 数组能够通过；
- 归档目录与文件名按配置的本地时区生成；
- 入库保留历史并可按历元查询最新记录，`compact` 只保留每个卫星最新一条；
- 旧结构数据库可迁移到哈希去重，且 `migrate_database` 幂等。

## 目录说明

```text
config.example.yaml                         配置模板
.env.example                                凭据变量名称模板
src/tle_aggregation/config.py               配置和环境变量校验
src/tle_aggregation/database.py              SQLite 建表、入库和查询
src/tle_aggregation/spacetrack.py           Space-Track 登录、请求和原始归档
src/tle_aggregation/cli.py                  validate/fetch/query/compact 命令入口
tests/                                      离线测试
archive/                                    下载后生成，已加入 .gitignore
deploy/tle-aggregation.service              systemd 单次下载服务
deploy/tle-aggregation.timer                每日北京时间定时器
```

## 接口选择说明

当前使用的接口是：

```text
https://www.space-track.org/basicspacedata/query/class/gp/DECAY_DATE/null-val/EPOCH/%3Enow-10/ORDERBY/NORAD_CAT_ID/format/json
```

它适合获取当前可传播的最新 GP 记录。`#recent` 是网页页面，不作为程序接口。`format/3le` 只适用于仍能用固定宽度 TLE 表示的目录号，因此当前实现选择 JSON。

## 安全和访问限制

- Space-Track 密码不应再次发送到聊天、提交到 Git 或写入日志；
- 生产环境应使用密钥管理器或进程环境变量注入凭据；
- 每日一次已经满足本项目归档需求，不应使用循环脚本高频请求；
- 遇到 401/403/404 不应盲目重试，应先检查账号、接口、权限和访问限制；
- 本地测试默认不访问 Space-Track，真实请求只能通过显式 `fetch` 触发。

## nano72 部署和自动运行

项目部署目录为 `/home/lzk/TLE_Aggregation_Service`。systemd 定时器配置为每天北京时间 03:20，允许最多随机延迟 5 分钟，并使用 `Persistent=true`，主机断电或重启后会补跑错过的任务。

在 nano72 上配置凭据（不要写入 Git）：

```bash
install -d -m 700 /home/lzk/.config/tle-aggregation
editor /home/lzk/.config/tle-aggregation/credentials.env
chmod 600 /home/lzk/.config/tle-aggregation/credentials.env
```

文件内容为：

```text
SPACE_TRACK_USER=你的账号
SPACE_TRACK_PASSWORD=你的密码
```

然后在 nano72 上安装并启用 timer：

```bash
cd /home/lzk/TLE_Aggregation_Service
sudo install -m 644 deploy/tle-aggregation.service /etc/systemd/system/tle-aggregation.service
sudo install -m 644 deploy/tle-aggregation.timer /etc/systemd/system/tle-aggregation.timer
sudo systemctl daemon-reload
sudo systemctl enable --now tle-aggregation.timer
systemctl status --no-pager tle-aggregation.timer
```

手动验证服务：

```bash
sudo systemctl start tle-aggregation.service
systemctl status --no-pager tle-aggregation.service
journalctl -u tle-aggregation.service -n 100 --no-pager
```

服务失败时不会删除旧 JSON 或 SQLite 数据。当前 nano72 的 `archive/tle.db` 已记录 4 个成功下载批次：初始化快照 31,927 条 GP 记录，最近一次 31,967 条；由于每次 `fetch` 后自动 compact，`gp_records` 只保留每个卫星的最新一条。

运维提示：

- 主机时区是 `Etc/UTC`，而 timer 使用 `Asia/Shanghai`，因此实际触发时间是 UTC 19:20（= 北京时间次日 03:20）；
- 手动执行 `fetch --force` 或 `systemctl start tle-aggregation.service` 会刷新“最近一次成功运行时间”，可能让紧随其后的计划任务被判为“未到间隔”而跳过。手动补跑后请确认下一次计划运行与它的间隔大于 `min_interval_minutes`。

如果远端尚未执行 systemd 安装，使用具备 sudo 权限的账号执行上面的安装命令。当前 SSH 账号可以写入项目目录，但不能免密码执行 sudo，因此无法由自动部署脚本代替这一步。凭据文件也必须由管理员或你本人写入，文件权限应为 `600`。

## 长期运行后的分析

`fetch` 每次成功后都会自动执行 `compact --latest-only`，所以 SQLite 默认是**当前状态缓存**：每个卫星只保留最新一条记录，不再累积多批次历史。需要历史历元时，请从按日期归档的原始 JSON 中读取。

常用查询（部署主机通常没有安装 `sqlite3` 命令行，以下示例直接使用 Python 标准库）：

```bash
python3 -c "import sqlite3;print('objects', sqlite3.connect('archive/tle.db').execute('SELECT COUNT(*) FROM gp_records').fetchone()[0])"
python3 -c "import sqlite3;print(*sqlite3.connect('archive/tle.db').execute('SELECT MIN(epoch), MAX(epoch) FROM gp_records').fetchone(), sep='\n')"
python3 -c "import sqlite3;[print(r) for r in sqlite3.connect('archive/tle.db').execute('SELECT run_id, retrieved_at, record_count, payload_path FROM runs ORDER BY run_id')]"
```

如果确实安装了 `sqlite3`，也可以直接执行等价 SQL：

```bash
sqlite3 archive/tle.db 'SELECT COUNT(*) FROM gp_records;'
sqlite3 archive/tle.db 'SELECT * FROM runs ORDER BY run_id;'
```

也可以使用项目命令查询并输出完整 JSON：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml --norad 25544 query
```

`runs` 表记录每次下载时间、记录数和对应原始 JSON 路径；`gp_records` 表记录对象编号、名称、国际编号、历元、来源、完整原始记录和短哈希。

原始 JSON 归档用于复核，SQLite 作为当前状态缓存，每个卫星只保留最新记录。

> `compact --latest-only` 的判据是**按 `(source, norad_cat_id)` 分区、取 `epoch` 最大的那一行**，跨所有批次生效。因此当某个对象不出现在最新一次抓取结果中时（例如查询条件为 `EPOCH > now-10`、对象已衰减或超过 10 天未更新），它此前入库的最新时代仍会保留，`SELECT COUNT(*) FROM gp_records` 可能**大于**最近一次的 `record_count`。例如 2026-09-22 的抓取为 32,002 条，而 `gp_records` 为 32,112 行。两者不应直接比较。

---

## 轨道时序分析与空间事件自动检测系统

针对归档的大规模历史 TLE/OMM 快照，系统提供了完整的**轨道演化可视化、空间天气联动、以及全自动在轨事件检测流水线**。

### 1. 核心检测算法机制

系统针对全量在轨载荷（PAYLOAD）提供标准 SSA 工业级两阶段检测架构：

1. **阶段一：物理去趋势与自适应残差初筛（Fast Screening）**
   * **气阻去趋势**：低轨自然气阻导致半长轴持续衰减（$\dot{a} < 0$），自适应捕获逆阻力跳跃（$\Delta a > 3\sigma$）；
   * **进动去趋势**：剥离地球 $J_2$ 摄动导致的升交点赤经（RAAN）自然线性进动；
   * **GEO 倾角矢量去趋势**：剥离日月三体引力导致的倾角自然年漂移，监控南北/东西定点死区（Deadband）。
2. **阶段二：双历元 SGP4 交叉外推验证与冲量反演（Verification & $\Delta V$ Inversion）**
   * 对初筛候选事件，调用底层 C++ 绑定的 SGP4 模型将前序 TLE 外推至后序历元；
   * 计算三维空间残差 $\Delta r$ 与速度差 $\Delta v$，并在航天器轨道坐标系（RTN: 径向 Radial / 切向 In-track / 法向 Cross-track）下精准反演推进器冲量分量；
   * 采用**三历元持久性一致性确认（Triple-Epoch Consistency）**，彻底消除单次测轨拟合噪声。
3. **空间天气环境解耦**
   * 自动集成 CelesTrak 高层大气参数（`SW-Last5Years.txt`，包含太阳通量 $F_{10.7}$ 与地磁指数 $Ap, Kp$）；
   * 当低轨航天器 BSTAR 阻力项激增时，若当日 $Ap \ge 25$（地磁暴），自动标记为**高层大气暴响应**；若空间天气平稳，则判定为**航天器自身姿态机动/迎风截面变化**。

### 2. 增量自适应状态引擎架构（$O(1)$ 复杂度）

为解决多年历史数据累积导致的全量回溯性能雪崩问题，系统采用 **SQLite 增量状态库（`satellite_state.db`，仅约 7.9 MB）**：
* **微分与稳态基准**：记录上次机动后的稳态半长轴（`stable_baseline_a`），长期累计评估轨道维持与推进剂消耗（`cumulative_da_km`）；
* **在线递归学习（Recursive Online Learning）**：采用指数平滑（EMA）自动递推估计每颗卫星的专属测轨噪声底（`noise_sigma_a`）与背景气阻衰减率（`baseline_decay_rate`），实现**千星千面、自适应 $3.5\sigma$ 动态门限，杜绝人工配置阈值**；
* **极速增量执行**：每日仅比对单日新增 JSON 快照，**单日扫描 18,620 颗在轨载荷仅需约 1.6 秒**。

### 3. 工具脚本索引 (`scripts/`)

| 脚本文件 | 功能说明 | 核心产出 |
| :--- | :--- | :--- |
| `scripts/step1_summarize_satellites.py` | 扫描全量历史 JSON 快照，盘点 32,643 颗目标的首现日期与历元跨度 | `satellite_summary.csv`, `.json` |
| `scripts/step2_extract_and_visualize.py` | 提取 7 类代表性轨道卫星（ISS、天和、Starlink、哨兵、北斗、天链、闪电），生成交互式 Plotly HTML 看板 | `orbit_elements_dashboard.html` 及各星独立报告 |
| `scripts/fetch_space_weather.py` | 自动下载/缓存 CelesTrak 空间天气参数，支持每日定时更新 | `SW-Last5Years.txt` |
| `scripts/detect_orbital_events.py` | 全量在轨载荷（PAYLOAD）批处理事件自动检测与空间天气归因 | `orbital_events_detected.csv`, `orbital_events_summary_report.md` |
| `scripts/advanced_incremental_engine.py` | **高阶自适应增量检测引擎**（带稳态微分基准、在线学习与秒级增量检测） | `satellite_state.db`, `advanced_incremental_events_YYYY-MM-DD.csv` |

### 4. 常用运行命令

```bash
# 1. 每日定时更新空间天气参数（已配置为每日凌晨 02:00 定时运行）
python3 scripts/fetch_space_weather.py

# 2. 运行单日增量自适应事件检测（耗时约 1.6 秒，可挂载在每日 fetch 任务后）
python3 scripts/advanced_incremental_engine.py

# 3. 查看交互式可视化看板
# 直接在浏览器中打开 analysis_output/orbit_elements_dashboard.html
```
