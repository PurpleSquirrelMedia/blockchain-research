#!/usr/bin/env python3
"""
Arweave permanent storage data collector.
Arweave stores petabytes of data with a 200-year endowment model.
"""

import requests
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

DATA_DIR = Path("/Volumes/Virtual Server/Projects/blockchain-research/data")
ARWEAVE_DIR = DATA_DIR / "arweave"


class ArweaveCollector:
    """Collect data from Arweave permanent storage."""

    def __init__(self):
        self.gateways = [
            'https://arweave.net',
            'https://ar-io.net',
            'https://g8way.io',
        ]
        self.graphql_endpoint = 'https://arweave.net/graphql'
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'BlockchainResearch/1.0'
        ARWEAVE_DIR.mkdir(parents=True, exist_ok=True)

    def graphql_query(self, query: str, variables: dict = None) -> dict:
        """Execute GraphQL query against Arweave."""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        resp = self.session.post(
            self.graphql_endpoint,
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def search_by_content_type(self, content_type: str, limit: int = 100) -> List[Dict]:
        """Search for transactions by content type."""
        query = """
        query($contentType: String!, $first: Int!) {
            transactions(
                tags: [
                    { name: "Content-Type", values: [$contentType] }
                ]
                first: $first
            ) {
                edges {
                    node {
                        id
                        data {
                            size
                            type
                        }
                        tags {
                            name
                            value
                        }
                        block {
                            height
                            timestamp
                        }
                    }
                }
            }
        }
        """
        result = self.graphql_query(query, {
            'contentType': content_type,
            'first': limit
        })
        return [edge['node'] for edge in result.get('data', {}).get('transactions', {}).get('edges', [])]

    def search_by_app(self, app_name: str, limit: int = 100) -> List[Dict]:
        """Search for transactions by app name."""
        query = """
        query($appName: String!, $first: Int!) {
            transactions(
                tags: [
                    { name: "App-Name", values: [$appName] }
                ]
                first: $first
            ) {
                edges {
                    node {
                        id
                        data {
                            size
                            type
                        }
                        tags {
                            name
                            value
                        }
                        block {
                            height
                            timestamp
                        }
                    }
                }
            }
        }
        """
        result = self.graphql_query(query, {
            'appName': app_name,
            'first': limit
        })
        return [edge['node'] for edge in result.get('data', {}).get('transactions', {}).get('edges', [])]

    def get_recent_transactions(self, limit: int = 100) -> List[Dict]:
        """Get recent transactions."""
        query = """
        query($first: Int!) {
            transactions(first: $first) {
                edges {
                    node {
                        id
                        data {
                            size
                            type
                        }
                        tags {
                            name
                            value
                        }
                        block {
                            height
                            timestamp
                        }
                    }
                }
            }
        }
        """
        result = self.graphql_query(query, {'first': limit})
        return [edge['node'] for edge in result.get('data', {}).get('transactions', {}).get('edges', [])]

    def fetch_content(self, tx_id: str) -> Optional[bytes]:
        """Fetch transaction content with gateway fallback."""
        for gateway in self.gateways:
            try:
                url = f"{gateway}/{tx_id}"
                resp = self.session.get(url, timeout=60)
                if resp.status_code == 200:
                    return resp.content
            except Exception as e:
                continue
        return None

    def save_transaction(self, tx: Dict, content: bytes) -> Dict:
        """Save transaction content to disk."""
        tx_id = tx.get('id', '')
        tags = {t['name']: t['value'] for t in tx.get('tags', [])}

        content_type = tags.get('Content-Type', tx.get('data', {}).get('type', 'application/octet-stream'))

        # Determine extension
        ext_map = {
            'image/png': '.png', 'image/webp': '.webp', 'image/gif': '.gif',
            'image/jpeg': '.jpg', 'image/svg+xml': '.svg',
            'text/plain': '.txt', 'text/html': '.html',
            'application/json': '.json', 'audio/mpeg': '.mp3',
            'video/mp4': '.mp4', 'application/pdf': '.pdf'
        }
        ext = ext_map.get(content_type.split(';')[0], '.bin')

        # Category folder
        category = content_type.split('/')[0] if '/' in content_type else 'other'
        category_dir = ARWEAVE_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Save
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        block_height = tx.get('block', {}).get('height', 0)
        filename = f"{block_height}_{file_hash}{ext}"
        filepath = category_dir / filename
        filepath.write_bytes(content)

        return {
            'id': tx_id,
            'chain': 'arweave',
            'block_height': block_height,
            'timestamp': tx.get('block', {}).get('timestamp'),
            'content_type': content_type,
            'content_length': len(content),
            'file_hash': file_hash,
            'local_path': str(filepath),
            'tags': tags,
            'app_name': tags.get('App-Name'),
        }

    def collect_by_type(self, content_type: str, count: int = 20) -> List[Dict]:
        """Collect transactions by content type."""
        print(f"\n[ARWEAVE] Collecting {content_type} (target: {count})")
        print("-" * 50)

        records = []
        try:
            transactions = self.search_by_content_type(content_type, count * 2)
            print(f"  Found {len(transactions)} transactions")

            for tx in transactions[:count]:
                try:
                    # Skip large files (>1MB)
                    size = tx.get('data', {}).get('size')
                    if size and int(size) > 1_000_000:
                        print(f"  - {tx['id'][:16]}... (skipping, {int(size)/1024:.0f}KB)")
                        continue

                    content = self.fetch_content(tx['id'])
                    if content:
                        record = self.save_transaction(tx, content)
                        records.append(record)
                        print(f"  ✓ {tx['id'][:16]}... ({len(content):,} bytes)")
                    else:
                        print(f"  ✗ {tx['id'][:16]}... (fetch failed)")

                    time.sleep(0.3)

                except Exception as e:
                    print(f"  ✗ Error: {e}")

                if len(records) >= count:
                    break

        except Exception as e:
            print(f"  Error: {e}")

        print(f"  Collected {len(records)} {content_type}")
        return records

    def collect_by_app(self, app_name: str, count: int = 20) -> List[Dict]:
        """Collect transactions by app name."""
        print(f"\n[ARWEAVE] Collecting from app: {app_name} (target: {count})")
        print("-" * 50)

        records = []
        try:
            transactions = self.search_by_app(app_name, count * 2)
            print(f"  Found {len(transactions)} transactions")

            for tx in transactions[:count]:
                try:
                    size = tx.get('data', {}).get('size')
                    if size and int(size) > 1_000_000:
                        continue

                    content = self.fetch_content(tx['id'])
                    if content:
                        record = self.save_transaction(tx, content)
                        records.append(record)
                        print(f"  ✓ {tx['id'][:16]}... ({len(content):,} bytes)")

                    time.sleep(0.3)

                except Exception as e:
                    print(f"  ✗ Error: {e}")

                if len(records) >= count:
                    break

        except Exception as e:
            print(f"  Error: {e}")

        return records


def main():
    print("=" * 60)
    print("ARWEAVE PERMANENT STORAGE COLLECTOR")
    print("=" * 60)

    collector = ArweaveCollector()

    all_records = []

    # Collect by content type
    content_types = [
        ('image/png', 15),
        ('image/gif', 10),
        ('text/plain', 15),
        ('application/json', 15),
        ('text/html', 10),
    ]

    for ct, count in content_types:
        records = collector.collect_by_type(ct, count)
        all_records.extend(records)
        print(f"  Total: {len(all_records)}")
        time.sleep(1)

    # Collect by popular apps
    apps = [
        ('ArDrive', 10),
        ('ArConnect', 5),
    ]

    for app, count in apps:
        try:
            records = collector.collect_by_app(app, count)
            all_records.extend(records)
        except:
            pass

    # Save metadata
    metadata_file = DATA_DIR / "metadata" / "arweave_collection.json"
    metadata_file.write_text(json.dumps(all_records, indent=2))

    print("\n" + "=" * 60)
    print(f"COLLECTED {len(all_records)} ARWEAVE TRANSACTIONS")
    print("=" * 60)
    print(f"Saved to: {metadata_file}")


if __name__ == '__main__':
    main()
