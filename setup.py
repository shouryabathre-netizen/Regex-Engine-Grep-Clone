from setuptools import setup, find_packages

setup(
    name="regex-engine",
    version="0.1.0",
    description="A from-scratch regex engine (Thompson NFA construction) with a grep-style CLI",
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.8",
    py_modules=["mygrep"],
    entry_points={
        "console_scripts": [
            "mygrep=mygrep:main",
        ],
    },
)
