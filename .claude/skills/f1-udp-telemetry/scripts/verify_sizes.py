"""
verify_sizes.py - Prove the packet layouts in f1_packets.py are byte-correct.

Every packet in the EA spec has a documented size. Because the structures are
packed with no padding, a single wrong field type shifts everything after it,
so a size match is strong evidence the whole layout is right. Run this after
any edit to f1_packets.py, and any time a parser starts returning nonsense.

    python verify_sizes.py          # check sizes
    python verify_sizes.py -v       # also round-trip a synthetic packet

Exit code is non-zero if anything mismatches, so it works in CI too.
"""

import struct
import sys

from f1_packets import (
    DOCUMENTED_SIZES, FORMATS, HEADER_SIZE, PACKET_NAMES,
    get_layout, parse_packet,
)


def check_sizes() -> bool:
    ok = True
    print(f"Header size: {HEADER_SIZE} bytes (expected 29)")
    if HEADER_SIZE != 29:
        ok = False
    for fmt in sorted(FORMATS):
        print(f"\n--- packet format {fmt} "
              f"({FORMATS[fmt]['max_cars']} cars) ---")
        for pid in sorted(FORMATS[fmt]["packets"]):
            layout = get_layout(fmt, pid)
            expected = DOCUMENTED_SIZES[fmt].get(pid)
            match = expected is not None and layout.size == expected
            ok &= match
            flag = "OK  " if match else "FAIL"
            print(f"  [{flag}] id {pid:>2} {PACKET_NAMES[pid]:<20} "
                  f"got {layout.size:>5}  expected {expected}")
    return ok


def check_roundtrip() -> bool:
    """Build a synthetic packet from each layout and parse it back."""
    ok = True
    for fmt in sorted(FORMATS):
        for pid in sorted(FORMATS[fmt]["packets"]):
            layout = get_layout(fmt, pid)
            header = struct.pack(
                "<HBBBBBQfIIBB", fmt, 25, 1, 0, 1, pid, 12345, 1.5, 10, 10, 0, 255
            )
            body = bytes(layout.size - HEADER_SIZE)
            try:
                parsed_header, parsed_body = parse_packet(header + body)
                assert parsed_header["m_packetId"] == pid
                assert parsed_body  # non-empty
            except Exception as exc:  # noqa: BLE001
                print(f"  [FAIL] format {fmt} id {pid}: {exc}")
                ok = False
    if ok:
        print("\nRound-trip parse of all layouts: OK")
    return ok


if __name__ == "__main__":
    passed = check_sizes()
    if "-v" in sys.argv or "--verbose" in sys.argv:
        passed &= check_roundtrip()
    print("\n" + ("ALL LAYOUTS VERIFIED" if passed else "MISMATCHES FOUND"))
    sys.exit(0 if passed else 1)
