#!/usr/bin/env python3
"""
Generate clean, professional figures for the 5-slide PPT presentation.
Outputs:
  - /home/lzk/TLE_Aggregation_Service/analysis_output/ppt_fig2_pipeline.png
  - /home/lzk/TLE_Aggregation_Service/analysis_output/ppt_fig3_methodology.png
  - /home/lzk/TLE_Aggregation_Service/analysis_output/ppt_fig4_results.png
  - /home/lzk/TLE_Aggregation_Service/analysis_output/ppt_fig5_performance.png
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd

OUTPUT_DIR = '/home/lzk/TLE_Aggregation_Service/analysis_output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams['font.sans-serif'] = ['Source Han Sans SC', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 300

# Color palette: Modern Deep Tech Blue / Teal / Coral / Slate
PRIMARY = '#10375C'
SECONDARY = '#0E8388'
ACCENT = '#EB455F'
BG_LIGHT = '#F8F9FA'
CARD_BG = '#FFFFFF'
TEXT_DARK = '#2C3E50'
TEXT_MUTED = '#7F8C8D'

# -------------------------------------------------------------
# Figure 2: Pipeline Diagram
# -------------------------------------------------------------
def make_fig2_pipeline():
    fig, ax = plt.subplots(figsize=(11.5, 3.3), facecolor='white')
    ax.axis('off')

    steps = [
        ("02:00", "空间天气同步", "CelesTrak 自动拉取\nF10.7, Kp, Ap 指数", "#0E8388"),
        ("03:20", "全量 TLE 下载", "Space-Track 官方 GP\n日均 3.2万条原子归档", "#10375C"),
        ("03:35", "增量自适应检测", "自适应门限初筛 +\nSGP4 双历元冲量反演", "#EB455F"),
        ("实时产出", "态势分析成果", "单星健康状态库刷新\n事件报表 + 交互看板", "#2E4F4F")
    ]

    for idx, (t_str, title, desc, col) in enumerate(steps):
        x = 0.05 + idx * 0.245
        y = 0.50
        w, h = 0.205, 0.78

        # Draw card box
        rect = patches.FancyBboxPatch((x, y - h/2), w, h, boxstyle="round,pad=0.03,rounding_size=0.04",
                                      facecolor='#F4F7FB', edgecolor=col, linewidth=2.0)
        ax.add_patch(rect)

        # Header badge
        badge = patches.FancyBboxPatch((x + 0.02, y + h/2 - 0.17), 0.165, 0.13, boxstyle="round,pad=0.01",
                                       facecolor=col, edgecolor='none')
        ax.add_patch(badge)
        ax.text(x + 0.102, y + h/2 - 0.105, t_str, color='white', weight='bold', fontsize=12, ha='center', va='center')

        # Title & desc
        ax.text(x + 0.102, y + 0.06, title, color='#1A252C', weight='bold', fontsize=12.5, ha='center', va='center')
        ax.text(x + 0.102, y - 0.18, desc, color='#506070', fontsize=10, ha='center', va='center', linespacing=1.35)

        # Arrow to next step
        if idx < len(steps) - 1:
            ax.annotate('', xy=(x + w + 0.035, y), xytext=(x + w + 0.005, y),
                        arrowprops=dict(arrowstyle="->", color='#9AA6B2', lw=2.5, mutation_scale=15))

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, 'ppt_fig2_pipeline.png')
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print("Saved:", out_path)

# -------------------------------------------------------------
# Figure 3: Methodology Diagram
# -------------------------------------------------------------
def make_fig3_methodology():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 3.4), facecolor='white', gridspec_kw={'width_ratios': [1.1, 1]})

    # Subplot 1: Two-Stage Architecture
    ax1.axis('off')
    ax1.text(0.5, 0.96, "两阶段高置信度检测架构", fontsize=12, weight='bold', color=PRIMARY, ha='center')

    # Stage 1 Card
    box1 = patches.FancyBboxPatch((0.05, 0.53), 0.90, 0.38, boxstyle="round,pad=0.03",
                                  facecolor='#F0F8FF', edgecolor=SECONDARY, linewidth=1.8)
    ax1.add_patch(box1)
    ax1.text(0.5, 0.81, "阶段一：物理去趋势 + 自适应残差初筛", fontsize=10.5, weight='bold', color=SECONDARY, ha='center')
    ax1.text(0.5, 0.65, "• 气阻单调衰减与 J2 摄动进动剥离\n• 在线自学习噪声底 σ_a，实现千星千面 3.5σ 门限\n• 30秒内排除 99%+ 平稳目标",
             fontsize=9, color=TEXT_DARK, ha='center', linespacing=1.25)

    # Down arrow
    ax1.annotate('', xy=(0.5, 0.45), xytext=(0.5, 0.52),
                 arrowprops=dict(arrowstyle="->", color=ACCENT, lw=2.5, mutation_scale=12))

    # Stage 2 Card
    box2 = patches.FancyBboxPatch((0.05, 0.04), 0.90, 0.38, boxstyle="round,pad=0.03",
                                  facecolor='#FFF5F5', edgecolor=ACCENT, linewidth=1.8)
    ax1.add_patch(box2)
    ax1.text(0.5, 0.32, "阶段二：双历元 SGP4 交叉外推验证", fontsize=10.5, weight='bold', color=ACCENT, ha='center')
    ax1.text(0.5, 0.16, "• 空间状态三维外推残差 Δr 门限过滤\n• RTN 坐标系反演冲量 ΔV (切向抬轨 / 法向控倾角)\n• 三历元一致性确认消灭地面拟合坏点",
             fontsize=9, color=TEXT_DARK, ha='center', linespacing=1.25)

    # Subplot 2: RTN Decomposition Visual
    ax2.axis('off')
    ax2.text(0.5, 0.96, "动力学冲量反演与环境归因", fontsize=12, weight='bold', color=PRIMARY, ha='center')

    theta = np.linspace(0, np.pi/2, 100)
    r = 0.5
    cx, cy = 0.25, 0.25
    ax2.plot(cx + r*np.cos(theta), cy + r*np.sin(theta), color='#B0BEC5', lw=2.0, ls='--')
    ax2.plot(cx + r*np.cos(np.pi/4), cy + r*np.sin(np.pi/4), 'o', color=PRIMARY, markersize=9)
    ax2.text(cx + r*np.cos(np.pi/4) - 0.05, cy + r*np.sin(np.pi/4) - 0.07, "卫星当前位置", fontsize=8.5, color=PRIMARY, weight='bold')

    # RTN Vectors
    sx, sy = cx + r*np.cos(np.pi/4), cy + r*np.sin(np.pi/4)
    ax2.annotate('Δv_T (切向加/减速)', xy=(sx - 0.18, sy + 0.18), xytext=(sx, sy),
                 arrowprops=dict(arrowstyle="->", color=SECONDARY, lw=2.2), fontsize=8.5, color=SECONDARY, weight='bold')
    ax2.annotate('Δv_N (法向倾角控制)', xy=(sx + 0.15, sy + 0.15), xytext=(sx, sy),
                 arrowprops=dict(arrowstyle="->", color='#8E44AD', lw=2.2), fontsize=8.5, color='#8E44AD', weight='bold')
    ax2.annotate('Δv_R (径向扰动)', xy=(sx + 0.18, sy - 0.18), xytext=(sx, sy),
                 arrowprops=dict(arrowstyle="->", color='#E67E22', lw=2.2), fontsize=8.5, color='#E67E22', weight='bold')

    # Space weather attribution card
    wx_box = patches.FancyBboxPatch((0.08, 0.04), 0.84, 0.32, boxstyle="round,pad=0.02",
                                    facecolor='#F9FBE7', edgecolor='#AFB42B', linewidth=1.5)
    ax2.add_patch(wx_box)
    ax2.text(0.50, 0.27, "BSTAR 阻力项与空间天气解耦", fontsize=9.5, weight='bold', color='#827717', ha='center')
    ax2.text(0.50, 0.13, "Ap >= 25 (地磁暴) -> 全域高层大气膨胀\nAp < 15 (平静期) -> 航天器自身姿态机动",
             fontsize=8.5, color=TEXT_DARK, ha='center', linespacing=1.2)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, 'ppt_fig3_methodology.png')
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print("Saved:", out_path)

# -------------------------------------------------------------
# Figure 4: Results & Real Cases
# -------------------------------------------------------------
def make_fig4_results():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 3.4), facecolor='white')

    # Subplot 1: Event Distribution Bar Chart
    categories = ['主动抬轨\n(Raise)', '主动降轨\n(Lower)', '姿态调整\n(Attitude)', 'GEO东西保持\n(E-W SK)', '大气暴响应\n(Storm)', 'GEO南北保持\n(N-S SK)']
    counts = [13073, 4074, 2970, 1745, 893, 406]
    colors = ['#10375C', '#1E88E5', '#0E8388', '#26A69A', '#EB455F', '#8E44AD']

    y_pos = np.arange(len(categories))
    bars = ax1.barh(y_pos, counts, color=colors, height=0.6)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(categories, fontsize=8.5)
    ax1.invert_yaxis()
    ax1.set_xlabel('检出事件次数 (20天全量扫描)', fontsize=8.5)
    ax1.set_title('全域在轨载荷事件分类统计 (共 23,161 起)', fontsize=10.5, weight='bold', color=PRIMARY, pad=10)
    ax1.grid(axis='x', linestyle='--', alpha=0.5)

    for bar in bars:
        w = bar.get_width()
        ax1.text(w + 200, bar.get_y() + bar.get_height()/2, f'{int(w):,}',
                 va='center', ha='left', fontsize=8, color='#333333', weight='bold')

    # Subplot 2: Real ISS Reboost Curve
    csv_iss = os.path.join(OUTPUT_DIR, 'timeseries_sat_25544.csv')
    if os.path.exists(csv_iss):
        df_iss = pd.read_csv(csv_iss)
        df_iss['dt'] = pd.to_datetime(df_iss['epoch'])
        ax2.plot(df_iss['dt'], df_iss['semimajor_axis'], marker='o', markersize=3.5, color='#10375C', lw=1.8, label='半长轴 a (km)')
        
        # Highlight Reboost Event
        reboost_time = pd.to_datetime('2026-09-26 09:35:46')
        ax2.axvline(reboost_time, color=ACCENT, linestyle='--', lw=1.2, alpha=0.8)
        ax2.annotate('真实抬轨机动\nΔa = +1.827 km\nΔv_T = +0.63 m/s',
                     xy=(reboost_time, 6798.77), xytext=(reboost_time - pd.Timedelta(days=5), 6798.1),
                     arrowprops=dict(facecolor=ACCENT, shrink=0.08, width=1.2, headwidth=5),
                     fontsize=8, weight='bold', color=ACCENT,
                     bbox=dict(boxstyle="round,pad=0.25", fc="#FFF0F2", ec=ACCENT, lw=1))

        ax2.set_title('国际空间站 (ISS) 轨道抬升实测反演', fontsize=10.5, weight='bold', color=PRIMARY, pad=10)
        ax2.set_ylabel('半长轴 a (km)', fontsize=8.5)
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.tick_params(axis='x', rotation=20, labelsize=7.5)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, 'ppt_fig4_results.png')
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print("Saved:", out_path)

# -------------------------------------------------------------
# Figure 5: Performance & Metrics Cards
# -------------------------------------------------------------
def make_fig5_performance():
    fig, ax = plt.subplots(figsize=(11.5, 3.3), facecolor='white')
    ax.axis('off')

    cards = [
        ("1.60 秒", "单日全量检测耗时", "18,620 颗在轨载荷端到端\n初筛 + SGP4 交叉校验", "#10375C"),
        ("O(1) 恒定", "时间算法复杂度", "基于状态库增量运算\n积累多年耗时绝不膨胀", "#0E8388"),
        ("58 MB", "内存峰值开销", "极轻量流式设计\n边缘嵌入式板卡零压力", "#2E4F4F"),
        ("7.9 MB", "单星状态库体积", "SQLite 紧凑持久化\n每颗星仅约 200 字节", "#D35400")
    ]

    for idx, (metric, title, desc, col) in enumerate(cards):
        x = 0.04 + idx * 0.245
        y = 0.50
        w, h = 0.215, 0.85

        card = patches.FancyBboxPatch((x, y - h/2), w, h, boxstyle="round,pad=0.03,rounding_size=0.04",
                                      facecolor='#F8FAFC', edgecolor=col, linewidth=2.0)
        ax.add_patch(card)

        # Big metric number
        ax.text(x + w/2, y + 0.20, metric, color=col, weight='bold', fontsize=16, ha='center', va='center')
        # Title
        ax.text(x + w/2, y + 0.04, title, color='#1A252C', weight='bold', fontsize=11, ha='center', va='center')
        # Line divider
        ax.plot([x + 0.02, x + w - 0.02], [y - 0.06, y - 0.06], color='#D0D7DE', lw=1)
        # Description
        ax.text(x + w/2, y - 0.22, desc, color='#57606A', fontsize=9.5, ha='center', va='center', linespacing=1.3)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, 'ppt_fig5_performance.png')
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print("Saved:", out_path)

if __name__ == '__main__':
    make_fig2_pipeline()
    make_fig3_methodology()
    make_fig4_results()
    make_fig5_performance()
