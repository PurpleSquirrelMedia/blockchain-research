#!/usr/bin/env python3
"""
Analyze collected blockchain inscription data.
"""

import json
from pathlib import Path
from collections import defaultdict
import hashlib

DATA_DIR = Path("/Volumes/Virtual Server/Projects/blockchain-research/data")

def load_metadata():
    """Load all metadata files."""
    metadata = []
    for f in (DATA_DIR / "metadata").glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if isinstance(data, list):
                metadata.extend(data)
        except:
            pass
    return metadata

def analyze_content_types(records):
    """Analyze distribution of content types."""
    by_type = defaultdict(lambda: {'count': 0, 'total_bytes': 0, 'examples': []})

    for r in records:
        ct = r.get('content_type', 'unknown')
        by_type[ct]['count'] += 1
        by_type[ct]['total_bytes'] += r.get('content_length', 0)
        if len(by_type[ct]['examples']) < 3:
            by_type[ct]['examples'].append(r.get('number', 0))

    return dict(by_type)

def analyze_file_sizes(records):
    """Analyze file size distribution."""
    sizes = [r.get('content_length', 0) for r in records]
    if not sizes:
        return {}

    sizes.sort()
    return {
        'min': min(sizes),
        'max': max(sizes),
        'median': sizes[len(sizes)//2],
        'mean': sum(sizes) / len(sizes),
        'total_bytes': sum(sizes),
        'total_mb': sum(sizes) / (1024 * 1024),
        'size_distribution': {
            '<1KB': len([s for s in sizes if s < 1024]),
            '1-10KB': len([s for s in sizes if 1024 <= s < 10240]),
            '10-100KB': len([s for s in sizes if 10240 <= s < 102400]),
            '100KB-1MB': len([s for s in sizes if 102400 <= s < 1048576]),
            '>1MB': len([s for s in sizes if s >= 1048576]),
        }
    }

def analyze_inscription_numbers(records):
    """Analyze inscription number distribution."""
    numbers = [r.get('number', 0) for r in records if r.get('number')]
    if not numbers:
        return {}

    numbers.sort()
    return {
        'earliest': min(numbers),
        'latest': max(numbers),
        'range': max(numbers) - min(numbers),
        'count': len(numbers)
    }

def check_duplicates(records):
    """Check for duplicate content."""
    hashes = defaultdict(list)
    for r in records:
        h = r.get('file_hash', '')
        if h:
            hashes[h].append(r.get('number', 0))

    duplicates = {h: nums for h, nums in hashes.items() if len(nums) > 1}
    return {
        'unique_content': len(hashes),
        'duplicate_groups': len(duplicates),
        'duplicate_examples': dict(list(duplicates.items())[:5])
    }

def analyze_text_content(records):
    """Analyze text inscriptions."""
    text_records = [r for r in records if r.get('content_type', '').startswith('text/')]

    stats = {'count': len(text_records), 'samples': []}

    for r in text_records[:5]:
        path = Path(r.get('local_path', ''))
        if path.exists():
            try:
                content = path.read_text(errors='ignore')[:200]
                stats['samples'].append({
                    'number': r.get('number'),
                    'type': r.get('content_type'),
                    'preview': content
                })
            except:
                pass

    return stats

def generate_report(records):
    """Generate full analysis report."""
    report = {
        'summary': {
            'total_records': len(records),
            'unique_inscriptions': len(set(r.get('id', '') for r in records if r.get('id'))),
        },
        'content_types': analyze_content_types(records),
        'file_sizes': analyze_file_sizes(records),
        'inscription_numbers': analyze_inscription_numbers(records),
        'duplicates': check_duplicates(records),
        'text_analysis': analyze_text_content(records)
    }
    return report

def print_report(report):
    """Pretty print the report."""
    print("=" * 70)
    print("BLOCKCHAIN INSCRIPTION DATA ANALYSIS")
    print("=" * 70)

    print(f"\n## Summary")
    print(f"   Total records: {report['summary']['total_records']}")
    print(f"   Unique inscriptions: {report['summary']['unique_inscriptions']}")

    print(f"\n## Content Types")
    for ct, data in sorted(report['content_types'].items(), key=lambda x: -x[1]['count']):
        mb = data['total_bytes'] / (1024*1024)
        print(f"   {ct}: {data['count']} files ({mb:.2f} MB)")

    print(f"\n## File Sizes")
    fs = report['file_sizes']
    print(f"   Min: {fs['min']:,} bytes")
    print(f"   Max: {fs['max']:,} bytes")
    print(f"   Median: {fs['median']:,} bytes")
    print(f"   Mean: {fs['mean']:,.0f} bytes")
    print(f"   Total: {fs['total_mb']:.2f} MB")
    print(f"\n   Distribution:")
    for bucket, count in fs['size_distribution'].items():
        bar = '#' * min(count, 30)
        print(f"   {bucket:>12}: {count:3} {bar}")

    print(f"\n## Inscription Numbers")
    ins = report['inscription_numbers']
    print(f"   Earliest: #{ins['earliest']:,}")
    print(f"   Latest: #{ins['latest']:,}")
    print(f"   Range: {ins['range']:,} inscriptions")

    print(f"\n## Duplicates")
    dup = report['duplicates']
    print(f"   Unique content hashes: {dup['unique_content']}")
    print(f"   Duplicate groups: {dup['duplicate_groups']}")

    print(f"\n## Text Content Samples")
    for sample in report['text_analysis']['samples'][:3]:
        print(f"\n   Inscription #{sample['number']} ({sample['type']}):")
        preview = sample['preview'].replace('\n', ' ')[:80]
        print(f"   \"{preview}...\"")

    print("\n" + "=" * 70)

def main():
    print("Loading metadata...")
    records = load_metadata()

    if not records:
        print("No data found. Run collectors first.")
        return

    print(f"Found {len(records)} records")

    report = generate_report(records)
    print_report(report)

    # Save full report
    report_file = DATA_DIR / "metadata" / "analysis_report.json"
    report_file.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nFull report saved to: {report_file}")

if __name__ == '__main__':
    main()
