import os

import sublime
import sublime_plugin

try:
    # Use a different name because PackageDev adds it to the path and that
    # takes precedence over local paths (for some reason).
    from .my_sublime_lib import WindowAndTextCommand
    from .my_sublime_lib.path import file_path_tuple
    from .my_sublime_lib.view import OutputPanel

    from .tinycsscheme.parser import CSSchemeParser
    from .tinycsscheme.dumper import CSSchemeDumper, DumpError

    from .scope_data import COMPILED_HEADS
    from . import converters
except:
    from my_sublime_lib import WindowAndTextCommand
    from my_sublime_lib.path import file_path_tuple
    from my_sublime_lib.view import OutputPanel

    from tinycsscheme.parser import CSSchemeParser
    from tinycsscheme.dumper import CSSchemeDumper, DumpError

    from scope_data import COMPILED_HEADS
    import converters


###############################################################################


PACKAGE = "CSScheme"  # my_sublime_lib.path.get_package_name() # __package__


def settings():
    """Load the settings file."""
    # We can safely call this over and over because it caches internally
    return sublime.load_settings("CSScheme.sublime-settings")


def status(msg, printonly=""):
    """Show a message in the statusbar and print to the console."""
    sublime.status_message("%s: %s" % (PACKAGE, msg))
    if printonly:
        msg = msg + '\n' + printonly
    print("[%s] %s" % (PACKAGE, msg))


###############################################################################


# Use window (and text) command to be able to call this command from both
# sources (build systems are always window commands).
class convert_csscheme(WindowAndTextCommand):

    """Convert the active CSScheme (or variant) file into a .tmTheme plist."""

    def is_enabled(self):
        path = self.view.file_name()
        return bool(path) and any(conv.valid_file(path) for conv in converters.all)

    def run(self, edit=None):
        if self.view.is_dirty():
            return status("Save the file first.")

        self.preview_opened = False
        in_file = self.view.file_name()
        in_tuple = file_path_tuple(in_file)
        out_file = in_tuple.no_ext + '.tmTheme'

        # Open up output panel and auto-finalize it when we are done
        with OutputPanel(self.view.window(), "csscheme") as out:

            # Determine our converter
            conv = tuple(c for c in converters.all if c.valid_file(in_file))
            if len(conv) > 1:
                print(conv)
                out.write_line("Found multiple contenders for conversion.\n"
                               "If this happened to you, please tell the developer "
                               "(me) to add code for this case. Thanks.")
                return
            assert len(conv) == 1
            conv = conv[0]

            out.set_path(in_tuple.path)
            executables = settings().get("executables")  # TOTEST

            # Run converter
            text = conv.convert(out, in_file, executables)
            if not text:
                return

            # Preview converted css for debugging, optionally
            if settings().get('preview_compiled_css'):
                self.preview_compiled_css(text, conv, in_tuple.base_name)

            # Parse the CSS
            stylesheet = CSSchemeParser().parse_stylesheet(text)

            # Do some awesome error printing action
            if stylesheet.errors:
                conv.report_parse_errors(out, in_file, text, stylesheet.errors)
                self.preview_compiled_css(text, conv, in_tuple.base_name)
                return
            elif not stylesheet.rules:
                # The CSS seems to be ... empty?
                out.write_line("No CSS data was found")
                return

            # Dump CSS data as plist into out_file
            try:
                CSSchemeDumper().dump_stylesheet_file(out_file, stylesheet)
            except DumpError as e:
                conv.report_dump_error(out, in_file, text, e)
                self.preview_compiled_css(text, conv, in_tuple.base_name)
                return

            status("Build successful")
            # Open out_file
            if settings().get('open_after_build'):
                self.view.window().open_file(out_file)

    def preview_compiled_css(self, text, conv, base_name):
        if conv.ext == 'csscheme' or self.preview_opened:
            return

        v = self.view.window().new_file()
        v.set_scratch(True)
        v.set_syntax_file("Packages/%s/Package/CSScheme.tmLanguage" % PACKAGE)
        v.set_name("Preview: %s.csscheme" % base_name)
        try:
            from .my_sublime_lib.edit import Edit
        except:
            from my_sublime_lib.edit import Edit
        with Edit(v) as edit:
            edit.append(text)

        self.preview_opened = True


###############################################################################


class CSSchemeCompletionListener(sublime_plugin.EventListener):
    def __init__(self):
        properties = []
        for l in CSSchemeDumper.known_properties.values():
            properties.extend(l)

        self.property_completions = list(("{0}\t{0}:".format(s), s + ": $0;") for s in properties)

    def get_scope(self, view, l):
        # Do some string math (instead of regex because fastness)
        _, col = view.rowcol(l)
        begin  = view.line(l).begin()
        line   = view.substr(sublime.Region(begin, l))
        scope  = line.rsplit(' ', 1)[-1]
        return scope.lstrip('-')

        # Provide a selection of naming convention from TextMate and/or property names
    def on_query_completions(self, view, prefix, locations):

        match_sel = lambda s: all(view.match_selector(l, s) for l in locations)

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
