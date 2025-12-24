#!/usr/bin/env python3
"""
Robust multi-API collector with rate limiting and fallbacks.
"""

import requests
import time
import json
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional

DATA_DIR = Path("/Volumes/Virtual Server/Projects/blockchain-research/data")
ORDINALS_DIR = DATA_DIR / "ordinals"

class MultiAPICollector:
    """Collector with multiple API fallbacks and smart rate limiting."""

    def __init__(self):
        self.apis = {
            'hiro': {
                'base': 'https://api.hiro.so/ordinals/v1',
                'rate_limit': 60,  # per minute
                'last_call': 0,
                'calls_this_minute': 0
            },
            'ordiscan': {
                'base': 'https://api.ordiscan.com/v1',
                'rate_limit': 100,
                'last_call': 0,
                'calls_this_minute': 0
            },
            'bestinslot': {
                'base': 'https://api.bestinslot.xyz/v3',
                'rate_limit': 30,
                'last_call': 0,
                'calls_this_minute': 0
            }
        }
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'BlockchainResearch/1.0'

    def _wait_for_rate_limit(self, api_name: str):
        """Smart rate limiting per API."""
        api = self.apis[api_name]
        now = time.time()

        # Reset counter every minute
        if now - api['last_call'] > 60:
            api['calls_this_minute'] = 0

        # If at limit, wait
        if api['calls_this_minute'] >= api['rate_limit']:
            wait_time = 60 - (now - api['last_call'])
            if wait_time > 0:
                print(f"    Rate limit hit on {api_name}, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                api['calls_this_minute'] = 0

        api['calls_this_minute'] += 1
        api['last_call'] = time.time()

    def fetch_inscriptions_hiro(self, mime_type: str, offset: int, limit: int) -> List[Dict]:
        """Fetch from Hiro API."""
        self._wait_for_rate_limit('hiro')
        url = f"{self.apis['hiro']['base']}/inscriptions"
        params = {'mime_type': mime_type, 'offset': offset, 'limit': limit}
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get('results', [])

    def fetch_inscriptions_ordiscan(self, mime_type: str, offset: int, limit: int) -> List[Dict]:
        """Fetch from Ordiscan API."""
        self._wait_for_rate_limit('ordiscan')
        # Ordiscan has different endpoint structure
        url = f"{self.apis['ordiscan']['base']}/inscriptions"
        params = {'content_type': mime_type, 'offset': offset, 'limit': limit}
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json().get('data', [])
        except:
            return []

    def fetch_content_hiro(self, inscription_id: str) -> Optional[bytes]:
        """Fetch content from Hiro."""
        self._wait_for_rate_limit('hiro')
        url = f"{self.apis['hiro']['base']}/inscriptions/{inscription_id}/content"
        try:
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            return None

    def fetch_content_ordinals_com(self, inscription_id: str) -> Optional[bytes]:
        """Fetch directly from ordinals.com (no rate limit)."""
        url = f"https://ordinals.com/content/{inscription_id}"
        try:
            resp = self.session.get(url, timeout=60)
            resp.raise_for_status()
            return resp.content
        except:
            return None

    def fetch_with_fallback(self, inscription_id: str) -> Optional[bytes]:
        """Try multiple sources for content."""
        # Try ordinals.com first (no rate limit)
        content = self.fetch_content_ordinals_com(inscription_id)
        if content:
            return content

        # Fallback to Hiro
        content = self.fetch_content_hiro(inscription_id)
        if content:
            return content

        return None

    def save_inscription(self, inscription: Dict, content: bytes) -> Dict:
        """Save inscription to disk."""
        content_type = inscription.get('content_type', 'application/octet-stream')
        number = inscription.get('number', 0)
        inscription_id = inscription.get('id', '')

        # Determine extension
        ext_map = {
            'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif',
            'image/jpeg': '.jpg', 'image/svg+xml': '.svg',
            'text/plain': '.txt', 'text/html': '.html',
            'application/json': '.json', 'audio/mpeg': '.mp3'
        }
        ext = ext_map.get(content_type, '.bin')

        # Category folder
        category = content_type.split('/')[0] if '/' in content_type else 'other'
        category_dir = ORDINALS_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Save
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        filename = f"{number}_{file_hash}{ext}"
        filepath = category_dir / filename
        filepath.write_bytes(content)

        return {
            'id': inscription_id,
            'number': number,
            'content_type': content_type,
            'content_length': len(content),
            'file_hash': file_hash,
            'local_path': str(filepath)
        }

    def collect(self, mime_type: str, count: int = 50) -> List[Dict]:
        """Collect inscriptions with smart rate limiting."""
        print(f"\n[COLLECTING] {mime_type} (target: {count})")
        print("-" * 50)

        records = []
        offset = 0

        while len(records) < count:
            try:
                # Fetch batch
                inscriptions = self.fetch_inscriptions_hiro(mime_type, offset, min(20, count - len(records)))
                if not inscriptions:
                    break

                print(f"  Fetched {len(inscriptions)} inscriptions (offset: {offset})")

                # Download each with fallback
                for insc in inscriptions:
                    content = self.fetch_with_fallback(insc['id'])
                    if content:
                        record = self.save_inscription(insc, content)
                        records.append(record)
                        print(f"  ✓ {record['number']} ({record['content_length']:,} bytes)")
                    else:
                        print(f"  ✗ {insc.get('number', 'unknown')} - failed all sources")

                    # Small delay between downloads
                    time.sleep(0.5)

                offset += len(inscriptions)

            except Exception as e:
                print(f"  Error: {e}")
                time.sleep(5)  # Wait on error

        print(f"  Collected {len(records)} {mime_type}")
        return records


def main():
    print("=" * 60)
    print("ROBUST MULTI-API COLLECTOR")
    print("=" * 60)

    collector = MultiAPICollector()

    targets = [
        ('image/png', 30),
        ('image/webp', 30),
        ('image/gif', 20),
        ('text/plain', 20),
        ('text/html', 20),
    ]

    all_records = []
    for mime_type, count in targets:
        records = collector.collect(mime_type, count)
        all_records.extend(records)
        print(f"  Total: {len(all_records)}")
        time.sleep(5)  # Pause between types

    # Save metadata
    metadata_file = DATA_DIR / "metadata" / "robust_collection.json"
    metadata_file.parent.mkdir(exist_ok=True)
    metadata_file.write_text(json.dumps(all_records, indent=2))
    print(f"\n[SAVED] {metadata_file} ({len(all_records)} records)")


if __name__ == '__main__':
    main()
