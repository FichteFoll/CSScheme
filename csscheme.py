import re
import os
import subprocess

import sublime
import sublime_plugin

try:
    # Use a different name because PackageDev adds it to the path and that
    # takes precedence over local paths (for some reason).
    from .my_sublime_lib.view import OutputPanel
    from .my_sublime_lib import WindowAndTextCommand
except:
    from my_sublime_lib.view import OutputPanel
    from my_sublime_lib import WindowAndTextCommand

try:
    from .tinycsscheme.parser import CSSchemeParser, ParseError
    from .tinycsscheme.dumper import CSSchemeDumper, DumpError
    from .scope_data import COMPILED_HEADS
except:
    from tinycsscheme.parser import CSSchemeParser, ParseError
    from tinycsscheme.dumper import CSSchemeDumper, DumpError
    from scope_data import COMPILED_HEADS


# Returns a function for use with `re.sub`, requires matches in groups 1 and 2
def swap_path_line(pattern, rel_dir):
    def repl(m):
        # Make path relative because we don't need long paths if in same dir
        path = os.path.relpath(m.group(2), rel_dir)
        return pattern % (path, m.group(1))
    return repl


def settings():
    # We can safely call this over and over because it caches internally
    return sublime.load_settings("CSScheme.sublime-settings")


def status(msg):
    package = "CSScheme"  # my_sublime_lib.path.get_package_name()
    sublime.status_message("%s: %s" % (package, msg))
    print("[%s] %s" % (package, msg))


# Use window (and text) command to be able to call this command from both sources
# (build systems are always window commands).
class convert_csscheme(WindowAndTextCommand):
    """docs
    """
    def is_enabled(self):
        return self.get_in_ext() is not None

    def get_in_ext(self):
        if not self.view.file_name():
            return None
        m = re.search(r'\.((?:sc|sa|c)ss)cheme$', self.view.file_name())
        return m and m.group(1)

    def run(self, edit=None):
        if self.view.is_dirty():
            return status("Save the file first")

        in_file = self.view.file_name()
        in_ext = self.get_in_ext()
        in_dir, in_base = os.path.split(in_file)
        out_file = os.path.splitext(in_file)[0] + '.tmTheme'

        # TODO do this in oop style (with error reporting and cmd and stuff)
        # Will probably do when more convertion options are added, if at all (syntaxes are a pita)
        sass_path = settings().get('sass_path', 'sass')
        commands = dict(
            sass=[sass_path, '-l'],
            scss=[sass_path, '-l',  '--scss'],
            # less='less',
            # stylus= ...
        )

        # Open up output panel and auto-finalize it when we are done
        with OutputPanel(self.view.window(), "csscheme") as out:
            out.set_path(in_dir)
            text = ""
            if in_ext in commands:
                try:
                    process = subprocess.Popen(commands[in_ext] + [in_file],
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE,
                                               shell=sublime.platform() == 'windows',
                                               universal_newlines=True)
                    text, stderr = process.communicate()
                except Exception as e:
                    out.write_line("Error converting from %s to CSS:\n"
                                   "%s: %s" % (in_ext, e.__class__.__name__, e))
                    return

                if process.returncode:
                    out.set_regex(r"^\s+in (.*?) on line (\d+)$")

                    out.write_line("Errors converting from %s to CSS, return code: %s\n"
                                   % (in_ext, process.returncode))
                    # Swap line and path because sublime can't parse them otherwise
                    out.write_line(re.sub(r"on line (\d+) of (.*?)$",
                                          swap_path_line(r"in %s on line %s", in_dir),
                                          stderr,
                                          flags=re.M))
                    return

                elif not text:
                    out.write_line("Unexpected error converting from %s to CSS:\nNo output"
                                   % in_ext)
                    return

                elif stderr:
                    out.write_line(stderr + "\n")
            else:
                assert in_ext == 'css'
                text = self.view.substr(sublime.Region(0, self.view.size()))

            # DEBUG
            if settings().get('preview_compiled_css') and in_ext != 'css':
                v = self.view.window().new_file()
                v.set_scratch(True)
                v.set_syntax_file("Packages/CSScheme/CSScheme.tmLanguage")
                from my_sublime_lib.edit import Edit
                with Edit(v) as edit:
                    edit.append(text)

            # Parse the CSS
            stylesheet = CSSchemeParser().parse_stylesheet(text)

            # Do some awesome error printing action
            if stylesheet.errors:
                if in_ext in ('sass', 'scss'):
                    err_reg = re.compile(r"/\* line (\d+), (.*?) \*/", re.M)

                    # Match our modified output
                    out.set_regex(r"^\s*/\* (.*?), line (\d+) \*/")

                    lines = text.split('\n')
                    # I could wrap this in an Edit(out.view) call because I modify it so often
                    for e in stylesheet.errors:
                        assert isinstance(e, ParseError)
                        out.write_line("ParseError from CSS on line %d:" % e.line)

                        # Search for last known line number (max 20)
                        start_dump = 0
                        for i in range(e.line, e.line - 20, -1):
                            if i < 0:
                                break
                            m = re.match(r"\s*/\* line (\d+),", lines[i])
                            if not m:
                                continue
                            start_dump = i
                            # Swap line and path because sublime can't parse them otherwise
                            out.write_line(
                                "  " + err_reg.sub(swap_path_line("/* %s, line %s */", in_dir),
                                                   lines[i])
                            )
                            break

                        # Nothing found in the past lines, just print the erroneous line then
                        if not start_dump:
                            start_dump = e.line - 2

                        for i in range(start_dump + 1, e.line):
                            out.write_line("  " + lines[i])
                        # Mark the column where the error happened (since we don't have source code)
                        out.write_line("  %s^" % ('-' * (e.column - 1)))
                        out.write_line("%s\n" % (e.reason))

                elif in_ext == 'css':
                    out.set_regex(r"^(.*):(\d+):(\d+):$")
                    for e in stylesheet.errors:
                        out.write_line("%s:%s:%s:\n  %s\n"
                                       % (in_base, e.line, e.column, e.reason))
                return
            elif not stylesheet.rules:
                # The CSS seems to be ... empty?
                out.write_line("No CSS data was found")
                return

            # Dump CSS data as plist into out_file
            try:
                CSSchemeDumper().dump_stylesheet_file(out_file, stylesheet)
            except DumpError as e:
                if in_ext == 'css':
                    out.set_regex(r"^(.*):(\d+):(\d+):$")
                    out.write_line("%s:%s:%s:\n  %s%s\n"
                                   % (in_base, e.line, e.column, e.reason, e.location))
                else:
                    # We can't accurately determine where the error occured (besides searching for
                    # the last referenced number like above, and that kinda sucks), so just use text
                    out.write_line("Error in data:\n  %s%s\n" % (e.reason, e.location))
                return

            status("Build successful")
            # Open out_file
            if settings().get('open_after_build'):
                self.view.window().open_file(out_file)


###############################################################################


# TODO completions (scope_data from PackageDev in selectors, known properties (from dumper))
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

        # import spdb ; spdb.start()
        # Check context
        if not match_sel("source.csscheme - comment - string - variable"):
            return

        if match_sel("meta.ruleset"):
            # No nested rulesets for CSS
            return self.property_completions

        if not match_sel("meta.selector, meta.property_list - meta.property"):
            return

        scope = self.get_scope(view, locations[0])

        # We can't work with different scopes
        for l in locations:
            if self.get_scope(view, l) != scope:
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
