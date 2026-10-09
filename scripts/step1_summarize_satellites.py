#!/usr/bin/env python3
"""
Step 1: Inventory all satellites from TLE JSON snapshots on Space-Track raw archives.
Outputs:
  - satellite_summary.csv
  - satellite_summary.json
"""

import os
import glob
import json
import time
import pandas as pd

RAW_DIR = '/home/jetson/TLE_Aggregation_Service/archive/raw/spacetrack'
OUTPUT_DIR = '/home/jetson/TLE_Aggregation_Service/analysis_output'

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start_time = time.time()
    date_dirs = sorted([d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d))])
    print(f"Found {len(date_dirs)} date directories: {date_dirs[0]} to {date_dirs[-1]}")

    sat_info = {}
    total_files = 0
    total_records = 0

    for d in date_dirs:
        dir_path = os.path.join(RAW_DIR, d)
        json_files = sorted(glob.glob(os.path.join(dir_path, '*.json')))
        for jf in json_files:
            total_files += 1
            file_t0 = time.time()
            with open(jf, 'r', encoding='utf-8') as f:
                records = json.load(f)
            rec_count = len(records)
            total_records += rec_count
            for r in records:
                sat_id = r.get('NORAD_CAT_ID')
                if not sat_id:
                    continue
                epoch = r.get('EPOCH', '')
                obj_name = r.get('OBJECT_NAME', '')
                obj_id = r.get('OBJECT_ID', '')
                obj_type = r.get('OBJECT_TYPE', '')

                if sat_id not in sat_info:
                    sat_info[sat_id] = {
                        'norad_cat_id': int(sat_id) if str(sat_id).isdigit() else sat_id,
                        'object_name': obj_name,
                        'object_id': obj_id,
                        'object_type': obj_type,
                        'first_seen_date': d,
                        'last_seen_date': d,
                        'first_epoch': epoch,
                        'last_epoch': epoch,
                        'unique_epochs': {epoch} if epoch else set(),
                        'record_count': 1,
                        'dates_count': 1,
                        'seen_dates': {d}
                    }
                else:
                    info = sat_info[sat_id]
                    info['record_count'] += 1
                    if d not in info['seen_dates']:
                        info['seen_dates'].add(d)
                        info['dates_count'] += 1
                    if d > info['last_seen_date']:
                        info['last_seen_date'] = d
                    if epoch:
                        info['unique_epochs'].add(epoch)
                        if not info['first_epoch'] or epoch < info['first_epoch']:
                            info['first_epoch'] = epoch
                        if not info['last_epoch'] or epoch > info['last_epoch']:
                            info['last_epoch'] = epoch
                    if obj_name and not info['object_name']:
                        info['object_name'] = obj_name

            print(f"[{total_files}/{len(date_dirs)*1}] Read {os.path.basename(jf)} ({rec_count} recs) in {time.time()-file_t0:.2f}s")

    print(f"\nAll files processed in {time.time()-start_time:.2f}s.")
    print(f"Total files: {total_files}, Total raw records: {total_records}, Unique satellites: {len(sat_info)}")

    summary_rows = []
    for sat_id, info in sat_info.items():
        summary_rows.append({
            'norad_cat_id': info['norad_cat_id'],
            'object_name': info['object_name'],
            'object_id': info['object_id'],
            'object_type': info['object_type'],
            'first_seen_date': info['first_seen_date'],
            'last_seen_date': info['last_seen_date'],
            'first_epoch': info['first_epoch'],
            'last_epoch': info['last_epoch'],
            'unique_epochs_count': len(info['unique_epochs']),
            'dates_count': info['dates_count'],
            'record_count': info['record_count']
        })

    summary_rows.sort(key=lambda x: int(x['norad_cat_id']) if str(x['norad_cat_id']).isdigit() else 999999)

    # Export to CSV
    csv_path = os.path.join(OUTPUT_DIR, 'satellite_summary.csv')
    df = pd.DataFrame(summary_rows)
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"Exported CSV to {csv_path} ({len(df)} rows)")

    # Export to JSON
    json_path = os.path.join(OUTPUT_DIR, 'satellite_summary.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_rows, f, indent=2, ensure_ascii=False)
    print(f"Exported JSON to {json_path}")

    # Display first-date distribution
    first_date_counts = df['first_seen_date'].value_counts().sort_index()
    print("\n--- Distribution of Satellites by First Seen Date ---")
    for date, count in first_date_counts.items():
        print(f"  {date}: {count} satellites")

if __name__ == '__main__':
    main()
