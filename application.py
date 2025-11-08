# app.py
import os
import sys
import json
import argparse
from typing import Dict, List, Tuple, Optional
from web3 import Web3

DEFAULT_RPC_A = os.environ.get("RPC_URL_A", os.environ.get("RPC_URL", "https://mainnet.infura.io/v3/YOUR_INFURA_KEY"))
DEFAULT_RPC_B = os.environ.get("RPC_URL_B", "https://arb1.arbitrum.io/rpc")

Slot = Tuple[str, int]  # (label, slot_index_int)


def to_checksum(addr: str) -> str:
    if not Web3.is_address(addr):
        raise ValueError(f"Invalid Ethereum address: {addr}")
    return Web3.to_checksum_address(addr)


def parse_slots(args) -> List[Slot]:
    slots: List[Slot] = []

    # Priority 1: --slot can be repeated, "label:0xSLOT" or just "0xSLOT"
    if args.slot:
        for item in args.slot:
            if ":" in item:
                label, raw = item.split(":", 1)
            else:
                label, raw = item, item
            slots.append((label, parse_slot_hex(raw)))
        return slots

    # Priority 2: --manifest JSON file
    if args.manifest:
        with open(args.manifest, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # ["0x..", "0x.."]
            for raw in data:
                slots.append((raw, parse_slot_hex(raw)))
        elif isinstance(data, dict):
            # {"label":"0x..", ...}
            for label, raw in data.items():
                slots.append((label, parse_slot_hex(raw)))
        else:
            raise ValueError("Manifest must be a list of 0x-hex slots or a mapping label -> 0x-hex slot.")
        return slots

    raise ValueError("No slots provided. Use --slot (repeatable) or --manifest JSON file.")


def parse_slot_hex(raw: str) -> int:
    s = raw.strip().lower()
    if not s.startswith("0x"):
        raise ValueError(f"Slot must be 0x-prefixed hex: {raw}")
    try:
        return int(s, 16)
    except Exception:
        raise ValueError(f"Invalid slot hex: {raw}")


def get_storage_at(w3: Web3, address: str, slot: int, block_id: str) -> str:
    val = w3.eth.get_storage_at(address, slot, block_identifier=block_id)
    return val.hex()


def read_slots(
    w3: Web3,
    address: str,
    block_id: str,
    slots: List[Slot],
) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for label, slot in slots:
        try:
            out[label] = get_storage_at(w3, address, slot, block_id)
        except Exception as e:
            out[label] = f"ERROR:{e}"
    return out


def compare(a: Dict[str, str], b: Dict[str, str]) -> Tuple[List[Tuple[str, str, str]], bool]:
    diffs: List[Tuple[str, str, str]] = []
    ok = True
    keys = sorted(set(a.keys()) | set(b.keys()))
    for k in keys:
        va, vb = a.get(k, "MISSING"), b.get(k, "MISSING")
        if va != vb:
            diffs.append((k, va, vb))
            ok = False
    return diffs, ok


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="zk-slot-soundness — compare raw EVM storage slot values across blocks/chains (useful for Aztec/Zama bridges, vaults, and Web3 audits)."
    )
    p.add_argument("--address", required=True, help="Contract address to inspect")
    p.add_argument("--rpc-a", default=DEFAULT_RPC_A, help="Primary RPC URL (default env RPC_URL_A or RPC_URL)")
    p.add_argument("--rpc-b", default=DEFAULT_RPC_B, help="Secondary RPC URL (default env RPC_URL_B)")
    p.add_argument("--block-a", default="latest", help="Block tag/number for RPC A (default: latest)")
    p.add_argument("--block-b", default="latest", help="Block tag/number for RPC B (default: latest)")
    p.add_argument("--slot", action="append", help="Storage slot to read. Use multiple times. Format: 0xSLOT or label:0xSLOT")
    p.add_argument("--manifest", help="Path to JSON file with slots: list ['0x..'] or map {'label':'0x..'}")
    p.add_argument("--timeout", type=int, default=30, help="RPC timeout seconds (default: 30)")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Validate URLs
    for url, name in [(args.rpc_a, "RPC A"), (args.rpc_b, "RPC B")]:
        if not str(url).startswith(("http://", "https://")):
            print(f"❌ Invalid {name} URL: {url}")
            sys.exit(1)

    # Validate address + slots
    try:
        address = to_checksum(args.address)
        slots = parse_slots(args)
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)

    # Build providers
    w3a = Web3(Web3.HTTPProvider(args.rpc_a, request_kwargs={"timeout": args.timeout}))
    w3b = Web3(Web3.HTTPProvider(args.rpc_b, request_kwargs={"timeout": args.timeout}))

    if not w3a.is_connected():
        print("❌ Connection failed for RPC A.")
        sys.exit(1)
    if not w3b.is_connected():
        print("❌ Connection failed for RPC B.")
        sys.exit(1)

    print("🔧 zk-slot-soundness")
    try:
        print(f"🧭 Chain A ID: {w3a.eth.chain_id}")
    except Exception:
        pass
    try:
        print(f"🧭 Chain B ID: {w3b.eth.chain_id}")
    except Exception:
        pass
    print(f"🔗 RPC A: {args.rpc_a}")
    print(f"🔗 RPC B: {args.rpc_b}")
    print(f"🏷️ Address: {address}")
    print(f"🧱 Block A: {args.block_a} | Block B: {args.block_b}")
    print(f"🗃️ Slots: {', '.join([f'{lbl}' for lbl, _ in slots])}")
 # ✅ New: Print UTC timestamp for when comparison is made
    from datetime import datetime
    timestamp = datetime.utcnow().isoformat() + "Z"
    print(f"🕒 Comparison Timestamp: {timestamp}")
    # Read
    a_vals = read_slots(w3a, address, args.block_a, slots)
    b_vals = read_slots(w3b, address, args.block_b, slots)

    # Display per-slot comparison
    print("\n📜 Comparison:")
    mismatches = 0
    for lbl, _ in slots:
        va = a_vals.get(lbl, "MISSING")
        vb = b_vals.get(lbl, "MISSING")
        status = "✅ MATCH" if va == vb else "❌ DIFF"
        print(f"  • {lbl:<20} A:{va} | B:{vb}  {status}")
        if va != vb:
            mismatches += 1

    # Summary
    if mismatches == 0:
        print("\n🎯 Storage soundness verified for all slots.")
    else:
        print(f"\n🚨 Storage soundness mismatch in {mismatches}/{len(slots)} slot(s).")

    if args.json:
        out = {
            "address": address,
            "rpc_a": args.rpc_a,
            "rpc_b": args.rpc_b,
            "block_a": args.block_a,
            "block_b": args.block_b,
            "slots": [{ "label": lbl, "index": hex(idx) } for lbl, idx in slots],
            "values_a": a_vals,
            "values_b": b_vals,
            "mismatches": mismatches,
            "ok": mismatches == 0,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))

    sys.exit(0 if mismatches == 0 else 2)


if __name__ == "__main__":
    main()
