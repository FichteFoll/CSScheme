CSScheme - Sublime Text Plugin
==============================

[![Build Status][]](https://travis-ci.org/FichteFoll/CSScheme)

[Build Status]: https://travis-ci.org/FichteFoll/CSScheme.png

Ever thought handwriting `.tmTheme` files sucks? But the other options for
editing color schemes are not programmatical enough? Then this is for you!

![What it looks like](http://i.imgur.com/0LTV2xq.gif)

CSScheme is a custom CSS-like syntax that converts into the `.tmTheme` files we
all love, but it does not end there. CSScheme (the package) can also take care
of **compiling SCSS, SASS or stylus** into CSScheme (the syntax) and *then* into
a color scheme using all features of these pre-compilers, such as variables,
conditionals or functions.

*Check the [example files](#example-files) for what's possible!*


## Installation

Use [Package Control][] to [install][] "CSScheme".

[Package Control]: https://packagecontrol.io/installation
[install]: https://packagecontrol.io/docs/usage


## Usage (Please Read!)

You can either create a new file with the **CSScheme: Create new \*Scheme file**
commands, open a file with the `.csscheme`, `.scsscheme`, `.sasscheme` or
`.styluscheme` extension or convert an existing `tmTheme` file using the
**CSScheme: Convert to CSScheme** command or build system. Conversion to other
syntaxes is not supported at the moment and likely won't in the future. Please
convert manually and to your own preferences.

Building (<kbd>ctrl+b</kbd> or <kbd>⌘b</kbd>) will convert the file to CSScheme,
if necessary, and then into a `.tmTheme` file. Errors during conversion are
captured in an output panel. For automation purposes, the command is named
`convert_csscheme`.

Things you *must* consider when using **CSScheme**:

- `@` at-rules will be added as string values to the "outer dictionary". You
  *may* specify a global `@name` rule to specify the scheme's name. `@name`
  rules in a ruleset will show as the name for various color scheme editing
  tools after compilation. Sublime Text itself does not use it.
- In order to create a `.hidden-tmTheme` file, you need to specify a global
  `@hidden true;` rule. The converter will consume this rule and change the
  output file's extension accordingly.
- If you want a property to have no font styles you have to specify 
  `fontStyle: none;`. This will be translated to
  `<key>fontStyle</key><string />`.
- The general settings (like main background color) are read from a general-
  purpose block with a `*` selector. This is required.
- Specifying a uuid (via `@uuid`) is optional because Sublime Text ignores it.


Things you *must* consider additionally when using CSScheme with **SCSS** or
**SASS**:

- Make sure that `sass` is available on your PATH or adjust the path to the
  executable in the settings.
- The SASS parser will not accept raw `#RRGGBBAA` hashes. You must enclose
  them in a string, e.g. `'#12345678'`, or just use the `rgba()` notation.
- The SASS parser will also not work with several scope selector operators (`-`,
  `&`, `(`, `)`, `|`). You must escape these with a backslash.
  The same applies to scope-segments starting with a number.

  CSScheme will take care of removing backslashes before emitting the final
  conversion result. 
  Examples can be found in the [example files](#example-files)).
  
  **Note**: Because the SASS parser does not know about the semantics of these
  operators, they will generally behave poorly when used in conjunction with
  scope nesting.


Things you *must* consider additionally when using CSScheme with **stylus**:

- Make sure that `stylus` is available on your PATH or adjust the path to the
  executable in the settings.
- At-rules, like the required global `@name` must be encapsulated with
  `unquote()`. Example: `unquote('@name "Example StyluScheme";')`
- At-rules in non-global scope **do not work**! You'd only need these for
  `@name` or possibly `@comment` anyway, but stylus does some weird stuff that
  does not translate into sane CSScheme.


### Supported Syntaxes

CSScheme (the package) provides native support for CSScheme-to-`.tmTheme`
conversion. Thus, all languages that compile to CSS will also work in one way or
another. SCSS/SASS and stylus are automatically built from within Sublime Text,
and SCSScheme even has its own syntax definition because the one from the SCSS
package highlights unknown properties as invalid. Furthermore they provide
snippets and completions.

- Syntax highlighting for CSScheme and SCSScheme is bundled. Snippets and
  completions are provided for both.
- For SASScheme syntax highlighting you additionally need the [Sass][] package.
- For StyluScheme syntax highlighting you additionally need the [Stylus][]
  package.

[Sass]: https://packagecontrol.io/packages/Sass
[Stylus]: https://packagecontrol.io/packages/Stylus

If you want to use something a different pre-processor, you can do so by
converting to CSScheme externally and then do conversion from CSScheme to
tmTheme from within Sublime Text. Feel free to file an issue (if there isn't one
already) if you'd like built-in support for an additional pre-processor.


### Utility for Scheme Creation
*(only CSScheme and SCSScheme)*

#### Symbol List

Just press <kbd>ctrl+r</kbd> (<kbd>⌘r</kbd>).

In StyluScheme this is *somewhat* supported but since scope names are not
regular html tags they don't get recognized (since I didn't bother to write a
new syntax definition for stylus as well).

#### Snippets

- `*` (`*` ruleset)
- `r` (general purpose ruleset)

*only SCSScheme:*

- `mixin`, `=` (short for `mixin`)
- `if`, `elif`, `else`
- `for` (from ... to), `fort` (from ... through)
- `each`
- `while`

#### Completions

All known properties are completed as well as the basic scopes from the
[Text Mate scope naming conventions](#useful-resources) when specifying a 
selector.


### Useful Resources

Here is a bunch of links that might help you when working on your color scheme.

- [TextMate Manual - Scope Selectors](http://manual.macromates.com/en/scope_selectors)
- [TextMate Manual - Scope Naming Conventions](http://manual.macromates.com/en/language_grammars.html#naming-conventions)

- [SASS/SCSS](http://sass-lang.com/)
- [SASS (color) function reference](http://sass-lang.com/documentation/Sass/Script/Functions.html)
- [Overview of SASS functions with example colors](http://jackiebalzer.com/color)
- [stylus reference](http://learnboost.github.io/stylus/)

- [HSL to RGB converter](http://serennu.com/colour/hsltorgb.php)
- [Color Scheme Calculator](http://serennu.com/colour/colourcalculator.php)
- [Hue scales using HCL](http://vis4.net/blog/posts/avoid-equidistant-hsv-colors/)
- [Multi-hued color scales](https://vis4.net/blog/posts/mastering-multi-hued-color-scales/)
- [Tool for multi-hued color scales](https://vis4.net/labs/multihue/)


## Example Files

I prepared two example files that are merely a proof of concept and show a few
of the features that are supported. The colors itself don't make much sense and
are not good on the eyes because I picked them pretty much randomly, but it
gives some great insight on what is possible.

- [**Example SCSScheme.scsscheme**](./Example SCSScheme.scsscheme)
- [**Example StyluScheme.scsscheme**](./Example StyluScheme.styluscheme)

If you would like to see a real world example, refer to the [Writerly Scheme][]
by [@alehandrof][] which heavily uses SASS's `@import` to make a larger scheme
more manageable.

[Writerly Scheme]: https://github.com/alehandrof/Writerly
[@alehandrof]: https://github.com/alehandrof


## Other Efforts for Easing Color Scheme Creation

Please note that all these work directly on `.tmTheme` files.

- <https://github.com/facelessuser/ColorSchemeEditor/> - Cross platform Python
  application for editing color schemes in a GUI
- <https://github.com/nilium/schemer> - OS X App, similar to the above
- <http://tmtheme-editor.herokuapp.com/> - Webapp, similar to the above but
  with a bunch of example color schemes to preview/edit and a nice preview
- <https://github.com/bobef/ColorSchemeEditor-ST2> - Sublime Text plugin that
  syncronizes
