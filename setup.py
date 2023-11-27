from setuptools import PEP420PackageFinder, setup

extras_require = {
    "auth": ["azure-identity"],
    "io": ["h5py"],
    "plot": ["matplotlib"],
    "processing": ["scipy"],
    "scikit": ["scikit-learn"],
}

extras_require["all"] = [pkg for pkgs in extras_require.values() for pkg in pkgs]

extras_require["dev"] = [
    "black",
    "bumpversion",
    "flake8",
    "isort",
    "pytest-cov",
    "pytest-mock",
    "pytest",
]

extras_require["docs"] = [
    "sphinx",
    "sphinx_design",
    "sphinx_rtd_theme",
]

setup(
    name="fiberoptics-common",
    version="1.9.1",
    packages=PEP420PackageFinder.find(include=["fiberoptics.common*"]),
    install_requires=["pandas"],
    extras_require=extras_require,
)
