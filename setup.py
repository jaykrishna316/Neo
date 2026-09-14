#!/usr/bin/env python3
"""Setup configuration for Neo agent coordination package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="neo-coordination",
    version="0.1.0",
    author="Neo Contributors",
    author_email="support@neo-coordination.dev",
    description="A production-oriented coordination layer for preventing conflicting work before autonomous agents execute code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jaykrishna316/Neo",
    project_urls={
        "Bug Tracker": "https://github.com/jaykrishna316/Neo/issues",
        "Documentation": "https://github.com/jaykrishna316/Neo/tree/main/docs",
        "Source Code": "https://github.com/jaykrishna316/Neo",
    },
    packages=find_packages(where="."),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "pylint>=2.17",
            "mypy>=1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="agent coordination conflict detection multi-agent autonomous",
    license="MIT",
    zip_safe=False,
)
