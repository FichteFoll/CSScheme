import os

import sublime
import sublime_plugin

# Use a different name because PackageDev adds it to the path and that
# takes precedence over local paths (for some reason).
from .my_sublime_lib import WindowAndTextCommand
from .my_sublime_lib.path import file_path_tuple
from .my_sublime_lib.view import OutputPanel, get_text, set_text

from .tinycsscheme.parser import CSSchemeParser, strvalue
from .tinycsscheme.dumper import CSSchemeDumper, DumpError

from . import converters
from .converters import tmtheme


###############################################################################


PACKAGE = __package__
DEBUG = False


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
        ext = '.tmTheme'

        # Open up output panel and auto-finalize it when we are done
        with OutputPanel(self.view.window(), "csscheme") as out:

            # Determine our converter
            conv = tuple(c for c in converters.all if c.valid_file(in_file))
            if len(conv) > 1:
                out.write_line("Found multiple contenders for conversion.\n"
                               "If this happened to you, please tell the developer "
                               "(me) to add code for this case. Thanks.")
                return
            elif not conv:
                out.write_line("Couldn't match extension against a known converter.\n"
                               "Known extensions are: %s"
                               % ', '.join("." + c.ext for c in converters.all))
                return
            conv = conv[0]

            out.set_path(in_tuple.path)
            executables = settings().get("executables", {})

            # Run converter
            text = conv.convert(out, in_file, executables)
            if not text:
                return

            # Preview converted css for debugging, optionally
            self.previewed = not settings().get('preview_compiled_css')

            def preview_compiled_css():
                if not self.previewed:
                    self.preview_compiled_css(text, conv, in_tuple.base_name)
                    self.previewed = True

            # Parse the CSS
            stylesheet = CSSchemeParser().parse_stylesheet(text)

            # Do some awesome error printing action
            if stylesheet.errors:
                conv.report_parse_errors(out, in_file, text, stylesheet.errors)
                preview_compiled_css()
                return
            elif not stylesheet.rules:
                # The CSS seems to be ... empty?
                out.write_line("No CSS data was found")
                return

            # Check for "hidden" at-rule
            for i, r in enumerate(stylesheet.rules):
                if not r.at_keyword or r.at_keyword.strip('@') != 'hidden':
                    continue
                if strvalue(r.value) == 'true':
                    ext = '.hidden-tmTheme'
                    del stylesheet.rules[i]
                    break
                else:
                    e = DumpError(r, "Unrecognized value for 'hidden' "
                                     "at-rule, expected 'true'")
                    conv.report_dump_error(out, in_file, text, e)
                    preview_compiled_css()
                    return

            # Dump CSS data as plist into out_file
            out_file = in_tuple.no_ext + ext
            try:
                CSSchemeDumper().dump_stylesheet_file(out_file, stylesheet)
            except DumpError as e:
                conv.report_dump_error(out, in_file, text, e)
                if DEBUG:
                    import traceback
                    traceback.print_exc()
                preview_compiled_css()
                return

        status("Build successful")
        # Open out_file
        if settings().get('open_after_build'):
            self.view.window().open_file(out_file)

    def preview_compiled_css(self, text, conv, base_name):
        if conv.ext == 'csscheme':
            return

        v = self.view.window().new_file()
        v.set_scratch(True)
        v.set_syntax_file("Packages/%s/Package/CSScheme.tmLanguage" % PACKAGE)
        v.set_name("Preview: %s.csscheme" % base_name)
        set_text(v, text)


class convert_tmtheme(sublime_plugin.TextCommand):

    """Convert a .tmTheme plist into a CSScheme file."""

    def is_enabled(self):
        path = self.view.file_name()
        return bool(path) and path.endswith(".tmTheme")

    def run(self, edit, overwrite=False, skip_names=False):
        path = self.view.file_name()
        new_path = os.path.splitext(path)[0] + '.csscheme'

        if not overwrite and os.path.exists(new_path):
            if not sublime.ok_cancel_dialog("The file %s already exists.\n"
                                            "Do you want to overwrite?"
                                            % new_path):
                return

        with OutputPanel(self.view.window(), "csscheme_tmtheme") as out:
            # Load the tmTheme file
            data = tmtheme.load(get_text(self.view), path, out)
            if not data:
                return

            csscheme = tmtheme.to_csscheme(data, out, skip_names)
            if not csscheme:
                return

        # View.insert respects the tab vs. spaces and tab_width settings,
        # whch is why we use it instead of writing to the file directly.
        v = self.view.window().open_file(new_path)

        # open_file returns an oddly behaving view that does not accept
        # inputs, unless invoked on a different thread e.g. using
        # set_timeout: https://github.com/SublimeTextIssues/Core/issues/678
        def continue_operation():
            # The 'insert' and 'insert_snippet' commands and View.insert
            # respect auto-indentation rules, which we don't want.
            v.settings().set('auto_indent', False)
            set_text(v, csscheme)
            v.settings().erase('auto_indent')

            v.run_command('save')

        sublime.set_timeout(continue_operation, 0)
