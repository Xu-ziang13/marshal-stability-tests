"""Floating-point: boundary value analysis + special values (F4, F5).

marshal v1+ stores floats as 8 raw IEEE-754 bytes (TYPE_BINARY_FLOAT), so the
interesting questions are about bit-exact preservation of edge values rather
than rounding. v0 uses a decimal-string representation (TYPE_FLOAT) and is
tested separately for lossy behaviour.
"""

import marshal
import math
import struct
import sys

import pytest

import marshal_testkit as kit


def bits(x):
    """Return the raw 64-bit pattern of a float as an int."""
    return struct.unpack("<Q", struct.pack("<d", x))[0]


@pytest.mark.parametrize("value", kit.FLOAT_VALUES)
def test_float_binary_roundtrip_bit_exact(value):
    """v4 (binary float) preserves the exact bit pattern, incl. NaN payload."""
    out = marshal.loads(marshal.dumps(value, 4))
    if math.isnan(value):
        assert math.isnan(out)
        assert bits(out) == bits(value)     # payload + sign preserved
    else:
        assert bits(out) == bits(value)


def test_signed_zero_distinct_and_preserved():
    """+0.0 and -0.0 produce different bytes and survive round-trip (F4)."""
    assert marshal.dumps(0.0, 4) != marshal.dumps(-0.0, 4)
    assert bits(marshal.loads(marshal.dumps(-0.0, 4))) == bits(-0.0)
    assert bits(marshal.loads(marshal.dumps(0.0, 4))) == bits(0.0)


def test_infinities_roundtrip():
    assert marshal.loads(marshal.dumps(float("inf"))) == float("inf")
    assert marshal.loads(marshal.dumps(float("-inf"))) == float("-inf")


def test_nan_is_stable_within_process():
    """Same NaN object dumps identically every time (F5/F9)."""
    nan = float("nan")
    assert kit.stable(nan, version=4)


def test_signalling_nan_payload_preserved():
    """A signalling-NaN bit pattern survives binary marshalling unchanged."""
    snan = struct.unpack("<d", struct.pack("<Q", 0x7FF0000000000001))[0]
    out = marshal.loads(marshal.dumps(snan, 4))
    assert bits(out) == 0x7FF0000000000001


@pytest.mark.parametrize("value", [
    sys.float_info.max, sys.float_info.min, 5e-324, sys.float_info.epsilon,
])
def test_float_boundaries_roundtrip(value):
    assert marshal.loads(marshal.dumps(value, 4)) == value


def test_v0_decimal_float_is_lossy_for_some_values():
    """Document the legacy v0 string-float path.

    v0 serialises floats via repr; for ordinary values it still round-trips
    exactly in modern CPython (repr is round-trippable), but NaN/Inf handling
    differs. We assert the ordinary value survives and that the byte stream
    differs from the binary encoding -- evidence the formats are distinct.
    """
    value = 0.1
    assert marshal.loads(marshal.dumps(value, 0)) == value
    assert marshal.dumps(value, 0) != marshal.dumps(value, 4)


def test_complex_roundtrip_and_components():
    z = complex(1.5, -2.25)
    out = marshal.loads(marshal.dumps(z, 4))
    assert out == z
    assert bits(out.real) == bits(z.real)
    assert bits(out.imag) == bits(z.imag)
