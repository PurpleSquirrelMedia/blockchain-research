# Blockchain Data for AI Training

## The Hypothesis
Millions of images, texts, and applications are permanently stored on-chain. This represents an untapped, censorship-resistant dataset that no AI model has been specifically trained on. Training on this data could unlock unique capabilities or insights.

## Data Sources

### 1. Bitcoin Ordinals (70M+ inscriptions)
- **What**: Images, text, HTML, audio, video inscribed directly on Bitcoin
- **Since**: January 2023
- **Access**: Free APIs (Hiro, Ordiscan)
- **Unique data**: First-of-kind digital artifacts, community art, on-chain apps

```python
from bitcoin_apis import OrdinalsAPI
api = OrdinalsAPI()
inscriptions = api.list_inscriptions(mime_type='image/png', limit=100)
```

### 2. OP_RETURN Data (Since 2014)
- **What**: 80-byte messages embedded in Bitcoin transactions
- **Used by**: Counterparty, Omni Layer, OpenTimestamps, various protocols
- **Volume**: Millions of transactions
- **Unique data**: Historical messages, protocol data, proofs

```python
from bitcoin_apis import OPReturnExtractor
extractor = OPReturnExtractor()
data = extractor.decode_op_return_text(txid)
```

### 3. Bitcoin Stamps (200k+)
- **What**: Base64 images in multisig outputs
- **Key feature**: Cannot be pruned, truly permanent
- **Format**: Small images (24x24 to 420x420)

### 4. Arweave (Pay once, store forever)
- **What**: Any file, unlimited size
- **Model**: 200-year endowment for storage
- **Used for**: NFT metadata, websites, apps, large datasets

```python
from bitcoin_apis import ArweaveAPI
ar = ArweaveAPI()
images = ar.search_by_tag('Content-Type', 'image/png', first=100)
```

### 5. Ethereum
- **Contract storage**: Persistent key-value data
- **Event logs**: Indexed, queryable events
- **Calldata**: Transaction input data

### 6. IPFS/Filecoin
- **Content-addressed**: Data has unique hash
- **Note**: Requires pinning to persist

## Quick Start

```bash
# Test APIs
python3 bitcoin_apis.py

# Collect sample data
python3 data_collector.py
```

## Data Categories Found on Bitcoin Ordinals

| Content Type | Examples |
|--------------|----------|
| image/png | Profile pictures, generative art, pixel art |
| image/webp | Compressed images, collections |
| image/svg+xml | Vector graphics, generative art |
| text/plain | Messages, poems, manifestos |
| text/html | Full web applications, games |
| application/json | Metadata, BRC-20 tokens |
| audio/mpeg | Music, sound effects |
| video/mp4 | Short clips, animations |

## API Endpoints (No Auth Required)

| API | URL | Rate Limit |
|-----|-----|------------|
| Hiro Ordinals | api.hiro.so/ordinals/v1 | 60/min |
| Blockstream | blockstream.info/api | Unlimited |
| Arweave | arweave.net | Unlimited |
| StampChain | stampchain.io/api/v2 | Unlimited |

## Running a Full Node (For Complete Data)

### Bitcoin Core + Ord
```bash
# Install Bitcoin Core
brew install bitcoin

# Run full node (requires ~600GB)
bitcoind -daemon

# Install Ord indexer
brew install ord

# Index ordinals
ord index
```

### Arweave Gateway
```bash
# Run local gateway for faster access
docker run -p 1984:1984 arweave/gateway
```

## Dataset Structure

```
~/blockchain-research/data/
├── ordinals/
│   ├── image/       # PNG, WEBP, GIF, SVG
│   ├── text/        # TXT, HTML, JSON
│   ├── audio/       # MP3, WAV
│   └── video/       # MP4, WEBM
├── arweave/
│   ├── image/
│   └── text/
└── metadata/
    ├── ordinals_metadata.json
    ├── arweave_metadata.json
    └── dataset_stats.json
```

## Potential Training Applications

1. **Image Generation**: Train on unique on-chain art styles
2. **Text Understanding**: Learn from permanent on-chain messages
3. **Code Generation**: On-chain HTML/JS apps are unique
4. **Multimodal**: Connect image + text inscriptions
5. **Temporal Analysis**: Track evolution of on-chain culture

## Key Insight
This data is:
- **Permanent**: Cannot be deleted or censored
- **Timestamped**: Exact block height/timestamp
- **Verified**: Proven to exist at specific time
- **Unique**: Much not replicated elsewhere
- **Paid for**: Someone valued it enough to inscribe
