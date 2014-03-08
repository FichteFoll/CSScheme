"""
    Parse files/strings in custom CSS format optimized for use with Text Mate and Sublime Text Color
    Schemes.

    Extends tinycss's css21 basic parser and differs in the following points:

    - Generally, all at-rules are only allowed once in a scope only accept a single value as their
      head, no body. Must be STRING, IDENT, HASH or a valid uuid4. Examples:

        @some-at-rule "a string value";
        @uuid 2e3af29f-ebee-431f-af96-72bda5d4c144;

    - At-rules are allowed in rulesets.

    - Declarations may only provide a list (separated by spaces) of values of the type FUNCTION,
      HASH, STRING, IDENT (and DELIM commas for function parameters).
"""

import re
from itertools import chain

from .tinycss.css21 import (ParseError, Declaration, RuleSet, CSS21Parser,
                            strip_whitespace, validate_any)

__all__ = [
    # from tinycss.css21 imported
    'ParseError',
    # from this file
    'StringRule',
    'CSSchemeParser'
]


def is_uuid(test):
    return bool(re.match(r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}",
                         test, re.I))


class StringRule(object):
    """Any parsed rule with a single STRING head (e.g. @comment).

    .. attribute:: at_keyword

        The at-keyword for this rule.

    .. attribute:: value

        The value for this rule (a Token).
    """
    at_keyword = ''

    def __init__(self, keyword, value, line, column):
        self.at_keyword = keyword
        self.value      = value
        self.line       = line
        self.column     = column

    def __repr__(self):
        return ('<{0.__class__.__name__} {0.at_keyword} {0.line}:{0.column} '
                '{0.value}>'.format(self))


class CSSchemeParser(CSS21Parser):
    """Documentation to be here.
    """

    def _check_at_rule_occurences(self, rule, previous_rules):
        for previous_rule in previous_rules:
            if previous_rule.at_keyword == rule.at_keyword:
                raise ParseError(previous_rule,
                                 '{0} only allowed once, previously line {1}'
                                 .format(rule.at_keyword, previous_rule.line))

    def parse_at_rule(self, rule, previous_rules, errors, context):
        """Parse an at-rule.

        This method handles @uuid, @name and any other "string rule".
        Example:
            @author "I am not an author";
            @name I-Myself;
        """
        # Every at-rule is only supposed to be used once in a context
        self._check_at_rule_occurences(rule, previous_rules)

        # Allow @uuid only in root
        if context != 'stylesheet' and rule.at_keyword == "@uuid":
            raise ParseError(rule, '{0} not allowed in {1}'.format(rule.at_keyword, context))

        # Check format:
        # - No body
        # - Only allow exactly one token in head (obviously)
        head = rule.head
        if rule.body is not None:
            raise ParseError(rule.head[-1] if rule.head else rule, "expected ';', got a block")

        if not head:
            raise ParseError(rule, 'expected value for {0} rule'.format(rule.at_keyword))
        if len(head) > 1:
            raise ParseError(head[1], 'expected 1 token for {0} rule, got {1}'
                                      .format(rule.at_keyword, len(head)))

        # DIMENSION for uuids that start with a number
        whole_value = str(head[0].value) + (head[0].unit if head[0].unit else '')
        if not (head[0].type in ('STRING', 'IDENT', 'HASH')
                or (head[0].type == 'DIMENSION' and is_uuid(whole_value))):
            raise ParseError(rule, 'expected STRING, IDENT or HASH token or a valid uuid4 for '
                                   '{0} rule, got {1}'.format(rule.at_keyword, head[0].type))

        return StringRule(rule.at_keyword, head[0], rule.line, rule.column)

    def parse_ruleset(self, first_token, tokens):
        """Parse a ruleset: a selector followed by declaration block.

        Modified in that we call :meth:`parse_declarations_and_at_rules` instead of
        :meth:`parse_declaration_list` and manually add at-rules afterwards.
        """
        selector = []
        for token in chain([first_token], tokens):
            if token.type == '{':
                # Parse/validate once we've read the whole rule
                selector = strip_whitespace(selector)
                if not selector:
                    raise ParseError(first_token, 'empty selector')
                for selector_token in selector:
                    validate_any(selector_token, 'selector')

                declarations, at_rules, errors = \
                    self.parse_declarations_and_at_rules(token.content, 'ruleset')

                ruleset = RuleSet(selector, declarations, first_token.line, first_token.column)
                # Set at-rules manually (because I cba to create yet another class for that)
                ruleset.at_rules = at_rules

                return ruleset, errors
            else:
                selector.append(token)
        raise ParseError(token, 'no declaration block found for ruleset')

    def parse_declarations_and_at_rules(self, tokens, context):
        """Allow each declaration only once.
        """
        declarations, at_rules, errors = \
            super(CSSchemeParser, self).parse_declarations_and_at_rules(tokens, context)

        known = set()
        for d in declarations:
            if d.name in known:
                errors.append(ParseError(d, "property {0} only allowed once".format(d.name)))
                declarations.remove(d)
            else:
                known.add(d.name)
        return declarations, at_rules, errors

    def parse_declaration(self, tokens):
        """Parse a single declaration.

        :returns:
            a :class:`Declaration`
        :raises:
            :class:`~.parsing.ParseError` if the tokens do not match the
            'declaration' production of the core grammar.
        """
        tokens = iter(tokens)

        name_token = next(tokens)  # Assume there is at least one
        if name_token.type == 'IDENT':
            # tmThemes are case-sensitive
            property_name = name_token.value
        else:
            raise ParseError(name_token,
                             'expected a property name, got {0}'.format(name_token.type))

        # Proceed with value
        for token in tokens:
            if token.type == ':':
                break
            elif token.type != 'S':
                raise ParseError(
                    token, "expected ':', got {0}".format(token.type))
        else:
            raise ParseError(name_token, "expected ':'")

        value = strip_whitespace(list(tokens))
        if not value:
            raise ParseError(name_token,
                             "expected a property value for property {0}".format(property_name))

        # Only allow a list of HASH, IDENT, STRING, FUNCTION (and S) (minimal requirements)
        # STRING is for arbitrary properties
        # inside FUNCTIONS we also allow: DELIM, INTEGER, NUMBER and PERCENTAGE
        def check_token_types(tokens, fn=None):
            for token in tokens:
                if not (token.type in ('S', 'IDENT', 'STRING', 'HASH', 'FUNCTION') or
                        fn and token.type in ('DELIM', 'INTEGER', 'NUMBER', 'PERCENTAGE')):
                    match_type = token.type in ('}', ')', ']') and 'unmatched' or 'unexpected'
                    raise ParseError(token, '{0} {1} token for property {2}{3}'
                                            .format(match_type, token.type, property_name,
                                                    " in function '%s()'" % fn if fn else ''))
                if token.type == 'FUNCTION':
                    check_token_types(token.content, token.function_name)
                # elif token.is_container:
                #     check_token_types(token.content)

        check_token_types(value)

        # Note: '!important' priority ignored
        return Declaration(property_name, value, None, name_token.line, name_token.column)
