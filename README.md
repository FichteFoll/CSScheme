CSScheme - Sublime Text Plugin
==============================

[![Build Status][]](https://travis-ci.org/FichteFoll/CSScheme)
[![Coverage Status][]](https://coveralls.io/r/FichteFoll/CSScheme)

[Build Status]: https://travis-ci.org/FichteFoll/CSScheme.png
[Coverage Status]: https://coveralls.io/repos/FichteFoll/CSScheme/badge.png

Ever thought handwriting `.tmTheme` files sucks? But the other options to
editing color schemes are not programmatical enough? Then this is for you!

CSScheme converts a custom CSS-like syntax into the `.tmTheme` files we all
love, but it does not end there. CSScheme can also take care of **compiling
SCSS** into CSS and then into a color scheme using all features from SASS, such
as variables or conditionals.

*Check the [example file](#example-file) for what's possible!*


## Installation

Use [Package Control][] to install CSScheme.

[Package Control]: https://sublime.wbond.net/installation


## Usage

Create a new file with the `.csscheme` or `.scsscheme` extension, or just select
the corresponding syntax for your file. Building (<kbd>ctrl+b</kbd> or
<kbd>command+b</kbd>) will convert the file to CSS, if necessary, and then into
a `.tmTheme` file. Errors during conversion are captured in an output panel.

Things you need to consider when using CSScheme:

- `@` at-rules will be added as string values to the outer dictionary. Thus, you
  need to specify a global `@name` rule to specify the scheme's name. `@name`
  rules in a ruleset will show as the name for various color scheme editing
  tools after compilation. You usually don't need it but it doesn't hurt either.
- If you want a property to have no font styles you have to specify 
  `fontStyle: none;`. This will be translated to the empty
  `<key>fontStyle</key><string></string>`.


Things you need to consider when using **SCSS**cheme (or SASScheme):

- Make sure that `sass` is available on your PATH or adjust the path to the
  executable in the settings.
- The SASS parser will not accept raw `#RRGGBBAA` hashes. You need to enclose
  them in a string, e.g. `'#12345678'`, or just use the `rgba()` notation.
- The SASS parser will also not work with the `-` subtract scope seletor
  operator, so you need to enclose it in a string if you want to use it (`'-'`).
  CSScheme will take care of removing the quotes in the resulting color scheme
  file (an example for this can be found in the [example file](#example-file)).

I won't outline conventions or the structure of color schemes in general (for
now), but you should probably check out the following
[Useful resources](#useful-resources) section if you have some questions.


### Supported Syntaxes

CSScheme provides native support for CSS to `.tmTheme` conversion. Thus, all
languages that compile to CSS will also work in some way. SCSS (and SASS) have a
special treatment in that they are automatically built and SCSScheme even has
its own syntax definition because the one from the SCSS package highlights
unknown propoerties as invalid. Furthermore they provide snippets and
completions. For SASSchemes, you can use the syntax from the [SASS Package][].

[SASS Package]: https://sublime.wbond.net/packages/Sass

If you want to use something different than SCSS, feel free to file an issue (if
there isn't one already). I initially considered supporting LESS too, but they
don't really provide much over SCSS and it's quite some work to write the syntax
definitions for each of them. The SASS package on Package Control provides
decent syntax highlighting that doesn't break with the properties that color
schemes use though, so you can at least use that if you prefer.


### Utility for Scheme Creation

**Symbol List**

Just press <kbd>ctrl+r</kbd> (<kbd>command+r</kbd>).

**Snippets**

- `*` (`*` ruleset)
- `r` (general purpose ruleset)

*SCSScheme*

- `mixin`, `=` (short for `mixin`)
- `if`, `elif`, `else`
- `for` (from ... to), `fort` (from ... through)
- `each`
- `while`

**Completions**

A few commonly used properties are completed as well as the basic scopes from
the [Text Mate scope naming conventions](#useful-resources) when specifying a
selector.


### Useful Resources

Here is a bunch of links that might help you when working on your color scheme.

- [TextMate Manual - Scope Selectors](http://manual.macromates.com/en/scope_selectors)
- [TextMate Manual - Scope Naming Conventions](http://manual.macromates.com/en/language_grammars.html#naming-conventions)
- [SASS/SCSS](http://sass-lang.com/)
- [SASS (color) function reference](http://sass-lang.com/documentation/Sass/Script/Functions.html)
- [Overview of SASS functions with example colors](http://jackiebalzer.com/color)
- [HSL to RGB converter](http://serennu.com/colour/hsltorgb.php)
- [Color Scheme Calculator](http://serennu.com/colour/colourcalculator.php)
- [Hue scales using HCL](http://vis4.net/blog/posts/avoid-equidistant-hsv-colors/)
- [Multi-hued color scales](https://vis4.net/blog/posts/mastering-multi-hued-color-scales/)
- [Tool for multi-hued color scales](https://vis4.net/labs/multihue/)


## Example File

I prepared an example file that is merely a proof of concept and shows a few of
the features that are supported. The colors itself don't make much sense and are
not good on the eyes because I picked them pretty much randomly, but it gives
some great insight on what is possible.

[**Example SCSScheme.scsscheme**](./Example SCSScheme.scsscheme)


## Other Efforts for Easing Color Scheme Creation

Please note that all these aim to work directly on `.tmTheme` files and will not
work together with CSScheme since it does not yet support converting existing
schemes to CSS (and will never convert to SCSS).

- <https://github.com/facelessuser/ColorSchemeEditor/> - Cross platform Python
  application for editing color schemes in a GUI
- <https://github.com/nilium/schemer> - OS X App, similar to the above
- <http://tmtheme-editor.herokuapp.com/> - Webapp, similar to the above but with a
  bunch of example color schemes to preview/edit and a nice preview
- <https://github.com/bobef/ColorSchemeEditor-ST2> - Sublime Text plugin that syncronizes
