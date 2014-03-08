CSScheme Changelog
==================

v0.3.0 (2014-03-08)
-------------------

- Differentiate between style and options list ("fontStyle" vs e.g.
  "tagsOptions") for validation (also #2)
- Allow `"fontStyle": none;` for empty style list (#4)
- Highlight SASS's `index` function
- Fix not showing error message if a line number was not found from the compiled
  SCSS (within the last x lines)
- Add snippets for `@for`, `@each`, `@else if`, `@else`, `@while`
- All "package" related files were moved to a sub-directory

v0.2.1 (2014-03-01)
-------------------

- Added "foreground" to allowed style list properties (.g. "bracketsOptions")


v0.2.0 (2014-02-24)
-------------------

- Added more known_properties to check values against (#2)
- Fixed errors when using functions in "unknown" properties (#1)
- Fixed incorrect error messages for empty output from running `sass`
- Fixed unexpected behavior from running `sass` on non-Windows


v0.1.1 (2014-02-24)
-------------------

- Removed `$` form the SCSS word separator list


v0.1.0 (2014-02-22)
-------------------

- Initial release
