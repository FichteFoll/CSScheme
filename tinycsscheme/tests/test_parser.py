"""
    Tests for the CSScheme parser
    ----------------------------
    Based on the original tests for tinycss's CSS 2.1 parser
    which is (c) 2012 by Simon Sapin and BSD-licensed.
"""

import pytest

from ..parser import CSSchemeParser
from ..tinycss.css21 import CSS21Parser
from . import jsonify, assert_errors, tuplify


# Carried over from css21 (to ensure that basic stuff still works)
@pytest.mark.parametrize(('css_source', 'expected_rules', 'expected_errors'), [
    (' /* hey */\n', [], []),

    ('foo{} /* hey */\n@bar;@baz{}',
        [('foo', []), ('@bar', [], None), ('@baz', [], [])], []),

    ('@import "foo.css"/**/;', [
        ('@import', [('STRING', 'foo.css')], None)], []),

    ('@import "foo.css"/**/', [
        ('@import', [('STRING', 'foo.css')], None)], []),

    ('@import "foo.css', [
        ('@import', [('STRING', 'foo.css')], None)], []),

    ('{}', [], ['empty selector']),

    ('a{b:4}', [('a', [('b', [('INTEGER', 4)])])], []),

    ('@page {\t b: 4; @margin}', [('@page', [], [
        ('S', '\t '), ('IDENT', 'b'), (':', ':'), ('S', ' '), ('INTEGER', 4),
        (';', ';'), ('S', ' '), ('ATKEYWORD', '@margin'),
    ])], []),

    ('foo', [], ['no declaration block found']),

    ('foo @page {} bar {}', [('bar', [])],
        ['unexpected ATKEYWORD token in selector']),

    ('foo { content: "unclosed string;\n color:red; ; margin/**/\n: 2cm; }',
        [('foo', [('margin', [('DIMENSION', 2)])])],
        ['unexpected BAD_STRING token in property value']),

    ('foo { 4px; bar: 12% }',
        [('foo', [('bar', [('PERCENTAGE', 12)])])],
        ['expected a property name, got DIMENSION']),

    ('foo { bar! 3cm auto ; baz: 7px }',
        [('foo', [('baz', [('DIMENSION', 7)])])],
        ["expected ':', got DELIM"]),

    ('foo { bar ; baz: {("}"/* comment */) {0@fizz}} }',
        [('foo', [('baz', [('{', [
            ('(', [('STRING', '}')]), ('S', ' '),
            ('{', [('INTEGER', 0), ('ATKEYWORD', '@fizz')])
        ])])])],
        ["expected ':'"]),

    ('foo { bar: ; baz: not(z) }',
        [('foo', [('baz', [('FUNCTION', 'not', [('IDENT', 'z')])])])],
        ['expected a property value']),

    ('foo { bar: (]) ; baz: U+20 }',
        [('foo', [('baz', [('UNICODE-RANGE', 'U+20')])])],
        ['unmatched ] token in (']),
])
def test_core_parser(css_source, expected_rules, expected_errors):
    class CoreParser(CSSchemeParser):
        """A parser that always accepts unparsed at-rules and is reduced to
        the core functions.
        """
        def parse_at_rule(self, rule, stylesheet_rules, errors, context):
            return rule

        # parse_ruleset = CSS21Parser.parse_ruleset
        parse_declaration = CSS21Parser.parse_declaration

    stylesheet = CoreParser().parse_stylesheet(css_source)
    assert_errors(stylesheet.errors, expected_errors)
    result = [
        (rule.at_keyword, list(jsonify(rule.head)),
            list(jsonify(rule.body))
            if rule.body is not None else None)
        if rule.at_keyword else
        (rule.selector.as_css(), [
            (decl.name, list(jsonify(decl.value)))
            for decl in rule.declarations])
        for rule in stylesheet.rules
    ]
    assert result == expected_rules


@pytest.mark.parametrize(('css_source', 'expected_rules', 'expected_errors'), [
    ('@charset "ascii"; foo{}', 2, []),
    (' @charset  "ascii"; foo { } ', 2, []),
    ('@charset ascii;', 1, []),
    ('@charset #123456;', 1, []),
    ('@uuid 2e3af29f-ebee-431f-af96-72bda5d4c144;', 1, []),
    # Errors
    ('foo{} @lipsum{} bar{}', 2,
        ["expected ';', got a block"]),
    ('@lipsum;', 0,
        ["expected value for @lipsum rule"]),
    ('@lipsum a b;', 0,
        ["expected 1 token for @lipsum rule, got 3"]),
    ('@lipsum 23;', 0,
        ["expected STRING, IDENT or HASH token or a valid uuid4 for @lipsum "
         "rule, got INTEGER"]),
    ('foo {@uuid #122323;}', 1,
        ["@uuid not allowed in ruleset"]),
    ('@baz ascii; @baz asciii;', 1,
        ["@baz only allowed once, previously line 1"]),
    #                                       -vvv- not hexadecimal
    ('@uuid 2e3af29f-ebee-431f-af96-72bda5d4cxyz;', 0,
        ["expected STRING, IDENT or HASH token or a valid uuid4 for @uuid rule, "
         "got DIMENSION"]),
    #                    -v- must be 4
    ('@uuid 2e3af29f-ebee-331f-af96-72bda5d4c144;', 0,
        ["expected STRING, IDENT or HASH token or a valid uuid4 for @uuid rule, "
         "got DIMENSION"]),
])
def test_at_rules(css_source, expected_rules, expected_errors):
    stylesheet = CSSchemeParser().parse_stylesheet(css_source)
    assert_errors(stylesheet.errors, expected_errors)
    assert len(stylesheet.rules) == expected_rules


@pytest.mark.parametrize(('css_source', 'expected_rules', 'expected_errors'), [
    ('foo {/* hey */}\n',
        [('foo', [], [])],
        []),

    (' * {}',
        [('*', [], [])],
        []),

    ('foo {@name "ascii"} foo{}',
        [('foo', [], [('@name', [('STRING', "ascii")])]),
         ('foo', [], [])],
        []),

    ('foo {decl: "im-a string"} foo{decl: #123456; decl2: ident}',
        [('foo',
          [('decl',  [('STRING', "im-a string")])],
          []),
         ('foo',
          [('decl',  [('HASH',   "#123456")]),
           ('decl2', [('IDENT',  "ident")])],
          [])],
        []),

    ('fooz {decl: function(param1, param2)}',
        [('fooz',
          [('decl',  [('FUNCTION', "function",
                       [('IDENT', 'param1'),
                        ('DELIM', ','),
                        ('S', ' '),
                        ('IDENT', 'param2')])])],
          [])],
        []),

    ('fooz {decl: function(0, 1% 0.2)}',
        [('fooz',
          [('decl',  [('FUNCTION', "function",
                       [('INTEGER', 0),
                        ('DELIM', ','),
                        ('S', ' '),
                        ('PERCENTAGE', 1),
                        ('S', ' '),
                        ('NUMBER', 0.2)])])],
          [])],
        []),

    ('foo {list: mixed ident and "string list"}',
        [('foo',
          [('list', [('IDENT',  "mixed"),
                     ('S',      " "),
                     ('IDENT',  "ident"),
                     ('S',      " "),
                     ('IDENT',  "and"),
                     ('S',      " "),
                     ('STRING', "string list")])],
          [])],
        []),


    # Errors
    ('foo {decl: 1; decl2: "str":; decl3: some ]}',
        [('foo', [], [])],
        ["unexpected INTEGER token for property decl",
         "unexpected : token for property decl2",
         "unmatched ] token for property decl3"]),

    ('foo {decl: a; decl: b}',
        [('foo', [('decl', [('IDENT', "a")])], [])],
        ["property decl only allowed once"]),

    ('foo {"decl": a; decl2 a; decl3: ;}',
        [('foo', [], [])],
        ["expected a property name, got STRING",
         "expected ':', got IDENT",
         "expected a property value for property decl3"]),

    ('foo {decl ;}',
        [('foo', [], [])],
        ["expected ':'"]),

    ('fooz {decl: function(param1}',
        [('fooz',
          [],
          [])],
        ["unmatched } token for property decl in function 'function()'"]),
])
def test_rulesets(css_source, expected_rules, expected_errors):
    stylesheet = CSSchemeParser().parse_stylesheet(css_source)
    assert_errors(stylesheet.errors, expected_errors)
    result = [tuplify(rule) for rule in stylesheet.rules]
    assert result == expected_rules
