#!/usr/bin/env python3
"""
Generate a 5-slide widescreen PowerPoint presentation for the TLE Aggregation & Orbital Event Detection System.
Target: /home/lzk/TLE_Aggregation_Service/TLE_Orbital_Event_Detection_System.pptx
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_DIR = '/home/lzk/TLE_Aggregation_Service/analysis_output'
PPT_FILE = '/home/lzk/TLE_Aggregation_Service/TLE_Orbital_Event_Detection_System.pptx'

# Colors
C_NAVY_DARK = RGBColor(11, 25, 44)
C_PRIMARY = RGBColor(16, 55, 92)
C_SECONDARY = RGBColor(14, 131, 136)
C_ACCENT = RGBColor(235, 69, 95)
C_BG_LIGHT = RGBColor(248, 249, 250)
C_TEXT_DARK = RGBColor(44, 62, 80)
C_TEXT_MUTED = RGBColor(127, 140, 141)
C_WHITE = RGBColor(255, 255, 255)
C_CARD_BG = RGBColor(240, 244, 248)
C_BORDER = RGBColor(200, 214, 229)

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================
    # SLIDE 1: Title & Background
    # =========================================================
    s1 = prs.slides.add_slide(blank_layout)

    # Dark background
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY_DARK
    bg1.line.color.rgb = C_NAVY_DARK

    # Top category tag
    tb_tag = s1.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(0.4))
    p_tag = tb_tag.text_frame.paragraphs[0]
    p_tag.text = "SPACE SITUATIONAL AWARENESS (SSA)  |  空间态势感知与自主监测"
    p_tag.font.size = Pt(11)
    p_tag.font.bold = True
    p_tag.font.color.rgb = C_SECONDARY

    # Title
    tb_title = s1.shapes.add_textbox(Inches(0.8), Inches(0.9), Inches(11.7), Inches(1.1))
    p_title = tb_title.text_frame.paragraphs[0]
    p_title.text = "空间目标轨道态势感知与自动化机动检测系统"
    p_title.font.size = Pt(28)
    p_title.font.bold = True
    p_title.font.color.rgb = C_WHITE

    # Subtitle
    tb_sub = s1.shapes.add_textbox(Inches(0.8), Inches(1.85), Inches(11.7), Inches(0.6))
    p_sub = tb_sub.text_frame.paragraphs[0]
    p_sub.text = "基于海量低频 TLE 轨道要素与空间天气驱动的高置信度、毫秒级增量事件感知方案"
    p_sub.font.size = Pt(14)
    p_sub.font.color.rgb = RGBColor(180, 200, 220)

    # 3 Background Cards
    bg_cards = [
        ("01 / 空间资产与威胁激增",
         "低轨星座密集组网与自主变轨",
         "• 全球在轨活跃载荷超 1.8 万颗，低推力机动频繁\n• 碰撞预警与空间防御对自主态势感知提出紧迫需求\n• 传统人工轮巡或静态监视模式在海量目标下难以为继"),
        ("02 / 监测数据特征与痛点",
         "海量低频快照伴随高噪声干扰",
         "• 依赖 Space-Track 每日全量 TLE/OMM 数据源（日均 3.2万条）\n• 均元拟合噪声与地面观测坏点极易引发严重误报\n• 高层大气阻力自然衰减与主动变轨信号交织耦合"),
        ("03 / 项目工程破局点",
         "无人值守闭环与自适应感知",
         "• 物理去趋势与 SGP4 交叉验证彻底消灭虚警\n• 融合空间天气解耦单星姿态机动与高层大气暴\n• 构建 O(1) 增量状态库，实现秒级响应与边缘部署")
    ]

    for idx, (badge, heading, body) in enumerate(bg_cards):
        x = Inches(0.8 + idx * 3.95)
        y = Inches(2.7)
        w = Inches(3.75)
        h = Inches(4.1)

        card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(20, 40, 68)
        card.line.color.rgb = C_SECONDARY
        card.line.width = Pt(1.5)

        tb = s1.shapes.add_textbox(x + Inches(0.15), y + Inches(0.15), w - Inches(0.3), h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = badge
        p0.font.size = Pt(11)
        p0.font.bold = True
        p0.font.color.rgb = C_SECONDARY

        p1 = tf.add_paragraph()
        p1.text = heading
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = C_WHITE
        p1.space_before = Pt(8)
        p1.space_after = Pt(14)

        p2 = tf.add_paragraph()
        p2.text = body
        p2.font.size = Pt(11)
        p2.font.color.rgb = RGBColor(200, 215, 230)
        p2.line_spacing = 1.3

    # =========================================================
    # SLIDE 2: End-to-End Pipeline
    # =========================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "02 / 业务流程", "全链路闭环业务流程", "从高层空间天气获取、TLE原子归档到增量态势感知的每日全自动闭环")

    img_pipeline = os.path.join(OUTPUT_DIR, 'ppt_fig2_pipeline.png')
    if os.path.exists(img_pipeline):
        s2.shapes.add_picture(img_pipeline, Inches(0.8), Inches(1.52), width=Inches(11.73))

    add_three_summary_cards(s2, Inches(5.05), [
        ("全自动定时触发", "02:00 同步空间天气参数，03:20 执行 TLE 快照安全下载，03:35 增量检测入库，全流程零人工干预。"),
        ("原子性安全归档", "基于临时文件替换与 SQLite 文件锁机制，保障在边缘复杂网络环境下数据下载无脏读、无中断。"),
        ("多维成果自动发布", "自动生成 Markdown 态势简报、结构化 CSV/JSON 事件日志、以及 Plotly 交互式 6 根数可视化看板。")
    ])

    # =========================================================
    # SLIDE 3: Methodology & Thinking
    # =========================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "03 / 方法与思路", "核心方法与动力学算法思路", "物理去趋势初筛 + 双历元 SGP4 交叉外推验证 + 空间环境动力学解耦")

    img_method = os.path.join(OUTPUT_DIR, 'ppt_fig3_methodology.png')
    if os.path.exists(img_method):
        s3.shapes.add_picture(img_method, Inches(0.8), Inches(1.52), width=Inches(11.73))

    add_three_summary_cards(s3, Inches(5.05), [
        ("阶段一：自适应残差初筛", "剥离高层气阻自然衰减与 J2 进动，在线递推学习单星测轨噪声底 σ_a，实现千星千面自适应 3.5σ 门限，杜绝人工配置阈值。"),
        ("阶段二：SGP4 冲量反演", "基于 C++ 极速 SGP4 模型外推三维空间残差 Δr，在 RTN 轨道坐标系反演切向与法向冲量 ΔV，三历元一致性确认消灭地面拟合坏点。"),
        ("空间天气环境智能解耦", "自动关联太阳通量 F10.7 与地磁指数 Ap。Ap≥25 时归因为高层热层膨胀事件；空间天气平静时归因为航天器自身姿态机动。")
    ])

    # =========================================================
    # SLIDE 4: Results & Real Cases
    # =========================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "04 / 结果与发现", "关键检测结果与典型案例", "全量 1.8 万颗在轨载荷 20 天时序扫描与空间站真实变轨实测反演")

    img_results = os.path.join(OUTPUT_DIR, 'ppt_fig4_results.png')
    if os.path.exists(img_results):
        s4.shapes.add_picture(img_results, Inches(0.8), Inches(1.52), width=Inches(11.73))

    add_three_summary_cards(s4, Inches(5.05), [
        ("全域事件宏观分布", "20 天内对 18,741 颗在轨载荷完成全量扫描，捕获 23,161 次事件（主动抬轨 13,073 起、降轨 4,074 起、GEO 定点保持 2,151 起）。"),
        ("空间站真实抬轨精准反演", "实测捕获国际空间站 (ISS) 抬轨机动（Δa = +1.827 km, Δv_T = +0.63 m/s）与中国空间站 (CSS) 天和舱维持抬轨（Δa = +0.621 km）。"),
        ("强地磁暴阻力脉冲捕获", "精准捕获 09-25（Ap=27）与 10-04（Ap=48 强地磁暴）期间数百颗低轨卫星 BSTAR 阻力系数的集体跃升，准确完成环境归因。")
    ])

    # =========================================================
    # SLIDE 5: Performance & Engineering Benefits
    # =========================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "05 / 性能与效益", "极致性能与工程效益", "基于 SQLite 状态库的 O(1) 增量检测引擎，彻底解决历史数据累积性能雪崩")

    img_perf = os.path.join(OUTPUT_DIR, 'ppt_fig5_performance.png')
    if os.path.exists(img_perf):
        s5.shapes.add_picture(img_perf, Inches(0.8), Inches(1.52), width=Inches(11.73))

    add_three_summary_cards(s5, Inches(5.05), [
        ("单日检测极速：1.60 秒", "在 ARM 架构边缘设备（Jetson nano72）上，端到端完成 18,620 颗在轨载荷的单日全量排查与入库仅需 1.6 秒。"),
        ("复杂度跃迁：恒定 O(1)", "摒弃全量历史重算，维护紧凑 SQLite 单星状态库（7.9 MB），历史数据累积 5 年、10 年，每日增量耗时绝不膨胀。"),
        ("边缘部署效益：内存 < 60 MB", "流式处理内存峰值仅 58 MB，轻量嵌入式板卡零压力运行，与 Linux Crontab 无缝嵌合，打造开箱即用的工业级态势感知节点。")
    ])

    prs.save(PPT_FILE)
    print("Successfully generated presentation:", PPT_FILE)

def add_header(slide, tag_text, title_text, sub_text):
    # Top Tag
    tb_tag = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.3))
    p_tag = tb_tag.text_frame.paragraphs[0]
    p_tag.text = tag_text
    p_tag.font.size = Pt(11)
    p_tag.font.bold = True
    p_tag.font.color.rgb = C_SECONDARY

    # Title
    tb_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(11.7), Inches(0.6))
    p_title = tb_title.text_frame.paragraphs[0]
    p_title.text = title_text
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = C_PRIMARY

    # Subtitle
    tb_sub = slide.shapes.add_textbox(Inches(0.8), Inches(1.15), Inches(11.7), Inches(0.45))
    p_sub = tb_sub.text_frame.paragraphs[0]
    p_sub.text = sub_text
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = C_TEXT_MUTED

def add_three_summary_cards(slide, y_pos, card_data):
    w = Inches(3.75)
    h = Inches(1.65)
    for idx, (title, text) in enumerate(card_data):
        x = Inches(0.8 + idx * 3.95)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y_pos, w, h)
        card.fill.solid()
        card.fill.fore_color.rgb = C_CARD_BG
        card.line.color.rgb = C_BORDER
        card.line.width = Pt(1.0)

        tb = slide.shapes.add_textbox(x + Inches(0.12), y_pos + Inches(0.10), w - Inches(0.24), h - Inches(0.20))
        tf = tb.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.size = Pt(12)
        p0.font.bold = True
        p0.font.color.rgb = C_PRIMARY

        p1 = tf.add_paragraph()
        p1.text = text
        p1.font.size = Pt(10)
        p1.font.color.rgb = C_TEXT_DARK
        p1.space_before = Pt(4)
        p1.line_spacing = 1.25

if __name__ == '__main__':
    create_deck()
