# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from dumbconf import ast
from dumbconf._tre import _pattern_expected_tokens
from dumbconf._tre import Or
from dumbconf._tre import Pattern
from dumbconf._tre import Star


@pytest.mark.parametrize(
    ('pattern', 'expected'),
    (
        # Base case
        (ast.Comment, (ast.Comment,)),
        # Or includes all possible ones
        (Or(ast.Comment, ast.NL), (ast.Comment, ast.NL)),
        # Pattern stops at the first element
        (Pattern(ast.Space, ast.Comment), (ast.Space,)),
        # Pattern with a Star continues though
        (Pattern(Star(ast.Space), ast.Comment), (ast.Comment, ast.Space)),
        # Pattern with a "Plus" does not
        (
            # Essentially Plus(ast.Space), ast.Comment
            Pattern(Pattern(ast.Space, Star(ast.Space)), ast.Comment),
            (ast.Space,),
        ),
        # Pattern with nested Star-only pattern continues
        (
            Pattern(Pattern(Star(ast.Space), Star(ast.Comment)), ast.NL),
            (ast.Comment, ast.NL, ast.Space),
        ),
    ),
)
def test_pattern_expected_tokens(pattern, expected):
    assert _pattern_expected_tokens(pattern) == expected
