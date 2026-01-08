from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="tap-openproject",
    version="0.1.0",
    description="Singer tap for OpenProject API - Extract projects, work packages, and metadata with surveilr integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="surveilr Team",
    author_email="support@surveilr.com",
    url="https://github.com/surveilr/tap-openproject",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    package_data={
        "tap_open_project": ["schemas/*.json"],
    },
    install_requires=[
        "requests>=2.28.0",
        "singer-python>=5.13.0",
    ],
    python_requires=">=3.8",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "tap-openproject=tap_open_project.run_with_config:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Groupware",
    ],
    keywords="singer tap openproject etl surveilr data-pipeline api",
    project_urls={
        "Bug Reports": "https://github.com/surveilr/tap-openproject/issues",
        "Source": "https://github.com/surveilr/tap-openproject",
        "Documentation": "https://github.com/surveilr/tap-openproject#readme",
    },
)
