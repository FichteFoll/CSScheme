import sublime
import sublime_plugin


from .tinycsscheme.dumper import CSSchemeDumper
from .scope_data import COMPILED_HEADS

from .convert import status


class CSSchemeCompletionListener(sublime_plugin.EventListener):
    def __init__(self):
        properties = set()
        for l in CSSchemeDumper.known_properties.values():
            properties |= l

        self.property_completions = list(("{0}\t{0}:".format(s), s + ": $1;$0")
                                         for s in properties)

    def get_scope(self, view, l):
        # Do some string math (instead of regex because fastness)
        _, col = view.rowcol(l)
        begin  = view.line(l).begin()
        line   = view.substr(sublime.Region(begin, l))
        scope  = line.rsplit(' ', 1)[-1]
        return scope.lstrip('-')

    def on_query_completions(self, view, prefix, locations):
        # Provide a selection of naming convention from TextMate and/or property names

        def match_sel(sel):
            return all(view.match_selector(l, sel) for l in locations)

        # Check context
        if not match_sel("source.csscheme - comment - string - variable"):
            return

        if match_sel("meta.ruleset"):
            # No nested rulesets for CSS
            return self.property_completions

        if not match_sel("meta.selector, meta.property_list - meta.property"):
            return

        scope = self.get_scope(view, locations[0])

        # We can't work with different prefixes
        if any(self.get_scope(view, l) != scope for l in locations):
            return

        # Tokenize the current selector (only to the cursor)
        tokens = scope.split(".")

        if len(tokens) > 1:
            del tokens[-1]  # The last token is either incomplete or empty

            # Browse the nodes and their children
            nodes = COMPILED_HEADS
            for i, token in enumerate(tokens):
                node = nodes.find(token)
                if not node:
                    status("Warning: `%s` not found in scope naming conventions"
                           % '.'.join(tokens[:i + 1]))
                    break
                nodes = node.children
                if not nodes:
                    break

            if nodes and node:
                return (nodes.to_completion(), sublime.INHIBIT_WORD_COMPLETIONS)
            else:
                status("No nodes available in scope naming conventions after `%s`"
                       % '.'.join(tokens))
                return  # Should I inhibit here?

        # Triggered completion on whitespace:
        elif match_sel("source.csscheme.scss"):
            # For SCSS just return all the head nodes + property completions
            return self.property_completions + COMPILED_HEADS.to_completion()
        else:
            return COMPILED_HEADS.to_completion()
