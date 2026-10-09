#!/usr/bin/env python3
"""
Generate 轨道计算能力-V4.pptx by fusing TLE Aggregation and SSA Event Detection
into 2 dedicated slides appended before the final closing slide of 轨道计算能力-V3.pptx.

Design and color palette completely identical to 轨道计算能力-V3.pptx:
  - Canvas: 24384000 x 13716000 (16:9 Widescreen)
  - Dark background: #03080C
  - Title color: #EADBBB (Warm Cream Gold), 60pt
  - Subtitle color: #A8B0B5 (Slate Blue), 31.5pt
  - Big metric number: #90E6F0 (Neon Cyan), 78-90pt
  - Value labels: #F4F5F3 (Off-white), 31.5pt
  - High-res seamless dark illustrations
  - Dark comparison tables matching Slide 5
  - Footers with test scenario, 具元天基 branding, and sequential page numbers (11, 12).
"""

import os
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

SRC_PPT = '/home/lzk/文档/斫月/文档/轨道计算能力-V3.pptx'
DST_PPT = '/home/lzk/文档/斫月/文档/轨道计算能力-V4.pptx'
OUTPUT_DIR = '/home/lzk/TLE_Aggregation_Service/analysis_output'

FIG1_PATH = os.path.join(OUTPUT_DIR, 'v4_fig1_tle_pipeline.png')
FIG2_PATH = os.path.join(OUTPUT_DIR, 'v4_fig2_ssa_engine.png')

# Color Constants
C_BG = RGBColor(0x03, 0x08, 0x0C)
C_TITLE = RGBColor(0xEA, 0xDB, 0xBB)
C_SUBTITLE = RGBColor(0xA8, 0xB0, 0xB5)
C_METRIC_NUM = RGBColor(0x90, 0xE6, 0xF0)
C_TEXT_WHITE = RGBColor(0xF4, 0xF5, 0xF3)
C_FOOTER_LINE = RGBColor(0x21, 0x2C, 0x33)
C_TABLE_HEADER_BG = RGBColor(0x0C, 0x16, 0x20)
C_TABLE_DATA_BG = RGBColor(0x03, 0x08, 0x0C)

FONT_FAMILY = "Source Han Sans SC"

def add_header(slide, title_text, subtitle_text):
    # Main Title
    tx_title = slide.shapes.add_textbox(1219200, 952500, 21945600, 1257300)
    tf = tx_title.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.name = FONT_FAMILY
    p.font.size = Pt(60)
    p.font.bold = True
    p.font.color.rgb = C_TITLE

    # Subtitle
    tx_sub = slide.shapes.add_textbox(1219200, 2362200, 21945600, 990600)
    tf_sub = tx_sub.text_frame
    tf_sub.word_wrap = True
    tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
    p_sub = tf_sub.paragraphs[0]
    p_sub.text = subtitle_text
    p_sub.font.name = FONT_FAMILY
    p_sub.font.size = Pt(31.5)
    p_sub.font.color.rgb = C_SUBTITLE

def add_footer(slide, scenario_text, page_num_str):
    # Divider line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 1219200, 11811000, 21945600, 25400)
    line.fill.solid()
    line.fill.fore_color.rgb = C_FOOTER_LINE
    line.line.color.rgb = C_FOOTER_LINE
    line.line.width = 0

    # Scenario text
    tx_scen = slide.shapes.add_textbox(1219200, 12096750, 21945600, 762000)
    tf = tx_scen.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = scenario_text
    p.font.name = FONT_FAMILY
    p.font.size = Pt(22.5)
    p.font.color.rgb = C_SUBTITLE

    # Brand text
    tx_brand = slide.shapes.add_textbox(1219200, 12992100, 5715000, 476250)
    tf_b = tx_brand.text_frame
    tf_b.margin_left = tf_b.margin_top = tf_b.margin_right = tf_b.margin_bottom = 0
    p_b = tf_b.paragraphs[0]
    p_b.text = "具元天基"
    p_b.font.name = FONT_FAMILY
    p_b.font.size = Pt(21)
    p_b.font.color.rgb = C_SUBTITLE

    # Page number
    tx_page = slide.shapes.add_textbox(22383750, 12992100, 857250, 476250)
    tf_p = tx_page.text_frame
    tf_p.margin_left = tf_p.margin_top = tf_p.margin_right = tf_p.margin_bottom = 0
    p_p = tf_p.paragraphs[0]
    p_p.text = page_num_str
    p_p.font.name = FONT_FAMILY
    p_p.font.size = Pt(21)
    p_p.font.color.rgb = C_SUBTITLE

def add_metric_block(slide, top_y, num_str, label_str, num_pt=90):
    tx_num = slide.shapes.add_textbox(1219200, top_y, 7800000, 1150000)
    tf = tx_num.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = num_str
    p.font.name = FONT_FAMILY
    p.font.size = Pt(num_pt)
    p.font.bold = True
    p.font.color.rgb = C_METRIC_NUM

    tx_lbl = slide.shapes.add_textbox(1219200, top_y + 1180000, 7800000, 500000)
    tf_l = tx_lbl.text_frame
    tf_l.word_wrap = True
    tf_l.margin_left = tf_l.margin_top = tf_l.margin_right = tf_l.margin_bottom = 0
    p_l = tf_l.paragraphs[0]
    p_l.text = label_str
    p_l.font.name = FONT_FAMILY
    p_l.font.size = Pt(31.5)
    p_l.font.color.rgb = C_TEXT_WHITE

def add_narrative_points(slide, top_y, lines):
    tx = slide.shapes.add_textbox(1219200, top_y, 7800000, 3200000)
    tf = tx.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    for idx, line_text in enumerate(lines):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.text = line_text
        p.font.name = FONT_FAMILY
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_WHITE
        p.space_after = Pt(14)

def add_dark_table(slide, left, top, width, height, col_widths, headers, data_rows):
    rows_count = 1 + len(data_rows)
    cols_count = len(headers)
    table_shape = slide.shapes.add_table(rows_count, cols_count, left, top, width, height)
    table = table_shape.table

    for i, w in enumerate(col_widths):
        table.columns[i].width = w

    # Header Row
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_TABLE_HEADER_BG
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.name = FONT_FAMILY
        p.font.size = Pt(19)
        p.font.bold = True
        p.font.color.rgb = C_TITLE

    # Data Rows
    for i, row in enumerate(data_rows):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_TABLE_DATA_BG
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = FONT_FAMILY
            p.font.size = Pt(18)
            p.font.bold = False
            p.font.color.rgb = C_TEXT_WHITE

def build_v4():
    print(f"Loading base presentation: {SRC_PPT}")
    prs = Presentation(SRC_PPT)
    blank_layout = prs.slide_layouts[1]

    # -------------------------------------------------------------
    # Slide 13 (Page 11): TLE 聚合与空间环境服务
    # -------------------------------------------------------------
    s13 = prs.slides.add_slide(blank_layout)
    s13.background.fill.solid()
    s13.background.fill.fore_color.rgb = C_BG

    add_header(s13, "TLE 聚合与空间环境服务", "全球在轨目标高频增量聚合，天级自适应空间天气与时序状态底座")
    add_metric_block(s13, 3600000, "3.2 万条/日", "日均 TLE 增量纳管与原子归档", num_pt=88)
    add_metric_block(s13, 5600000, "2,500 万+ 条", "全历史在轨全周期时序状态库", num_pt=78)
    add_narrative_points(s13, 7600000, [
        "全球在轨有效载荷全量纳管",
        "NOAA / CelesTrak 空间天气同步",
        "单星历元演化库支撑下游毫秒级外推"
    ])

    # Right Top Image
    s13.shapes.add_picture(FIG1_PATH, 9528810, 2969895, 13635990, 6297295)

    # Right Bottom Table
    table_headers_13 = ["功能维度", "核心机制与支撑协议", "业务指标与量化产出"]
    table_rows_13 = [
        ["全网 TLE 聚合", "Space-Track GP API + 原子增量去重", "4,375 颗在轨载荷全纳管，零单点断流"],
        ["空间天气同步", "CelesTrak / NOAA SWPC 连续时序", "F10.7、Kp、Ap 毫秒级空间天气关联"]
    ]
    add_dark_table(s13, 9528810, 9450070, 13635990, 1802765,
                   [3200000, 4800000, 5635990], table_headers_13, table_rows_13)

    add_footer(s13, "测试场景：全球在轨 PAYLOAD 载荷全量纳管、空间天气实测连续日更、全历史 TLE 增量基准库。", "11")

    # -------------------------------------------------------------
    # Slide 14 (Page 12): 在轨态势感知与机动检测
    # -------------------------------------------------------------
    s14 = prs.slides.add_slide(blank_layout)
    s14.background.fill.solid()
    s14.background.fill.fore_color.rgb = C_BG

    add_header(s14, "在轨态势感知与机动检测", "两阶段高置信度自适应检测架构，RTN 动力学冲量反演与空间环境智能解耦")
    add_metric_block(s14, 3600000, "23,157 起", "全网在轨事件自动化反演与分类识别", num_pt=88)
    add_metric_block(s14, 5600000, "28.6 s", "单日全网在轨载荷全量增量检测耗时", num_pt=78)
    add_narrative_points(s14, 7600000, [
        "98.7% 常态背景初筛过滤 (3.5σ 自适应门限)",
        "RTN 动力学三轴冲量解算辨识变轨意图",
        "地磁暴/高层大气膨胀全自动环境解耦"
    ])

    # Right Top Image
    s14.shapes.add_picture(FIG2_PATH, 9528810, 2969895, 13635990, 6297295)

    # Right Bottom Table
    table_headers_14 = ["检测阶段 / 方法", "核心动力学与环境算法", "量化效能与验证依据"]
    table_rows_14 = [
        ["阶段一：自适应初筛", "气阻/J2 剥离 + 递推单星噪声底 σ_a", "30 秒内筛除 98.7% 平稳目标，杜绝误报"],
        ["阶段二：冲量反演", "SGP4 双历元外推残差 + RTN 反演", "解算切/法向 ΔV，三历元一致性剔除坏点"]
    ]
    add_dark_table(s14, 9528810, 9450070, 13635990, 1802765,
                   [3200000, 4800000, 5635990], table_headers_14, table_rows_14)

    add_footer(s14, "测试场景：4,375 颗在轨有效载荷全量筛查、双历元交叉外推验证、SGP4 毫秒级 C++ 极速引擎复核。", "12")

    # -------------------------------------------------------------
    # Reorder slides: Move original closing slide (Slide 13) to position 15
    # -------------------------------------------------------------
    sld_lst = prs.slides._sldIdLst
    closing_elem = sld_lst[12]
    sld_lst.remove(closing_elem)
    sld_lst.append(closing_elem)
    print(f"Reordered slides so closing slide is at index {len(sld_lst)-1}")

    prs.save(DST_PPT)
    print(f"Successfully saved V4 presentation: {DST_PPT}")

if __name__ == '__main__':
    build_v4()
