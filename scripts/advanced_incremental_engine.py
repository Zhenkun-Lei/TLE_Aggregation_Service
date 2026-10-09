#!/usr/bin/env python3
"""
Advanced Production Incremental Engine with Full State Baseline & Online Learning:
- State Store: SQLite (/home/jetson/TLE_Aggregation_Service/analysis_output/satellite_state.db)
- Tracks:
    1. Instantaneous State (last_epoch, last_a, last_i, last_tle1, last_tle2)
    2. Differential & Steady Baseline (stable_baseline_a, stable_baseline_epoch)
    3. Background Statistical Baseline (baseline_decay_rate, baseline_bstar_median, noise_sigma_a, geo_slot_longitude)
    4. Lifecycle State Machine (operational_status, pending_event, sample_count)
- Self-learning:
    Online Welford / EMA recursive estimation of per-satellite noise floor sigma_a and decay rate.
    Adaptive 3.5-Sigma per-satellite threshold gating.
"""

import os
import sys
import glob
import json
import time
import math
import sqlite3
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from sgp4.api import Satrec

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW_DIR = os.path.join(BASE_DIR, 'archive/raw/spacetrack')
OUTPUT_DIR = os.path.join(BASE_DIR, 'analysis_output')
DB_PATH = os.path.join(OUTPUT_DIR, 'satellite_state.db')
SW_FILE = os.path.join(OUTPUT_DIR, 'SW-Last5Years.txt')
SUMMARY_CSV = os.path.join(OUTPUT_DIR, 'satellite_summary.csv')

def init_advanced_db(db_path, reset=False):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if reset:
        cur.execute("DROP TABLE IF EXISTS sat_state")
        cur.execute("DROP TABLE IF EXISTS detected_events")

    cur.execute('''
    CREATE TABLE IF NOT EXISTS sat_state (
        norad_cat_id            INTEGER PRIMARY KEY,
        object_name             TEXT,
        orbit_type              TEXT,
        last_epoch              TEXT,
        last_a                  REAL,
        last_i                  REAL,
        last_e                  REAL,
        last_raan               REAL,
        last_bstar              REAL,
        last_tle1               TEXT,
        last_tle2               TEXT,
        stable_baseline_a       REAL,
        stable_baseline_epoch   TEXT,
        baseline_decay_rate     REAL,
        baseline_bstar_median   REAL,
        noise_sigma_a           REAL,
        geo_slot_longitude      REAL,
        pending_event           TEXT,
        operational_status      TEXT,
        sample_count            INTEGER,
        updated_at              TEXT
    )''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS detected_events (
        event_id                INTEGER PRIMARY KEY AUTOINCREMENT,
        norad_cat_id            INTEGER,
        object_name             TEXT,
        orbit_type              TEXT,
        event_type              TEXT,
        epoch_before            TEXT,
        epoch_event             TEXT,
        delta_a_km              REAL,
        cumulative_da_km        REAL,
        delta_i_deg             REAL,
        sgp4_dr_km              REAL,
        delta_v_total_mps       REAL,
        delta_v_in_track_mps    REAL,
        delta_v_cross_track_mps REAL,
        bstar                   REAL,
        space_weather_ap        INTEGER,
        space_weather_kp_sum    INTEGER,
        adaptive_threshold_km   REAL,
        attribution             TEXT,
        operational_status      TEXT,
        created_at              TEXT
    )''')

    cur.execute('CREATE INDEX IF NOT EXISTS idx_events_sat ON detected_events(norad_cat_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_events_epoch ON detected_events(epoch_event)')
    conn.commit()
    conn.close()

def load_space_weather(sw_file):
    space_wx = {}
    if not os.path.exists(sw_file):
        return space_wx
    with open(sw_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('BEGIN') or line.startswith('NUM') or line.startswith('DATATYPE') or line.startswith('VERSION') or line.startswith('UPDATED'):
                continue
            parts = line.split()
            if len(parts) >= 27:
                try:
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    date_key = f"{y:04d}-{m:02d}-{d:02d}"
                    space_wx[date_key] = {
                        'kp_sum': int(parts[12]),
                        'ap_avg': int(parts[21]),
                        'f107': float(parts[26])
                    }
                except (ValueError, IndexError):
                    continue
    return space_wx

def get_payload_ids():
    if not os.path.exists(SUMMARY_CSV):
        return set(), {}
    df = pd.read_csv(SUMMARY_CSV)
    payloads = df[df['object_type'] == 'PAYLOAD']
    payload_ids = set(payloads['norad_cat_id'].astype(int))
    name_map = dict(zip(payloads['norad_cat_id'].astype(int), payloads['object_name'].fillna('UNKNOWN')))
    return payload_ids, name_map

def determine_orbit_type(a, i, e):
    if a > 40000 and i < 25:
        return 'GEO'
    elif 19000 <= a <= 40000:
        return 'MEO'
    elif e > 0.25:
        return 'HEO'
    elif a < 10000 and 95 <= i <= 105:
        return 'SSO'
    elif a < 10000:
        return 'LEO'
    return 'OTHER'

def verify_sgp4(tle1_1, tle1_2, tle2_1, tle2_2):
    try:
        sat1 = Satrec.twoline2rv(tle1_1, tle1_2)
        sat2 = Satrec.twoline2rv(tle2_1, tle2_2)
        jd2, fr2 = sat2.jdsatepoch, sat2.jdsatepochF
        e1, r_prop, v_prop = sat1.sgp4(jd2, fr2)
        e2, r_true, v_true = sat2.sgp4(jd2, fr2)
        if e1 != 0 or e2 != 0:
            return None
        r_true, v_true = np.array(r_true), np.array(v_true)
        r_prop, v_prop = np.array(r_prop), np.array(v_prop)
        dr = np.linalg.norm(r_true - r_prop)
        dv_vec = (v_true - v_prop) * 1000.0  # m/s
        dv_total = np.linalg.norm(dv_vec)

        v_unit = v_true / np.linalg.norm(v_true)
        h_unit = np.cross(r_true, v_true) / np.linalg.norm(np.cross(r_true, v_true))
        r_unit = np.cross(v_unit, h_unit)

        dv_T = float(np.dot(dv_vec, v_unit))
        dv_N = float(np.dot(dv_vec, h_unit))
        dv_R = float(np.dot(dv_vec, r_unit))
        return {
            'dr_km': dr,
            'dv_total_mps': dv_total,
            'dv_T_mps': dv_T,
            'dv_N_mps': dv_N,
            'dv_R_mps': dv_R
        }
    except Exception:
        return None

def process_advanced_snapshot(snapshot_file, db_path, payload_ids, name_map, space_wx, is_bootstrap=False):
    t_start = time.time()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Load all existing states into memory
    cur.execute("""
        SELECT norad_cat_id, object_name, orbit_type, last_epoch, last_a, last_i, last_e, last_raan, last_bstar,
               last_tle1, last_tle2, stable_baseline_a, stable_baseline_epoch, baseline_decay_rate,
               baseline_bstar_median, noise_sigma_a, geo_slot_longitude, pending_event, operational_status, sample_count
        FROM sat_state
    """)
    states = {}
    for row in cur.fetchall():
        states[row[0]] = {
            'norad_cat_id': row[0], 'object_name': row[1], 'orbit_type': row[2],
            'last_epoch': row[3], 'last_a': row[4], 'last_i': row[5], 'last_e': row[6],
            'last_raan': row[7], 'last_bstar': row[8], 'last_tle1': row[9], 'last_tle2': row[10],
            'stable_baseline_a': row[11], 'stable_baseline_epoch': row[12],
            'baseline_decay_rate': row[13] or 0.0, 'baseline_bstar_median': row[14] or row[8],
            'noise_sigma_a': row[15] or 0.02, 'geo_slot_longitude': row[16],
            'pending_event': json.loads(row[17]) if row[17] else None,
            'operational_status': row[18] or 'NORMAL', 'sample_count': row[19] or 1
        }

    with open(snapshot_file, 'r', encoding='utf-8') as f:
        records = json.load(f)

    latest_recs = {}
    for r in records:
        try:
            sid = int(r.get('NORAD_CAT_ID'))
        except (ValueError, TypeError):
            continue
        if sid in payload_ids and r.get('TLE_LINE1') and r.get('TLE_LINE2'):
            ep = r.get('EPOCH', '')
            if sid not in latest_recs or ep > latest_recs[sid].get('EPOCH', ''):
                latest_recs[sid] = r

    detected_events = []
    state_updates = []
    state_inserts = []
    now_str = datetime.now().isoformat()

    for sid, r in latest_recs.items():
        ep = r['EPOCH']
        a = float(r.get('SEMIMAJOR_AXIS', 0))
        i = float(r.get('INCLINATION', 0))
        e = float(r.get('ECCENTRICITY', 0))
        raan = float(r.get('RA_OF_ASC_NODE', 0))
        bstar = float(r.get('BSTAR', 0))
        tle1 = r['TLE_LINE1']
        tle2 = r['TLE_LINE2']
        name = name_map.get(sid, r.get('OBJECT_NAME', 'UNKNOWN'))
        orbit = determine_orbit_type(a, i, e)

        prev = states.get(sid)
        if not prev:
            # First initialization: establish initial baseline
            geo_lon = ((raan - 100.0) % 360.0) if orbit == 'GEO' else None
            state_inserts.append((
                sid, name, orbit, ep, a, i, e, raan, bstar, tle1, tle2,
                a, ep, 0.0, bstar, 0.015, geo_lon, None, 'NORMAL', 1, now_str
            ))
            continue

        if ep <= prev['last_epoch']:
            continue

        dt_days = (datetime.fromisoformat(ep) - datetime.fromisoformat(prev['last_epoch'])).total_seconds() / 86400.0
        da = a - prev['last_a']
        di = i - prev['last_i']

        date_str = ep[:10]
        wx = space_wx.get(date_str, {'ap_avg': 0, 'kp_sum': 0, 'f107': 0})

        new_pending = None
        new_status = prev['operational_status']
        stable_a = prev['stable_baseline_a'] or prev['last_a']
        stable_epoch = prev['stable_baseline_epoch'] or prev['last_epoch']

        # Per-satellite adaptive threshold
        # Dynamically set threshold = max(35m, 3.5 * sigma_noise)
        adaptive_threshold_a = max(0.035, 3.5 * prev['noise_sigma_a'])

        if not is_bootstrap and 0 < dt_days <= 4.0:
            # 1. Triple-Epoch Consistency for yesterday's pending event
            if prev['pending_event']:
                p_ev = prev['pending_event']
                # If current altitude remains near the post-maneuver altitude, confirm!
                if abs(a - prev['last_a']) < abs(p_ev['delta_a_km']) * 0.45:
                    detected_events.append(p_ev)
                    new_status = 'NORMAL'
                    stable_a = prev['last_a']
                    stable_epoch = prev['last_epoch']
                else:
                    new_status = 'NORMAL'  # False glitch rejected

            # 2. Maneuver Detection
            if orbit in ['LEO', 'SSO', 'MEO']:
                is_candidate = False
                ev_type = None
                if da > adaptive_threshold_a:
                    is_candidate = True
                    ev_type = 'ORBIT_RAISE_MANEUVER'
                elif da < -max(0.30, 4.0 * adaptive_threshold_a):
                    is_candidate = True
                    ev_type = 'ORBIT_LOWER_MANEUVER'

                if is_candidate:
                    sgp4_res = verify_sgp4(prev['last_tle1'], prev['last_tle2'], tle1, tle2)
                    if sgp4_res and sgp4_res['dr_km'] >= 5.0 and 0.05 <= sgp4_res['dv_total_mps'] <= 45.0:
                        cum_da = round(a - stable_a, 4)
                        ev_item = {
                            'norad_cat_id': sid,
                            'object_name': name,
                            'orbit_type': orbit,
                            'event_type': ev_type,
                            'epoch_before': prev['last_epoch'],
                            'epoch_event': ep,
                            'delta_a_km': round(da, 4),
                            'cumulative_da_km': cum_da,
                            'delta_i_deg': round(di, 5),
                            'sgp4_dr_km': round(sgp4_res['dr_km'], 2),
                            'delta_v_total_mps': round(sgp4_res['dv_total_mps'], 3),
                            'delta_v_in_track_mps': round(sgp4_res['dv_T_mps'], 3),
                            'delta_v_cross_track_mps': round(sgp4_res['dv_N_mps'], 3),
                            'bstar': bstar,
                            'space_weather_ap': wx['ap_avg'],
                            'space_weather_kp_sum': wx['kp_sum'],
                            'adaptive_threshold_km': round(adaptive_threshold_a, 4),
                            'attribution': 'Active Thruster Propulsion (推进机动抬轨/降轨)',
                            'operational_status': 'MANEUVERING'
                        }
                        detected_events.append(ev_item)
                        new_pending = ev_item
                        new_status = 'MANEUVERING'

            elif orbit == 'GEO':
                if di < -0.004 or abs(da) > max(0.04, adaptive_threshold_a):
                    sgp4_res = verify_sgp4(prev['last_tle1'], prev['last_tle2'], tle1, tle2)
                    if sgp4_res and sgp4_res['dr_km'] >= 5.0 and 0.02 <= sgp4_res['dv_total_mps'] <= 30.0:
                        ev_type = 'GEO_NORTH_SOUTH_STATION_KEEPING' if di < -0.004 else 'GEO_EAST_WEST_STATION_KEEPING'
                        detected_events.append({
                            'norad_cat_id': sid,
                            'object_name': name,
                            'orbit_type': orbit,
                            'event_type': ev_type,
                            'epoch_before': prev['last_epoch'],
                            'epoch_event': ep,
                            'delta_a_km': round(da, 4),
                            'cumulative_da_km': round(a - stable_a, 4),
                            'delta_i_deg': round(di, 5),
                            'sgp4_dr_km': round(sgp4_res['dr_km'], 2),
                            'delta_v_total_mps': round(sgp4_res['dv_total_mps'], 3),
                            'delta_v_in_track_mps': round(sgp4_res['dv_T_mps'], 3),
                            'delta_v_cross_track_mps': round(sgp4_res['dv_N_mps'], 3),
                            'bstar': bstar,
                            'space_weather_ap': wx['ap_avg'],
                            'space_weather_kp_sum': wx['kp_sum'],
                            'adaptive_threshold_km': round(adaptive_threshold_a, 4),
                            'attribution': 'GEO 定点位置保持控制 (Station-Keeping)',
                            'operational_status': 'STATION_KEEPING'
                        })

            # BSTAR Anomaly & Space Weather
            if orbit in ['LEO', 'SSO'] and bstar > 0 and prev['last_bstar'] > 0:
                bstar_ratio = bstar / prev['baseline_bstar_median'] if prev['baseline_bstar_median'] > 0 else 1.0
                if bstar_ratio >= 3.0:
                    if wx['ap_avg'] >= 25 or wx['kp_sum'] >= 35:
                        ev_type = 'BSTAR_SPIKE_SPACE_WEATHER'
                        attr = f"Space Weather Storm Event (地磁暴引发高层热层膨胀, Ap={wx['ap_avg']})"
                    else:
                        ev_type = 'BSTAR_SPIKE_ATTITUDE_MANEUVER'
                        attr = "Attitude / Aerodynamic Profile Maneuver (航天器姿态机动/迎风截面变化)"

                    detected_events.append({
                        'norad_cat_id': sid,
                        'object_name': name,
                        'orbit_type': orbit,
                        'event_type': ev_type,
                        'epoch_before': prev['last_epoch'],
                        'epoch_event': ep,
                        'delta_a_km': round(da, 4),
                        'cumulative_da_km': 0.0,
                        'delta_i_deg': round(di, 5),
                        'sgp4_dr_km': 0.0,
                        'delta_v_total_mps': 0.0,
                        'delta_v_in_track_mps': 0.0,
                        'delta_v_cross_track_mps': 0.0,
                        'bstar': bstar,
                        'space_weather_ap': wx['ap_avg'],
                        'space_weather_kp_sum': wx['kp_sum'],
                        'adaptive_threshold_km': round(adaptive_threshold_a, 4),
                        'attribution': attr,
                        'operational_status': prev['operational_status']
                    })

        # Online Recursive Learning: update background statistical baseline (if in normal flight)
        alpha = 0.15
        decay_rate_today = (da / dt_days) if dt_days > 0 else 0.0
        new_decay_rate = prev['baseline_decay_rate']
        new_sigma = prev['noise_sigma_a']
        new_bstar_median = prev['baseline_bstar_median']

        if new_status == 'NORMAL' and abs(da) < 0.2:
            # Update baseline decay rate
            new_decay_rate = (1.0 - alpha) * prev['baseline_decay_rate'] + alpha * decay_rate_today
            # Update online noise sigma
            residual = abs(da - prev['baseline_decay_rate'] * dt_days)
            new_sigma = (1.0 - alpha) * prev['noise_sigma_a'] + alpha * max(0.005, residual)
            # Update baseline BSTAR
            if bstar > 0:
                new_bstar_median = (1.0 - alpha) * prev['baseline_bstar_median'] + alpha * bstar

        state_updates.append((
            name, orbit, ep, a, i, e, raan, bstar, tle1, tle2,
            stable_a, stable_epoch, new_decay_rate, new_bstar_median, new_sigma,
            prev['geo_slot_longitude'], json.dumps(new_pending) if new_pending else None,
            new_status, prev['sample_count'] + 1, now_str, sid
        ))

    # Commit DB updates
    if state_inserts:
        cur.executemany("INSERT INTO sat_state VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", state_inserts)
    if state_updates:
        cur.executemany("""
            UPDATE sat_state SET 
                object_name=?, orbit_type=?, last_epoch=?, last_a=?, last_i=?, last_e=?, 
                last_raan=?, last_bstar=?, last_tle1=?, last_tle2=?, stable_baseline_a=?, 
                stable_baseline_epoch=?, baseline_decay_rate=?, baseline_bstar_median=?, 
                noise_sigma_a=?, geo_slot_longitude=?, pending_event=?, operational_status=?, 
                sample_count=?, updated_at=?
            WHERE norad_cat_id=?
        """, state_updates)

    if detected_events and not is_bootstrap:
        event_rows = [(
            e['norad_cat_id'], e['object_name'], e['orbit_type'], e['event_type'],
            e['epoch_before'], e['epoch_event'], e['delta_a_km'], e['cumulative_da_km'],
            e['delta_i_deg'], e['sgp4_dr_km'], e['delta_v_total_mps'], e['delta_v_in_track_mps'],
            e['delta_v_cross_track_mps'], e['bstar'], e['space_weather_ap'],
            e['space_weather_kp_sum'], e['adaptive_threshold_km'], e['attribution'],
            e['operational_status'], now_str
        ) for e in detected_events]
        cur.executemany("""
            INSERT INTO detected_events (
                norad_cat_id, object_name, orbit_type, event_type, epoch_before, epoch_event,
                delta_a_km, cumulative_da_km, delta_i_deg, sgp4_dr_km, delta_v_total_mps,
                delta_v_in_track_mps, delta_v_cross_track_mps, bstar, space_weather_ap,
                space_weather_kp_sum, adaptive_threshold_km, attribution, operational_status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, event_rows)

    conn.commit()
    conn.close()

    elapsed = time.time() - t_start
    return len(latest_recs), detected_events, elapsed

def main():
    parser = argparse.ArgumentParser(description="Advanced Incremental Event Engine")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark on 2026-10-09")
    parser.add_argument("--process-day", help="Process specific day YYYY-MM-DD")
    parser.add_argument("--snapshot", help="Process specific snapshot JSON file")
    args = parser.parse_args()

    init_advanced_db(DB_PATH, reset=False)
    space_wx = load_space_weather(SW_FILE)
    payload_ids, name_map = get_payload_ids()

    # Check if DB has been initialized
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM sat_state")
    cached_count = cur.fetchone()[0]
    conn.close()

    if cached_count == 0 or args.benchmark:
        print("=== Initializing / Bootstrapping State Database ===")
        init_advanced_db(DB_PATH, reset=True)
        date_dirs = sorted([d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d)) and d < '2026-10-09'])
        boot_t0 = time.time()
        for d in date_dirs:
            for jf in sorted(glob.glob(os.path.join(RAW_DIR, d, '*.json'))):
                count, _, _ = process_advanced_snapshot(jf, DB_PATH, payload_ids, name_map, space_wx, is_bootstrap=True)
        print(f"Bootstrapped {len(date_dirs)} baseline days in {time.time()-boot_t0:.2f}s.")

    # Determine target file to process
    if args.snapshot:
        target_file = args.snapshot
    elif args.process_day:
        files = sorted(glob.glob(os.path.join(RAW_DIR, args.process_day, '*.json')))
        if not files:
            print(f"Error: No JSON snapshot found for {args.process_day}")
            return
        target_file = files[-1]
    else:
        # Auto-detect latest snapshot file
        all_snapshots = sorted(glob.glob(os.path.join(RAW_DIR, '*', '*.json')))
        if not all_snapshots:
            print("Error: No raw TLE snapshots found in archive.")
            return
        target_file = all_snapshots[-1]

    print(f"\n=== Executing Daily Incremental Detection on: {os.path.basename(target_file)} ===")
    t_start = time.time()
    sats_checked, events_today, process_elapsed = process_advanced_snapshot(
        target_file, DB_PATH, payload_ids, name_map, space_wx, is_bootstrap=False
    )
    total_wall_time = time.time() - t_start

    print(f"  * Evaluated: {sats_checked} satellites")
    print(f"  * Gating & SGP4 Verification Time: {process_elapsed:.3f} s")
    print(f"  * Total End-to-End Time: {total_wall_time:.3f} s")
    print(f"  * Events Detected: {len(events_today)}")

    # Extract date for output CSV
    target_date = os.path.basename(os.path.dirname(target_file))
    out_csv = os.path.join(OUTPUT_DIR, f'advanced_incremental_events_{target_date}.csv')
    df_today = pd.DataFrame(events_today)
    df_today.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"  * Saved events to {out_csv}")

    if not df_today.empty:
        print("\n--- Event Distribution ---")
        print(df_today['event_type'].value_counts().to_string())

if __name__ == '__main__':
    main()
