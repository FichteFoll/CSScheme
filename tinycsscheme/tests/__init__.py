# coding: utf8
"""
    Test suite for tinycsscheme
    ---------------------------
"""


from __future__ import unicode_literals


# from ...tinycss.tests import assert_errors
def assert_errors(errors, expected_errors):
    """Test not complete error messages but only substrings."""
    assert len(errors) == len(expected_errors)
    for error, expected in zip(errors, expected_errors):
        assert expected in str(error)


# from ...tinycss.tests.test_tokenizer
def jsonify(tokens):
    """Turn tokens into "JSON-compatible" data structures."""
    for token in tokens:
        if token.type == 'FUNCTION':
            yield (token.type, token.function_name,
                   list(jsonify(token.content)))
        elif token.is_container:
            yield token.type, list(jsonify(token.content))
        else:
            yield token.type, token.value


def tuplify(rule):
    if rule.at_keyword:
        return (rule.at_keyword, list(jsonify([rule.value])))
    else:
        return (rule.selector.as_css(),
                [(decl.name, list(jsonify(decl.value)))
                 for decl in rule.declarations],
                [tuplify(at_rule)
                 for at_rule in rule.at_rules])
