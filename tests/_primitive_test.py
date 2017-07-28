from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from dumbconf import _primitive


@pytest.mark.parametrize(
    ('v', 'tp', 'expected'),
    (
        ('foo', _primitive.String, "'foo'"),
        (True, _primitive.Bool, 'true'),
        (None, _primitive.Null, 'null'),
        ('key', _primitive.BareWord, 'key'),
    ),
)
def test_roundtrip(v, tp, expected):
    assert tp.parse(tp.dump(v)) == v
    assert tp.dump(v) == expected
