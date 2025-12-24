#!/usr/bin/env python3
"""
Overnight batch collection script.
Runs continuously to collect blockchain data while you sleep.
Use: python3 overnight_collect.py --hours 8
"""

import argparse
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Import collectors
from robust_collector import MultiAPICollector
from arweave_collector import ArweaveCollector
from solana_collector import SolanaCollector

DATA_DIR = Path("/Volumes/Virtual Server/Projects/blockchain-research/data")
LOG_FILE = DATA_DIR / "overnight_log.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OvernightCollector:
    """Run collection jobs overnight with progress tracking."""

    def __init__(self, hours: float = 8):
        self.end_time = datetime.now() + timedelta(hours=hours)
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'end_time': self.end_time.isoformat(),
            'bitcoin_ordinals': 0,
            'arweave': 0,
            'solana': 0,
            'total_bytes': 0,
            'errors': []
        }

    def should_continue(self) -> bool:
        """Check if we should continue collecting."""
        return datetime.now() < self.end_time

    def time_remaining(self) -> str:
        """Get human-readable time remaining."""
        delta = self.end_time - datetime.now()
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def collect_bitcoin_ordinals(self, batch_size: int = 50):
        """Collect Bitcoin Ordinals inscriptions."""
        logger.info("=== Starting Bitcoin Ordinals collection ===")

        collector = MultiAPICollector()

        content_types = [
            ('image/png', 20),
            ('image/webp', 20),
            ('image/gif', 15),
            ('image/svg+xml', 15),
            ('text/plain', 20),
            ('text/html', 15),
            ('application/json', 15),
            ('audio/mpeg', 10),
        ]

        for mime_type, count in content_types:
            if not self.should_continue():
                logger.info("Time limit reached, stopping Bitcoin collection")
                break

            try:
                logger.info(f"Collecting {count} x {mime_type}")
                records = collector.collect(mime_type, count)
                self.stats['bitcoin_ordinals'] += len(records)
                self.stats['total_bytes'] += sum(r.get('content_length', 0) for r in records)
                logger.info(f"  Collected {len(records)}, total: {self.stats['bitcoin_ordinals']}")

                # Rate limit pause
                time.sleep(10)

            except Exception as e:
                logger.error(f"Bitcoin collection error: {e}")
                self.stats['errors'].append(f"Bitcoin {mime_type}: {str(e)}")

        logger.info(f"Bitcoin Ordinals complete: {self.stats['bitcoin_ordinals']} items")

    def collect_arweave(self, batch_size: int = 30):
        """Collect Arweave permanent storage data."""
        logger.info("=== Starting Arweave collection ===")

        if not self.should_continue():
            return

        try:
            collector = ArweaveCollector()

            content_types = [
                ('image/png', 10),
                ('image/gif', 10),
                ('text/plain', 10),
            ]

            for ct, count in content_types:
                if not self.should_continue():
                    break

                records = collector.collect_by_type(ct, count)
                self.stats['arweave'] += len(records)
                self.stats['total_bytes'] += sum(r.get('content_length', 0) for r in records)
                time.sleep(5)

            logger.info(f"Arweave complete: {self.stats['arweave']} items")

        except Exception as e:
            logger.error(f"Arweave collection error: {e}")
            self.stats['errors'].append(f"Arweave: {str(e)}")

    def collect_solana(self, collections_count: int = 3, per_collection: int = 5):
        """Collect Solana NFTs."""
        logger.info("=== Starting Solana collection ===")

        if not self.should_continue():
            return

        try:
            collector = SolanaCollector()
            records = collector.collect_popular_nfts(count_per_collection=per_collection)
            self.stats['solana'] += len(records)
            self.stats['total_bytes'] += sum(r.get('content_length', 0) for r in records)
            logger.info(f"Solana complete: {self.stats['solana']} items")

        except Exception as e:
            logger.error(f"Solana collection error: {e}")
            self.stats['errors'].append(f"Solana: {str(e)}")

    def save_stats(self):
        """Save collection statistics."""
        self.stats['actual_end_time'] = datetime.now().isoformat()
        self.stats['total_items'] = (
            self.stats['bitcoin_ordinals'] +
            self.stats['arweave'] +
            self.stats['solana']
        )
        self.stats['total_mb'] = self.stats['total_bytes'] / (1024 * 1024)

        stats_file = DATA_DIR / "metadata" / f"overnight_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        stats_file.write_text(json.dumps(self.stats, indent=2))
        logger.info(f"Stats saved to: {stats_file}")

    def run(self):
        """Run the overnight collection."""
        logger.info("=" * 60)
        logger.info("OVERNIGHT BLOCKCHAIN DATA COLLECTION")
        logger.info(f"Running until: {self.end_time}")
        logger.info("=" * 60)

        cycles = 0
        while self.should_continue():
            cycles += 1
            logger.info(f"\n>>> Cycle {cycles} - Time remaining: {self.time_remaining()}")

            # Collect from each chain
            self.collect_bitcoin_ordinals()

            if self.should_continue():
                self.collect_arweave()

            if self.should_continue():
                self.collect_solana()

            # Progress report
            logger.info(f"\n--- Progress Report ---")
            logger.info(f"Bitcoin: {self.stats['bitcoin_ordinals']}")
            logger.info(f"Arweave: {self.stats['arweave']}")
            logger.info(f"Solana: {self.stats['solana']}")
            logger.info(f"Total: {self.stats['total_bytes'] / (1024*1024):.1f} MB")
            logger.info(f"Time remaining: {self.time_remaining()}")

            # Pause between cycles
            if self.should_continue():
                logger.info("Pausing 60 seconds before next cycle...")
                time.sleep(60)

        # Final report
        self.save_stats()
        logger.info("\n" + "=" * 60)
        logger.info("OVERNIGHT COLLECTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total items: {self.stats['total_items']}")
        logger.info(f"Total size: {self.stats['total_mb']:.2f} MB")
        logger.info(f"Errors: {len(self.stats['errors'])}")


def main():
    parser = argparse.ArgumentParser(description='Overnight blockchain data collection')
    parser.add_argument('--hours', type=float, default=8, help='Hours to run (default: 8)')
    args = parser.parse_args()

    collector = OvernightCollector(hours=args.hours)
    collector.run()


if __name__ == '__main__':
    main()
