"""
    Dump Stylesheet objects returned by CSSchemeParser methods into .tmTheme-style property lists.

    Does a few checks to assure that data is valid:

    - Must define exactly one * ruleset.

    - @name at-rule is required.

    - You can not overwrite keys with the @settins at-rule, neither can you overwrite @scope keys in
      rulesets.

    - Known property names are checked for validity. This includes but is not limited to:
      + 'foreground', 'background', 'caret' which accept color values, and
      + 'fontStyle', 'tagsOptions' which accept a list of idents with valid font decoration options.

    - CSS color names as well as color functions 'rgb', 'hsl' and their alpha variants are checked
      for validity of parameters and **evaluated to color hashes**, three-digit hashes (like #123)
      are expanded to six digits.
"""

import re
from collections import OrderedDict

from .parser import StringRule
from .tinycss.parsing import split_on_comma, strip_whitespace
from .tinycss.token_data import Token


def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))


def strvalue(token):
    # Required for uuids in at-rules which are represented as DIMENSION
    return str(token.value) + (token.unit if token.unit else '')


class DumpError(ValueError):
    def __init__(self, subject, reason, location=None):
        self.line = subject.line
        self.column = subject.column
        self.reason = reason
        self.location = ' in "%s"' % location if location else ''
        super(DumpError, self).__init__('Dump error at {0.line}:{0.column}, {0.reason}'
                                        .format(self))


class DummyToken(object):
    def __init__(self, line, column):
        self.line = line
        self.column = column


class CSSchemeDumper(object):
    # I could test this, but it is like one line and I only forward anyway. I'll just leave this
    # comment here to remind myself.
    def dump_stylesheet_file(self, out_file, stylesheet):  # pragma: no cover
        data = self.datafy_stylesheet(stylesheet)
        import plistlib
        plistlib.writePlist(data, out_file)

    def datafy_stylesheet(self, stylesheet):
        # Use OrderedDicts to retain order
        data = OrderedDict()
        at_rules = OrderedDict()
        rulesets = []
        asterisk = None
        dummy = DummyToken(0, 0)

        # Save all at-rules and rulesets separately
        for r in stylesheet.rules:
            if r.at_keyword:
                at_rules[r.at_keyword.strip('@')] = r
            else:
                if r.selector.as_css() == "*":
                    if asterisk:
                        # Actually it is not, but the second will always override the first and it
                        # doesn't make sense anyway
                        raise DumpError(r, "Only one *-rule allowed")
                    else:
                        asterisk = r
                else:
                    rulesets.append(r)

        # Make sure the name is at the top
        if not 'name' in at_rules:
            raise DumpError(dummy, "Must contain 'name' at-rule")
        data['name'] = strvalue(at_rules['name'].value)
        del at_rules['name']

        # Then all remaining at-rules (should be subclasses of StringRule)
        for k, r in at_rules.items():
            assert isinstance(r, StringRule)
            if k == 'settings':
                raise DumpError(r, "Can not override 'settings' key using at-rules.", '@%s' % k)
            data[k] = strvalue(r.value)

        # Build 'settings' dict from rules
        s = []
        data['settings'] = s

        # Add *-rule first
        if not asterisk:
            # Actually it needs not, but it doesn't make sense to not add one at all
            raise DumpError(dummy, "Must contain '*' ruleset")
        else:
            s.append(self.datafy_ruleset(asterisk))

        # And finally get to the normal rules
        for r in rulesets:
            s.append(self.datafy_ruleset(r))

        # Return the constructed mapping (OrderedDict)
        return data

    def datafy_ruleset(self, rset):
        rdict = OrderedDict()
        # TODO test selector?
        sel = rset.selector.as_css()
        if sel != '*':
            # We replace escaping of the subtract operator because SASS doesn't like the literal -
            # Also replace multiple whitespaces (including newlines) with single space; we don't
            # know how exactly it will perform otherwise.
            rdict['scope'] = ' '.join(sel.replace("'-'", "-").split())

        # Arbitrary at-rules -> add to dict
        for r in rset.at_rules:
            invalid = ('@scope', '@settings')
            if r.at_keyword in invalid:
                raise DumpError(r, "You can not override the '{0}' key using at-rules"
                                   .format(r.at_keyword.strip('@')),
                                '%s; %s' % (sel, r.at_keyword))
            rdict[r.at_keyword.strip('@')] = r.value.value

        # Add real declarations to a sub-'settings' dict
        s = OrderedDict()
        for decl in rset.declarations:
            self.validify_declaration(decl, sel)
            # One or multiple HASH, STRING or IDENT (separated by S) tokens
            s[decl.name] = "".join(v.value for v in decl.value)
        rdict['settings'] = s

        return rdict

    known_properties = dict(
        color=('foreground', 'background', 'caret', 'invisibles', 'lineHighlight', 'selection',
               'activeGuide'),
        style_list=('fontStyle', 'tagsOptions')
        # Maybe some more?
    )

    def validify_declaration(self, decl, sel):
        # Check for property characteristics (if we know its type)
        if decl.name in self.known_properties['color']:
            if len(decl.value) > 1:
                # We only expect one token for colors
                raise DumpError(decl.value[1], 'expected 1 token for property {0}, got {1}'
                                               .format(decl.name, len(decl.value)), sel)

            v = decl.value[0]
            color = None
            if v.type == 'IDENT':
                # Lookup css color names and replace them with their HASH
                from .css_colors import css_colors
                if not v.value in css_colors:
                    raise DumpError(v, "unknown color name '{1}' for property {0}"
                                       .format(decl.name, v.value), sel)

                color = css_colors[v.value]

            elif v.type == 'FUNCTION':
                # Apparently, tinycss.color3 does this too but with no exception messages and I
                # found out about it after I finished my own implementation anyway.
                fn = v.function_name
                if fn not in ('rgb', 'hsl', 'rgba', 'hsla'):
                    raise DumpError(v, "unknown function '{1}()' for property {0}"
                                       .format(decl.name, fn), sel)

                # Parse parameters
                raw_params = list(map(strip_whitespace, split_on_comma(v.content)))
                if raw_params == [[]]:  # Reduce the list if no arguments found for param count
                    raw_params = []
                # Check parameter count
                if len(raw_params) != len(fn):
                    raise DumpError(v, "expected {0} parameters for function '{1}()', got {2}"
                                       .format(len(fn), fn, len(raw_params)),
                                    '%s; %s' % (sel, decl.name))

                # Validate parameters
                def unexpected_value(i, v, p):
                    raise DumpError(p, "unexpected {2} value for parameter {0} in function "
                                       "'{1}()'".format(i + 1, fn, p.type),
                                    '%s; %s' % (sel, decl.name))
                # Save everything as floating numbers between 0 and 1
                params = []
                for i, p in enumerate(raw_params):
                    if len(p) != 1:
                        raise DumpError(p[1], "expected 1 token for parameter {0} in function "
                                              "'{1}()', got {2}".format(i + 1, fn, len(p)),
                                        '%s; %s' % (sel, decl.name))
                    p = p[0]

                    if fn[i] in 'rgb':
                        if p.type == 'INTEGER':
                            params.append(clamp(0, p.value, 255) / 255.0)
                        elif p.type == 'PERCENTAGE':
                            params.append(clamp(0, p.value, 100) / 100.0)
                        else:
                            unexpected_value(i, v, p)
                    elif fn[i] == 'a':
                        if p.type not in ('NUMBER', 'INTEGER'):
                            unexpected_value(i, v, p)
                        params.append(1 - clamp(0, p.value, 1))
                    elif fn[i] == 'h':
                        if p.type not in ('NUMBER', 'INTEGER'):
                            unexpected_value(i, v, p)
                        params.append((p.value % 360) / 360.0)
                    elif fn[i] in 'sl':
                        if p.type != 'PERCENTAGE':
                            unexpected_value(i, v, p)
                        params.append(clamp(0, p.value, 100) / 100.0)

                # Convert hsl to rgb
                if 'hsl' in fn:
                    import colorsys
                    params[:3] = colorsys.hls_to_rgb(params[0], params[2], params[1])

                color = "#" + ''.join("{:02X}".format(round(c * 255)) for c in params)
            elif v.type == 'STRING':
                if re.match(r"^#[a-f\d]+$", v.value):
                    color = v.value
                else:
                    raise DumpError(v, "unexpected value for property {0}, expected color hash"
                                       .format(decl.name),
                                    '%s; %s' % (sel, decl.name))
            elif v.type == 'HASH':
                color = v.value
            # No other types are allowed from the parser
            # else:
            #     raise DumpError(v, "unexpected {1} value for property {0}"
            #                        .format(decl.name, v.type),
            #                     '%s; %s' % (sel, decl.name))
            assert color

            if (len(color) - 1) not in (3, 6, 8):
                raise DumpError(v, "unexpected length of {1} of color hash for property {0}"
                                   .format(decl.name, len(color) - 1),
                                '%s; %s' % (sel, decl.name))

            # Translate 3-lenght color hashes
            if len(color) == 4:
                color = '#' + ''.join(color[i] * 2 for i in range(1, 4))

            # Replace the old value
            if v.type != 'HASH' or color != v.value:
                decl.value[0] = Token('HASH', v.as_css(), color, None, v.line, v.column)

        elif decl.name in self.known_properties['style_list']:
            for token in decl.value:
                if token.type == 'S':
                    continue
                elif token.type != 'IDENT':
                    raise DumpError(token, "unexpected {1} token for property {0}"
                                           .format(decl.name, token.type), sel)
                elif token.value not in ('bold', 'italic', 'underline', 'stippled_underline'):
                    raise DumpError(token, "invalid value '{1}' for property {0}"
                                           .format(decl.name, token.value), sel)
