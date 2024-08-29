# setup.py
from setuptools import setup, find_packages

setup(
    name="hexfix",
    version="0.0.1",
    author="Shashikumar K L",
    author_email="raghashashikumar@gmail.com",
    description="",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ShashikumarKL/hexfix.git",  # Replace with your GitHub repo or project URL
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)
