import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from hexfix.edit import _encode_srec_line, patch_srec
from hexfix.checksum import parse_srec_line


def _create_sample_file(path):
    lines = [
        _encode_srec_line("S1", 0x0010, bytes(range(16))),
        _encode_srec_line("S1", 0x0020, bytes(range(16, 32))),
    ]
    path.write_text("".join(lines))


def test_patch_single_byte(tmp_path):
    src = tmp_path / "in.srec"
    dst = tmp_path / "out.srec"
    _create_sample_file(src)
    patch_srec(str(src), str(dst), {0x0015: 0xAA})
    lines = dst.read_text().splitlines()
    records = {addr: data for _, addr, data in (parse_srec_line(l) for l in lines)}
    assert records[0x0010][5] == 0xAA
    assert records[0x0020] == bytes(range(16, 32))


def test_patch_cross_record(tmp_path):
    src = tmp_path / "in.srec"
    dst = tmp_path / "out.srec"
    _create_sample_file(src)
    patch_srec(str(src), str(dst), {0x001F: 0xAA, 0x0020: 0xBB})
    lines = dst.read_text().splitlines()
    rec1 = parse_srec_line(lines[0])[1:]
    rec2 = parse_srec_line(lines[1])[1:]
    assert rec1[0] == 0x0010
    assert rec1[1] == bytes(range(15)) + b"\xAA"
    assert rec2[0] == 0x0020
    assert rec2[1] == b"\xBB" + bytes(range(17, 32))
