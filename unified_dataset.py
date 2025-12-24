#!/usr/bin/env python3
"""
Generate unified multi-chain dataset for AI training.
Combines data from Bitcoin, Arweave, Solana, and other chains.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict
from datetime import datetime

DATA_DIR = Path("/Volumes/Virtual Server/Projects/blockchain-research/data")
OUTPUT_DIR = DATA_DIR / "unified"


@dataclass
class UnifiedRecord:
    """Unified schema for all blockchain data."""
    # Core identifiers
    id: str
    chain: str
    chain_id: str  # Chain-specific ID

    # Content info
    content_type: str
    content_hash: str
    content_length: int
    local_path: str

    # Temporal
    block_height: int = 0
    timestamp: int = 0

    # Chain-specific metadata
    inscription_number: int = 0  # Bitcoin Ordinals
    collection: str = ""         # NFT collection
    name: str = ""               # NFT/inscription name
    protocol: str = ""           # BRC-20, Sparkle, etc.

    # Analysis flags
    is_recursive: bool = False
    is_nft: bool = False
    is_protocol_data: bool = False

    # Quality signals
    price_usd: float = 0.0       # Market value if known
    rarity_score: float = 0.0    # Calculated rarity


class UnifiedDatasetGenerator:
    """Generate unified dataset from all collected data."""

    def __init__(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.records: List[UnifiedRecord] = []

    def load_bitcoin_data(self):
        """Load Bitcoin Ordinals data."""
        print("\n[LOADING] Bitcoin Ordinals")

        metadata_files = [
            'robust_collection.json',
            'ordinals_metadata.json',
            'ordinals_large_metadata.json',
            'extended_collection.json',
        ]

        for filename in metadata_files:
            filepath = DATA_DIR / "metadata" / filename
            if not filepath.exists():
                continue

            try:
                data = json.loads(filepath.read_text())
                if not isinstance(data, list):
                    continue

                for item in data:
                    record = UnifiedRecord(
                        id=hashlib.sha256(item.get('id', '').encode()).hexdigest()[:32],
                        chain='bitcoin',
                        chain_id=item.get('id', ''),
                        content_type=item.get('content_type', ''),
                        content_hash=item.get('file_hash', ''),
                        content_length=item.get('content_length', 0),
                        local_path=item.get('local_path', ''),
                        inscription_number=item.get('number', 0),
                    )

                    # Detect protocol data
                    if 'brc-20' in record.content_type.lower() or 'json' in record.content_type:
                        record.is_protocol_data = True
                        record.protocol = 'brc-20'

                    self.records.append(record)

                print(f"  Loaded {len(data)} from {filename}")

            except Exception as e:
                print(f"  Error loading {filename}: {e}")

    def load_arweave_data(self):
        """Load Arweave data."""
        print("\n[LOADING] Arweave")

        filepath = DATA_DIR / "metadata" / "arweave_collection.json"
        if not filepath.exists():
            # Scan arweave directory directly
            arweave_dir = DATA_DIR / "arweave"
            if arweave_dir.exists():
                count = 0
                for category_dir in arweave_dir.iterdir():
                    if not category_dir.is_dir():
                        continue
                    for file in category_dir.iterdir():
                        if file.suffix in ['.png', '.gif', '.jpg', '.webp', '.svg']:
                            content = file.read_bytes()
                            record = UnifiedRecord(
                                id=hashlib.sha256(file.name.encode()).hexdigest()[:32],
                                chain='arweave',
                                chain_id=file.stem,
                                content_type=f"image/{file.suffix[1:]}",
                                content_hash=hashlib.sha256(content).hexdigest()[:16],
                                content_length=len(content),
                                local_path=str(file),
                            )
                            self.records.append(record)
                            count += 1
                print(f"  Loaded {count} from directory scan")
            return

        try:
            data = json.loads(filepath.read_text())
            for item in data:
                record = UnifiedRecord(
                    id=hashlib.sha256(item.get('id', '').encode()).hexdigest()[:32],
                    chain='arweave',
                    chain_id=item.get('id', ''),
                    content_type=item.get('content_type', ''),
                    content_hash=item.get('file_hash', ''),
                    content_length=item.get('content_length', 0),
                    local_path=item.get('local_path', ''),
                    block_height=item.get('block_height', 0),
                    timestamp=item.get('timestamp', 0),
                )
                self.records.append(record)
            print(f"  Loaded {len(data)} records")
        except Exception as e:
            print(f"  Error: {e}")

    def load_solana_data(self):
        """Load Solana NFT data."""
        print("\n[LOADING] Solana")

        filepath = DATA_DIR / "metadata" / "solana_collection.json"
        if not filepath.exists():
            # Scan solana directory
            solana_dir = DATA_DIR / "solana"
            if solana_dir.exists():
                count = 0
                for collection_dir in (solana_dir / "nfts").iterdir() if (solana_dir / "nfts").exists() else []:
                    if not collection_dir.is_dir():
                        continue
                    for file in collection_dir.iterdir():
                        if file.suffix in ['.png', '.gif', '.jpg', '.webp']:
                            content = file.read_bytes()
                            record = UnifiedRecord(
                                id=hashlib.sha256(file.name.encode()).hexdigest()[:32],
                                chain='solana',
                                chain_id=file.stem.split('_')[0],
                                content_type=f"image/{file.suffix[1:]}",
                                content_hash=hashlib.sha256(content).hexdigest()[:16],
                                content_length=len(content),
                                local_path=str(file),
                                collection=collection_dir.name,
                                is_nft=True,
                            )
                            self.records.append(record)
                            count += 1
                print(f"  Loaded {count} from directory scan")
            return

        try:
            data = json.loads(filepath.read_text())
            for item in data:
                record = UnifiedRecord(
                    id=hashlib.sha256(item.get('id', '').encode()).hexdigest()[:32],
                    chain='solana',
                    chain_id=item.get('id', ''),
                    content_type=item.get('content_type', ''),
                    content_hash=item.get('file_hash', ''),
                    content_length=item.get('content_length', 0),
                    local_path=item.get('local_path', ''),
                    collection=item.get('collection', ''),
                    name=item.get('name', ''),
                    is_nft=True,
                    price_usd=item.get('price', 0) or 0,
                )
                self.records.append(record)
            print(f"  Loaded {len(data)} records")
        except Exception as e:
            print(f"  Error: {e}")

    def deduplicate(self):
        """Remove duplicate records by content hash."""
        print("\n[DEDUPLICATING]")
        original = len(self.records)

        seen = set()
        unique = []
        for record in self.records:
            key = f"{record.chain}:{record.content_hash}"
            if key not in seen:
                seen.add(key)
                unique.append(record)

        self.records = unique
        removed = original - len(self.records)
        print(f"  Removed {removed} duplicates, {len(self.records)} unique records")

    def generate_stats(self) -> Dict:
        """Generate dataset statistics."""
        stats = {
            'generated_at': datetime.now().isoformat(),
            'total_records': len(self.records),
            'total_bytes': sum(r.content_length for r in self.records),
            'by_chain': {},
            'by_content_type': {},
            'nft_count': 0,
            'protocol_data_count': 0,
            'recursive_count': 0,
        }

        for record in self.records:
            # By chain
            if record.chain not in stats['by_chain']:
                stats['by_chain'][record.chain] = {'count': 0, 'bytes': 0}
            stats['by_chain'][record.chain]['count'] += 1
            stats['by_chain'][record.chain]['bytes'] += record.content_length

            # By content type
            ct = record.content_type.split(';')[0]
            if ct not in stats['by_content_type']:
                stats['by_content_type'][ct] = 0
            stats['by_content_type'][ct] += 1

            # Flags
            if record.is_nft:
                stats['nft_count'] += 1
            if record.is_protocol_data:
                stats['protocol_data_count'] += 1
            if record.is_recursive:
                stats['recursive_count'] += 1

        stats['total_mb'] = stats['total_bytes'] / (1024 * 1024)
        return stats

    def export(self):
        """Export unified dataset."""
        print("\n[EXPORTING]")

        # Export as JSONL (for ML pipelines)
        jsonl_file = OUTPUT_DIR / "blockchain_unified.jsonl"
        with open(jsonl_file, 'w') as f:
            for record in self.records:
                f.write(json.dumps(asdict(record)) + '\n')
        print(f"  JSONL: {jsonl_file}")

        # Export as JSON (for inspection)
        json_file = OUTPUT_DIR / "blockchain_unified.json"
        json_file.write_text(json.dumps([asdict(r) for r in self.records], indent=2))
        print(f"  JSON: {json_file}")

        # Export by chain
        chains = {}
        for record in self.records:
            if record.chain not in chains:
                chains[record.chain] = []
            chains[record.chain].append(asdict(record))

        for chain, records in chains.items():
            chain_file = OUTPUT_DIR / f"{chain}.jsonl"
            with open(chain_file, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
            print(f"  {chain}: {len(records)} records -> {chain_file}")

        # Export stats
        stats = self.generate_stats()
        stats_file = OUTPUT_DIR / "stats.json"
        stats_file.write_text(json.dumps(stats, indent=2))
        print(f"  Stats: {stats_file}")

        return stats

    def run(self):
        """Generate unified dataset."""
        print("=" * 60)
        print("UNIFIED MULTI-CHAIN DATASET GENERATOR")
        print("=" * 60)

        self.load_bitcoin_data()
        self.load_arweave_data()
        self.load_solana_data()

        self.deduplicate()

        stats = self.export()

        print("\n" + "=" * 60)
        print("DATASET SUMMARY")
        print("=" * 60)
        print(f"Total records: {stats['total_records']}")
        print(f"Total size: {stats['total_mb']:.2f} MB")
        print(f"\nBy chain:")
        for chain, data in stats['by_chain'].items():
            mb = data['bytes'] / (1024 * 1024)
            print(f"  {chain}: {data['count']} records ({mb:.2f} MB)")
        print(f"\nNFTs: {stats['nft_count']}")
        print(f"Protocol data: {stats['protocol_data_count']}")
        print(f"\nOutput: {OUTPUT_DIR}")


def main():
    generator = UnifiedDatasetGenerator()
    generator.run()


if __name__ == '__main__':
    main()
