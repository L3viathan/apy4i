from setuptools import setup, find_packages

setup(
    name="apy4i",
    version="0.1.0",
    install_requires=[
        "quart_trio",
        "textflip",
    ],
    author="L3viathan",
    author_email="git@l3vi.de",
    description="Fourth version of my API",
    url="https://github.com/L3viathan/apy4i",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
    ],
)
