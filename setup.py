from setuptools import setup, find_packages

setup(
    name="infomentor",
    version="1.0.0",
    url="https://github.com/mypackage.git",
    author="Matthias Bilger",
    author_email="matthias@bilger.info",
    description="grab infomentor news and push or mail them",
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'infomentor=infomentor.__main__:main',
        ],
    }
)
