#!/usr/bin/env python3
"""Parse the eps field of a production ``D:`` report.

Two encodings exist, and both are unambiguous:

* ``-105`` / ``12`` -- signed DECIMAL centi-percent.  What the SHIPPING
  TERSE image (`rbarf_prod.c`, no ``-DVERBOSE``) emits, and what every
  pre-v2.3 bench log holds.
* ``xFF97``        -- ``'x'`` + 4 hex digits, the raw big-endian
  two's-complement int16, same centi-percent units.  What the VERBOSE
  BENCH image emits from protocol v2.3 onwards: the 92 B of decimal
  printer (`uart_put_i16` 84 B + its power-of-ten table 8 B) does not
  fit in the 8 KB image alongside the ``V:`` line, and reusing the hex
  printer the ``V:`` line already carries costs 6 B instead.  The
  ``'x'`` sentinel keeps ``xFF97`` from ever being read as decimal.

The units, the sign convention and the meaning (the decoder's own clock
lock, 0 when there is no lock) are identical in both encodings.
"""


def parse_eps(field: str) -> int:
    """``'-105'`` -> -105, ``'xFF97'`` -> -105.  Raises on anything else."""
    s = field.strip()
    if s[:1] in ("x", "X"):
        v = int(s[1:], 16)
        if len(s) != 5:
            raise ValueError(f"hex eps must be x + 4 digits: {field!r}")
        return v - 0x10000 if v & 0x8000 else v
    return int(s)


if __name__ == "__main__":
    assert parse_eps("-105") == -105
    assert parse_eps("0") == 0
    assert parse_eps("1645") == 1645
    assert parse_eps("xFF97") == -105
    assert parse_eps("x0000") == 0
    assert parse_eps("x066D") == 1645
    assert parse_eps("xF993") == -1645
    for v in range(-32768, 32768, 7):
        assert parse_eps("x%04X" % (v & 0xFFFF)) == v, v
        assert parse_eps("%d" % v) == v
    print("epsfmt self-test OK")
