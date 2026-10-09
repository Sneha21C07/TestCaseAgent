"""Utilities to export CSV and debug JSON files."""
import csv
import json
import os
from typing import List, Dict


def ensure_debug_dir(debug_path: str):
    os.makedirs(debug_path, exist_ok=True)


def write_csv(path: str, rows: List[Dict], headers: List[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def write_debug_json(debug_path: str, filename: str, obj):
    ensure_debug_dir(debug_path)
    p = os.path.join(debug_path, filename)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
