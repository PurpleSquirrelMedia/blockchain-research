# Bitcoin & Blockchain Interaction Quick Reference

## Collection Stats (Sample Run)
- **Ordinals**: 46 files, 3.4MB (images, text, HTML)
- **Types**: PNG, WebP, GIF, TXT, HTML, JSON

---

## 1. ORDINALS API (No Auth, Free)

```bash
# List latest inscriptions
curl "https://api.hiro.so/ordinals/v1/inscriptions?limit=10"

# Get specific inscription metadata
curl "https://api.hiro.so/ordinals/v1/inscriptions/{INSCRIPTION_ID}"

# Download inscription content (image/text/etc)
curl "https://api.hiro.so/ordinals/v1/inscriptions/{INSCRIPTION_ID}/content" -o file.png

# Filter by content type
curl "https://api.hiro.so/ordinals/v1/inscriptions?mime_type=image/png&limit=60"

# Get stats
curl "https://api.hiro.so/ordinals/v1/stats/inscriptions"
```

**Content types available**:
- `image/png`, `image/webp`, `image/gif`, `image/svg+xml`
- `text/plain`, `text/html`, `application/json`
- `audio/mpeg`, `video/mp4`

---

## 2. OP_RETURN DATA

```bash
# Get transaction with OP_RETURN
curl "https://blockstream.info/api/tx/{TXID}"

# Decode OP_RETURN hex to text
echo "48656c6c6f" | xxd -r -p
```

**Python extraction**:
```python
from bitcoin_apis import OPReturnExtractor
extractor = OPReturnExtractor()
text = extractor.decode_op_return_text(txid)
```

---

## 3. ARWEAVE

```bash
# Get transaction data
curl "https://arweave.net/{TX_ID}"

# GraphQL search
curl -X POST https://arweave.net/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ transactions(first: 10, tags: [{name: \"Content-Type\", values: [\"image/png\"]}]) { edges { node { id } } } }"}'
```

---

## 4. ETHEREUM

```bash
# Get transaction input data
curl -X POST https://eth.llamarpc.com \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getTransactionByHash","params":["0x..."],"id":1}'

# Get event logs
curl -X POST https://eth.llamarpc.com \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getLogs","params":[{"address":"0x...","fromBlock":"0x0","toBlock":"latest"}],"id":1}'
```

---

## 5. RUN FULL NODE (Complete Data Access)

### Bitcoin Core + Ord
```bash
# Install
brew install bitcoin
brew install ord

# Sync full node (~600GB required)
bitcoind -daemon

# Index ordinals (after sync)
ord index

# Query local
ord inscription 0
ord traits
```

### Arweave Gateway
```bash
docker run -p 1984:1984 arweave/gateway
```

---

## 6. PYTHON TOOLKIT

```python
# Located at: ~/blockchain-research/bitcoin_apis.py

from bitcoin_apis import OrdinalsAPI, OPReturnExtractor, ArweaveAPI, EthereumDataAPI

# Ordinals
ordinals = OrdinalsAPI()
inscriptions = ordinals.list_inscriptions(mime_type='image/png', limit=100)
content = ordinals.get_inscription_content(inscription_id)

# OP_RETURN
op = OPReturnExtractor()
data = op.extract_op_return(txid)

# Arweave
ar = ArweaveAPI()
images = ar.search_by_tag('Content-Type', 'image/png', first=100)
data = ar.get_data(tx_id)

# Ethereum
eth = EthereumDataAPI()
logs = eth.get_logs(contract_address, from_block, to_block)
```

---

## 7. BULK COLLECTION

```bash
cd ~/blockchain-research
python3 data_collector.py
```

Collects to: `~/blockchain-research/data/`
- `ordinals/image/` - PNG, WebP, GIF, SVG
- `ordinals/text/` - TXT, HTML, JSON
- `arweave/` - Arweave content
- `metadata/` - JSON metadata files

---

## 8. KEY INSIGHT: WHAT'S ON-CHAIN

| Data Type | On Bitcoin | Unique Value |
|-----------|------------|--------------|
| Images | 70M+ Ordinals | Generative art, pixel art, PFPs |
| Text | Millions | Manifestos, poems, messages |
| HTML/JS | Thousands | Full on-chain apps, games |
| BRC-20 | Millions | Token protocol data |
| OP_RETURN | Millions | Timestamps, proofs, protocols |
| Stamps | 200k+ | Truly unprunable images |

---

## 9. AI TRAINING POTENTIAL

1. **Image models**: Train on unique on-chain art
2. **Language models**: On-chain text corpus
3. **Code generation**: On-chain HTML/JS apps
4. **Multimodal**: Pair inscriptions with metadata
5. **Temporal**: Track cultural evolution via block height

---

## 10. API RATE LIMITS

| API | Limit | Notes |
|-----|-------|-------|
| Hiro Ordinals | 60/min | Free tier |
| Blockstream | Unlimited | |
| Arweave Gateway | Unlimited | |
| Ethereum RPC | Varies | Use llamarpc.com |
| StampChain | Unlimited | |

---

## Files Created

```
~/blockchain-research/
├── bitcoin_apis.py      # API toolkit
├── data_collector.py    # Bulk downloader
├── README.md            # Full documentation
├── QUICK_REF.md         # This file
└── data/                # Collected data
    ├── ordinals/
    ├── arweave/
    └── metadata/
```
