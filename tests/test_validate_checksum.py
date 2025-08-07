import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from hexfix.checksum import validate_srec_file
from hexfix.edit import _encode_srec_line


def test_validate_srec_file_valid(tmp_path):
    """No errors are reported for a file with correct checksums."""
    path = tmp_path / "in.srec"
    lines = [
        _encode_srec_line("S1", 0x0010, bytes(range(4))),
        _encode_srec_line("S1", 0x0020, bytes(range(4, 8))),
    ]
    path.write_text("".join(lines))
    assert validate_srec_file(str(path)) == []


def test_validate_srec_file_fix(tmp_path):
    """Lines with bad checksums are reported and can be fixed in-place."""
    path = tmp_path / "bad.srec"
    line1 = _encode_srec_line("S1", 0x0010, bytes(range(4)))
    line2 = _encode_srec_line("S1", 0x0020, bytes(range(4, 8)))
    # Corrupt the checksum of the second line
    bad_line2 = line2[:-3] + "00\n"
    path.write_text(line1 + bad_line2)

    assert validate_srec_file(str(path)) == [2]
    # Fix the file
    assert validate_srec_file(str(path), fix=True) == [2]
    # After fixing, file should validate cleanly
    assert validate_srec_file(str(path)) == []
    # And the contents restored
    assert path.read_text().splitlines()[1] == line2.rstrip("\n")

