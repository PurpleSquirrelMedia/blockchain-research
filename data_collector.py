#!/usr/bin/env python3
"""
Blockchain Data Collector for AI Training
==========================================
Bulk download and categorize on-chain content.
"""

import os
import json
import time
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_DIR = Path.home() / "blockchain-research" / "data"
ORDINALS_DIR = DATA_DIR / "ordinals"
ARWEAVE_DIR = DATA_DIR / "arweave"
METADATA_DIR = DATA_DIR / "metadata"

# Create directories
for d in [ORDINALS_DIR, ARWEAVE_DIR, METADATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class InscriptionRecord:
    """Metadata record for an inscription"""
    id: str
    number: int
    content_type: str
    content_length: int
    genesis_height: int
    genesis_timestamp: int
    sat_ordinal: str
    sat_rarity: str
    file_hash: str
    local_path: str
    source: str = "ordinals"


class OrdinalsCollector:
    """Collect Ordinals inscriptions for AI training"""

    def __init__(self):
        self.api = "https://api.hiro.so/ordinals/v1"
        self.session = requests.Session()
        self.session.headers['Accept'] = 'application/json'

    def get_inscriptions_page(self,
                              mime_type: str = None,
                              offset: int = 0,
                              limit: int = 60) -> Dict:
        """Fetch a page of inscriptions"""
        params = {'offset': offset, 'limit': limit}
        if mime_type:
            params['mime_type'] = mime_type

        resp = self.session.get(f"{self.api}/inscriptions", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_inscription_content(self, inscription_id: str) -> bytes:
        """Download inscription content"""
        url = f"{self.api}/inscriptions/{inscription_id}/content"
        resp = self.session.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content

    def download_inscription(self, inscription: Dict) -> Optional[InscriptionRecord]:
        """Download and save a single inscription"""
        inscription_id = inscription['id']
        content_type = inscription.get('content_type', 'unknown')
        number = inscription.get('number', 0)

        # Determine file extension
        ext_map = {
            'image/png': '.png',
            'image/webp': '.webp',
            'image/gif': '.gif',
            'image/jpeg': '.jpg',
            'image/svg+xml': '.svg',
            'text/plain': '.txt',
            'text/html': '.html',
            'application/json': '.json',
            'text/javascript': '.js',
            'audio/mpeg': '.mp3',
            'video/mp4': '.mp4',
        }
        ext = ext_map.get(content_type, '.bin')

        # Create category subdirectory
        category = content_type.split('/')[0] if '/' in content_type else 'other'
        category_dir = ORDINALS_DIR / category
        category_dir.mkdir(exist_ok=True)

        # Download content
        try:
            content = self.get_inscription_content(inscription_id)
            file_hash = hashlib.sha256(content).hexdigest()[:16]

            # Save file
            filename = f"{number}_{file_hash}{ext}"
            filepath = category_dir / filename
            filepath.write_bytes(content)

            return InscriptionRecord(
                id=inscription_id,
                number=number,
                content_type=content_type,
                content_length=len(content),
                genesis_height=inscription.get('genesis_block_height', 0),
                genesis_timestamp=inscription.get('genesis_timestamp', 0),
                sat_ordinal=inscription.get('sat_ordinal', ''),
                sat_rarity=inscription.get('sat_rarity', 'common'),
                file_hash=file_hash,
                local_path=str(filepath),
            )

        except Exception as e:
            print(f"  Error downloading {inscription_id[:16]}: {e}")
            return None

    def collect_by_type(self,
                        mime_type: str,
                        max_count: int = 100,
                        workers: int = 5) -> List[InscriptionRecord]:
        """Collect inscriptions of a specific type"""
        print(f"\n[COLLECTING] {mime_type} (max: {max_count})")
        print("-" * 50)

        records = []
        offset = 0
        limit = min(60, max_count)

        while len(records) < max_count:
            try:
                page = self.get_inscriptions_page(mime_type=mime_type, offset=offset, limit=limit)
                inscriptions = page.get('results', [])

                if not inscriptions:
                    break

                print(f"  Fetched {len(inscriptions)} inscriptions (offset: {offset})")

                # Download in parallel
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {executor.submit(self.download_inscription, insc): insc
                               for insc in inscriptions}

                    for future in as_completed(futures):
                        record = future.result()
                        if record:
                            records.append(record)
                            print(f"  ✓ {record.number} - {record.content_type} ({record.content_length:,} bytes)")

                offset += len(inscriptions)
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                print(f"  Page error: {e}")
                break

        print(f"  Collected {len(records)} {mime_type} inscriptions")
        return records

    def collect_all_types(self, per_type: int = 50) -> Dict[str, List[InscriptionRecord]]:
        """Collect multiple content types"""
        types = [
            'image/png',
            'image/webp',
            'image/gif',
            'text/plain',
            'text/html',
            'application/json',
        ]

        all_records = {}
        for mime_type in types:
            records = self.collect_by_type(mime_type, max_count=per_type)
            all_records[mime_type] = records
            time.sleep(1)  # Rate limiting between types

        return all_records


class ArweaveCollector:
    """Collect data from Arweave"""

    def __init__(self):
        self.gateway = "https://arweave.net"
        self.graphql = f"{self.gateway}/graphql"
        self.session = requests.Session()

    def search_by_content_type(self, content_type: str, first: int = 50) -> List[Dict]:
        """Search for transactions by content type"""
        query = """
        query {
            transactions(
                first: %d,
                tags: [{ name: "Content-Type", values: ["%s"] }]
            ) {
                edges {
                    node {
                        id
                        tags { name value }
                        data { size type }
                        block { height timestamp }
                    }
                }
            }
        }
        """ % (first, content_type)

        resp = self.session.post(self.graphql, json={'query': query}, timeout=30)
        data = resp.json()
        edges = data.get('data', {}).get('transactions', {}).get('edges', [])
        return [edge['node'] for edge in edges]

    def download_transaction(self, tx_id: str) -> bytes:
        """Download transaction data"""
        url = f"{self.gateway}/{tx_id}"
        resp = self.session.get(url, timeout=60)
        resp.raise_for_status()
        return resp.content

    def collect_by_type(self, content_type: str, max_count: int = 20) -> List[Dict]:
        """Collect Arweave data by content type"""
        print(f"\n[ARWEAVE] Collecting {content_type}")
        print("-" * 50)

        try:
            txs = self.search_by_content_type(content_type, first=max_count)
            print(f"  Found {len(txs)} transactions")

            records = []
            for tx in txs:
                try:
                    tx_id = tx['id']
                    content = self.download_transaction(tx_id)

                    # Determine extension
                    ext = '.bin'
                    if 'png' in content_type:
                        ext = '.png'
                    elif 'jpeg' in content_type or 'jpg' in content_type:
                        ext = '.jpg'
                    elif 'json' in content_type:
                        ext = '.json'
                    elif 'text' in content_type:
                        ext = '.txt'

                    # Save file
                    category = content_type.split('/')[0]
                    category_dir = ARWEAVE_DIR / category
                    category_dir.mkdir(exist_ok=True)

                    file_hash = hashlib.sha256(content).hexdigest()[:16]
                    filepath = category_dir / f"ar_{file_hash}{ext}"
                    filepath.write_bytes(content)

                    records.append({
                        'id': tx_id,
                        'content_type': content_type,
                        'size': len(content),
                        'local_path': str(filepath),
                        'block_height': tx.get('block', {}).get('height'),
                        'source': 'arweave'
                    })

                    print(f"  ✓ {tx_id[:20]}... ({len(content):,} bytes)")
                    time.sleep(0.2)

                except Exception as e:
                    print(f"  ✗ {tx['id'][:20]}: {e}")

            return records

        except Exception as e:
            print(f"  Error: {e}")
            return []


def save_metadata(records: List, filename: str):
    """Save metadata to JSON"""
    filepath = METADATA_DIR / filename
    data = [asdict(r) if hasattr(r, '__dataclass_fields__') else r for r in records]
    filepath.write_text(json.dumps(data, indent=2))
    print(f"\n[SAVED] {filepath} ({len(data)} records)")


def generate_dataset_stats():
    """Generate statistics about collected data"""
    stats = {
        'generated_at': datetime.now().isoformat(),
        'ordinals': {},
        'arweave': {},
    }

    # Count Ordinals files
    for category in ORDINALS_DIR.iterdir():
        if category.is_dir():
            files = list(category.glob('*'))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            stats['ordinals'][category.name] = {
                'count': len(files),
                'total_bytes': total_size,
                'total_mb': round(total_size / 1024 / 1024, 2)
            }

    # Count Arweave files
    for category in ARWEAVE_DIR.iterdir():
        if category.is_dir():
            files = list(category.glob('*'))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            stats['arweave'][category.name] = {
                'count': len(files),
                'total_bytes': total_size,
                'total_mb': round(total_size / 1024 / 1024, 2)
            }

    # Save stats
    stats_file = DATA_DIR / 'dataset_stats.json'
    stats_file.write_text(json.dumps(stats, indent=2))
    return stats


def main():
    print("=" * 60)
    print("BLOCKCHAIN DATA COLLECTOR FOR AI TRAINING")
    print("=" * 60)
    print(f"\nData directory: {DATA_DIR}")

    # Collect Ordinals
    ordinals = OrdinalsCollector()
    all_ordinals = ordinals.collect_all_types(per_type=10)  # Small batch for testing

    # Save Ordinals metadata
    all_records = []
    for mime_type, records in all_ordinals.items():
        all_records.extend(records)
    save_metadata(all_records, 'ordinals_metadata.json')

    # Collect Arweave
    arweave = ArweaveCollector()
    ar_records = []
    for content_type in ['image/png', 'text/plain', 'application/json']:
        records = arweave.collect_by_type(content_type, max_count=5)
        ar_records.extend(records)
    save_metadata(ar_records, 'arweave_metadata.json')

    # Generate stats
    stats = generate_dataset_stats()

    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
