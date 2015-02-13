import os
from io import StringIO

__all__ = ('load',)

debug_base = 'Error parsing Property List "%s": %s, line %s, column %s'
debug_base_2 = 'Error parsing Property List "%s": %s'
file_regex = r'Error parsing Property List "(.*?)": .*?(?:, line (\d+), column (\d+))?'


def load(text, path, out):
    """Load a tmTheme property list and write errors to an output panel.

    :param text:
        The text of the file to be parsed.
    :param path:
        The path of the file, for error output purposes.
    :param out:
        OutputPanel instance.

    :return:
        `None` if errored, the parsed data otherwise (mostly a dict).
    """
    dirname = os.path.dirname(path)
    out.set_path(dirname, file_regex)
    if text.startswith('<?xml version="1.0" encoding="UTF-8"?>'):
        text = text[38:]

    try:
        from xml.parsers.expat import ExpatError, ErrorString
    except ImportError:
        # TODO: provide a compat plist parser as dependency
        # xml.parsers.expat is not available on certain Linux dists, try to use plist_parser then.
        # See https://github.com/SublimeText/AAAPackageDev/issues/19
        # Let's just hope AAAPackageDev is installed
        try:
            import plist_parser
        except ImportError:
            out.write_line("Unable to load xml.parsers.expat or plist_parser modules.\n"
                           "Please report to the package author.")
            return
        else:
            out.write_line("Unable to load plistlib, using plist_parser instead\n")

        try:
            data = plist_parser.parse_string(text)
        except plist_parser.PropertyListParseError as e:
            out.write_line(debug_base_2 % (path, str(e)))
        else:
            return data
    else:
        import plistlib
        try:
            # This will try `from xml.parsers.expat import ParserCreate`
            # but since it is already tried above it should succeed.
            return plistlib.readPlistFromBytes(text.encode('utf-8'))
        except ExpatError as e:
            out.write_line(debug_base
                           % (path,
                              ErrorString(e.code),
                              e.lineno,
                              e.offset + 1)
                           )


def to_csscheme(data, out, skip_names):
    with StringIO() as stream:
        # Name
        name = data.get('name', "INSERT NAME HERE")
        stream.write('@name "%s";' % name)

        uuid = data.get('uuid')
        if uuid:
            stream.write('\n\n@uuid %s;' % uuid)

        # Search for settings item and extract the others
        items = data['settings']
        settings = None
        for i, item in enumerate(items):
            if 'scope' not in item:
                if 'settings' not in item:
                    out.write_line("Expected 'settings' key in item without scope")
                    return
                settings = item['settings']
                del items[i]  # remove from the regular items list
                break

        if not settings:
            settings = []
        else:
            settings = list(settings.items())

        # Global settings
        settings.sort(key=lambda x: x[0].lower())
        stream.write("\n\n* {")
        for key, value in settings:
            stream.write("\n\t%s: %s;" % (key, value))
        stream.write("\n}")

        # The other items
        for item in items:
            if 'scope' not in item:
                out.write_line("Missing 'scope' key in item")
                return
            stream.write("\n\n%s {" % item['scope'])

            if not skip_names and 'name' in item:
                stream.write('\n\t@name "%s";' % item['name'])

            if 'settings' not in item:
                out.write_line("Missing 'settings' key in item")
                return
            for key, value in item['settings'].items():
                stream.write("\n\t%s: %s;" % (key, value))

            stream.write("\n}")

        return stream.getvalue()
