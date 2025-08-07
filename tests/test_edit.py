import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from hexfix.edit import extract_range_srec, relocate_range_srec, _encode_srec_line
from hexfix.checksum import parse_srec_line


def _create_sample_file(path):
    # Two 16-byte blocks starting at 0x0010 and 0x0020
    lines = [
        _encode_srec_line("S1", 0x0010, bytes(range(16))),
        _encode_srec_line("S1", 0x0020, bytes(range(16, 32))),
    ]
    path.write_text("".join(lines))


def test_extract_range_srec(tmp_path):
    src = tmp_path / "in.srec"
    dst = tmp_path / "out.srec"
    _create_sample_file(src)
    extract_range_srec(str(src), str(dst), 0x0018, 0x0028)
    lines = dst.read_text().splitlines()
    assert len(lines) == 2
    rec1 = parse_srec_line(lines[0])[1:]
    rec2 = parse_srec_line(lines[1])[1:]
    # First record trimmed to address 0x0018 with bytes 8..15
    assert rec1[0] == 0x0018
    assert rec1[1] == bytes(range(8, 16))
    # Second record starts at 0x0020 with bytes 16..23
    assert rec2[0] == 0x0020
    assert rec2[1] == bytes(range(16, 24))


def test_relocate_range_srec(tmp_path):
    src = tmp_path / "in.srec"
    dst = tmp_path / "out.srec"
    _create_sample_file(src)
    relocate_range_srec(str(src), str(dst), 0x0010, 0x0020, 0x0030)
    lines = dst.read_text().splitlines()
    assert len(lines) == 2
    addrs = [parse_srec_line(line)[1] for line in lines]
    assert 0x0020 in addrs
    assert 0x0030 in addrs
    data_by_addr = {parse_srec_line(line)[1]: parse_srec_line(line)[2] for line in lines}
    assert data_by_addr[0x0030] == bytes(range(16))
    assert data_by_addr[0x0020] == bytes(range(16, 32))
