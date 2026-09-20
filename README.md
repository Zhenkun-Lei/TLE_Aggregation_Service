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
- 原始 JSON 保存到 `archive/raw/spacetrack/YYYY-MM-DD/`；每次成功下载的记录同时写入 SQLite 数据库。
- SQLite 保存下载运行信息和 GP 历史记录，可按 NORAD 目录号或每个对象的最新历元查询。

当前版本尚未实现：CelesTrak 适配器、SatNOGS 适配器、持久化全局限速状态、OMM 规范化、TLE 导出、manifest 和源间回退。自动每日调度已经提供 systemd service/timer 文件，但需要在部署主机上完成安装和凭据配置。

## 实际表现

已完成的本地验证：

```text
4 个离线单元测试全部通过
Python compileall 编译检查通过
示例配置校验通过
缺少凭据时 fetch 安全退出，不发起请求、不重试
```

测试不会访问外网。真实 Space-Track 下载只有在用户主动设置环境变量并执行 `fetch` 时才会发生。

已完成一次真实接口下载：2026-09-20 归档文件大小约 47.0 MiB，包含 31,927 条 GP JSON 记录，JSON 结构校验通过。该结果说明当前登录、接口请求、响应解析和原始文件归档链路可用；它不代表后续请求可以高频执行。

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
  min_interval_minutes: 1440
  request_timeout_seconds: 60

sources:
  spacetrack:
    base_url: https://www.space-track.org
    username_env: SPACE_TRACK_USER
    password_env: SPACE_TRACK_PASSWORD
    query: /basicspacedata/query/class/gp/DECAY_DATE/null-val/EPOCH/%3Enow-10/ORDERBY/NORAD_CAT_ID/format/json
```

`min_interval_minutes` 当前用于配置校验，默认值为 1440 分钟。当前 CLI 尚未持久化或执行跨进程限速状态，因此不要并发或频繁启动 `fetch`。

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

成功后会输出归档文件路径，例如：

```text
archive/raw/spacetrack/2026-09-20/gp-032000.json
```

本命令只执行一次登录和一次 GP 请求。当前代码不做自动重试，因此遇到 401、403、404 或网络错误时会直接退出，避免重复请求导致账号或 IP 被限制。

### 3. 查看归档

```bash
find archive/raw/spacetrack -type f -name '*.json' -print
python3 -m json.tool archive/raw/spacetrack/YYYY-MM-DD/gp-HHMMSS.json >/dev/null
```

### 4. 查询 SQLite

查询每个 NORAD 号的最新记录：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml query
```

查询一个 NORAD 号的全部历史记录：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml --norad 25544 query
```

SQLite 文件默认是 `archive/tle.db`。表 `runs` 保存每次下载，表 `gp_records` 保存每条 GP 历史记录；原始 JSON 路径仍保存在 `payload_path` 中。

## 运行测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.example.yaml validate
```

测试内容包括：

- 示例配置能够加载；
- HTTP 数据源被拒绝；
- 非法 JSON 被拒绝；
- 合法 JSON 数组能够通过；
- 配置校验不需要读取真实凭据。

## 目录说明

```text
config.example.yaml                         配置模板
.env.example                                凭据变量名称模板
src/tle_aggregation/config.py               配置和环境变量校验
src/tle_aggregation/database.py              SQLite 建表、入库和查询
src/tle_aggregation/spacetrack.py           Space-Track 登录、请求和原始归档
src/tle_aggregation/cli.py                  validate/fetch 命令入口
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

服务失败时不会删除旧 JSON 或 SQLite 数据。当前已将已有快照初始化到 nano72 的 `archive/tle.db`：1 个下载批次、31,927 条 GP 记录。

如果远端尚未执行 systemd 安装，使用具备 sudo 权限的账号执行上面的安装命令。当前 SSH 账号可以写入项目目录，但不能免密码执行 sudo，因此无法由自动部署脚本代替这一步。凭据文件也必须由管理员或你本人写入，文件权限应为 `600`。

## 一个月后的分析

数据库会保留不同下载批次和不同历元的历史记录，不会只保留最新值。常用查询示例：

```bash
sqlite3 archive/tle.db 'SELECT COUNT(*) FROM gp_records;'
sqlite3 archive/tle.db 'SELECT COUNT(*), MIN(epoch), MAX(epoch) FROM gp_records;'
sqlite3 archive/tle.db 'SELECT norad_cat_id, COUNT(*), MIN(epoch), MAX(epoch) FROM gp_records GROUP BY norad_cat_id ORDER BY COUNT(*) DESC LIMIT 20;'
```

也可以使用项目命令查询 JSON：

```bash
PYTHONPATH=src python3 -m tle_aggregation.cli --config config.yaml --norad 25544 query
```

`runs` 表记录每次下载时间、记录数和对应原始 JSON 路径；`gp_records` 表记录对象编号、名称、国际设计ator、历元、来源和完整原始记录。原始 JSON 与 SQLite 应同时保留，便于一个月后复核解析结果。
