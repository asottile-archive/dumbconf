from __future__ import absolute_import
from __future__ import unicode_literals

import io
import re

import pytest

from dumbconf import loads


START = '```yaml\n'
END = '\n```'
BLOCK = re.compile('(?<=```yaml\n).*?(?=\n```)', re.MULTILINE | re.DOTALL)
README = io.open('README.md').read()


@pytest.mark.parametrize('code_block', BLOCK.findall(README))
def test_readme_code_examples(code_block):
    loads(code_block)
