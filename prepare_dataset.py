#!/usr/bin/env python3
"""
Prepare collected blockchain inscriptions for AI training.
Outputs datasets in formats suitable for various ML frameworks.
"""

import json
import base64
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import shutil

DATA_DIR = Path("/Volumes/Virtual Server/Projects/blockchain-research/data")
OUTPUT_DIR = DATA_DIR / "training"

@dataclass
class TrainingExample:
    """Single training example."""
    id: str
    inscription_number: int
    content_type: str
    chain: str
    content_hash: str
    file_path: str
    # For images
    image_base64: Optional[str] = None
    # For text
    text_content: Optional[str] = None
    # Metadata
    is_recursive: bool = False
    is_brc20: bool = False
    protocol: Optional[str] = None


class DatasetPreparer:
    """Prepare datasets for AI training."""

    def __init__(self):
        self.metadata = self._load_all_metadata()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _load_all_metadata(self) -> List[Dict]:
        """Load all metadata files."""
        records = []
        for f in (DATA_DIR / "metadata").glob("*.json"):
            if 'analysis' in f.name or 'stats' in f.name:
                continue
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    records.extend(data)
            except:
                pass
        # Deduplicate by ID
        seen = set()
        unique = []
        for r in records:
            rid = r.get('id', '')
            if rid and rid not in seen:
                seen.add(rid)
                unique.append(r)
        return unique

    def _detect_recursive(self, content: bytes) -> bool:
        """Detect if content references other inscriptions."""
        text = content.decode('utf-8', errors='ignore')
        return '/content/' in text or 'inscription' in text.lower()

    def _detect_brc20(self, content: bytes) -> tuple:
        """Detect BRC-20 or other protocols."""
        try:
            text = content.decode('utf-8')
            data = json.loads(text)
            if data.get('p') == 'brc-20':
                return True, 'brc-20', data
            elif data.get('p'):
                return False, data.get('p'), data
        except:
            pass
        return False, None, None

    def prepare_image_dataset(self) -> Path:
        """Prepare image dataset for vision models."""
        print("\n[PREPARING] Image Dataset")
        print("-" * 50)

        image_dir = OUTPUT_DIR / "images"
        image_dir.mkdir(exist_ok=True)

        manifest = []
        image_types = {'image/png', 'image/webp', 'image/gif', 'image/jpeg', 'image/svg+xml'}

        for record in self.metadata:
            if record.get('content_type') not in image_types:
                continue

            path = Path(record.get('local_path', ''))
            if not path.exists():
                continue

            try:
                content = path.read_bytes()
                is_recursive = self._detect_recursive(content)

                # Copy to training dir
                dest = image_dir / path.name
                shutil.copy(path, dest)

                example = TrainingExample(
                    id=record.get('id', ''),
                    inscription_number=record.get('number', 0),
                    content_type=record.get('content_type', ''),
                    chain='bitcoin',
                    content_hash=record.get('file_hash', ''),
                    file_path=str(dest),
                    is_recursive=is_recursive
                )
                manifest.append(asdict(example))
                print(f"  ✓ {record.get('number')} - {record.get('content_type')}")

            except Exception as e:
                print(f"  ✗ {record.get('number')} - {e}")

        # Save manifest
        manifest_file = image_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))
        print(f"\n  Saved {len(manifest)} images to {image_dir}")

        # Create JSONL for training
        jsonl_file = image_dir / "training.jsonl"
        with open(jsonl_file, 'w') as f:
            for item in manifest:
                f.write(json.dumps(item) + '\n')

        return image_dir

    def prepare_text_dataset(self) -> Path:
        """Prepare text dataset for language models."""
        print("\n[PREPARING] Text Dataset")
        print("-" * 50)

        text_dir = OUTPUT_DIR / "text"
        text_dir.mkdir(exist_ok=True)

        manifest = []
        text_types = {'text/plain', 'text/html', 'application/json', 'text/html;charset=utf-8'}

        for record in self.metadata:
            if record.get('content_type') not in text_types:
                continue

            path = Path(record.get('local_path', ''))
            if not path.exists():
                continue

            try:
                content = path.read_bytes()
                text = content.decode('utf-8', errors='ignore')

                is_brc20, protocol, parsed = self._detect_brc20(content)
                is_recursive = self._detect_recursive(content)

                example = TrainingExample(
                    id=record.get('id', ''),
                    inscription_number=record.get('number', 0),
                    content_type=record.get('content_type', ''),
                    chain='bitcoin',
                    content_hash=record.get('file_hash', ''),
                    file_path=str(path),
                    text_content=text[:10000],  # Limit size
                    is_recursive=is_recursive,
                    is_brc20=is_brc20,
                    protocol=protocol
                )
                manifest.append(asdict(example))

                label = f"[{protocol}]" if protocol else ""
                print(f"  ✓ {record.get('number')} - {record.get('content_type')} {label}")

            except Exception as e:
                print(f"  ✗ {record.get('number')} - {e}")

        # Save manifest
        manifest_file = text_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))

        # Create JSONL
        jsonl_file = text_dir / "training.jsonl"
        with open(jsonl_file, 'w') as f:
            for item in manifest:
                f.write(json.dumps(item) + '\n')

        # Create protocol-specific subsets
        protocols = {}
        for item in manifest:
            proto = item.get('protocol') or 'other'
            if proto not in protocols:
                protocols[proto] = []
            protocols[proto].append(item)

        for proto, items in protocols.items():
            proto_file = text_dir / f"{proto}.jsonl"
            with open(proto_file, 'w') as f:
                for item in items:
                    f.write(json.dumps(item) + '\n')
            print(f"  Created {proto}.jsonl ({len(items)} items)")

        print(f"\n  Saved {len(manifest)} text items to {text_dir}")
        return text_dir

    def prepare_audio_dataset(self) -> Path:
        """Prepare audio dataset."""
        print("\n[PREPARING] Audio Dataset")
        print("-" * 50)

        audio_dir = OUTPUT_DIR / "audio"
        audio_dir.mkdir(exist_ok=True)

        manifest = []
        audio_types = {'audio/mpeg', 'audio/wav', 'audio/ogg'}

        for record in self.metadata:
            if record.get('content_type') not in audio_types:
                continue

            path = Path(record.get('local_path', ''))
            if not path.exists():
                continue

            try:
                dest = audio_dir / path.name
                shutil.copy(path, dest)

                example = TrainingExample(
                    id=record.get('id', ''),
                    inscription_number=record.get('number', 0),
                    content_type=record.get('content_type', ''),
                    chain='bitcoin',
                    content_hash=record.get('file_hash', ''),
                    file_path=str(dest)
                )
                manifest.append(asdict(example))
                print(f"  ✓ {record.get('number')} - {path.stat().st_size / 1024:.1f}KB")

            except Exception as e:
                print(f"  ✗ {record.get('number')} - {e}")

        manifest_file = audio_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))
        print(f"\n  Saved {len(manifest)} audio files to {audio_dir}")
        return audio_dir

    def prepare_video_dataset(self) -> Path:
        """Prepare video dataset."""
        print("\n[PREPARING] Video Dataset")
        print("-" * 50)

        video_dir = OUTPUT_DIR / "video"
        video_dir.mkdir(exist_ok=True)

        manifest = []
        video_types = {'video/mp4', 'video/webm'}

        for record in self.metadata:
            if record.get('content_type') not in video_types:
                continue

            path = Path(record.get('local_path', ''))
            if not path.exists():
                continue

            try:
                dest = video_dir / path.name
                shutil.copy(path, dest)

                example = TrainingExample(
                    id=record.get('id', ''),
                    inscription_number=record.get('number', 0),
                    content_type=record.get('content_type', ''),
                    chain='bitcoin',
                    content_hash=record.get('file_hash', ''),
                    file_path=str(dest)
                )
                manifest.append(asdict(example))
                print(f"  ✓ {record.get('number')} - {path.stat().st_size / 1024:.1f}KB")

            except Exception as e:
                print(f"  ✗ {record.get('number')} - {e}")

        manifest_file = video_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))
        print(f"\n  Saved {len(manifest)} video files to {video_dir}")
        return video_dir

    def generate_stats(self) -> Dict:
        """Generate dataset statistics."""
        stats = {
            'total_records': len(self.metadata),
            'by_content_type': {},
            'by_protocol': {},
            'recursive_count': 0,
            'brc20_count': 0,
        }

        for record in self.metadata:
            ct = record.get('content_type', 'unknown')
            stats['by_content_type'][ct] = stats['by_content_type'].get(ct, 0) + 1

            path = Path(record.get('local_path', ''))
            if path.exists():
                try:
                    content = path.read_bytes()
                    if self._detect_recursive(content):
                        stats['recursive_count'] += 1
                    is_brc20, protocol, _ = self._detect_brc20(content)
                    if is_brc20:
                        stats['brc20_count'] += 1
                    if protocol:
                        stats['by_protocol'][protocol] = stats['by_protocol'].get(protocol, 0) + 1
                except:
                    pass

        return stats

    def prepare_all(self):
        """Prepare all datasets."""
        print("=" * 60)
        print("PREPARING AI TRAINING DATASETS")
        print("=" * 60)

        self.prepare_image_dataset()
        self.prepare_text_dataset()
        self.prepare_audio_dataset()
        self.prepare_video_dataset()

        stats = self.generate_stats()
        stats_file = OUTPUT_DIR / "dataset_stats.json"
        stats_file.write_text(json.dumps(stats, indent=2))

        print("\n" + "=" * 60)
        print("DATASET STATISTICS")
        print("=" * 60)
        print(f"Total records: {stats['total_records']}")
        print(f"Recursive inscriptions: {stats['recursive_count']}")
        print(f"BRC-20 operations: {stats['brc20_count']}")
        print(f"\nBy content type:")
        for ct, count in sorted(stats['by_content_type'].items(), key=lambda x: -x[1]):
            print(f"  {ct}: {count}")
        print(f"\nBy protocol:")
        for proto, count in sorted(stats['by_protocol'].items(), key=lambda x: -x[1]):
            print(f"  {proto}: {count}")

        print(f"\nOutput: {OUTPUT_DIR}")


def main():
    preparer = DatasetPreparer()
    preparer.prepare_all()


if __name__ == '__main__':
    main()
