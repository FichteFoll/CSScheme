"""TODO
"""
from collections import OrderedDict
import plistlib

from .parser import StringRule


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
                                '%s %s' % (sel, r.at_keyword))
            rdict[r.at_keyword.strip('@')] = r.value.value

        # Add real declarations to a sub-'settings' dict
        s = OrderedDict()
        for d in rset.declarations:
            # One or multiple HASH, STRING or IDENT (separated by S)
            s[d.name] = "".join(v.value for v in d.value)
        rdict['settings'] = s

        return rdict
