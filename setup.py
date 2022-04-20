from setuptools import PEP420PackageFinder, setup

setup(
    name="fiberoptics-common",
    version="0.0.1",
    packages=PEP420PackageFinder.find(include=["fiberoptics.*"]),
    install_requires=["pandas"],
    extras_require={
        "auth": ["azure-identity"],
        "hdf": ["h5py"],
        "plot": ["matplotlib"],
    },
)
