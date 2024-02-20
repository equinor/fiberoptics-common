# fiberoptics-common

![Python](https://img.shields.io/badge/python-%23239120.svg?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-%23239120.svg?style=for-the-badge&logo=pandas&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-%23239120.svg?style=for-the-badge&logo=pytest&logoColor=white)

## Quickstart

Take a look at the [documentation](https://equinor.github.io/fiberoptics-common/) to get started with _fiberoptics-common_.

## Development

The package is divided into multiple submodules, each with a different set of dependencies.
This allows you to only install e.g. plotting dependencies if you're only interested in the plotting functionality in the `plot` submodule. The repository structure is as follows:

```
├── docs                        <-- Sphinx documentation
├── fiberoptics/common          <-- Contains submodules
│   ├── auth
│   ├── io
│   ├── misc
│   └── ...
└── tests                       <-- Contains tests for each submodule
    ├── auth
    ├── io
    ├── misc
    └── ...
```

### Installing locally

- clone `fiberoptics-common` repository:

```
git clone https://github.com/equinor/fiberoptics-common.git
```

- Navigate into `fiberoptics-common` folder:

```
cd fiberoptics-common
```

- Create a virtual environment:

```
  python -m venv .venv
```

- Activate the virtual environment:
  - Windows:
  ```
  .venv\Scripts\activate
  ```
  - MacOS and Linux:
  ```
  source .venv/bin/activate
  ```
- Install minimal dependencies:

```
poetry install
```

- Install dependencies & dev-dependencies:

```
poetry install --with dev
```

Available dependency groups are `dev` and `docs`

- Install extra optional dependencies:

```
poetry install -E "auth"
```

Available extra dependencies are `auth`, `io`, `plot`, `processing`, `scikit`. All extra dependencies can be installed using `poetry install -E "all"`.

### Adding functionality

**IMPORTANT: This repository is public and only non-sensitive code should be added!**

All new functionality should be added to a submodule. To decide where to add your function, class or module, there are two factors to keep in mind. A submodule groups together functionality that is either _related_ or _shares dependencies_.

If your additions introduce several new dependencies, you should consider creating a separate submodule for them. On the other hand, if your additions are not related to any existing submodules, and do **not** require any dependencies, you should consider placing them in the `fiberoptics.common.misc` submodule.

Remember to also write tests!

### Versioning

This repository uses semantic versioning, where the version number consists of three parts, namely `major.minor.patch`. To decide which part to increment, the standard is as follows:

- `major` Incremented on **breaking** changes where existing code must be updated for the users to install the latest version.
- `minor` Incremented when new functionality is added in a backwards compatible manner.
- `patch` Incremented on code changes that are backwards compatible and do not change the interface.

## Documentation

The documentation is built with Sphinx using a theme provided by Read the Docs.

All files associated with the documentation is found under `docs/` and are organized as follows

```
├── _build                <-- Contains the output from `make html`
├── _static               <-- Contains static data such as css and images
├── _templates            <-- Contains templates used by autosummary
├── conf.py               <-- Configures Sphinx and all extensions
├── index.rst             <-- Content entrypoint
├── make.bat              <-- Convenience script to simplify building (Windows)
└── Makefile              <-- Convenience script to simplify building (Unix)
```

The Sphinx documentation is automatically deployed to GitHub pages by triggering the `Publish Sphinx documentation` action in GitHub.

### Building locally

To contribute to the docs, you must first install the documentation dependencies.

- [**sphinx**](https://www.sphinx-doc.org/en/master/) - Core library to generate the documentation.
- [**sphinx_design**](https://sphinx-design.readthedocs.io/en/latest/) - Extension to add responsive web-components such as grids and cards.
- [**sphinx_rtd_theme**](https://sphinx-rtd-theme.readthedocs.io/en/stable/index.html) - Extension to add the Read the Docs theme.

- Install dependencies & dev-dependencies:

```
poetry install --with dev,docs
```

- Navigate into `docs` folder:

```
cd docs
```

- The next step is to build the docs by running the following command:

```
poetry run make html
```

_Note_: Replace `make html` with `make clean html` to rebuild everything from scratch.

Doing so outputs the HTML files in the `docs/_build/html` folder. To view the files, start an HTTP server by running

```
python -m http.server 5500 --bind 127.0.0.1 --directory docs/_build/html/
```

and opening http://127.0.0.1:5500/index.html in your browser.

### Updating content pages

The content pages are written in the [reStructuredText](https://docutils.sourceforge.io/rst.html) markup language. To get an overview of how to write _rst_ files, refer to the Sphinx documentation [here](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html). In particular, take a look at the [Directives](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html) section, as well as [The Python Domain](https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#the-python-domain) to get a sense of the available "keywords".
For general formatting, lists, tables and so on, take a look at the cheatsheet [here](https://docs.generic-mapping-tools.org/6.2/rst-cheatsheet.html).

_Note:_ If you make changes to css or other static resources, you will not necessarily see your changes when you reload the browser. This is because the browser caches these resources. One way to avoid it is to do a full reload (`ctrl + F5`) instead of a normal reload (`F5`).

### Updating docstrings

The docstrings are automatically converted into HTML using the [**sphinx.ext.autosummary**](https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html) extension as well as the [**sphinx.ext.autodoc**](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html) extension. All there is left to do, is to write proper docstrings.

The docstrings follow the syntax and best practices described in the NumPy [Style guide](https://numpydoc.readthedocs.io/en/latest/format.html). Furthermore, [here](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_numpy.html) is a collection of examples on how to write NumPy style docstrings. Note that in some docstring sections, such as the _Returns_ section, reStructuredText formatting is fully supported. Take a look at the cheatsheet [here](https://docs.generic-mapping-tools.org/6.2/rst-cheatsheet.html).
