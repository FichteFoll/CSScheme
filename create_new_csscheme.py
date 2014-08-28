import re

import sublime_plugin


PACKAGE = "CSScheme"  # my_sublime_lib.path.get_package_name()


csscheme_snippet = """
@name "${1:Name}";

* {
    background: ${2:#ddd};
    foreground: ${3:#222};

    caret: ${4:#fff};
    lineHighlight: ${5:#12345678};
    selection: ${6:#f00};
}

string {
    foreground: ;
}

string punctuation.definition {
    foreground: ;
}

string.constant {
    foreground: ;
}

constant {
    foreground: ;
}

constant.numeric {
    foreground: ;
}

comment {
    foreground: ;
    fontStyle: italic;
}

support {
    foreground: ;
}

support.constant {
    foreground: ;
}

entity {
    foreground: ;
}

invalid {
    foreground: ;
}

invalid.illegal {
    background: ;
}

keyword {
    foreground: ;
}

storage {
    foreground: ;
}

variable, support.variable {
    foreground: ;
}
""".strip().replace("    ", "\t")

scsscheme_snippet = """
@name "${1:Name}";

* {
    background: ${2:#ddd};
    foreground: ${3:#222};

    caret: ${4:#fff};
    lineHighlight: ${5:'#12345678'};
    selection: ${6:#f00};
}

string {
    foreground: ;

    punctuation.definition {
        foreground: ;
    }

    &.constant {
        foreground: ;
    }
}

constant {
    foreground: ;

    &.numeric {
        foreground: ;
    }
}

comment {
    foreground: ;
    fontStyle: italic;
}

support {
    foreground: ;

    &.constant {
        foreground: ;
    }
}

entity {
    foreground: ;
}

invalid {
    foreground: ;

    &.illegal {
        background: ;
    }
}

keyword {
    foreground: ;
}

storage {
    foreground: ;
}

variable, support.variable {
    foreground: ;
}
""".strip().replace("    ", "\t")

# Do some dirty regex replaces because ... well, it's easy
sasscheme_snippet = re.sub(r" \{$|\n\t*\}|;$", '', scsscheme_snippet, flags=re.M)
# Does anyone actually like removing these colons? I prefer them visible
styluscheme_snippet = re.sub(r":(?= )", '', sasscheme_snippet, flags=re.M)


class create_csscheme(sublime_plugin.WindowCommand):
    snippets = dict(
        CSScheme=csscheme_snippet,
        SCSScheme=scsscheme_snippet,
        SASScheme=sasscheme_snippet,
        StyluScheme=styluscheme_snippet
    )

    def run(self, syntax=None):
        if not syntax or syntax not in self.snippets:
            print("create_csscheme: Invalid type parameter")
            return

        v = self.window.new_file()
        v.set_syntax_file("Packages/%s/Package/%s.tmLanguage"
                          % (PACKAGE, syntax))
        v.run_command("insert_snippet", {"contents": self.snippets[syntax]})
