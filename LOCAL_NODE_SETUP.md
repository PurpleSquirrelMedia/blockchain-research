# Local Bitcoin Node + Ordinals Indexer Setup

**Purpose**: Run your own infrastructure for unlimited, rate-limit-free access to all Bitcoin Ordinals data.

---

## Overview

Running a local node gives you:
- **Unlimited API access** - No rate limits or API keys needed
- **Complete data** - Access all 70M+ inscriptions
- **Historical data** - Full blockchain history
- **Privacy** - No third-party tracking of your queries
- **Reliability** - No dependency on external services

## Requirements

### Hardware (Minimum)
| Component | Requirement | Notes |
|-----------|-------------|-------|
| Storage | 1TB SSD (NVMe preferred) | Bitcoin blockchain is ~600GB, Ord index adds ~200GB |
| RAM | 16GB | 32GB recommended for faster indexing |
| CPU | 4+ cores | More cores = faster initial sync |
| Network | Stable broadband | Initial sync downloads ~600GB |

### Hardware (Recommended for Research)
| Component | Recommendation |
|-----------|----------------|
| Storage | 2TB NVMe SSD |
| RAM | 64GB |
| CPU | 8+ cores |
| Network | 100Mbps+ |

---

## Option 1: Bitcoin Core + Ord (Full Setup)

### Step 1: Install Bitcoin Core

```bash
# macOS
brew install bitcoin

# Linux (Ubuntu/Debian)
sudo apt-get install snapd
sudo snap install bitcoin-core

# Or download from https://bitcoincore.org/en/download/
```

### Step 2: Configure Bitcoin Core

Create `~/.bitcoin/bitcoin.conf`:

```ini
# Network
server=1
txindex=1
daemon=1

# RPC
rpcuser=your_rpc_user
rpcpassword=your_secure_password
rpcbind=127.0.0.1
rpcallowip=127.0.0.1

# Performance
dbcache=4096
maxconnections=40

# Pruning disabled (required for ord)
prune=0
```

### Step 3: Start Bitcoin Core & Sync

```bash
# Start daemon
bitcoind

# Check sync progress
bitcoin-cli getblockchaininfo

# This will take 1-3 days for initial sync
# You can monitor with:
watch -n 60 'bitcoin-cli getblockchaininfo | grep -E "blocks|progress"'
```

### Step 4: Install Ord

```bash
# Install Rust (if not installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Install ord
cargo install ord

# Or download pre-built binary from:
# https://github.com/ordinals/ord/releases
```

### Step 5: Build Ord Index

```bash
# Start ord indexer (after Bitcoin Core is synced)
ord --bitcoin-rpc-username your_rpc_user \
    --bitcoin-rpc-password your_secure_password \
    index

# This takes 12-48 hours depending on hardware
```

### Step 6: Run Ord Server

```bash
# Start the ord server
ord --bitcoin-rpc-username your_rpc_user \
    --bitcoin-rpc-password your_secure_password \
    server --http-port 8080

# Now you have unlimited local API access at:
# http://localhost:8080
```

### Local Ord API Endpoints

```bash
# Get inscription content
curl http://localhost:8080/content/<inscription_id>

# Get inscription info
curl http://localhost:8080/inscription/<inscription_id>

# List inscriptions
curl http://localhost:8080/inscriptions

# Get sat info
curl http://localhost:8080/sat/<sat_number>
```

---

## Option 2: Docker Setup (Easier)

### docker-compose.yml

```yaml
version: '3.8'

services:
  bitcoin:
    image: ruimarinho/bitcoin-core:latest
    container_name: bitcoin-core
    restart: unless-stopped
    volumes:
      - bitcoin-data:/home/bitcoin/.bitcoin
    ports:
      - "8332:8332"
      - "8333:8333"
    command:
      -server=1
      -txindex=1
      -rpcuser=bitcoin
      -rpcpassword=bitcoin
      -rpcallowip=0.0.0.0/0
      -rpcbind=0.0.0.0
      -prune=0
      -dbcache=4096

  ord:
    image: ghcr.io/ordinals/ord:latest
    container_name: ord
    restart: unless-stopped
    depends_on:
      - bitcoin
    volumes:
      - ord-data:/root/.local/share/ord
    ports:
      - "8080:8080"
    command:
      --bitcoin-rpc-url=bitcoin:8332
      --bitcoin-rpc-username=bitcoin
      --bitcoin-rpc-password=bitcoin
      server
      --http-port=8080
      --http=0.0.0.0

volumes:
  bitcoin-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/your/storage/bitcoin
  ord-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/your/storage/ord
```

```bash
# Start everything
docker-compose up -d

# Watch logs
docker-compose logs -f
```

---

## Option 3: Cloud Instance (Fastest Initial Setup)

For immediate research, spin up a cloud instance:

### AWS/GCP/OCI Instance

| Provider | Instance Type | Storage | Cost/month |
|----------|---------------|---------|------------|
| AWS | m5.xlarge | 1TB gp3 | ~$150 |
| GCP | n2-standard-4 | 1TB SSD | ~$140 |
| OCI | VM.Standard.E4.Flex | 1TB Block | ~$80 |

```bash
# Quick setup on Ubuntu
sudo apt update && sudo apt install -y snapd
sudo snap install bitcoin-core
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
cargo install ord
```

---

## Python Integration

Once running locally, update `bitcoin_apis.py`:

```python
class LocalOrdinalsAPI:
    """Connect to local ord server - no rate limits!"""

    def __init__(self, host='localhost', port=8080):
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()

    def get_inscription(self, inscription_id: str) -> dict:
        """Get inscription metadata."""
        resp = self.session.get(f"{self.base_url}/inscription/{inscription_id}")
        resp.raise_for_status()
        return resp.json()

    def get_content(self, inscription_id: str) -> bytes:
        """Get inscription content - unlimited speed!"""
        resp = self.session.get(f"{self.base_url}/content/{inscription_id}")
        resp.raise_for_status()
        return resp.content

    def get_inscriptions(self, offset: int = 0, limit: int = 100) -> list:
        """List inscriptions with pagination."""
        # Note: ord server pagination differs from Hiro API
        resp = self.session.get(f"{self.base_url}/inscriptions/{offset}")
        resp.raise_for_status()
        return resp.json()

    def get_sat_inscriptions(self, sat: int) -> list:
        """Get all inscriptions on a specific sat."""
        resp = self.session.get(f"{self.base_url}/sat/{sat}")
        resp.raise_for_status()
        return resp.json().get('inscriptions', [])
```

---

## Bulk Data Export

With local node, you can export ALL inscriptions:

```python
#!/usr/bin/env python3
"""Bulk export all ordinals inscriptions locally."""

import requests
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

class BulkExporter:
    def __init__(self, ord_url="http://localhost:8080"):
        self.ord_url = ord_url
        self.session = requests.Session()
        self.output_dir = Path("/Volumes/Virtual Server/Projects/blockchain-research/data/full_export")

    def export_all(self, start=0, workers=10):
        """Export all inscriptions - no rate limits!"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        inscription_num = start
        batch_size = 100

        while True:
            # Get batch of inscriptions
            try:
                resp = self.session.get(f"{self.ord_url}/inscriptions/{inscription_num}")
                inscriptions = resp.json()

                if not inscriptions:
                    break

                # Download content in parallel
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    executor.map(self.save_inscription, inscriptions)

                inscription_num += len(inscriptions)
                print(f"Exported {inscription_num} inscriptions...")

            except Exception as e:
                print(f"Error at {inscription_num}: {e}")
                break

    def save_inscription(self, inscription_id):
        """Save single inscription."""
        try:
            # Get content
            content = self.session.get(f"{self.ord_url}/content/{inscription_id}").content

            # Get metadata
            meta = self.session.get(f"{self.ord_url}/inscription/{inscription_id}").json()

            # Save
            content_type = meta.get('content_type', 'application/octet-stream')
            ext = content_type.split('/')[-1].split(';')[0]

            (self.output_dir / f"{inscription_id}.{ext}").write_bytes(content)
            (self.output_dir / f"{inscription_id}.json").write_text(json.dumps(meta))

        except Exception as e:
            print(f"Failed {inscription_id}: {e}")
```

---

## Storage Estimates

| Data Type | Approximate Size |
|-----------|------------------|
| Bitcoin blockchain | 600 GB |
| Ord index | 200 GB |
| All inscription content | 500+ GB |
| Total for full research setup | 1.5+ TB |

---

## Recommended Path

1. **Immediate**: Continue using public APIs with robust_collector.py
2. **Short-term**: Spin up OCI cloud instance for syncing
3. **Long-term**: Move synced data to external drive for local research

---

## Resources

- [Bitcoin Core Downloads](https://bitcoincore.org/en/download/)
- [Ord GitHub](https://github.com/ordinals/ord)
- [Ord Handbook](https://docs.ordinals.com/)
- [Ordinals Explorer](https://ordinals.com/)

---

*Document created: December 2024*
*Part of the Immutable Intelligence research project*
