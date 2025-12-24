#!/usr/bin/env python3
"""
Large-scale data collection for AI training.
Collects 500+ inscriptions across multiple content types.
"""

import sys
sys.path.insert(0, '/Volumes/Virtual Server/Projects/blockchain-research')

from data_collector import OrdinalsCollector, save_metadata, generate_dataset_stats
import time

def main():
    print("=" * 60)
    print("LARGE SCALE BLOCKCHAIN DATA COLLECTION")
    print("=" * 60)

    collector = OrdinalsCollector()

    # Collect more of each type
    targets = [
        ('image/png', 100),
        ('image/webp', 100),
        ('image/gif', 50),
        ('image/svg+xml', 50),
        ('text/plain', 100),
        ('text/html', 50),
        ('application/json', 50),
    ]

    all_records = []
    for mime_type, count in targets:
        print(f"\n>>> Collecting {count} x {mime_type}")
        records = collector.collect_by_type(mime_type, max_count=count, workers=3)
        all_records.extend(records)
        print(f"    Total so far: {len(all_records)}")
        time.sleep(2)  # Rate limiting between types

    # Save metadata
    save_metadata(all_records, 'ordinals_large_metadata.json')

    # Generate stats
    stats = generate_dataset_stats()
    print("\n" + "=" * 60)
    print("FINAL STATS")
    print("=" * 60)
    import json
    print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    main()
