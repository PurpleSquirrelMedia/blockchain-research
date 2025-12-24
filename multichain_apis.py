#!/usr/bin/env python3
"""
Multi-Chain Data Access Toolkit
================================
Extends bitcoin_apis.py to support additional chains.
"""

import requests
import json
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

# =============================================================================
# SOLANA
# =============================================================================

class SolanaAPI:
    """
    Access Solana data - NFTs, SPL tokens, inscriptions.
    """

    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        self.rpc = rpc_url
        self.helius_api = "https://api.helius.xyz/v0"  # Requires API key for full access
        self.session = requests.Session()

    def rpc_call(self, method: str, params: list = None) -> Dict:
        """Make JSON-RPC call to Solana"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        resp = self.session.post(self.rpc, json=payload, timeout=30)
        return resp.json()

    def get_account_info(self, pubkey: str) -> Dict:
        """Get account data"""
        return self.rpc_call("getAccountInfo", [
            pubkey,
            {"encoding": "base64"}
        ])

    def get_transaction(self, signature: str) -> Dict:
        """Get transaction details"""
        return self.rpc_call("getTransaction", [
            signature,
            {"encoding": "json", "maxSupportedTransactionVersion": 0}
        ])

    def get_nft_metadata(self, mint: str) -> Dict:
        """Get NFT metadata from on-chain data"""
        # Token metadata program
        return self.get_account_info(mint)

    def search_nfts_magiceden(self, collection: str = None, limit: int = 20) -> List[Dict]:
        """Search NFTs via Magic Eden API"""
        url = "https://api-mainnet.magiceden.dev/v2/tokens"
        params = {"limit": limit}
        if collection:
            url = f"https://api-mainnet.magiceden.dev/v2/collections/{collection}/listings"

        try:
            resp = self.session.get(url, params=params, timeout=10)
            return resp.json()
        except:
            return []


# =============================================================================
# BASE (L2 on Ethereum)
# =============================================================================

class BaseAPI:
    """
    Access Base L2 data - uses standard Ethereum JSON-RPC.
    """

    def __init__(self):
        self.rpc = "https://mainnet.base.org"
        self.session = requests.Session()

    def rpc_call(self, method: str, params: list = None) -> Dict:
        """Make JSON-RPC call"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        resp = self.session.post(self.rpc, json=payload, timeout=30)
        return resp.json()

    def get_logs(self, address: str, from_block: int, to_block: int) -> List[Dict]:
        """Get event logs"""
        params = [{
            "address": address,
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block)
        }]
        result = self.rpc_call("eth_getLogs", params)
        return result.get("result", [])

    def get_transaction(self, tx_hash: str) -> Dict:
        """Get transaction"""
        return self.rpc_call("eth_getTransactionByHash", [tx_hash])


# =============================================================================
# POLYGON
# =============================================================================

class PolygonAPI:
    """
    Access Polygon data.
    """

    def __init__(self):
        self.rpc = "https://polygon-rpc.com"
        self.session = requests.Session()

    def rpc_call(self, method: str, params: list = None) -> Dict:
        """Make JSON-RPC call"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or []
        }
        resp = self.session.post(self.rpc, json=payload, timeout=30)
        return resp.json()

    def get_logs(self, address: str, from_block: int, to_block: int) -> List[Dict]:
        """Get event logs"""
        params = [{
            "address": address,
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block)
        }]
        result = self.rpc_call("eth_getLogs", params)
        return result.get("result", [])


# =============================================================================
# NEAR
# =============================================================================

class NearAPI:
    """
    Access NEAR data - contracts, NFTs.
    """

    def __init__(self):
        self.rpc = "https://rpc.mainnet.near.org"
        self.session = requests.Session()

    def rpc_call(self, method: str, params: Dict) -> Dict:
        """Make JSON-RPC call"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        resp = self.session.post(self.rpc, json=payload, timeout=30)
        return resp.json()

    def get_account(self, account_id: str) -> Dict:
        """Get account state"""
        return self.rpc_call("query", {
            "request_type": "view_account",
            "finality": "final",
            "account_id": account_id
        })

    def view_function(self, contract: str, method: str, args: Dict = None) -> Dict:
        """Call view function on contract"""
        import base64
        args_base64 = base64.b64encode(json.dumps(args or {}).encode()).decode()
        return self.rpc_call("query", {
            "request_type": "call_function",
            "finality": "final",
            "account_id": contract,
            "method_name": method,
            "args_base64": args_base64
        })


# =============================================================================
# COSMOS (via public REST APIs)
# =============================================================================

class CosmosAPI:
    """
    Access Cosmos Hub data.
    """

    def __init__(self):
        self.rest = "https://rest.cosmos.directory/cosmoshub"
        self.session = requests.Session()

    def get_block(self, height: int = None) -> Dict:
        """Get block data"""
        url = f"{self.rest}/cosmos/base/tendermint/v1beta1/blocks/"
        if height:
            url += str(height)
        else:
            url += "latest"
        resp = self.session.get(url, timeout=10)
        return resp.json()

    def get_txs(self, height: int) -> List[Dict]:
        """Get transactions in block"""
        url = f"{self.rest}/cosmos/tx/v1beta1/txs?events=tx.height={height}"
        resp = self.session.get(url, timeout=10)
        return resp.json().get("txs", [])


# =============================================================================
# STACKS (Bitcoin L2)
# =============================================================================

class StacksAPI:
    """
    Access Stacks data - Bitcoin-secured smart contracts.
    """

    def __init__(self):
        self.api = "https://api.mainnet.hiro.so"
        self.session = requests.Session()

    def get_block(self, height: int = None) -> Dict:
        """Get block data"""
        if height:
            url = f"{self.api}/extended/v1/block/by_height/{height}"
        else:
            url = f"{self.api}/extended/v1/block"
        resp = self.session.get(url, timeout=10)
        return resp.json()

    def get_nft_holdings(self, address: str) -> List[Dict]:
        """Get NFTs held by address"""
        url = f"{self.api}/extended/v1/tokens/nft/holdings"
        params = {"principal": address}
        resp = self.session.get(url, params=params, timeout=10)
        return resp.json().get("results", [])

    def search_nfts(self, limit: int = 50) -> List[Dict]:
        """Search NFT events"""
        url = f"{self.api}/extended/v1/tokens/nft/mints"
        params = {"limit": limit}
        resp = self.session.get(url, params=params, timeout=10)
        return resp.json().get("results", [])


# =============================================================================
# IPFS/FILECOIN
# =============================================================================

class IPFSGateway:
    """
    Access IPFS data via public gateways.
    Note: Data permanence depends on pinning.
    """

    def __init__(self):
        self.gateways = [
            "https://ipfs.io/ipfs",
            "https://cloudflare-ipfs.com/ipfs",
            "https://gateway.pinata.cloud/ipfs",
            "https://dweb.link/ipfs"
        ]
        self.session = requests.Session()

    def get_content(self, cid: str, timeout: int = 30) -> bytes:
        """Fetch content by CID, trying multiple gateways"""
        for gateway in self.gateways:
            try:
                url = f"{gateway}/{cid}"
                resp = self.session.get(url, timeout=timeout)
                if resp.status_code == 200:
                    return resp.content
            except:
                continue
        return None

    def get_json(self, cid: str) -> Dict:
        """Fetch JSON metadata"""
        content = self.get_content(cid)
        if content:
            try:
                return json.loads(content)
            except:
                return {}
        return {}


# =============================================================================
# UNIFIED INTERFACE
# =============================================================================

@dataclass
class ChainRecord:
    """Unified record across all chains"""
    chain: str
    chain_id: str
    block_height: int
    timestamp: int
    content_type: str
    content_hash: str
    content_size: int
    local_path: str = None
    metadata: Dict = None


class MultiChainCollector:
    """
    Unified interface for collecting data from multiple chains.
    """

    def __init__(self):
        self.chains = {
            "solana": SolanaAPI(),
            "base": BaseAPI(),
            "polygon": PolygonAPI(),
            "near": NearAPI(),
            "cosmos": CosmosAPI(),
            "stacks": StacksAPI(),
            "ipfs": IPFSGateway(),
        }

    def get_chain(self, name: str):
        """Get chain API instance"""
        return self.chains.get(name.lower())

    def test_all_chains(self) -> Dict[str, bool]:
        """Test connectivity to all chains"""
        results = {}

        # Solana
        try:
            sol = self.chains["solana"]
            result = sol.rpc_call("getHealth")
            results["solana"] = result.get("result") == "ok"
        except:
            results["solana"] = False

        # Base
        try:
            base = self.chains["base"]
            result = base.rpc_call("eth_blockNumber")
            results["base"] = "result" in result
        except:
            results["base"] = False

        # Polygon
        try:
            poly = self.chains["polygon"]
            result = poly.rpc_call("eth_blockNumber")
            results["polygon"] = "result" in result
        except:
            results["polygon"] = False

        # NEAR
        try:
            near = self.chains["near"]
            result = near.rpc_call("status", {})
            results["near"] = "result" in result
        except:
            results["near"] = False

        # Cosmos
        try:
            cosmos = self.chains["cosmos"]
            result = cosmos.get_block()
            results["cosmos"] = "block" in result
        except:
            results["cosmos"] = False

        # Stacks
        try:
            stacks = self.chains["stacks"]
            result = stacks.get_block()
            results["stacks"] = "height" in result or "results" in result
        except:
            results["stacks"] = False

        return results


def demo():
    print("=" * 60)
    print("MULTI-CHAIN DATA ACCESS TOOLKIT")
    print("=" * 60)

    collector = MultiChainCollector()

    print("\n[TESTING CHAIN CONNECTIVITY]")
    print("-" * 40)
    results = collector.test_all_chains()
    for chain, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {chain}: {status}")

    # Test Stacks NFTs
    print("\n[STACKS NFT MINTS]")
    print("-" * 40)
    try:
        stacks = collector.get_chain("stacks")
        nfts = stacks.search_nfts(limit=3)
        for nft in nfts[:3]:
            print(f"  TX: {nft.get('tx_id', 'N/A')[:20]}...")
            print(f"  Asset: {nft.get('asset_identifier', 'N/A')[:40]}...")
    except Exception as e:
        print(f"  Error: {e}")

    # Test Cosmos block
    print("\n[COSMOS LATEST BLOCK]")
    print("-" * 40)
    try:
        cosmos = collector.get_chain("cosmos")
        block = cosmos.get_block()
        height = block.get("block", {}).get("header", {}).get("height", "N/A")
        print(f"  Height: {height}")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("CHAINS AVAILABLE:")
    print("=" * 60)
    chains = [
        ("Bitcoin", "Ordinals, OP_RETURN, Stamps", "bitcoin_apis.py"),
        ("Ethereum", "Logs, calldata, storage", "bitcoin_apis.py"),
        ("Arweave", "Permanent storage", "bitcoin_apis.py"),
        ("Solana", "NFTs, SPL tokens", "multichain_apis.py"),
        ("Base", "L2 logs, calldata", "multichain_apis.py"),
        ("Polygon", "L2 logs, calldata", "multichain_apis.py"),
        ("NEAR", "Contracts, NFTs", "multichain_apis.py"),
        ("Cosmos", "IBC, transactions", "multichain_apis.py"),
        ("Stacks", "Bitcoin-secured NFTs", "multichain_apis.py"),
        ("IPFS", "Content-addressed", "multichain_apis.py"),
    ]

    for name, data_types, module in chains:
        print(f"  {name}: {data_types} ({module})")


if __name__ == "__main__":
    demo()
