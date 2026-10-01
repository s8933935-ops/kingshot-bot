#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch YouTube Knowledge Harvester for Satisfactory v1.0
Collects expert video guides on fluids, trains, aluminum, nuclear, and recipes.
"""

import sys
import os

# Force UTF-8 console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from youtube_harvester import search_and_harvest, save_processed_tips

SEED_QUERIES = [
    # Fluids & Plumbing
    {"query": "Satisfactory 1.0 pipe guide", "limit": 2},
    {"query": "Satisfactory 1.0 aluminum water recycle loop", "limit": 2},
    # Train Signals & Logistics
    {"query": "Satisfactory 1.0 train signals guide block path", "limit": 2},
    # Nuclear Power (v1.0 Ficsonium / Waste-free)
    {"query": "Satisfactory 1.0 nuclear power waste free guide", "limit": 2},
    # Japanese Guides
    {"query": "Satisfactory 1.0 パイプ 液体 攻略", "limit": 2},
    {"query": "Satisfactory 1.0 列車 信号 解説", "limit": 2},
]

def run_batch_harvest():
    print("==================================================")
    print("🚀 Satisfactory v1.0 YouTube Knowledge Harvester")
    print("==================================================")
    total_new = []

    for item in SEED_QUERIES:
        q = item["query"]
        lim = item["limit"]
        print(f"\n▶ Processing Target: '{q}' (Limit: {lim})")
        try:
            chunks = search_and_harvest(q, max_results=lim)
            if chunks:
                total_new.extend(chunks)
        except Exception as e:
            print(f"[!] Error processing query '{q}': {e}")

    if total_new:
        save_processed_tips(total_new)
        print(f"\n🎉 Batch harvest completed. {len(total_new)} chunks harvested across categories.")
    else:
        print("\n[!] No new chunks were harvested.")

if __name__ == "__main__":
    run_batch_harvest()
