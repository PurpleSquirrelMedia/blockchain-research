#!/usr/bin/env python3
"""
Bitcoin & Blockchain Data Access Toolkit
========================================
Multiple vectors for accessing on-chain content for AI training.
"""

import requests
import json
import base64
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import time

# =============================================================================
# ORDINALS INSCRIPTIONS (Images, Text, HTML, Audio, Video on Bitcoin)
# =============================================================================

class OrdinalsAPI:
    """
    Access 70M+ inscriptions on Bitcoin via multiple APIs.
    Data includes: images, text, HTML/JS apps, audio, video, 3D models
    """

    def __init__(self):
        # Multiple API endpoints for redundancy
        self.apis = {
            'hiro': 'https://api.hiro.so/ordinals/v1',
            'ordiscan': 'https://api.ordiscan.com/v1',
            'ordinals_com': 'https://ordinals.com',
            'magiceden': 'https://api-mainnet.magiceden.dev/v2/ord'
        }

    def get_inscription(self, inscription_id: str) -> Dict:
        """Fetch inscription metadata and content"""
        # Try Hiro API (most reliable, free tier)
        try:
            url = f"{self.apis['hiro']}/inscriptions/{inscription_id}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {'error': str(e)}

    def get_inscription_content(self, inscription_id: str) -> bytes:
        """Fetch raw inscription content (image/text/etc)"""
        url = f"{self.apis['hiro']}/inscriptions/{inscription_id}/content"
        resp = requests.get(url, timeout=30)
        return resp.content

    def list_inscriptions(self,
                         mime_type: str = None,
                         from_number: int = 0,
                         limit: int = 60) -> List[Dict]:
        """
        List inscriptions with optional filters.
        mime_type examples: 'image/png', 'image/webp', 'text/plain',
                           'text/html', 'application/json', 'audio/mpeg'
        """
        params = {'offset': from_number, 'limit': limit}
        if mime_type:
            params['mime_type'] = mime_type

        url = f"{self.apis['hiro']}/inscriptions"
        resp = requests.get(url, params=params, timeout=10)
        return resp.json().get('results', [])

    def search_inscriptions_by_content_type(self, content_type: str) -> List[Dict]:
        """Search for specific content types"""
        return self.list_inscriptions(mime_type=content_type)

    def get_stats(self) -> Dict:
        """Get overall Ordinals statistics"""
        url = f"{self.apis['hiro']}/stats/inscriptions"
        resp = requests.get(url, timeout=10)
        return resp.json()


# =============================================================================
# OP_RETURN DATA (80-byte messages embedded in Bitcoin transactions)
# =============================================================================

class OPReturnExtractor:
    """
    Extract OP_RETURN data from Bitcoin transactions.
    Used by: Counterparty, Omni, OpenTimestamps, various protocols
    """

    def __init__(self):
        # Public blockchain explorers with API access
        self.apis = {
            'blockstream': 'https://blockstream.info/api',
            'blockchain_info': 'https://blockchain.info',
            'blockcypher': 'https://api.blockcypher.com/v1/btc/main'
        }

    def get_tx(self, txid: str) -> Dict:
        """Get full transaction data"""
        url = f"{self.apis['blockstream']}/tx/{txid}"
        resp = requests.get(url, timeout=10)
        return resp.json()

    def extract_op_return(self, txid: str) -> Optional[bytes]:
        """Extract OP_RETURN data from a transaction"""
        tx = self.get_tx(txid)
        for vout in tx.get('vout', []):
            script = vout.get('scriptpubkey_type', '')
            if script == 'op_return':
                # Decode the hex data
                asm = vout.get('scriptpubkey_asm', '')
                if 'OP_RETURN' in asm:
                    parts = asm.split(' ')
                    if len(parts) > 1:
                        hex_data = parts[-1]
                        return bytes.fromhex(hex_data)
        return None

    def decode_op_return_text(self, txid: str) -> Optional[str]:
        """Extract and decode OP_RETURN as text"""
        data = self.extract_op_return(txid)
        if data:
            try:
                return data.decode('utf-8')
            except:
                return data.hex()
        return None

    def get_block_op_returns(self, block_hash: str) -> List[Dict]:
        """Get all OP_RETURN data from a block"""
        url = f"{self.apis['blockstream']}/block/{block_hash}/txids"
        resp = requests.get(url, timeout=30)
        txids = resp.json()

        op_returns = []
        for txid in txids[:50]:  # Limit to avoid rate limits
            data = self.extract_op_return(txid)
            if data:
                op_returns.append({
                    'txid': txid,
                    'data': data.hex(),
                    'decoded': data.decode('utf-8', errors='ignore')
                })
            time.sleep(0.1)  # Rate limiting

        return op_returns


# =============================================================================
# STAMPS (Base64 images in multisig outputs - immortal on Bitcoin)
# =============================================================================

class StampsAPI:
    """
    Bitcoin Stamps - images stored as base64 in multisig outputs.
    Cannot be pruned, truly permanent on Bitcoin.
    """

    def __init__(self):
        self.api = 'https://stampchain.io/api/v2'

    def get_stamp(self, stamp_id: int) -> Dict:
        """Get stamp by ID"""
        url = f"{self.api}/stamps/{stamp_id}"
        resp = requests.get(url, timeout=10)
        return resp.json()

    def list_stamps(self, page: int = 1, limit: int = 100) -> List[Dict]:
        """List stamps"""
        url = f"{self.api}/stamps"
        params = {'page': page, 'limit': limit}
        resp = requests.get(url, params=params, timeout=10)
        return resp.json()


# =============================================================================
# ARWEAVE (Permanent storage, 200-year endowment model)
# =============================================================================

class ArweaveAPI:
    """
    Arweave - pay once, store forever.
    Used for: NFT metadata, websites, apps, datasets
    """

    def __init__(self):
        self.gateway = 'https://arweave.net'
        self.graphql = 'https://arweave.net/graphql'

    def get_transaction(self, tx_id: str) -> Dict:
        """Get transaction metadata"""
        url = f"{self.gateway}/tx/{tx_id}"
        resp = requests.get(url, timeout=10)
        return resp.json()

    def get_data(self, tx_id: str) -> bytes:
        """Get raw transaction data"""
        url = f"{self.gateway}/{tx_id}"
        resp = requests.get(url, timeout=30)
        return resp.content

    def search_by_tag(self, tag_name: str, tag_value: str, first: int = 100) -> List[Dict]:
        """Search transactions by tag using GraphQL"""
        query = """
        query {
            transactions(
                first: %d,
                tags: [{ name: "%s", values: ["%s"] }]
            ) {
                edges {
                    node {
                        id
                        tags { name value }
                        data { size type }
                    }
                }
            }
        }
        """ % (first, tag_name, tag_value)

        resp = requests.post(self.graphql, json={'query': query}, timeout=10)
        data = resp.json()
        return [edge['node'] for edge in data.get('data', {}).get('transactions', {}).get('edges', [])]

    def search_images(self, first: int = 100) -> List[Dict]:
        """Search for image content"""
        return self.search_by_tag('Content-Type', 'image/png', first)


# =============================================================================
# ETHEREUM (Contract storage, event logs, calldata)
# =============================================================================

class EthereumDataAPI:
    """
    Ethereum on-chain data sources.
    """

    def __init__(self, rpc_url: str = 'https://eth.llamarpc.com'):
        self.rpc = rpc_url

    def eth_call(self, method: str, params: list) -> Dict:
        """Make JSON-RPC call"""
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': 1
        }
        resp = requests.post(self.rpc, json=payload, timeout=10)
        return resp.json()

    def get_logs(self, address: str, from_block: int, to_block: int, topics: list = None) -> List[Dict]:
        """Get event logs (NFT mints, transfers, etc)"""
        params = [{
            'address': address,
            'fromBlock': hex(from_block),
            'toBlock': hex(to_block)
        }]
        if topics:
            params[0]['topics'] = topics

        result = self.eth_call('eth_getLogs', params)
        return result.get('result', [])

    def get_transaction_input(self, tx_hash: str) -> str:
        """Get transaction input data (calldata)"""
        result = self.eth_call('eth_getTransactionByHash', [tx_hash])
        tx = result.get('result', {})
        return tx.get('input', '0x')


# =============================================================================
# DEMO & TESTING
# =============================================================================

def demo():
    print("=" * 60)
    print("BITCOIN & BLOCKCHAIN DATA ACCESS TOOLKIT")
    print("=" * 60)

    # Test Ordinals API
    print("\n[1] ORDINALS INSCRIPTIONS")
    print("-" * 40)
    ordinals = OrdinalsAPI()

    try:
        stats = ordinals.get_stats()
        print(f"Total inscriptions: {stats.get('count', 'N/A'):,}")
    except Exception as e:
        print(f"Stats error: {e}")

    print("\nFetching recent image inscriptions...")
    try:
        images = ordinals.list_inscriptions(mime_type='image/png', limit=5)
        for i, img in enumerate(images[:3]):
            print(f"  {i+1}. ID: {img.get('id', 'N/A')[:20]}...")
            print(f"     Type: {img.get('content_type', 'N/A')}")
            print(f"     Number: {img.get('number', 'N/A')}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test OP_RETURN
    print("\n[2] OP_RETURN DATA")
    print("-" * 40)
    op_return = OPReturnExtractor()

    # Famous OP_RETURN: Satoshi's message in block 0
    famous_txs = [
        ('4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b', 'Genesis block coinbase'),
    ]

    for txid, desc in famous_txs:
        print(f"  {desc}: {txid[:16]}...")

    # Test Arweave
    print("\n[3] ARWEAVE PERMANENT STORAGE")
    print("-" * 40)
    arweave = ArweaveAPI()

    try:
        images = arweave.search_images(first=3)
        print(f"Found {len(images)} image transactions")
        for img in images[:2]:
            print(f"  ID: {img.get('id', 'N/A')[:20]}...")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("CONTENT TYPES AVAILABLE FOR AI TRAINING:")
    print("=" * 60)
    content_types = [
        ("Ordinals Images", "image/png, image/webp, image/gif, image/svg+xml"),
        ("Ordinals Text", "text/plain, text/html, application/json"),
        ("Ordinals Code", "text/javascript, text/css"),
        ("Ordinals Audio", "audio/mpeg, audio/wav"),
        ("Ordinals Video", "video/mp4, video/webm"),
        ("OP_RETURN", "80-byte messages, protocol data"),
        ("Stamps", "Base64 images (24x24 to 420x420)"),
        ("Arweave", "Any file type, unlimited size"),
        ("Ethereum", "Event logs, contract storage, calldata"),
    ]

    for name, types in content_types:
        print(f"  {name}: {types}")

    print("\n" + "=" * 60)
    print("APIs AVAILABLE (no auth required):")
    print("=" * 60)
    apis = [
        ("Hiro Ordinals", "https://api.hiro.so/ordinals/v1", "60 req/min free"),
        ("Blockstream", "https://blockstream.info/api", "Unlimited"),
        ("Arweave Gateway", "https://arweave.net", "Unlimited"),
        ("Ethereum RPC", "https://eth.llamarpc.com", "Rate limited"),
        ("StampChain", "https://stampchain.io/api/v2", "Unlimited"),
    ]

    for name, url, limit in apis:
        print(f"  {name}")
        print(f"    URL: {url}")
        print(f"    Limit: {limit}")
        print()


if __name__ == '__main__':
    demo()
