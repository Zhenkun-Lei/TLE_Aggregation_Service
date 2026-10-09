#!/usr/bin/env python3
"""
Fetch and update Space Weather data from CelesTrak.
URL: https://celestrak.org/SpaceData/SW-Last5Years.txt
Stores data in /home/jetson/TLE_Aggregation_Service/analysis_output/SW-Last5Years.txt
"""

import os
import sys
import time
import urllib.request
import logging

DEST_DIR = '/home/jetson/TLE_Aggregation_Service/analysis_output'
ARCHIVE_DIR = '/home/jetson/TLE_Aggregation_Service/archive/space_weather'
URL = 'https://celestrak.org/SpaceData/SW-Last5Years.txt'

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def download_space_weather(force=False):
    os.makedirs(DEST_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    target_file = os.path.join(DEST_DIR, 'SW-Last5Years.txt')
    archive_file = os.path.join(ARCHIVE_DIR, 'SW-Last5Years.txt')

    # If already downloaded today and size > 100KB, skip unless forced
    if not force and os.path.exists(target_file):
        mtime = os.path.getmtime(target_file)
        if (time.time() - mtime) < 12 * 3600 and os.path.getsize(target_file) > 100000:
            logging.info(f"Space weather file is up to date (modified {int((time.time()-mtime)/3600)}h ago): {target_file}")
            return target_file

    logging.info(f"Downloading space weather from {URL} ...")
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (TLE-Aggregation-Service)'})
    tmp_file = target_file + '.tmp'
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_file, 'wb') as out_f:
            total_bytes = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out_f.write(chunk)
                total_bytes += len(chunk)

        if total_bytes < 50000:
            raise ValueError(f"Downloaded file too small ({total_bytes} bytes), download may be incomplete.")

        os.replace(tmp_file, target_file)
        # Also sync to archive
        with open(target_file, 'rb') as src, open(archive_file, 'wb') as dst:
            dst.write(src.read())

        logging.info(f"Successfully updated space weather data ({total_bytes / 1024:.1f} KB) to {target_file}")
        return target_file
    except Exception as e:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass
        logging.error(f"Failed to download space weather: {e}")
        if os.path.exists(target_file):
            logging.warning(f"Using existing cached file: {target_file}")
            return target_file
        raise

if __name__ == '__main__':
    force_update = '--force' in sys.argv
    download_space_weather(force=force_update)
