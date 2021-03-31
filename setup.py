#!/usr/bin/env python

import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.dirname(__file__))

about = {}
with open(os.path.join(HERE, "skill_sdk", "__version__.py")) as f:
    exec(f.read(), about)


setup(
    name=about["__name__"],
    version=about["__version__"],
    description=about["__description__"],
    url=about["__url__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    license=about["__license__"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    packages=find_packages(),
    package_data={"": ["*"], "skill_sdk.ui": ["css/*", "js/*"]},
    install_requires=[
        "fastapi",
        "pydantic>=1.8,<2.0.0",
        "starlette_context",
        "python-dateutil",
        "babel",
        "uvicorn[standard]",
        "isodate",
        "orjson",
        "aiobreaker",
        "httpx>=0.16, <1",
        "pyyaml",
        "nest-asyncio",
    ],
    extras_require={
        "dev": [
            "starlette[full] ==0.13.6",
            "mypy",
            "respx",
            "pytest",
            "pytest-cov",
            "pytest-mock",
            "pytest-asyncio",
            "questionary",
            "starlette-opentracing>=0.1.0",
            "starlette-exporter>=0.7.0",
        ],
        "all": [
            # TODO: describe in the docs the process of plugging in the StarletteTracingMiddleWare with a tracer
            "starlette-opentracing>=0.1.0",
            "starlette-exporter>=0.7.0",
        ],
    },
    entry_points={"console_scripts": ["vs = skill_sdk.__main__:main"]},
    setup_requires=["wheel"],
    python_requires=">=3.7",
)
