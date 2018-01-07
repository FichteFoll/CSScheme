"""Provides various to-csscheme converters."""

import re
import os
import subprocess

__all__ = ('all', 'CSSConverter', 'SCSSConverter', 'SASSConverter', 'StylusConverter')


def swap_path_line(pattern, rel_dir):
    """Create a function for use with `re.sub`.

    Requires matches in groups 1 and 2 and also replaces absolute paths with
    relative where possible.
    """
    def repl(m):
        # Make path relative because we don't need long paths if in same dir
        path = m.group(2)
        try:
            path = os.path.relpath(m.group(2), rel_dir)
        except ValueError:
            # In case the file is on a different drive
            pass

        # Don't make relative if going up more than N folders
        if path.startswith((".." + os.sep) * 3):
            path = m.group(2)
        return pattern % (path, m.group(1))

    return repl


class BaseConverter(object):

    """abstract base class."""

    name = ""
    ext = ""
    default_executable = ""
    cmd_params = ()

    @classmethod
    def valid_file(cls, file_path):
        """Test if a file is applicable for this builder.

        By default, matches against the class's extension.
        """
        return file_path.endswith('.' + cls.ext)

    @classmethod
    def convert(cls, out, file_path, executables, shell):
        """Convert the specified file to CSScheme and return as string.

        * out - output panel to write output to
        * file_path - file to convert
        * executables - dict with optional path settings
        * shell - whether to invoke external commands using shell
        """
        # Just read the file when we have no executable
        if not cls.default_executable:
            try:
                with open(file_path) as f:
                    return f.read()
            except OSError as e:
                out.write_line("Error reading %s:\n%s" % (file_path, e))
                return

        # Construct command
        executable = cls.default_executable
        if cls.default_executable in executables:
            executable = executables[cls.default_executable]
        cmd = (executable,) + cls.cmd_params + (file_path,)

        try:
            # TODO fix encoding from stylus output, mainly paths
            process = subprocess.Popen(cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       shell=shell,
                                       universal_newlines=True)
            stdout, stderr = process.communicate()
        except Exception as e:
            out.write_line("Error converting from %s to CSScheme:\n"
                           "%s: %s" % (cls.name, e.__class__.__name__, e))
            return

        # Process results
        if process.returncode:
            cls.report_convert_errors(out, file_path, process.returncode, stderr)
        elif not stdout:
            out.write_line("Unexpected error converting from %s to CSS:\nNo output"
                           % cls.name)
        else:
            # e.g. "warn(msg)" in stylus
            if stderr:
                out.write_line(stderr)
            return stdout

    @classmethod
    def report_convert_errors(cls, out, file_path, returncode, stderr):
        out.write_line("Error(s) converting from %s to CSS, return code: %s\n"
                       % (cls.name, returncode))

        out.write_line(stderr)

    @classmethod
    def report_parse_errors(cls, out, file_path, source, errors):
        out.write_line("Error(s) parsing CSScheme:\n")
        out.set_regex(r"^(.*):(\d+):(\d+):$")
        for e in errors:
            out.write_line("%s:%s:%s:\n  %s\n"
                           % (os.path.basename(file_path), e.line, e.column, e.reason))

    @classmethod
    def report_dump_error(cls, out, file_path, source, e):
        out.write_line("Error in CSScheme data:\n")
        out.set_regex(r"^(.*):(\d+):(\d+):$")
        out.write_line("%s:%s:%s:\n  %s%s\n"
                       % (os.path.basename(file_path), e.line, e.column, e.reason, e.location))


class CSSConverter(BaseConverter):

    """Convert CSScheme to tmTheme."""

    name = "CSScheme"
    ext = "csscheme"


class SCSSConverter(BaseConverter):

    """Convert SCSScheme to tmTheme."""

    name = "SCSScheme"
    ext = "scsscheme"
    default_executable = "sass"
    cmd_params = ('--line-numbers', '--no-cache', '--scss')

    @classmethod
    def report_convert_errors(cls, out, file_path, returncode, stderr):
        in_dir = os.path.dirname(file_path)

        out.set_regex(r"^\s+in (.*?) on line (\d+)$")

        out.write_line("Errors converting from %s to CSS, return code: %s\n"
                       % (cls.name, returncode))

        # Swap line and path because sublime can't parse them otherwise
        out.write_line(re.sub(r"on line (\d+) of (.*?)$",
                              swap_path_line(r"in %s on line %s", in_dir),
                              stderr,
                              flags=re.M))

    @classmethod
    def report_parse_errors(cls, out, file_path, source, errors):
        in_dir = os.path.dirname(file_path)

        # Match our modified output
        out.set_regex(r"^\s*/\* (.*?), line (\d+) \*/")

        lines = source.split('\n')
        for e in errors:
            out.write_line("ParseError from CSS on line %d:" % e.line)

            printlines = cls.get_lines_till_last_lineno(lines, e.line, in_dir)
            for l in printlines:
                out.write_line("  " + l)
            # Mark the column where the error happened (since we don't have source code)
            out.write_line("  %s^" % ('-' * (e.column - 1)))
            out.write_line("%s\n" % (e.reason))

    @classmethod
    def report_dump_error(cls, out, file_path, source, e):
        in_dir = os.path.dirname(file_path)

        # Match our modified output
        out.set_regex(r"^\s*/\* (.*?), line (\d+) \*/")

        lines = source.split('\n')
        out.write_line("Error in CSScheme data on line %d:" % e.line)

        printlines = cls.get_lines_till_last_lineno(lines, e.line, in_dir)
        for l in printlines:
            out.write_line("  " + l)
        # Mark the column where the error happened (since we don't have source code)
        out.write_line("  %s^" % ('-' * (e.column - 1)))
        out.write_line("%s%s\n" % (e.reason, e.location))

    lineno_reg = re.compile(r"/\* line (\d+), (.+?) \*/", re.M)

    @classmethod
    def get_lines_till_last_lineno(cls, lines, lineno, in_dir):
        printlines = []

        # Search for last known line number (max 20)
        start_dump = 0
        for i in range(lineno, lineno - 20, -1):
            if i < 0:
                break
            m = re.match(r"\s*/\* line (\d+)", lines[i])
            if not m:
                continue

            start_dump = i
            # Swap line and path because sublime can't parse them otherwise
            printlines.append(
                cls.lineno_reg.sub(swap_path_line("/* %s, line %s */", in_dir), lines[i])
            )
            break

        if not start_dump:
            # Nothing found in the past lines => only store the erroneous line
            start_dump = lineno - 2

        # printlines.extend(lines[start_dump + 1:lineno])
        for i in range(start_dump + 1, lineno):
            printlines.append(lines[i])

        return printlines


class SASSConverter(SCSSConverter):

    """Convert SASScheme to tmTheme."""

    name = "SASScheme"
    ext = "sasscheme"
    cmd_params = SCSSConverter.cmd_params[:-1]


class StylusConverter(SCSSConverter):

    """Convert Styluscheme to tmTheme."""

    name = "StyluScheme"
    ext = "styluscheme"
    default_executable = "stylus"
    cmd_params = ('-l', '-p')

    lineno_reg = re.compile(r"/\* line (\d+) : (.+?) \*/", re.M)

    @classmethod
    def report_convert_errors(cls, out, *args, **kwargs):
        out.set_regex(r"Error: (.+?):(\d+)$")
        # The error is already well-formatted so we just need to print it.
        # If you didn't notice, this skips SCSSConverter's implementation.
        super(SCSSConverter, cls).report_convert_errors(out, *args, **kwargs)

# For exporting
all = (CSSConverter, SCSSConverter, SASSConverter, StylusConverter)
