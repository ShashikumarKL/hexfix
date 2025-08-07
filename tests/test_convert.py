import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import hexfix


def test_basic_conversion():
    srec = """\
S107000001020304EE
S10500040506EB
S9030000FC
""".splitlines()
    result = hexfix.srec_to_binary(srec)
    assert result == bytes([1, 2, 3, 4, 5, 6])


def test_gapped_conversion_with_padding():
    srec = """\
S1040100AA50
S1040104BB3B
S9030000FC
""".splitlines()
    result = hexfix.srec_to_binary(srec, start_address=0x0100, output_length=5)
    assert result == bytes([0xAA, 0xFF, 0xFF, 0xFF, 0xBB])
