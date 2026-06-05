"""Cross-version format stability (F8).

The marshal format is intentionally *not* stable across format versions: each
version adds type codes (e.g. v1 binary floats, v2 long-int packing, v3/v4
references and interning). These tests pin the observed behaviour so that:

* a change in default version is caught,
* the version-to-version differences are documented as tests,
* round-trip still holds for every version the value supports.
"""

import marshal

import pytest

import marshal_testkit as kit


def test_default_version_is_current():
    """``dumps`` with no version must equal an explicit ``marshal.version``."""
    obj = {"x": [1, 2.0, "three"]}
    assert marshal.dumps(obj) == marshal.dumps(obj, marshal.version)


@pytest.mark.parametrize("obj", [
    0, 1, -1, 2 ** 70, 3.14, "text", b"bytes", (1, 2), [1, 2], {"k": 1},
])
@pytest.mark.parametrize("version", kit.ALL_VERSIONS)
def test_roundtrip_holds_for_every_version(obj, version):
    assert marshal.loads(marshal.dumps(obj, version)) == obj


def test_float_encoding_changed_between_v1_and_v2():
    """v0/v1 store floats as text; v2+ as 8 raw bytes -> different streams.

    v2 and v3 share the binary float *payload* but differ in the head byte
    because v3 sets FLAG_REF (0x80) on the value. We compare the masked code.
    """
    assert marshal.dumps(1.0, 0) == marshal.dumps(1.0, 1)   # both decimal
    assert marshal.dumps(1.0, 1) != marshal.dumps(1.0, 2)   # text vs binary
    v2, v3 = marshal.dumps(1.0, 2), marshal.dumps(1.0, 3)
    assert v2[1:] == v3[1:]                                  # same payload
    assert (v2[0] & 0x7F) == (v3[0] & 0x7F)                  # same type code
    assert v3[0] & 0x80 and not v2[0] & 0x80                 # v3 adds FLAG_REF


def test_interning_added_in_v3_changes_repeated_string_layout():
    """Repeated strings shrink at v3+ thanks to references (F7/F8)."""
    obj = ("repeat-me", "repeat-me", "repeat-me")
    assert len(marshal.dumps(obj, 2)) > len(marshal.dumps(obj, 3))


@pytest.mark.parametrize("version", kit.ALL_VERSIONS)
def test_each_version_is_internally_deterministic(version):
    obj = {"a": 1, "b": [2, 3], "c": (4.0, "five")}
    assert kit.stable(obj, version=version)


def test_version_outputs_are_mutually_distinct_for_floats():
    """Snapshot: distinct encodings of a bare float across all versions.

    Three distinct byte streams are expected:
      * v0/v1 -- decimal text float (TYPE_FLOAT 'f'),
      * v2    -- binary float (TYPE_BINARY_FLOAT 'g'), no FLAG_REF,
      * v3/v4 -- same binary float but with FLAG_REF set ('g' | 0x80),
                 because v3+ adds the value to the reference table.
    """
    streams = {marshal.dumps(0.1, v) for v in kit.ALL_VERSIONS}
    assert len(streams) == 3
