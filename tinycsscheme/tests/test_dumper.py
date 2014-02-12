"""
    Tests for the CSScheme dumper
"""

import pytest

from ..tinycss.css21 import Stylesheet, Declaration, RuleSet
from ..tinycss.token_data import Token
from ..tinycss.tokenizer import tokenize_grouped

from ..dumper import CSSchemeDumper, DumpError
from ..parser import StringRule

from . import jsonify


# Shorthand functions for tinycss classes
def T(type_, value):
    return Token(type_, value, value, None, 0, 0)


def SR(keyword, value):
    tokens = list(tokenize_grouped(value))
    assert len(tokens) == 1
    return StringRule(keyword, tokens[0], 0, 0)


def SS(rules):
    return Stylesheet(rules, [], None)


def RS(sel, decl, at_rules=[]):
    sel = tokenize_grouped(sel)
    rs = RuleSet(sel, decl, 0, 0)
    rs.at_rules = at_rules
    return rs


def DC(name, value):
    return Declaration(name, tokenize_grouped(value), None, 0, 0)


@pytest.mark.parametrize(('stylesheet', 'expected_data'), [
    (SS([
        SR('@name', "Test"),
        SR('@at-rule', "hi"),
        RS('*', []),
        # Should this be tested here?
        RS('source', [DC('foreground', "#123456")]),
        SR('@uuid', '2e3af29f-ebee-431f-af96-72bda5d4c144')
        ]),
     {'name': "Test",
      'at-rule': "hi",
      'uuid': "2e3af29f-ebee-431f-af96-72bda5d4c144",
      'settings': [
          {'settings': {}},
          {'scope': "source",
           'settings': {'foreground': "#123456"}},
      ]}
     ),
])
def test_datafy(stylesheet, expected_data):
    data = CSSchemeDumper().datafy_stylesheet(stylesheet)
    assert data == expected_data


@pytest.mark.parametrize(('stylesheet', 'expected_error'), [
    (SS([
        SR('@name', "Test"),
        ]),
     "Must contain '*' ruleset"
     ),

    (SS([
        RS('*', [])
        ]),
     "Must contain 'name' at-rule"
     ),

    (SS([
        SR('@name', "Test"),
        RS('*', []),
        RS('*', [])
        ]),
     "Only one *-rule allowed"
     ),

    (SS([
        SR('@settings', "value"),
        SR('@name', "Test"),
        RS('*', [])
        ]),
     "Can not override 'settings' key using at-rules."
     ),
])
def test_datafy_errors(stylesheet, expected_error):
    try:
        CSSchemeDumper().datafy_stylesheet(stylesheet)
        assert False, "no exception was raised"
    except DumpError as e:
        assert expected_error in str(e)


@pytest.mark.parametrize(('ruleset', 'expected_data'), [
    (RS('*', [
        DC('foreground', "#123456"),
        DC('someSetting', "yeah"),
        ],
        []),
     {'settings': {
         'foreground': "#123456",
         'someSetting': "yeah",
     }}
     ),

    (RS('some other ruleset', [
        DC('fontStyle', "bold"),
        ], [
        SR('@name', "\"Test name\"")
        ]),
     {'name': "Test name",
      'scope': "some other ruleset",
      'settings': {
          'fontStyle': "bold",
      }}
     ),
])
def test_datafy_ruleset(ruleset, expected_data):
    data = CSSchemeDumper().datafy_ruleset(ruleset)
    assert data == expected_data


@pytest.mark.parametrize(('ruleset', 'expected_error'), [
    (RS('*', [], [
        SR('@settings', "a"),
        ]),
     "You can not override the 'settings' key using at-rules"
     ),
    (RS('yeah', [], [
        SR('@scope', "a"),
        ]),
     "You can not override the 'scope' key using at-rules"
     ),
])
def test_datafy_ruleset_errors(ruleset, expected_error):
    try:
        CSSchemeDumper().datafy_ruleset(ruleset)
        assert False, "no exception was raised"
    except DumpError as e:
        assert expected_error in str(e)


@pytest.mark.parametrize(('decl', 'expected_decl'), [
    # color
    (DC('background', "#123456"),
     ('background', [('HASH', "#123456")])),

    (DC('foreground', "black"),
     ('foreground', [('HASH', "#000000")])),

    (DC('background', "cyan"),
     ('background', [('HASH', "#00FFFF")])),

    (DC('background', "rgb(16, 32, 50.2%)"),
     ('background', [('HASH', "#102080")])),

    (DC('background', "rgba(-100%, 312.6%, 5, .5)"),
     ('background', [('HASH', "#00FF0580")])),

    (DC('background', "hsl(0, 50%, 50%)"),
     ('background', [('HASH', "#BF4040")])),

    (DC('background', "hsla(123.4, 250%, 13.54%, 0.1)"),
     ('background', [('HASH', "#004504E6")])),

    # style list
    (DC('fontStyle', 'bold italic underline stippled_underline'),
     ('fontStyle', [('IDENT',  "bold"),
                    ('S',      " "),
                    ('IDENT', "italic"),
                    ('S',      " "),
                    ('IDENT',  "underline"),
                    ('S',      " "),
                    ('IDENT',  "stippled_underline")])),

])
def test_validify_decl(decl, expected_decl):
    CSSchemeDumper().validify_declaration(decl, '')
    assert (decl.name, list(jsonify(decl.value))) == expected_decl


@pytest.mark.parametrize(('decl', 'expected_error'), [
    # color
    (DC('background', "\"#123456\""),
     "unexpected STRING value for property background"),

    (DC('background', "#123456 #12345678"),
     "expected 1 token for property background, got 3"),

    (DC('foreground', "not-a-color"),
     "unknown color name 'not-a-color' for property foreground"),

    (DC('background', "yolo()"),
     "unknown function 'yolo()' for property background"),

    (DC('background', "rgb()"),
     "expected 3 parameters for function 'rgb()', got 0"),

    (DC('background', "rgba(1, 2, 3, 4, 5)"),
     "expected 4 parameters for function 'rgba()', got 5"),

    (DC('background', "rgb(1, 2 3, 4)"),
     "expected 1 token for parameter 2 in function 'rgb()', got 3"),

    (DC('background', "rgb(1, 2, 3}"),
     "expected 1 token for parameter 3 in function 'rgb()', got 2"),

    # Can't test all possible value types here, so only cover all params and
    # possible values as a whole
    (DC('background', "rgb(hi, 2, 3)"),
     "unexpected IDENT value for parameter 1 in function 'rgb()'"),

    (DC('background', "rgb(1, 2, 2.2)"),
     "unexpected NUMBER value for parameter 3 in function 'rgb()'"),

    (DC('background', "rgba(1, 2, 2, 10%)"),
     "unexpected PERCENTAGE value for parameter 4 in function 'rgba()'"),

    (DC('background', "hsl(\"string\", 2%, 3%)"),
     "unexpected STRING value for parameter 1 in function 'hsl()'"),

    (DC('background', "hsl(0, 2, 3%)"),
     "unexpected INTEGER value for parameter 2 in function 'hsl()'"),

    (DC('background', "hsla(0, 2%, 3%, #123)"),
     "unexpected HASH value for parameter 4 in function 'hsla()'"),

    # style list
    (DC('fontStyle', "#000001"),
     "unexpected HASH token for property fontStyle"),

    (DC('fontStyle', "\"hi\""),
     "unexpected STRING token for property fontStyle"),

    (DC('tagsOptions', "italicc"),
     "invalid value 'italicc' for property tagsOptions")
])
def test_validify_decl_errors(decl, expected_error):
    try:
        CSSchemeDumper().validify_declaration(decl, '')
        assert False, "no exception was raised"
    except DumpError as e:
        assert expected_error in str(e)
