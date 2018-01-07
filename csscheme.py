import converters
from converters import tmtheme
from tinycsscheme import parser, dumper
import argparse


def main():
    parser = argparse.ArgumentParser(description="Convert between csscheme and tmTheme format")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--skip-names", action='store_true')

    args = parser.parse_args()

    if validate_extensions(tmtheme=args.input, csscheme=args.output):
        convert_tmtheme_to_csscheme(args.input, args.output, args.skip_names)
    elif validate_extensions(tmtheme=args.output, csscheme=args.input):
        convert_csscheme_to_tmtheme(args.input, args.output)


def validate_extensions(tmtheme, csscheme):
    return (csscheme.endswith(tuple("." + c.ext for c in converters.all))
            and tmtheme.lower().endswith(".tmtheme"))


def convert_tmtheme_to_csscheme(input_file, output_file, skip_names=False):

    out = MockSublimeOutputPanel()

    with open(input_file, "r") as f:
        input = f.read()

    input_text = tmtheme.load(input, "", out)

    csscheme = tmtheme.to_csscheme(input_text, out, skip_names)

    with open(output_file, "w") as f:
        f.write(csscheme)


def convert_csscheme_to_tmtheme(input_file, output_file):
    # determine the converter to use
    possible_converters = [c for c in converters.all if c.valid_file(input_file)]
    if len(possible_converters) > 1:
        error("Found multiple possible converters")
        return
    if len(possible_converters) == 0:
        exts = ["." + c.ext for c in converters.all]
        error("No converters found for this file extension. Known extensions are " + str(exts))
        return

    converter = possible_converters[0]

    out = MockSublimeOutputPanel()

    output = converter.convert(out, input_file, {}, True)

    stylesheet = parser.parse_stylesheet(output)

    if stylesheet.errors:
        converter.report_parse_errors(out, input_file, output, stylesheet.errors)

    # TODO: support hidden at-rule

    try:
        dumper.dump_stylesheet_file(output_file, stylesheet)
    except dumper.DumpError as ex:
        converter.report_dump_error(out, input_file, output, ex)


class MockSublimeOutputPanel:
    def write_line(self, message):
        print(message)

    def set_regex(self, regex):
        pass

    def set_path(self, dirname, regex):
        pass


def error(reason):
    print("error:", reason)


if __name__ == "__main__":
    main()
