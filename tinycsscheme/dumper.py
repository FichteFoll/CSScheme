"""TODO
"""
from collections import OrderedDict
import plistlib

from .parser import StringRule
from .tinycss.parsing import split_on_comma, strip_whitespace
from .tinycss.token_data import Token


def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))


class DumpError(ValueError):
    def __init__(self, subject, reason, location=None):
        self.line = subject.line
        self.column = subject.column
        self.reason = reason
        self.location = ' in "%s"' % location if location else ''
        super(DumpError, self).__init__(
            'Dump error at {0.line}:{0.column}, {0.reason}'.format(self))


class DummyToken(object):
    def __init__(self, line, column):
        self.line = line
        self.column = column


class CSSchemeDumper(object):
    def dump_stylesheet_file(self, out_file, stylesheet):
        data = self.datafy_stylesheet(stylesheet)
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

        # from pprint import pprint
        # pprint(at_rules)
        # pprint(rulesets)

        # Make sure the name is at the top
        if not 'name' in at_rules:
            raise DumpError(dummy, "Must contain 'name' at-rule")
        data['name'] = at_rules['name'].value.value
        del at_rules['name']

        # Then all remaining at-rules (should be subclasses of StringRule)
        for k, r in at_rules.items():
            assert isinstance(r, StringRule)
            if k == 'settings':
                raise DumpError(r, "Can not override 'settings' key using at-rules.", '@%s' % k)
            data[k] = r.value.value

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
        sel = rset.selector.as_css()
        if sel != '*':
            rdict['scope'] = sel

        # Arbitrary at-rules -> add to dict
        for r in rset.at_rules:
            invalid = ('@scope', '@settings')
            if r.at_keyword in invalid:
                raise DumpError(r, "You can not override the '{0}' key using at-rules"
                                   .format(r.at_keyword.strip('@')),
                                '%s, %s' % (sel, r.at_keyword))
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
            if v.type in ('IDENT', 'STRING'):
                # Lookup css color names and replace them with their HASH
                from .css_colors import css_colors
                if not v.value in css_colors:
                    raise DumpError(v, "unknown color name '{1}' for property {0}"
                                       .format(decl.name, v.value), sel)

                color = css_colors[v.value]

            elif v.type == 'FUNCTION':
                fn = v.function_name
                if fn not in ('rgb', 'hsl', 'rgba', 'hsla'):
                    raise DumpError(v, "unknown function '{1}()' for property {0}"
                                       .format(decl.name, fn), sel)

                # Parse parameters
                raw_params = list(map(strip_whitespace, split_on_comma(v.content)))
                if len(raw_params) != len(fn):
                    raise DumpError(v, "expected {0} parameters for function '{1}()', got {2}"
                                       .format(len(fn), fn, len(raw_params)),
                                    '%s, %s' % (sel, decl.name))

                # Validate parameters
                def unexpected_value(i, v, p):
                    raise DumpError(p, "unexpected value {2} for parameter {0} in function "
                                       "'{1}()'".format(i, fn, p.type),
                                    '%s, %s' % (sel, decl.name))
                # Save everything as floating numbers between 0 and 1
                params = []
                for i, p in enumerate(raw_params):
                    if len(p) != 1:
                        raise DumpError(p[1], "expected 1 token for parameter {0} in function "
                                              "'{1}()', got {2}".format(i, fn, len(p)),
                                        '%s, %s' % (sel, decl.name))
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
                        params.append(clamp(0, p.value, 1))
                    elif fn[i] == 'h':
                        if p.type not in ('NUMBER', 'INTEGER'):
                            unexpected_value(i, v, p)
                        params.append((p.value % 360) / 360.0)
                    elif fn[i] in 'sl':
                        if p.type != 'PERCENTAGE':
                            unexpected_value(i, v, p)
                        params.append(p.value)

                # Convert hsl to rgb
                if 'hsl' in fn:
                    import colorsys
                    params[:3] = colorsys.hls_to_rgb(params[0], params[2], params[1])

                color = "#" + ''.join("{:02X}".format(round(c * 255)) for c in params)

            # Replace the old value (could be a FunctionToken)
            if color:
                decl.value[0] = Token('HASH', v.as_css(), color, None, v.line, v.column)
            assert decl.value[0].type == 'HASH'

        elif decl.name in self.known_properties['style_list']:
            for token in decl.value:
                if token.type == 'S':
                    continue
                elif token.type not in ('IDENT', 'STRING'):
                    raise DumpError(token, "unexpected {1} token for property {0}"
                                           .format(decl.name, token.type), sel)
                elif token.value not in ('bold', 'italic', 'underline', 'stippled_underline'):
                    raise DumpError(token, "invalid value '{1}' for property {0}"
                                           .format(decl.name, token.value), sel)
