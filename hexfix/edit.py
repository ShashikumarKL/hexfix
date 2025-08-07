"""Functions to extract address ranges and relocate data within SREC files."""
from __future__ import annotations

from typing import List, Tuple

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
