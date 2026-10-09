import pandas as pd

df = pd.read_csv('/home/jetson/TLE_Aggregation_Service/analysis_output/satellite_summary.csv')
candidates = [
    (25544, "LEO 载人航天器 (国际空间站 ISS)"),
    (48274, "LEO 载人航天器 (中国空间站 天和核心舱 CSS)"),
    (44713, "LEO 低轨巨型星座 (Starlink-1007)"),
    (42969, "SSO 太阳同步气象卫星 (风云三号D FY-3D)"),
    (40697, "SSO 太阳同步对地观测 (哨兵2A SENTINEL-2A)"),
    (40294, "MEO 导航卫星 (GPS NAVSTAR 70)"),
    (43001, "MEO 导航卫星 (北斗三号 M1 BEIDOU-3 M1)"),
    (32779, "GEO 地球同步中继卫星 (天链一号01 TIANLIAN 1-01)"),
    (44061, "GEO 静止通信卫星 (中星6C CHINASAT 6C)")
]

print(f"Total satellites in summary: {len(df)}")
for norad, desc in candidates:
    m = df[df['norad_cat_id'] == norad]
    if not m.empty:
        r = m.iloc[0]
        print(f"NORAD {norad:<5} | {r['object_name']:<20} | FirstDate: {r['first_seen_date']} | Epochs: {r['unique_epochs_count']:<2} | {desc}")
    else:
        print(f"NORAD {norad:<5} | NOT FOUND | {desc}")
