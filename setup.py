from setuptools import PEP420PackageFinder, setup

setup(
    name="fiberoptics-common",
    version="1.0.0",
    packages=PEP420PackageFinder.find(include=["fiberoptics.*"]),
    install_requires=["pandas"],
    extras_require={
        "auth": ["azure-identity"],
        "io": ["h5py"],
        "plot": ["matplotlib"],
        "processing": ["scipy"],
        "sklearn": ["scikit-learn"],
    },
)
