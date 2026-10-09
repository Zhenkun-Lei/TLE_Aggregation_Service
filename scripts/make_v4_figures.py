#!/usr/bin/env python3
"""
Generate ultra-high-resolution, seamless dark-themed figures for V4 slides:
Slide 1: TLE Data Aggregation & Space Weather Ingestion Architecture
Slide 2: Two-Stage Space Situational Awareness & Maneuver Detection Engine
Color palette matches 轨道计算能力-V3.pptx:
  Background: #03080C (matches PPT dark background)
  Title/Gold: #EADBBB
  Cyan Accent: #56D2FF / #90E6F0
  Card Fill: #081119 / #0D1924
  Border: #1B3547 / #2B5270
  Text: #F4F5F3 / #A8B0B5
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

OUTPUT_DIR = '/home/lzk/TLE_Aggregation_Service/analysis_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams['font.sans-serif'] = ['Source Han Sans SC', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 300

BG_COLOR = '#03080C'
CARD_BG = '#08131C'
CARD_BORDER = '#1E3A4E'
CYAN_ACCENT = '#56D2FF'
GOLD_ACCENT = '#EADBBB'
GREEN_ACCENT = '#17B978'
ORANGE_ACCENT = '#FF7B54'
PURPLE_ACCENT = '#A370F7'
TEXT_WHITE = '#F4F5F3'
TEXT_MUTED = '#A8B0B5'

# -------------------------------------------------------------------------
# Figure 1: TLE Ingestion & Space Weather Pipeline Architecture (16:7.5)
# -------------------------------------------------------------------------
def make_v4_fig1_tle_pipeline():
    fig, ax = plt.subplots(figsize=(13.16, 6.30), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Top Header Banner
    ax.text(50, 95, "全网多源 TLE 自动化聚合与空间环境同步全链路", fontsize=15, weight='bold', color=GOLD_ACCENT, ha='center', va='center')
    ax.text(50, 89, "高频自动化数据采集 → 原子级增量归档 → 单星物理基准库 → 毫秒级任务分析 API", fontsize=10.5, color=TEXT_MUTED, ha='center', va='center')

    # 4 Main Architecture Columns (Cards)
    cards = [
        {
            "rect": (3, 10, 21, 72),
            "tag": "数据源层 (SOURCES)",
            "title": "全球多源实时拉取",
            "tag_color": CYAN_ACCENT,
            "border_color": '#1E3A4E',
            "items": [
                ("Space-Track 官方 GP", "32,000+ 条/日增量原子同步"),
                ("CelesTrak 空间天气", "全周期太阳辐射/地磁环境"),
                ("NOAA SWPC 实测", "近实时地磁指数 Kp / Ap"),
                ("内部遥测 / GNSS", "高精度星载真值校准校验")
            ]
        },
        {
            "rect": (27, 10, 21, 72),
            "tag": "管道调度 (CRON ENGINE)",
            "title": "定时自动化原子归档",
            "tag_color": GREEN_ACCENT,
            "border_color": '#17B978',
            "items": [
                ("02:00 空间环境同步", "解析 F10.7、Kp、Ap 连续时序"),
                ("03:20 全网 TLE 抓取", "4,375 颗在轨载荷全量拉取"),
                ("原子级增量校验", "历元时间戳排重与格式校验"),
                ("动态失败重试", "指数退避容错，零单点断流")
            ]
        },
        {
            "rect": (51, 10, 21, 72),
            "tag": "存储底座 (STORAGE ENGINE)",
            "title": "单星时序基准状态库",
            "tag_color": ORANGE_ACCENT,
            "border_color": '#FF7B54',
            "items": [
                ("SQLite / Parquet", "原子结构化时序持久化存储"),
                ("物理基准参数底座", "滑动微分基准与拟合均值 μ"),
                ("测轨噪声在线学习", "单星递推测轨方差 σ 噪声底"),
                ("全历史全量资产", "2,500 万+ 条在轨 TLE 存量")
            ]
        },
        {
            "rect": (75, 10, 21, 72),
            "tag": "业务赋能 (DOWNSTREAM)",
            "title": "毫秒级计算能力输出",
            "tag_color": PURPLE_ACCENT,
            "border_color": '#A370F7',
            "items": [
                ("多弧动力学定轨", "多条 TLE 联合拟合 OEM 轨道"),
                ("空间态势感知", "全网机动事件秒级增量识别"),
                ("全天区碰撞交会", "20万对编目 135 秒高效初筛"),
                ("标准 REST / JSON", "无缝接入遥感规划业务系统")
            ]
        }
    ]

    for c in cards:
        rx, ry, rw, rh = c["rect"]
        # Outer card box
        card_box = patches.FancyBboxPatch((rx, ry), rw, rh, boxstyle="round,pad=1.2",
                                         facecolor=CARD_BG, edgecolor=c["border_color"], linewidth=1.6)
        ax.add_patch(card_box)

        # Header tag & title
        ax.text(rx + rw/2, ry + rh - 4.5, c["tag"], fontsize=9, weight='bold', color=c["tag_color"], ha='center', va='center')
        ax.text(rx + rw/2, ry + rh - 10.5, c["title"], fontsize=12.5, weight='bold', color=TEXT_WHITE, ha='center', va='center')
        ax.plot([rx + 2.5, rx + rw - 2.5], [ry + rh - 14.5, ry + rh - 14.5], color='#182E3E', lw=1.2)

        # Content bullets
        curr_y = ry + rh - 22
        for heading, desc in c["items"]:
            # bullet point
            ax.plot(rx + 2.8, curr_y, 's', markersize=3.8, color=c["tag_color"])
            ax.text(rx + 5.0, curr_y, heading, fontsize=10, weight='bold', color=TEXT_WHITE, va='center')
            ax.text(rx + 5.0, curr_y - 4.8, desc, fontsize=8.5, color=TEXT_MUTED, va='center')
            curr_y -= 12.8

    # Arrows between cards
    for ax_x in [24.7, 48.7, 72.7]:
        ax.annotate('', xy=(ax_x + 1.8, 46), xytext=(ax_x - 0.2, 46),
                    arrowprops=dict(arrowstyle="->", color=CYAN_ACCENT, lw=2.2, mutation_scale=12))

    out_path = os.path.join(OUTPUT_DIR, 'v4_fig1_tle_pipeline.png')
    fig.savefig(out_path, dpi=300, facecolor=BG_COLOR, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    print("Saved:", out_path)

# -------------------------------------------------------------------------
# Figure 2: SSA & Maneuver Detection Engine (16:7.5)
# -------------------------------------------------------------------------
def make_v4_fig2_ssa_engine():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.16, 6.30), facecolor=BG_COLOR)
    for ax in (ax1, ax2):
        ax.set_facecolor(BG_COLOR)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis('off')

    # ------------------ Subplot 1 (Left): Two-Stage Detection Flow ------------------
    ax1.text(50, 95, "两阶段高置信度自适应检测架构", fontsize=14, weight='bold', color=GOLD_ACCENT, ha='center', va='center')

    # Stage 1 Card
    box1 = patches.FancyBboxPatch((4, 48), 92, 38, boxstyle="round,pad=1.2",
                                  facecolor=CARD_BG, edgecolor=CYAN_ACCENT, linewidth=1.6)
    ax1.add_patch(box1)
    ax1.text(50, 81, "阶段一：物理去趋势 + 自适应残差初筛", fontsize=12, weight='bold', color=CYAN_ACCENT, ha='center')
    
    stage1_lines = [
        ("• 物理去趋势：", "基于单星物理模型剥离高层大气阻力衰减与 J2 摄动进动"),
        ("• 统计学基准：", "在线学习单星常态测轨噪声底 σ_a，构建自适应 3.5σ 门限"),
        ("• 极速初筛效能：", "30 秒内秒级排除 98.7% 常态背景目标，杜绝固定阈值误报")
    ]
    curr_y = 70
    for title, desc in stage1_lines:
        ax1.text(8, curr_y, title, fontsize=9.5, weight='bold', color=TEXT_WHITE)
        ax1.text(34, curr_y, desc, fontsize=8.8, color=TEXT_MUTED)
        curr_y -= 8.5

    # Down Arrow
    ax1.annotate('', xy=(50, 42), xytext=(50, 47),
                 arrowprops=dict(arrowstyle="->", color=ORANGE_ACCENT, lw=2.5, mutation_scale=14))

    # Stage 2 Card
    box2 = patches.FancyBboxPatch((4, 4), 92, 36, boxstyle="round,pad=1.2",
                                  facecolor=CARD_BG, edgecolor=ORANGE_ACCENT, linewidth=1.6)
    ax1.add_patch(box2)
    ax1.text(50, 34, "阶段二：双历元 SGP4 交叉外推验证", fontsize=12, weight='bold', color=ORANGE_ACCENT, ha='center')

    stage2_lines = [
        ("• 空间残差外推：", "SGP4 正/反向交叉比对，空间位置残差 Δr 门限核验"),
        ("• RTN 冲量反演：", "精准解算切向 ΔV_T / 法向 ΔV_N，定量辨识变轨意图"),
        ("• 三历元拟合校验：", "多历元趋势一致性复核，100% 消除地面拟合粗差点")
    ]
    curr_y = 24.5
    for title, desc in stage2_lines:
        ax1.text(8, curr_y, title, fontsize=9.5, weight='bold', color=TEXT_WHITE)
        ax1.text(34, curr_y, desc, fontsize=8.8, color=TEXT_MUTED)
        curr_y -= 8.5

    # ------------------ Subplot 2 (Right): RTN Dynamics & Weather Decoupling ------------------
    ax2.text(50, 95, "RTN 冲量反演与空间环境智能解耦", fontsize=14, weight='bold', color=GOLD_ACCENT, ha='center', va='center')

    # Upper visual area: RTN Diagram
    cx, cy = 18, 40
    r = 30
    theta = np.linspace(0.15, 1.35, 100)
    ax2.plot(cx + r*np.cos(theta), cy + r*np.sin(theta), color='#37474F', lw=2.0, ls='--')

    # Satellite center
    sx = cx + r*np.cos(np.pi/4)
    sy = cy + r*np.sin(np.pi/4)
    ax2.plot(sx, sy, 'o', color=CYAN_ACCENT, markersize=8.5, zorder=5)
    ax2.text(sx - 3, sy - 5.5, "卫星当前位置", fontsize=9.2, color=GOLD_ACCENT, weight='bold', ha='center', va='top')

    # Vector 1: Tangential (Along-track) -> Top-Left
    tx, ty = sx - 15, sy + 13
    ax2.annotate('', xy=(tx, ty), xytext=(sx, sy),
                 arrowprops=dict(arrowstyle="->", color=GREEN_ACCENT, lw=2.4, mutation_scale=13))
    ax2.text(tx - 2, ty + 1.2, "ΔV_T (切向加/减速)", fontsize=9.2, color=GREEN_ACCENT, weight='bold', ha='right', va='bottom')

    # Vector 2: Normal (Cross-track) -> Top-Right
    nx, ny = sx + 4, sy + 16
    ax2.annotate('', xy=(nx, ny), xytext=(sx, sy),
                 arrowprops=dict(arrowstyle="->", color=PURPLE_ACCENT, lw=2.4, mutation_scale=13))
    ax2.text(nx + 2, ny + 1.2, "ΔV_N (法向倾角控制)", fontsize=9.2, color=PURPLE_ACCENT, weight='bold', ha='left', va='bottom')

    # Vector 3: Radial -> Right
    rx, ry = sx + 17, sy - 4
    ax2.annotate('', xy=(rx, ry), xytext=(sx, sy),
                 arrowprops=dict(arrowstyle="->", color=ORANGE_ACCENT, lw=2.4, mutation_scale=13))
    ax2.text(rx + 2, ry, "ΔV_R (径向离心扰动)", fontsize=9.2, color=ORANGE_ACCENT, weight='bold', ha='left', va='center')

    # Lower Box: Space weather decoupling card
    wx_box = patches.FancyBboxPatch((4, 4), 92, 34, boxstyle="round,pad=1.2",
                                    facecolor=CARD_BG, edgecolor='#AFB42B', linewidth=1.6)
    ax2.add_patch(wx_box)
    ax2.text(50, 32, "BSTAR 阻力项与空间天气智能解耦机制", fontsize=11.5, weight='bold', color='#D4E157', ha='center')
    
    wx_lines = [
        ("• 地磁暴受热膨胀：", "Ap ≥ 25 → 全域高层大气增温膨胀，归因为自然气阻扰动"),
        ("• 地磁平静期机动：", "Ap < 15 → 环境阻力平稳，BSTAR 突变归因为航天器自主控轨"),
        ("• 全闭环机动归因：", "彻底解决单靠半长轴变化无法区分自然阻力与姿控变轨的行业难题")
    ]
    curr_y = 22.5
    for title, desc in wx_lines:
        ax2.text(8, curr_y, title, fontsize=9.2, weight='bold', color=TEXT_WHITE)
        ax2.text(34, curr_y, desc, fontsize=8.8, color=TEXT_MUTED)
        curr_y -= 8.0

    out_path = os.path.join(OUTPUT_DIR, 'v4_fig2_ssa_engine.png')
    fig.savefig(out_path, dpi=300, facecolor=BG_COLOR, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    print("Saved:", out_path)

if __name__ == '__main__':
    make_v4_fig1_tle_pipeline()
    make_v4_fig2_ssa_engine()
