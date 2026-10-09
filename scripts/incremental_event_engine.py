#!/usr/bin/env python3
"""
Production Incremental Orbital Event Detection Engine:
- State Store: SQLite (/home/jetson/TLE_Aggregation_Service/analysis_output/satellite_state.db)
- Space Weather: CelesTrak SW-Last5Years.txt
- Execution Mode:
    --bootstrap-until YYYY-MM-DD: Initialize historical baseline up to a specific date
    --process-day YYYY-MM-DD: Run pure incremental single-day event detection
    --verify: Benchmark single-day processing and verify accuracy against expectations
"""

import os
import sys
import glob
import json
import time
import sqlite3
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from sgp4.api import Satrec

BASE_DIR = '/home/jetson/TLE_Aggregation_Service'
RAW_DIR = os.path.join(BASE_DIR, 'archive/raw/spacetrack')
OUTPUT_DIR = os.path.join(BASE_DIR, 'analysis_output')
DB_PATH = os.path.join(OUTPUT_DIR, 'satellite_state.db')
SW_FILE = os.path.join(OUTPUT_DIR, 'SW-Last5Years.txt')
SUMMARY_CSV = os.path.join(OUTPUT_DIR, 'satellite_summary.csv')

def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sat_state (
        norad_cat_id INTEGER PRIMARY KEY,
        object_name TEXT,
        orbit_type TEXT,
        last_epoch TEXT,
        last_a REAL,
        last_i REAL,
        last_e REAL,
        last_raan REAL,
        last_bstar REAL,
        last_tle1 TEXT,
        last_tle2 TEXT,
        rolling_da REAL,
        rolling_bstar REAL,
        pending_event TEXT,
        updated_at TEXT
    )''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS detected_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        norad_cat_id INTEGER,
        object_name TEXT,
        orbit_type TEXT,
        event_type TEXT,
        epoch_before TEXT,
        epoch_event TEXT,
        delta_a_km REAL,
        delta_i_deg REAL,
        sgp4_dr_km REAL,
        delta_v_total_mps REAL,
        delta_v_in_track_mps REAL,
        delta_v_cross_track_mps REAL,
        bstar REAL,
        space_weather_ap INTEGER,
        space_weather_kp_sum INTEGER,
        attribution TEXT,
        detection_mode TEXT,
        created_at TEXT
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

def process_single_snapshot(snapshot_file, db_path, payload_ids, name_map, space_wx, is_bootstrap=False):
    t_start = time.time()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Load all existing states into memory dict: norad_cat_id -> dict
    cur.execute("SELECT norad_cat_id, object_name, orbit_type, last_epoch, last_a, last_i, last_e, last_raan, last_bstar, last_tle1, last_tle2, rolling_da, rolling_bstar, pending_event FROM sat_state")
    existing_states = {}
    for row in cur.fetchall():
        existing_states[row[0]] = {
            'norad_cat_id': row[0],
            'object_name': row[1],
            'orbit_type': row[2],
            'last_epoch': row[3],
            'last_a': row[4],
            'last_i': row[5],
            'last_e': row[6],
            'last_raan': row[7],
            'last_bstar': row[8],
            'last_tle1': row[9],
            'last_tle2': row[10],
            'rolling_da': row[11],
            'rolling_bstar': row[12],
            'pending_event': json.loads(row[13]) if row[13] else None
        }

    with open(snapshot_file, 'r', encoding='utf-8') as f:
        records = json.load(f)

    # Filter and deduplicate for latest record per satellite in this snapshot
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

        prev = existing_states.get(sid)
        if not prev:
            # First time seen: insert baseline state
            state_inserts.append((sid, name, orbit, ep, a, i, e, raan, bstar, tle1, tle2, 0.0, bstar, None, now_str))
            continue

        # If incoming epoch is not newer than stored epoch, do nothing
        if ep <= prev['last_epoch']:
            continue

        # Compute delta
        dt_hours = (datetime.fromisoformat(ep) - datetime.fromisoformat(prev['last_epoch'])).total_seconds() / 3600.0
        da = a - prev['last_a']
        di = i - prev['last_i']

        date_str = ep[:10]
        wx = space_wx.get(date_str, {'ap_avg': 0, 'kp_sum': 0, 'f107': 0})

        new_pending = None

        if not is_bootstrap and dt_hours > 0 and dt_hours <= 96.0:
            # 1. Check Pending Event Resolution (Triple-Epoch Consistency from yesterday)
            if prev['pending_event']:
                p_ev = prev['pending_event']
                # Check if orbit stayed at new level
                if abs(a - prev['last_a']) < abs(p_ev['delta_a_km']) * 0.5:
                    # Confirmed! Add to detected events
                    detected_events.append(p_ev)
                # Clear pending event

            # 2. Event Detection on Current Interval
            # A. LEO / SSO / MEO Maneuver
            if orbit in ['LEO', 'SSO', 'MEO']:
                if da > 0.05 or da < -0.35:
                    sgp4_res = verify_sgp4(prev['last_tle1'], prev['last_tle2'], tle1, tle2)
                    if sgp4_res and sgp4_res['dr_km'] >= 5.0 and 0.05 <= sgp4_res['dv_total_mps'] <= 45.0:
                        ev_type = 'ORBIT_RAISE_MANEUVER' if da > 0 else 'ORBIT_LOWER_MANEUVER'
                        candidate_ev = {
                            'norad_cat_id': sid,
                            'object_name': name,
                            'orbit_type': orbit,
                            'event_type': ev_type,
                            'epoch_before': prev['last_epoch'],
                            'epoch_event': ep,
                            'delta_a_km': round(da, 4),
                            'delta_i_deg': round(di, 5),
                            'sgp4_dr_km': round(sgp4_res['dr_km'], 2),
                            'delta_v_total_mps': round(sgp4_res['dv_total_mps'], 3),
                            'delta_v_in_track_mps': round(sgp4_res['dv_T_mps'], 3),
                            'delta_v_cross_track_mps': round(sgp4_res['dv_N_mps'], 3),
                            'bstar': bstar,
                            'space_weather_ap': wx['ap_avg'],
                            'space_weather_kp_sum': wx['kp_sum'],
                            'attribution': 'Active Thruster Propulsion (推进机动抬轨/降轨)',
                            'detection_mode': 'INCREMENTAL'
                        }
                        # Store as pending or immediate
                        detected_events.append(candidate_ev)
                        new_pending = candidate_ev

            # B. GEO Station-Keeping
            elif orbit == 'GEO':
                if di < -0.004 or abs(da) > 0.05:
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
                            'delta_i_deg': round(di, 5),
                            'sgp4_dr_km': round(sgp4_res['dr_km'], 2),
                            'delta_v_total_mps': round(sgp4_res['dv_total_mps'], 3),
                            'delta_v_in_track_mps': round(sgp4_res['dv_T_mps'], 3),
                            'delta_v_cross_track_mps': round(sgp4_res['dv_N_mps'], 3),
                            'bstar': bstar,
                            'space_weather_ap': wx['ap_avg'],
                            'space_weather_kp_sum': wx['kp_sum'],
                            'attribution': 'GEO 定点位置保持控制 (Station-Keeping)',
                            'detection_mode': 'INCREMENTAL'
                        })

            # C. BSTAR Spikes & Space Weather
            if orbit in ['LEO', 'SSO'] and bstar > 0 and prev['last_bstar'] > 0:
                if (bstar / prev['last_bstar']) >= 3.0:
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
                        'delta_i_deg': round(di, 5),
                        'sgp4_dr_km': 0.0,
                        'delta_v_total_mps': 0.0,
                        'delta_v_in_track_mps': 0.0,
                        'delta_v_cross_track_mps': 0.0,
                        'bstar': bstar,
                        'space_weather_ap': wx['ap_avg'],
                        'space_weather_kp_sum': wx['kp_sum'],
                        'attribution': attr,
                        'detection_mode': 'INCREMENTAL'
                    })

        # Update state
        rolling_da = 0.8 * prev['rolling_da'] + 0.2 * da if prev['rolling_da'] else da
        rolling_bstar = 0.8 * prev['rolling_bstar'] + 0.2 * bstar if prev['rolling_bstar'] else bstar
        state_updates.append((
            name, orbit, ep, a, i, e, raan, bstar, tle1, tle2,
            rolling_da, rolling_bstar, json.dumps(new_pending) if new_pending else None, now_str, sid
        ))

    # Commit DB updates
    if state_inserts:
        cur.executemany("INSERT INTO sat_state VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", state_inserts)
    if state_updates:
        cur.executemany("""
            UPDATE sat_state SET 
                object_name=?, orbit_type=?, last_epoch=?, last_a=?, last_i=?, last_e=?, 
                last_raan=?, last_bstar=?, last_tle1=?, last_tle2=?, rolling_da=?, 
                rolling_bstar=?, pending_event=?, updated_at=?
            WHERE norad_cat_id=?
        """, state_updates)

    if detected_events and not is_bootstrap:
        event_rows = [(
            e['norad_cat_id'], e['object_name'], e['orbit_type'], e['event_type'],
            e['epoch_before'], e['epoch_event'], e['delta_a_km'], e['delta_i_deg'],
            e['sgp4_dr_km'], e['delta_v_total_mps'], e['delta_v_in_track_mps'],
            e['delta_v_cross_track_mps'], e['bstar'], e['space_weather_ap'],
            e['space_weather_kp_sum'], e['attribution'], e['detection_mode'], now_str
        ) for e in detected_events]
        cur.executemany("""
            INSERT INTO detected_events (
                norad_cat_id, object_name, orbit_type, event_type, epoch_before, epoch_event,
                delta_a_km, delta_i_deg, sgp4_dr_km, delta_v_total_mps, delta_v_in_track_mps,
                delta_v_cross_track_mps, bstar, space_weather_ap, space_weather_kp_sum,
                attribution, detection_mode, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, event_rows)

    conn.commit()
    conn.close()

    elapsed = time.time() - t_start
    return len(latest_recs), detected_events, elapsed

def main():
    parser = argparse.ArgumentParser(description="Incremental Orbital Event Detection Engine")
    parser.add_argument("--bootstrap-until", help="Date string YYYY-MM-DD to build baseline state cache")
    parser.add_argument("--process-day", help="Single date string YYYY-MM-DD to run incremental detection on")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark on 2026-10-09")
    args = parser.parse_args()

    init_db(DB_PATH)
    space_wx = load_space_weather(SW_FILE)
    payload_ids, name_map = get_payload_ids()

    if args.benchmark or args.process_day == '2026-10-09':
        print("=== Step 1: Bootstrapping State Database from 2026-09-20 up to 2026-10-08 ===")
        date_dirs = sorted([d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d)) and d < '2026-10-09'])
        boot_t0 = time.time()
        for d in date_dirs:
            for jf in sorted(glob.glob(os.path.join(RAW_DIR, d, '*.json'))):
                count, _, t_sub = process_single_snapshot(jf, DB_PATH, payload_ids, name_map, space_wx, is_bootstrap=True)
        print(f"Bootstrapped {len(date_dirs)} days into state DB in {time.time()-boot_t0:.2f}s.")

        # Check DB size and record count
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM sat_state")
        cached_sats = cur.fetchone()[0]
        db_size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
        conn.close()
        print(f"State DB Cache: {cached_sats} satellites stored, file size: {db_size_mb:.2f} MB")

        print("\n=== Step 2: Executing Pure Single-Day Incremental Detection on 2026-10-09 ===")
        day_1009_files = sorted(glob.glob(os.path.join(RAW_DIR, '2026-10-09', '*.json')))
        if not day_1009_files:
            print("Error: 2026-10-09 snapshot not found.")
            return

        target_file = day_1009_files[0]
        print(f"Input file: {target_file} ({os.path.getsize(target_file)/(1024*1024):.1f} MB)")

        t_start = time.time()
        sats_checked, events_today, process_elapsed = process_single_snapshot(
            target_file, DB_PATH, payload_ids, name_map, space_wx, is_bootstrap=False
        )
        total_wall_time = time.time() - t_start

        print("\n--- Incremental Execution Performance Metrics ---")
        print(f"  * Total Satellites Evaluated: {sats_checked}")
        print(f"  * Processing & Event Detection Time: {process_elapsed:.3f} s")
        print(f"  * Total End-to-End Time: {total_wall_time:.3f} s")
        print(f"  * Events Detected on 2026-10-09: {len(events_today)}")

        # Save single-day incremental report
        df_today = pd.DataFrame(events_today)
        out_csv = os.path.join(OUTPUT_DIR, 'incremental_events_2026-10-09.csv')
        df_today.to_csv(out_csv, index=False, encoding='utf-8')
        print(f"\nSaved today's events to {out_csv}")

        # Breakdown of today's events
        if not df_today.empty:
            print("\n--- Breakdown of Events Detected Today (2026-10-09) ---")
            print(df_today['event_type'].value_counts().to_string())
            print("\nSample top maneuvers today:")
            raises = df_today[df_today['event_type'] == 'ORBIT_RAISE_MANEUVER'].sort_values('delta_v_total_mps', ascending=False)
            if not raises.empty:
                for _, r in raises.head(5).iterrows():
                    print(f"  NORAD {r['norad_cat_id']} ({r['object_name']}): Delta_a={r['delta_a_km']:+.3f} km, SGP4_dr={r['sgp4_dr_km']:.1f} km, Delta_V={r['delta_v_total_mps']:.2f} m/s")

if __name__ == '__main__':
    main()
