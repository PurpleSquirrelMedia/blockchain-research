#!/usr/bin/env python3
"""
Solana NFT and on-chain data collector.
Collects Metaplex NFTs and other permanent Solana data.
"""

import requests
import json
import time
import hashlib
import base64
from pathlib import Path
from typing import List, Dict, Optional

DATA_DIR = Path("/Volumes/Virtual Server/Projects/blockchain-research/data")
SOLANA_DIR = DATA_DIR / "solana"


class SolanaCollector:
    """Collect NFTs and data from Solana."""

    def __init__(self):
        self.rpc_endpoints = [
            'https://api.mainnet-beta.solana.com',
            'https://solana-mainnet.g.alchemy.com/v2/demo',
        ]
        self.helius_api = 'https://mainnet.helius-rpc.com/?api-key=demo'
        self.session = requests.Session()
        self.session.headers['Content-Type'] = 'application/json'
        SOLANA_DIR.mkdir(parents=True, exist_ok=True)

    def rpc_call(self, method: str, params: list = None) -> dict:
        """Make RPC call to Solana."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }

        for endpoint in self.rpc_endpoints:
            try:
                resp = self.session.post(endpoint, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()
            except:
                continue
        return {}

    def get_nft_metadata_from_uri(self, uri: str) -> Optional[dict]:
        """Fetch NFT metadata from URI."""
        try:
            # Handle IPFS URIs
            if uri.startswith('ipfs://'):
                uri = f"https://ipfs.io/ipfs/{uri[7:]}"
            elif uri.startswith('ar://'):
                uri = f"https://arweave.net/{uri[5:]}"

            resp = self.session.get(uri, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def get_nft_image(self, image_url: str) -> Optional[bytes]:
        """Download NFT image."""
        try:
            if image_url.startswith('ipfs://'):
                image_url = f"https://ipfs.io/ipfs/{image_url[7:]}"
            elif image_url.startswith('ar://'):
                image_url = f"https://arweave.net/{image_url[5:]}"

            resp = self.session.get(image_url, timeout=60)
            if resp.status_code == 200:
                return resp.content
        except:
            pass
        return None

    def search_nfts_magiceden(self, collection: str = None, limit: int = 20) -> List[Dict]:
        """Search NFTs via Magic Eden API."""
        try:
            if collection:
                url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection}/listings"
            else:
                url = "https://api-mainnet.magiceden.dev/v2/marketplace/popular_collections"

            params = {'limit': limit}
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json() if isinstance(resp.json(), list) else []
        except Exception as e:
            print(f"  Magic Eden error: {e}")
        return []

    def get_popular_collections(self) -> List[str]:
        """Get list of popular NFT collections."""
        collections = []
        try:
            url = "https://api-mainnet.magiceden.dev/v2/marketplace/popular_collections"
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                collections = [c.get('symbol') for c in data if c.get('symbol')]
        except:
            pass
        return collections[:10]

    def collect_collection_nfts(self, collection_symbol: str, count: int = 10) -> List[Dict]:
        """Collect NFTs from a specific collection."""
        print(f"\n[SOLANA] Collecting from: {collection_symbol}")
        print("-" * 50)

        records = []

        try:
            # Get listings
            url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection_symbol}/listings"
            resp = self.session.get(url, params={'limit': count * 2}, timeout=30)

            if resp.status_code != 200:
                print(f"  Failed to get listings: {resp.status_code}")
                return records

            listings = resp.json()
            print(f"  Found {len(listings)} listings")

            for listing in listings[:count]:
                try:
                    mint = listing.get('tokenMint', '')
                    if not mint:
                        continue

                    # Get token metadata
                    token_url = f"https://api-mainnet.magiceden.dev/v2/tokens/{mint}"
                    token_resp = self.session.get(token_url, timeout=30)

                    if token_resp.status_code != 200:
                        continue

                    token_data = token_resp.json()
                    image_url = token_data.get('image', '')
                    name = token_data.get('name', 'Unknown')

                    if not image_url:
                        continue

                    # Download image
                    image_data = self.get_nft_image(image_url)
                    if not image_data:
                        print(f"  ✗ {name[:30]} - image download failed")
                        continue

                    # Save image
                    file_hash = hashlib.sha256(image_data).hexdigest()[:16]

                    # Determine extension
                    content_type = 'image/png'
                    ext = '.png'
                    if image_url.endswith('.gif'):
                        ext = '.gif'
                        content_type = 'image/gif'
                    elif image_url.endswith('.jpg') or image_url.endswith('.jpeg'):
                        ext = '.jpg'
                        content_type = 'image/jpeg'
                    elif image_url.endswith('.webp'):
                        ext = '.webp'
                        content_type = 'image/webp'

                    category_dir = SOLANA_DIR / "nfts" / collection_symbol
                    category_dir.mkdir(parents=True, exist_ok=True)

                    filename = f"{mint[:16]}_{file_hash}{ext}"
                    filepath = category_dir / filename
                    filepath.write_bytes(image_data)

                    record = {
                        'id': mint,
                        'chain': 'solana',
                        'collection': collection_symbol,
                        'name': name,
                        'content_type': content_type,
                        'content_length': len(image_data),
                        'file_hash': file_hash,
                        'local_path': str(filepath),
                        'price': listing.get('price'),
                        'seller': listing.get('seller'),
                    }
                    records.append(record)
                    print(f"  ✓ {name[:30]} ({len(image_data):,} bytes)")

                    time.sleep(0.5)

                except Exception as e:
                    print(f"  ✗ Error: {e}")

                if len(records) >= count:
                    break

        except Exception as e:
            print(f"  Collection error: {e}")

        print(f"  Collected {len(records)} NFTs")
        return records

    def collect_popular_nfts(self, count_per_collection: int = 5) -> List[Dict]:
        """Collect NFTs from popular collections."""
        print("=" * 60)
        print("SOLANA NFT COLLECTOR")
        print("=" * 60)

        all_records = []

        # Get popular collections
        collections = self.get_popular_collections()
        print(f"\nFound {len(collections)} popular collections")

        for collection in collections[:5]:  # Limit to 5 collections
            records = self.collect_collection_nfts(collection, count_per_collection)
            all_records.extend(records)
            print(f"  Total: {len(all_records)}")
            time.sleep(2)

        # Save metadata
        if all_records:
            metadata_file = DATA_DIR / "metadata" / "solana_collection.json"
            metadata_file.write_text(json.dumps(all_records, indent=2))
            print(f"\n[SAVED] {metadata_file} ({len(all_records)} records)")

        return all_records


def main():
    collector = SolanaCollector()
    records = collector.collect_popular_nfts(count_per_collection=5)

    print("\n" + "=" * 60)
    print(f"TOTAL COLLECTED: {len(records)} Solana NFTs")
    print("=" * 60)


if __name__ == '__main__':
    main()
