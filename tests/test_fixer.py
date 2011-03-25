# -*- coding: utf-8 -*-

from supplement.fixer import fix, sanitize_encoding

def test_encoding_sanitization():
    tree, source = fix(sanitize_encoding(u'# coding: utf-8\n\n\n"вау"'))