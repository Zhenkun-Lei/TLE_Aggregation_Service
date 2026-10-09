# 空间在轨载荷（PAYLOAD）轨道事件与机动自动检测分析简报

* **数据时间跨度**：2026-09-20 至 2026-10-09（共 20 天）
* **扫描在轨载荷总数**：18741 颗有效工作卫星（PAYLOAD）
* **算法核心架构**：物理去趋势自适应残差初筛 + 双历元 SGP4 交叉外推验证 + CelesTrak 空间天气联动归因
* **生成时间**：2026-10-09 02:03:41

---

## 一、 事件检测总体统计

* **发生事件的独立卫星总数**：**9915** 颗（占在轨载荷总数的 52.91%）
* **检测到的总事件次数**：**23161** 次

| 事件类型 | 事件定义与物理特征 | 检测发生次数 | 涉及卫星数 |
| :--- | :--- | :---: | :---: |
| **ORBIT_RAISE_MANEUVER** | 主动轨道抬升机动 (抵消气阻/抬高轨道，SGP4验证) | 13073 | 7672 |
| **ORBIT_LOWER_MANEUVER** | 主动降轨机动 (变轨调相/离轨操作) | 4074 | 956 |
| **BSTAR_SPIKE_ATTITUDE_MANEUVER** | 航天器姿态调整/气动截面异动 (空间天气平静期独立突变) | 2970 | 2523 |
| **GEO_EAST_WEST_STATION_KEEPING** | GEO 东西位置保持 (调整半长轴进行经度定点维持) | 1745 | 474 |
| **BSTAR_SPIKE_SPACE_WEATHER** | 高层大气暴响应 (与 09-25 及 10-04 地磁暴直接关联) | 893 | 874 |
| **GEO_NORTH_SOUTH_STATION_KEEPING** | GEO 南北位置保持 (主动点火反向修正倾角自然漂移) | 406 | 202 |

---

## 二、 典型重点航天器机动事件档案（精选代表性案例）

### 1. 载人空间站与重点卫星事件实测验证
| NORAD ID | 卫星名称 | 轨道类型 | 事件类型 | 发生时刻 (UTC) | 变轨幅度 Δa | SGP4残差 Δr | 反演冲量 ΔV | 归因说明 |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| `55310` | **STARLINK-5309** | LEO | ORBIT_RAISE_MANEUVER | `2026-09-28T06:00:02` | +3.052 km | 40.2 km | **44.98 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `62193` | **STARLINK-32688** | LEO | ORBIT_RAISE_MANEUVER | `2026-09-26T13:49:55` | +0.055 km | 42.5 km | **44.98 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `64221` | **STARLINK-34326** | LEO | ORBIT_RAISE_MANEUVER | `2026-09-26T11:23:13` | +0.149 km | 39.5 km | **44.98 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `66471` | **STARLINK-35569** | LEO | ORBIT_RAISE_MANEUVER | `2026-10-08T02:30:05` | +0.118 km | 41.2 km | **44.97 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `57528` | **STARLINK-30269** | LEO | ORBIT_RAISE_MANEUVER | `2026-10-02T00:45:55` | +0.115 km | 39.4 km | **44.97 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `64069` | **STARLINK-11649** | LEO | ORBIT_RAISE_MANEUVER | `2026-09-24T15:46:05` | +0.223 km | 39.2 km | **44.97 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `100293` | **STARLINK-37812** | LEO | ORBIT_RAISE_MANEUVER | `2026-09-20T11:08:01` | +0.150 km | 39.8 km | **44.97 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `66808` | **STARLINK-36071** | LEO | ORBIT_RAISE_MANEUVER | `2026-09-27T20:41:55` | +0.119 km | 40.3 km | **44.97 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `52502` | **STARLINK-3912** | LEO | ORBIT_RAISE_MANEUVER | `2026-09-23T08:59:02` | +0.502 km | 40.5 km | **44.97 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |
| `100182` | **STARLINK-38140** | SSO | ORBIT_RAISE_MANEUVER | `2026-10-02T14:00:01` | +2.517 km | 40.3 km | **44.96 m/s** | Active Thruster Propulsion (推进机动抬轨/降轨) |

---

## 三、 空间天气（地磁暴）对低轨大气阻力（BSTAR）影响分析

本周期内共检测到 **893** 起低轨航天器大气阻力系数急剧突增。集中暴发高峰日期如下：
* **2026-09-25**：**330 颗卫星** 同时触发 BSTAR 突跃，当日地磁指数 **$Ap = 27$**（确认为地磁暴引发的高层热层大气整体受热膨胀）。
* **2026-10-05**：**303 颗卫星** 同时触发 BSTAR 突跃，当日地磁指数 **$Ap = 22$**（确认为地磁暴引发的高层热层大气整体受热膨胀）。
* **2026-10-04**：**260 颗卫星** 同时触发 BSTAR 突跃，当日地磁指数 **$Ap = 48$**（确认为地磁暴引发的高层热层大气整体受热膨胀）。

---

## 四、 成果输出文件索引
* 详细事件数据库（CSV）：`/home/jetson/TLE_Aggregation_Service/analysis_output/orbital_events_detected.csv`
* 结构化事件数据（JSON）：`/home/jetson/TLE_Aggregation_Service/analysis_output/orbital_events_detected.json`
* 空间天气环境基准文件：`/home/jetson/TLE_Aggregation_Service/analysis_output/SW-Last5Years.txt`