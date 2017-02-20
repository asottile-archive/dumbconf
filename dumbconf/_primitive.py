from __future__ import absolute_import
from __future__ import unicode_literals

import ast


class Bool(object):
    @staticmethod
    def parse(s):
        return ast.literal_eval(s.lower().capitalize())

    dump = staticmethod(repr)


class Null(object):
    @staticmethod
    def parse(_):
        return None

    dump = staticmethod(repr)


class Float(object):
    parse = staticmethod(ast.literal_eval)
    dump = staticmethod(repr)


class Int(object):
    parse = staticmethod(ast.literal_eval)
    dump = staticmethod(repr)


class String(object):
    @staticmethod
    def parse(s):
        # python2 will literal_eval as bytes
        return ast.literal_eval('u' + s)

    @staticmethod
    def dump(v):
        # python2 will repr with a `u` prefix
        return repr(v).lstrip('u')


class BareWord(object):
    @staticmethod
    def parse(s):
        return s

    @staticmethod
    def dump(v):
        return v
