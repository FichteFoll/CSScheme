from itertools import chain

try:
    from ..tinycss.css21 import (ParseError, AtRule, Declaration, TokenList, RuleSet, Stylesheet,
                                 CSS21Parser, strip_whitespace, validate_any)
    # For running tests from the "tests" subdir
    from ..tinycss.token_data import Token
except:
    from tinycss.css21 import (ParseError, AtRule, Declaration, TokenList, RuleSet, Stylesheet,
                               CSS21Parser, strip_whitespace, validate_any)
    from tinycss.token_data import Token

# Notes on the tinycss codestyle vs this one:
# - The documentation is Sphinx-optimized, I'll try to adapt to the style.
# - tinycss previously had a max line lenght of 80, raised it to 100.

__all__ = [
    # from tinycss.css21
    'Stylesheet',
    'Declaration',
    'AtRule',
    'RuleSet',
    # from tinycss.css21 imported
    'TokenList',
    'ParseError',
    # from this file
    'StringRule',
    'CSSchemeParser',
    'Token'
]


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
        if head[0].type not in ('STRING', 'IDENT', 'HASH'):
            raise ParseError(rule, 'expected STRING, IDENT or HASH token for {0} rule, got {1}'
                                   .format(rule.at_keyword, head[0].type))

        return StringRule(rule.at_keyword, head[0], rule.line, rule.column)

    def parse_ruleset(self, first_token, tokens):
        """Parse a ruleset: a selector followed by declaration block.

        Modified in that we call :meth:`parse_declarations_and_at_rules` instead of
        :meth:`parse_declaration_list` and manually add at-rules afterwards.
        """
        selector = []
        for token in chain([first_token], tokens):
            if token.type == '{':
                # Parse/validate once we’ve read the whole rule
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

    known_properties = dict(
        color=('foreground', 'background', 'caret', 'invisibles', 'lineHighlight', 'selection',
               'activeGuide'),
        style_list=('fontStyle', 'tagsOptions')
        # Maybe some more?
    )

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
                             "expected a property value for property {}".format(property_name))

        # Validate the value(s)
        def invalid_value(token, msg=""):
            match_type = token.type in ('}', ')', ']') and 'unmatched' or 'unexpected'
            raise ParseError(token, '{0} {1} token for property {2}{3}'
                                    .format(match_type, token.type, property_name,
                                            ': ' + msg if msg else ""))

        # Only allow HASH, IDENT, STRING (and S) (minimal requirements)
        # TODO rgb(), rgba(), hsl(), hsla() FUNCTION
        for token in value:
            if token.type not in ('S', 'IDENT', 'STRING', 'HASH'):
                invalid_value(token)

        # Check if we know the property's type
        property_type = None
        for type_, elmnts in self.known_properties.items():
            if property_name in elmnts:
                property_type = type_
                break

        # Check for property characteristics (if we know its type)
        if property_type == 'color':
            if len(value) > 1:
                raise ParseError(value[1], 'expected 1 token for property {0}, got {1}'
                                           .format(property_name, len(value)))
            v = value[0]
            if v.type in ('IDENT', 'STRING'):
                # Lookup css color names and replace them with their HASH
                from .css_colors import css_colors
                if not v.value in css_colors:
                    raise ParseError(v, "unknown color name for property {}".format(property_name))

                v.value = css_colors[v.value]
                v.type  = 'HASH'  # This feels a bit dirty, but I guess it's k

            assert v.type == 'HASH'

        elif property_type == 'style_list':
            for token in value:
                if token.type == 'S':
                    continue
                elif token.type not in ('IDENT', 'STRING'):
                    invalid_value(token)
                elif token.value not in ('bold', 'italic', 'underline', 'stippled_underline'):
                    raise ParseError(token, "invalid value '{0}' for property {1}"
                                            .format(token.value, property_name))

        # Note: '!important' priority ignored
        return Declaration(property_name, value, None, name_token.line, name_token.column)
