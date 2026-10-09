import json, glob
from sgp4.api import Satrec
import numpy as np

files = sorted(glob.glob('/home/jetson/TLE_Aggregation_Service/archive/raw/spacetrack/*/*.json'))
iss_tles = []
for f in files:
    with open(f) as fp:
        data = json.load(fp)
    for r in data:
        if r.get('NORAD_CAT_ID') == '25544':
            iss_tles.append(r)

seen = set()
unique_iss = []
for r in iss_tles:
    if r['EPOCH'] not in seen:
        seen.add(r['EPOCH'])
        unique_iss.append(r)
unique_iss.sort(key=lambda x: x['EPOCH'])

print(f"Total ISS epochs: {len(unique_iss)}")
# Index 8 (pre-reboost) and 9 (post-reboost)
r1 = unique_iss[8]
r2 = unique_iss[9]
print(f"Pre-reboost  Epoch (T1): {r1['EPOCH']}, a: {r1['SEMIMAJOR_AXIS']} km")
print(f"Post-reboost Epoch (T2): {r2['EPOCH']}, a: {r2['SEMIMAJOR_AXIS']} km")

# SGP4 propagation from T1 to T2
sat1 = Satrec.twoline2rv(r1['TLE_LINE1'], r1['TLE_LINE2'])
sat2 = Satrec.twoline2rv(r2['TLE_LINE1'], r2['TLE_LINE2'])

jd2, fr2 = sat2.jdsatepoch, sat2.jdsatepochF
e1, r_prop, v_prop = sat1.sgp4(jd2, fr2)
e2, r_true, v_true = sat2.sgp4(jd2, fr2)

dr = np.linalg.norm(np.array(r_true) - np.array(r_prop))
dv_vec = (np.array(v_true) - np.array(v_prop)) * 1000  # m/s
dv = np.linalg.norm(dv_vec)

v_unit = np.array(v_true) / np.linalg.norm(v_true)
h_unit = np.cross(r_true, v_true) / np.linalg.norm(np.cross(r_true, v_true))
r_unit = np.cross(v_unit, h_unit)

dv_T = np.dot(dv_vec, v_unit)
dv_N = np.dot(dv_vec, h_unit)
dv_R = np.dot(dv_vec, r_unit)

print(f"--> SGP4 位置残差 Δr: {dr:.2f} km")
print(f"--> SGP4 速度残差 (反演总冲量 ΔV): {dv:.2f} m/s")
print(f"--> RTN 分解冲量: 沿迹切向(In-Track)={dv_T:+.2f} m/s, 法向(Cross-Track)={dv_N:+.2f} m/s, 径向(Radial)={dv_R:+.2f} m/s")
