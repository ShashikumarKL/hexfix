"""Functions to extract address ranges and relocate data within SREC files."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .checksum import parse_srec_line

# Mapping of record type to address length in bytes
ADDRESS_LENGTH = {"S1": 2, "S2": 3, "S3": 4}


def _encode_srec_line(record_type: str, address: int, data: bytes) -> str:
    """Encode a data record into an SREC line.

    Parameters
    ----------
    record_type: str
        The record type (S1/S2/S3).
    address: int
        Starting address for the data bytes.
    data: bytes
        Data payload for the record.
    """
    addr_len = ADDRESS_LENGTH[record_type]
    byte_count = addr_len + len(data) + 1  # +1 for checksum byte
    addr_fmt = f"{address:0{addr_len*2}X}"
    data_hex = data.hex().upper()
    # Compute checksum: ones' complement of sum of count, address bytes, data
    addr_bytes = [(address >> (8*(addr_len-1-i))) & 0xFF for i in range(addr_len)]
    checksum = (~(byte_count + sum(addr_bytes) + sum(data)) & 0xFF)
    return f"{record_type}{byte_count:02X}{addr_fmt}{data_hex}{checksum:02X}\n"


def extract_range_srec(input_name: str, output_name: str, start_address: int, end_address: int) -> None:
    """Extract a range of addresses from an SREC file.

    Data records that intersect the given range are trimmed so that the
    resulting file contains only bytes within ``start_address`` (inclusive)
    and ``end_address`` (exclusive).
    """
    result_lines: List[str] = []
    termination_line = None
    with open(input_name, "r") as infile:
        for line in infile:
            line = line.rstrip("\n")
            if not line.startswith("S"):
                continue
            record_type = line[0:2]
            if record_type in ("S7", "S8", "S9"):
                termination_line = line + "\n"
                continue
            if record_type == "S0":
                result_lines.append(line + "\n")
                continue
            rec_type, address, data = parse_srec_line(line)
            if rec_type not in ADDRESS_LENGTH:
                continue
            record_end = address + len(data)
            if record_end <= start_address or address >= end_address:
                continue
            start_trim = max(start_address - address, 0)
            end_trim = max(record_end - end_address, 0)
            new_data = data[start_trim: len(data) - end_trim]
            new_address = address + start_trim
            result_lines.append(_encode_srec_line(record_type, new_address, new_data))
    # append termination line if present
    if termination_line:
        result_lines.append(termination_line)
    with open(output_name, "w") as outfile:
        outfile.writelines(result_lines)


def relocate_range_srec(input_name: str, output_name: str, src_start: int, src_end: int, dest_start: int) -> None:
    """Relocate a block of addresses from one range to another.

    Bytes within ``[src_start, src_end)`` are moved so that the byte that was at
    ``src_start`` now resides at ``dest_start``. Bytes outside of the range are
    left untouched. Overlapping regions are not specially handled.
    """
    output_lines: List[str] = []
    relocated_lines: List[Tuple[int, str]] = []
    termination_line = None
    with open(input_name, "r") as infile:
        for line in infile:
            line = line.rstrip("\n")
            if not line.startswith("S"):
                continue
            record_type = line[0:2]
            if record_type in ("S7", "S8", "S9"):
                termination_line = line + "\n"
                continue
            if record_type == "S0":
                output_lines.append(line + "\n")
                continue
            rec_type, address, data = parse_srec_line(line)
            if rec_type not in ADDRESS_LENGTH:
                output_lines.append(line + "\n")
                continue
            record_end = address + len(data)
            if record_end <= src_start or address >= src_end:
                output_lines.append(line + "\n")
                continue
            # Determine portions before, within, and after the relocation range
            inter_start = max(address, src_start)
            inter_end = min(record_end, src_end)
            before_len = inter_start - address
            after_len = record_end - inter_end
            if before_len > 0:
                before_data = data[:before_len]
                output_lines.append(_encode_srec_line(record_type, address, before_data))
            if after_len > 0:
                after_data = data[-after_len:]
                out_address = record_end - after_len
                output_lines.append(_encode_srec_line(record_type, out_address, after_data))
            # Relocated middle part
            middle_data = data[before_len: len(data) - after_len]
            new_address = dest_start + (inter_start - src_start)
            relocated_lines.append((new_address, _encode_srec_line(record_type, new_address, middle_data)))
    # sort relocated lines by address and append
    relocated_lines.sort(key=lambda x: x[0])
    output_lines.extend(line for _, line in relocated_lines)
    if termination_line:
        output_lines.append(termination_line)
    with open(output_name, "w") as outfile:
        outfile.writelines(output_lines)


def parse_patch_file(patch_file: str | Path) -> Dict[int, int]:
    """Parse a simple patch file into a dictionary.

    Each non-empty line should contain an address and a byte value separated
    by whitespace or a colon. Numbers may be in decimal or prefixed hexadecimal
    form. Lines beginning with ``#`` are treated as comments.
    """

    patches: Dict[int, int] = {}
    for raw in Path(patch_file).read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" in line:
            addr_str, byte_str = line.split(":", 1)
        else:
            parts = line.split()
            if len(parts) != 2:
                continue
            addr_str, byte_str = parts
        address = int(addr_str, 0)
        byte_val = int(byte_str, 0) & 0xFF
        patches[address] = byte_val
    return patches


def patch_srec(
    input_name: str,
    output_name: str,
    patches: Dict[int, int] | str | Path,
) -> None:
    """Apply byte patches to an SREC file.

    Parameters
    ----------
    input_name:
        Path to the source SREC file.
    output_name:
        Where the patched SREC will be written.
    patches:
        Mapping of ``{address: byte}`` or a path to a text file understood by
        :func:`parse_patch_file`.
    """

    if not isinstance(patches, dict):
        patches = parse_patch_file(patches)

    header_lines: List[str] = []
    term_lines: List[str] = []
    data_records: List[Tuple[str, int, bytearray]] = []
    addr_index: Dict[int, Tuple[int, int]] = {}

    with open(input_name, "r") as infile:
        for line in infile:
            line = line.rstrip("\n")
            if not line.startswith("S"):
                continue
            record_type = line[0:2]
            if record_type in ("S1", "S2", "S3"):
                rec_type, address, data = parse_srec_line(line)
                buf = bytearray(data)
                idx = len(data_records)
                for offset in range(len(buf)):
                    addr_index[address + offset] = (idx, offset)
                data_records.append((record_type, address, buf))
            elif record_type == "S0":
                header_lines.append(line + "\n")
            elif record_type in ("S7", "S8", "S9"):
                term_lines.append(line + "\n")

    missing: Dict[int, int] = {}
    for addr, val in patches.items():
        if addr in addr_index:
            idx, offset = addr_index[addr]
            data_records[idx][2][offset] = val & 0xFF
        else:
            missing[addr] = val & 0xFF

    if missing:
        sorted_addrs = sorted(missing)
        start = sorted_addrs[0]
        chunk = [missing[start]]
        prev = start
        groups: List[Tuple[int, List[int]]] = []
        for addr in sorted_addrs[1:]:
            if addr == prev + 1:
                chunk.append(missing[addr])
            else:
                groups.append((start, chunk))
                start = addr
                chunk = [missing[addr]]
            prev = addr
        groups.append((start, chunk))

        MAX_LEN = 16
        for start_addr, data_list in groups:
            offset = 0
            while offset < len(data_list):
                piece = data_list[offset : offset + MAX_LEN]
                addr = start_addr + offset
                record_type = (
                    "S1"
                    if addr <= 0xFFFF
                    else "S2"
                    if addr <= 0xFFFFFF
                    else "S3"
                )
                data_records.append(
                    (record_type, addr, bytearray(piece))
                )
                offset += len(piece)

    data_records.sort(key=lambda r: r[1])
    output_lines = header_lines[:]
    for record_type, address, buf in data_records:
        output_lines.append(_encode_srec_line(record_type, address, bytes(buf)))
    output_lines.extend(term_lines)

    with open(output_name, "w") as outfile:
        outfile.writelines(output_lines)
