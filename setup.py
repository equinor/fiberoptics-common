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
    *extras_require["all"],
    "black",
    "bumpversion",
    "flake8",
    "pytest",
    "pytest_mock",
]

setup(
    name="fiberoptics-common",
    version="1.2.0",
    packages=PEP420PackageFinder.find(include=["fiberoptics.*"]),
    install_requires=["pandas"],
    extras_require=extras_require,
)
