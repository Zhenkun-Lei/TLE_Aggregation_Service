#!/usr/bin/env python3
"""
Step 2: Extract time series of orbital elements for representative satellites across different orbit types,
and generate interactive Plotly HTML dashboards.

Target Satellites:
  - 25544: ISS (ZARYA)           [LEO 载人航天器 - 国际空间站]
  - 48274: CSS (TIANHE-1)        [LEO 载人航天器 - 中国空间站天和核心舱]
  - 44718: STARLINK-1012         [LEO 巨型星座 - Starlink]
  - 40697: SENTINEL 2A           [SSO 太阳同步轨道 - 哨兵2A]
  - 43001: BEIDOU 3M1            [MEO 导航卫星 - 北斗三号M1]
  - 32779: TIANLIAN 1-01         [GEO 地球同步中继卫星 - 天链一号01]
  - 7392:  MOLNIYA 1-S           [HEO 高椭圆轨道 - 闪电1-S]
"""

import os
import glob
import json
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RAW_DIR = '/home/jetson/TLE_Aggregation_Service/archive/raw/spacetrack'
OUTPUT_DIR = '/home/jetson/TLE_Aggregation_Service/analysis_output'

TARGET_SATS = {
    25544: {"name": "ISS (ZARYA)", "orbit_type": "LEO 载人空间站", "desc": "低地轨道，受微气阻明显衰减与定期轨道抬升抬高"},
    48274: {"name": "CSS (TIANHE-1)", "orbit_type": "LEO 载人空间站 (中国)", "desc": "中国空间站天和核心舱，轨道高度约380-400km"},
    44718: {"name": "STARLINK-1012", "orbit_type": "LEO 宽带巨型星座", "desc": "低轨密集星座，具备自主离子电推变轨/维持能力"},
    40697: {"name": "SENTINEL 2A", "orbit_type": "SSO 太阳同步轨道", "desc": "欧洲哨兵2A对地观测卫星，高度约786km，高倾角98.5°"},
    43001: {"name": "BEIDOU 3M1", "orbit_type": "MEO 中圆导航轨道", "desc": "北斗三号中圆地球轨道导航卫星，高度约21500km"},
    32779: {"name": "TIANLIAN 1-01", "orbit_type": "GEO 地球同步轨道", "desc": "天链一号中继卫星，高度约35786km，倾角接近0°"},
    7392:  {"name": "MOLNIYA 1-S", "orbit_type": "HEO 高椭圆轨道", "desc": "大偏心率轨道，近地点远地点落差极大，倾角约63.4°"}
}

def extract_target_timeseries():
    date_dirs = sorted([d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d))])
    records_by_sat = {sat_id: [] for sat_id in TARGET_SATS}

    t0 = time.time()
    for d in date_dirs:
        dir_path = os.path.join(RAW_DIR, d)
        for jf in sorted(glob.glob(os.path.join(dir_path, '*.json'))):
            with open(jf, 'r', encoding='utf-8') as f:
                records = json.load(f)
            for r in records:
                try:
                    sat_id = int(r.get('NORAD_CAT_ID'))
                except (ValueError, TypeError):
                    continue
                if sat_id in records_by_sat:
                    records_by_sat[sat_id].append({
                        'norad_cat_id': sat_id,
                        'file_date': d,
                        'epoch': r.get('EPOCH'),
                        'semimajor_axis': float(r.get('SEMIMAJOR_AXIS', 0)),
                        'eccentricity': float(r.get('ECCENTRICITY', 0)),
                        'inclination': float(r.get('INCLINATION', 0)),
                        'ra_of_asc_node': float(r.get('RA_OF_ASC_NODE', 0)),
                        'arg_of_pericenter': float(r.get('ARG_OF_PERICENTER', 0)),
                        'mean_anomaly': float(r.get('MEAN_ANOMALY', 0)),
                        'mean_motion': float(r.get('MEAN_MOTION', 0)),
                        'period': float(r.get('PERIOD', 0)),
                        'apoapsis': float(r.get('APOAPSIS', 0)),
                        'periapsis': float(r.get('PERIAPSIS', 0)),
                        'bstar': float(r.get('BSTAR', 0))
                    })
    print(f"Extracted records in {time.time()-t0:.2f}s.")

    # Convert to DataFrames and deduplicate by epoch
    dfs = {}
    for sat_id, recs in records_by_sat.items():
        if recs:
            df = pd.DataFrame(recs)
            df['epoch_dt'] = pd.to_datetime(df['epoch'])
            # Deduplicate by epoch, keep last
            df = df.drop_duplicates(subset=['epoch']).sort_values('epoch_dt').reset_index(drop=True)
            dfs[sat_id] = df
            print(f"Satellite {sat_id} ({TARGET_SATS[sat_id]['name']}): {len(df)} unique epoch records")
        else:
            print(f"Satellite {sat_id}: No records found!")
    return dfs

def create_single_sat_figure(sat_id, df, meta):
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "1. 半长轴 a (km) 与 近地/远地点高度",
            "2. 偏心率 e (Eccentricity)",
            "3. 轨道倾角 i (Inclination, °)",
            "4. 升交点赤经 RAAN Ω (°)",
            "5. 近地点幅角 ω (°)",
            "6. BSTAR 阻力项 / 平均运动 n (rev/day)"
        ),
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )

    # 1. Semi-major axis & perigee/apogee
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['semimajor_axis'],
        mode='lines+markers', name='半长轴 a (km)',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=5),
        hovertemplate="Epoch: %{x}<br>a: %{y:.3f} km<extra></extra>"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['apoapsis'],
        mode='lines', name='远地点高度 (km)',
        line=dict(color='#aec7e8', width=1, dash='dot'),
        hovertemplate="Epoch: %{x}<br>远地点: %{y:.2f} km<extra></extra>"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['periapsis'],
        mode='lines', name='近地点高度 (km)',
        line=dict(color='#ffbb78', width=1, dash='dot'),
        hovertemplate="Epoch: %{x}<br>近地点: %{y:.2f} km<extra></extra>"
    ), row=1, col=1)

    # 2. Eccentricity
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['eccentricity'],
        mode='lines+markers', name='偏心率 e',
        line=dict(color='#ff7f0e', width=2),
        marker=dict(size=5),
        hovertemplate="Epoch: %{x}<br>e: %{y:.7f}<extra></extra>"
    ), row=1, col=2)

    # 3. Inclination
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['inclination'],
        mode='lines+markers', name='轨道倾角 i (°)',
        line=dict(color='#2ca02c', width=2),
        marker=dict(size=5),
        hovertemplate="Epoch: %{x}<br>i: %{y:.4f}°<extra></extra>"
    ), row=2, col=1)

    # 4. RAAN
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['ra_of_asc_node'],
        mode='lines+markers', name='升交点赤经 RAAN (°)',
        line=dict(color='#d62728', width=2),
        marker=dict(size=5),
        hovertemplate="Epoch: %{x}<br>RAAN: %{y:.4f}°<extra></extra>"
    ), row=2, col=2)

    # 5. Arg of Perigee
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['arg_of_pericenter'],
        mode='lines+markers', name='近地点幅角 ω (°)',
        line=dict(color='#9467bd', width=2),
        marker=dict(size=5),
        hovertemplate="Epoch: %{x}<br>ω: %{y:.4f}°<extra></extra>"
    ), row=3, col=1)

    # 6. BSTAR & Mean Motion
    fig.add_trace(go.Scatter(
        x=df['epoch_dt'], y=df['bstar'],
        mode='lines+markers', name='BSTAR 阻力项',
        line=dict(color='#8c564b', width=2),
        marker=dict(size=5),
        hovertemplate="Epoch: %{x}<br>BSTAR: %{y:.3e}<extra></extra>"
    ), row=3, col=2)

    # Update axis labels
    fig.update_xaxes(title_text="历元时间 (UTC)", showgrid=True, gridcolor='#eaeaea')
    fig.update_yaxes(showgrid=True, gridcolor='#eaeaea')
    fig.update_yaxes(title_text="距离 (km)", row=1, col=1)
    fig.update_yaxes(title_text="无量纲", row=1, col=2)
    fig.update_yaxes(title_text="角度 (°)", row=2, col=1)
    fig.update_yaxes(title_text="角度 (°)", row=2, col=2)
    fig.update_yaxes(title_text="角度 (°)", row=3, col=1)
    fig.update_yaxes(title_text="阻力系数 (1/Earth radii)", row=3, col=2)

    title_html = (
        f"<b>{meta['name']} (NORAD: {sat_id})</b> 轨道元素时间演化曲线<br>"
        f"<span style='font-size: 13px; color: #555;'>轨道类型: {meta['orbit_type']} | {meta['desc']} | 数据跨度: 2026-09-20 ~ 2026-10-09</span>"
    )

    fig.update_layout(
        title=dict(text=title_html, x=0.03, y=0.98),
        height=950,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def create_integrated_dashboard(dfs):
    """
    Creates a single unified interactive HTML dashboard containing a dropdown selector
    to switch smoothly between all 7 target satellites.
    """
    sat_list = list(dfs.keys())
    first_sat = sat_list[0]

    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            "1. 半长轴 a (km) 与 近地点/远地点高度",
            "2. 偏心率 e (Eccentricity)",
            "3. 轨道倾角 i (Inclination, °)",
            "4. 升交点赤经 RAAN Ω (°)",
            "5. 近地点幅角 ω (°)",
            "6. BSTAR 阻力项 / 轨道摄动"
        ),
        vertical_spacing=0.10,
        horizontal_spacing=0.08
    )

    traces_per_sat = 8  # 3 in subplot 1, 1 in subplots 2-6

    # Add all traces for all satellites
    for sat_id in sat_list:
        df = dfs[sat_id]
        meta = TARGET_SATS[sat_id]
        visible = (sat_id == first_sat)

        # 1.1 Semi-major axis
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['semimajor_axis'],
            mode='lines+markers', name=f"{meta['name']} - 半长轴 a",
            line=dict(color='#1f77b4', width=2), marker=dict(size=5),
            visible=visible, hovertemplate="Epoch: %{x}<br>a: %{y:.3f} km<extra></extra>"
        ), row=1, col=1)

        # 1.2 Apoapsis
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['apoapsis'],
            mode='lines', name=f"{meta['name']} - 远地点",
            line=dict(color='#aec7e8', width=1, dash='dot'),
            visible=visible, hovertemplate="Epoch: %{x}<br>远地点: %{y:.2f} km<extra></extra>"
        ), row=1, col=1)

        # 1.3 Periapsis
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['periapsis'],
            mode='lines', name=f"{meta['name']} - 近地点",
            line=dict(color='#ffbb78', width=1, dash='dot'),
            visible=visible, hovertemplate="Epoch: %{x}<br>近地点: %{y:.2f} km<extra></extra>"
        ), row=1, col=1)

        # 2. Eccentricity
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['eccentricity'],
            mode='lines+markers', name=f"{meta['name']} - 偏心率 e",
            line=dict(color='#ff7f0e', width=2), marker=dict(size=5),
            visible=visible, hovertemplate="Epoch: %{x}<br>e: %{y:.7f}<extra></extra>"
        ), row=1, col=2)

        # 3. Inclination
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['inclination'],
            mode='lines+markers', name=f"{meta['name']} - 轨道倾角 i",
            line=dict(color='#2ca02c', width=2), marker=dict(size=5),
            visible=visible, hovertemplate="Epoch: %{x}<br>i: %{y:.4f}°<extra></extra>"
        ), row=2, col=1)

        # 4. RAAN
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['ra_of_asc_node'],
            mode='lines+markers', name=f"{meta['name']} - 升交点赤经 RAAN",
            line=dict(color='#d62728', width=2), marker=dict(size=5),
            visible=visible, hovertemplate="Epoch: %{x}<br>RAAN: %{y:.4f}°<extra></extra>"
        ), row=2, col=2)

        # 5. Arg of Perigee
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['arg_of_pericenter'],
            mode='lines+markers', name=f"{meta['name']} - 近地点幅角 ω",
            line=dict(color='#9467bd', width=2), marker=dict(size=5),
            visible=visible, hovertemplate="Epoch: %{x}<br>ω: %{y:.4f}°<extra></extra>"
        ), row=3, col=1)

        # 6. BSTAR
        fig.add_trace(go.Scatter(
            x=df['epoch_dt'], y=df['bstar'],
            mode='lines+markers', name=f"{meta['name']} - BSTAR",
            line=dict(color='#8c564b', width=2), marker=dict(size=5),
            visible=visible, hovertemplate="Epoch: %{x}<br>BSTAR: %{y:.3e}<extra></extra>"
        ), row=3, col=2)

    # Build buttons for dropdown menu
    buttons = []
    for i, sat_id in enumerate(sat_list):
        meta = TARGET_SATS[sat_id]
        visibility = [False] * (len(sat_list) * traces_per_sat)
        for j in range(traces_per_sat):
            visibility[i * traces_per_sat + j] = True

        title_text = (
            f"<b>{meta['name']} (NORAD: {sat_id})</b> 轨道元素时间演化曲线<br>"
            f"<span style='font-size: 13px; color: #555;'>轨道类型: {meta['orbit_type']} | {meta['desc']}</span>"
        )

        buttons.append(dict(
            label=f"{meta['name']} [{meta['orbit_type']}]",
            method="update",
            args=[
                {"visible": visibility},
                {"title": {"text": title_text, "x": 0.03, "y": 0.98}}
            ]
        ))

    # Update axis styling
    fig.update_xaxes(title_text="历元时间 (UTC)", showgrid=True, gridcolor='#eaeaea')
    fig.update_yaxes(showgrid=True, gridcolor='#eaeaea')
    fig.update_yaxes(title_text="距离 (km)", row=1, col=1)
    fig.update_yaxes(title_text="无量纲", row=1, col=2)
    fig.update_yaxes(title_text="角度 (°)", row=2, col=1)
    fig.update_yaxes(title_text="角度 (°)", row=2, col=2)
    fig.update_yaxes(title_text="角度 (°)", row=3, col=1)
    fig.update_yaxes(title_text="阻力系数 (1/Earth radii)", row=3, col=2)

    initial_meta = TARGET_SATS[first_sat]
    fig.update_layout(
        title=dict(
            text=(
                f"<b>{initial_meta['name']} (NORAD: {first_sat})</b> 轨道元素时间演化曲线<br>"
                f"<span style='font-size: 13px; color: #555;'>轨道类型: {initial_meta['orbit_type']} | {initial_meta['desc']}</span>"
            ),
            x=0.03, y=0.98
        ),
        updatemenus=[dict(
            buttons=buttons,
            direction="down",
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.98,
            xanchor="right",
            y=1.12,
            yanchor="top"
        )],
        height=980,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0.01)
    )

    return fig

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dfs = extract_target_timeseries()

    # Save target satellites time series CSV for easy access
    for sat_id, df in dfs.items():
        csv_file = os.path.join(OUTPUT_DIR, f"timeseries_sat_{sat_id}.csv")
        df.drop(columns=['epoch_dt']).to_csv(csv_file, index=False)
        print(f"Saved timeseries CSV to {csv_file}")

        # Generate individual HTML
        meta = TARGET_SATS[sat_id]
        single_fig = create_single_sat_figure(sat_id, df, meta)
        single_html = os.path.join(OUTPUT_DIR, f"orbit_evolution_sat_{sat_id}_{meta['name'].replace(' ', '_').replace('(', '').replace(')', '')}.html")
        single_fig.write_html(single_html, include_plotlyjs='cdn')
        print(f"Saved single HTML to {single_html}")

    # Generate integrated master dashboard HTML
    integrated_fig = create_integrated_dashboard(dfs)
    dashboard_html = os.path.join(OUTPUT_DIR, "orbit_elements_dashboard.html")
    integrated_fig.write_html(dashboard_html, include_plotlyjs='cdn')
    print(f"\nSaved integrated dashboard to {dashboard_html}")

if __name__ == '__main__':
    main()
