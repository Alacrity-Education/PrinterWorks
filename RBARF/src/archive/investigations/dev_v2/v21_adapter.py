"""Adapter so the stock eval.py can score embedded_v2 on v2.1 datasets.

eval.py compares against the dataset's 19-byte payload'.  embedded_v2
emits the 16 DATA bytes after verifying crc8(DATA) against the decoded
2-of-3 majority; payload' is DATA || [crc8(DATA)]*3 by construction, so
rebuilding the check block from the emitted data is exact: the 19-byte
comparison succeeds if and only if the 16 DATA bytes are exact.

    python3 eval.py approaches/dev_v2/v21_adapter.py --data ../data/captures_v21.json
"""
import sys
import pathlib

_R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_R / "approaches"))
import embedded_v2 as _v2                        # noqa: E402

_v2._configure(16)                               # v2.1 test build


def decode(samples, meta):
    data = _v2.decode(samples, meta)
    if data is None:
        return None
    c = _v2._crc8(data)
    return bytes(data) + bytes((c, c, c))
