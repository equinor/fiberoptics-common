# sphinx.ext.autosummary - templates

The original templates can be found [here](https://github.com/sphinx-doc/sphinx/tree/master/sphinx/ext/autosummary/templates/autosummary).

The adapted templates include the following changes:
- Titles have been modified from using `fullname` to `objname`.
- Added `:toctree:` to nested autosummary of functions and classes.

The `main.rst` file is identical to `module.rst` with the exception of using the default `fullname` instead of `objname`.