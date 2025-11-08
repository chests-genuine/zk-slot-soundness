# zk-slot-soundness

## Overview
`zk-slot-soundness` compares raw EVM storage slot values for a single contract across two chains or two blocks.  
It’s a tiny, audit-friendly tool to validate state **soundness** for bridges, rollup inbox/outbox pairs, vaults, and other critical contracts in zk ecosystems like **Aztec** and **Zama**.  
By reading exact storage slots (no ABI required), it helps catch unintended upgrades, diverging states, or faulty relayers.

## Features
- Read arbitrary storage slots via JSON-RPC (`eth_getStorageAt`)
- Compare values across two RPC endpoints and/or block heights
- Human-friendly labels for slots, plus JSON output for CI
- Clear exit codes for automation (0 on match, 2 on mismatch)
- No ABI or verification required — raw, deterministic storage checks

## Installation
1) Python 3.9+  
2) Install dependency:  
   pip install web3  
3) (Optional) Set RPCs via environment to avoid long CLI flags:  
   export RPC_URL_A=https://mainnet.infura.io/v3/YOUR_KEY  
   export RPC_URL_B=https://arb1.arbitrum.io/rpc

## Usage

Compare a couple of slots by repeating `--slot` (same slot names on both sides):
   python app.py --address 0xYourContract --slot owner:0x0 --slot impl:0x360894A13BA1A3210667C828492DB98DCA3E2076CC3735A920A3CA505D382BBC

Use a manifest file (list of hex slots):
   python app.py --address 0xYourContract --manifest slots.json

Use a manifest with labels (map label -> slot):
   python app.py --address 0xYourContract --manifest labeled-slots.json

Compare between different blocks on the same RPCs:
   python app.py --address 0xYourContract --block-a 19000000 --block-b 20000000

Compare mainnet vs L2 at latest blocks:
   python app.py --rpc-a https://mainnet.infura.io/v3/YOUR_KEY --rpc-b https://arb1.arbitrum.io/rpc --address 0xYourContract

Emit JSON for CI:
   python app.py --address 0xYourContract --slot totalSupply:0x0 --json

Increase timeout for slow providers:
   python app.py --address 0xYourContract --manifest slots.json --timeout 60

## Manifest formats
List form:
[
  "0x0",
  "0x360894A13BA1A3210667C828492DB98DCA3E2076CC3735A920A3CA505D382BBC"
]

Map form:
{
  "owner": "0x0",
  "implementation": "0x360894A13BA1A3210667C828492DB98DCA3E2076CC3735A920A3CA505D382BBC"
}

## Expected result
- The tool prints chain info (when available), the two RPCs/blocks used, and each slot’s A vs B value with a ✅ MATCH or ❌ DIFF flag.  
- A final summary line states whether storage is sound across all requested slots.  
- Exit code `0` if all slots match; `2` if any mismatch occurs.

Example (truncated):
🔧 zk-slot-soundness  
🧭 Chain A ID: 1  
🧭 Chain B ID: 42161  
🔗 RPC A: https://mainnet.infura.io/v3/…  
🔗 RPC B: https://arb1.arbitrum.io/rpc  
🏷️ Address: 0xABC…  
🧱 Block A: latest | Block B: latest  
🗃️ Slots: owner, implementation

📜 Comparison:  
  • owner                A:0x000000…01 | B:0x000000…01  ✅ MATCH  
  • implementation       A:0x000000…9f | B:0x000000…a3  ❌ DIFF

🚨 Storage soundness mismatch in 1/2 slot(s).

- **Timestamp Added:** Each run now prints a UTC timestamp to correlate results with system logs.  
- **Cross-RPC Caution:** Ensure both RPCs have archive access to avoid missing historical state data.  
- **Slot Labels:** Use descriptive labels like `owner`, `impl`, or `root` for clarity in comparisons.  
- **Historical Queries:** When querying older blocks, use archive nodes (Infura/Alchemy Premium).  
- **Proxy Awareness:** For EIP-1967 proxies, track slot `0x3608...BBC` to ensure implementation consistency.  
- **JSON Output:** Includes both RPC details, blocks, and timestamp for reproducibility.  
- **ZK Importance:** Stable state parity between chains ensures deterministic proofs and sound cross-domain messaging.  
- **Security Use:** Useful for verifying L1 ↔ L2 bridge states, vault integrity, and upgrade correctness.  
- **Best Practice:** Run daily or per-deployment to catch unauthorized or silent state changes early.  

**Exit Codes:**  
  `0` → All slots matched  
  `2` → At least one mismatch or partial error  
