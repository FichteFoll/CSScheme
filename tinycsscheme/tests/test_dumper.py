"""
    Tests for the CSScheme dumper
"""

import pytest

from ..dumper import CSSchemeDumper, DumpError
from ..parser import Stylesheet, Declaration, RuleSet, StringRule, Token


# Shorthand functions for tinycss classes
def T(type_, value):
    return Token(type_, value, value, None, 0, 0)


def SR(keyword, value):
    return StringRule(keyword, T('STRING', value), 0, 0)


def SS(rules):
    return Stylesheet(rules, [], None)


def RS(sel, decl, at_rules=[]):
    # sel = [T('DELIM', sel)]
    sel = tokenize(sel)
    rs = RuleSet(sel, decl, 0, 0)
    rs.at_rules = at_rules
    return rs


def DC(name, value):
    return Declaration(name, tokenize(value), None, 0, 0)


# Quick and dirty implementation of a tokenizer so I don't need to use parts
# of the parser
def tokenize(value):
    tl = []
    for v in value.split():
        # Add S separator
        if tl:
            tl.append(T('S', ' '))

        if value.startswith('#'):
            tl.append(T('HASH', v))
        else:
            tl.append(T('IDENT', v))
    return tl


@pytest.mark.parametrize(('stylesheet', 'expected_data'), [
    (SS([
        SR('@name', "Test"),
        SR('@at-rule', "hi"),
        RS('*', []),
        # Should this be tested here?
        RS('source', [DC('foreground', "#123456")]),
        ]),
     {'name': "Test",
      'settings': [
          {'settings': {}},
          {'scope': "source",
           'settings': {'foreground': "#123456"}},
      ],
      'at-rule': "hi"}
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
        SR('@settings', ""),
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
        SR('@name', "Test name")
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
