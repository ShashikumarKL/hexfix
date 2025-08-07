"""Utilities for converting SREC data to binary."""
from __future__ import annotations

from typing import Iterable, Union


def srec_to_binary(
    srec: Union[str, Iterable[str]],
    start_address: int = 0,
    output_length: int | None = None,
) -> bytes:
    """Convert SREC data into a binary blob.

    Parameters
    ----------
    srec: Union[str, Iterable[str]]
        Either a path to an SREC file or an iterable of SREC lines.
    start_address: int
        First address that should appear in the output. Bytes below this
        address are ignored and padding inserted if necessary.
    output_length: int | None
        Desired length of the output. If ``None`` the output will extend up to
        the highest address encountered in the SREC data.

    Returns
    -------
    bytes
        Binary representation of the requested address range.
    """
    if isinstance(srec, str):
        # Treat as filename
        with open(srec, "r") as infile:
            lines = infile.readlines()
    else:
        lines = list(srec)

    records = []
    max_address = start_address
    for line in lines:
        line = line.strip()
        if not line.startswith("S"):
            continue
        record_type = line[:2]
        addr_len = {"S1": 4, "S2": 6, "S3": 8}.get(record_type)
        if addr_len is None:
            continue
        try:
            address = int(line[4:4 + addr_len], 16)
            data = bytes.fromhex(line[4 + addr_len : -2])
        except ValueError:
            continue
        records.append((address, data))
        rec_end = address + len(data)
        if rec_end > max_address:
            max_address = rec_end

    if output_length is None:
        length = max(0, max_address - start_address)
    else:
        length = output_length

    output = bytearray([0xFF] * length)
    for address, data in records:
        if address + len(data) <= start_address:
            continue
        offset = address - start_address
        if offset < 0:
            data = data[-offset:]
            offset = 0
        end = offset + len(data)
        if end > length:
            data = data[: length - offset]
            end = length
        output[offset:end] = data

    return bytes(output)
