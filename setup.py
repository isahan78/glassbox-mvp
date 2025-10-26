"""
GlassBox package setup configuration.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="glassbox",
    version="0.1.0",
    author="GlassBox Team",
    author_email="team@glassbox.ai",
    description="Interpretable-by-design AI runtime for language models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/glassbox",
    packages=find_packages(exclude=["tests", "notebooks", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "transformer-lens>=1.0.0",
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "streamlit>=1.28.0",
        "plotly>=5.17.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "mypy>=1.6.0",
            "flake8>=6.1.0",
        ],
        "notebooks": [
            "jupyter>=1.0.0",
            "ipywidgets>=8.1.0",
            "matplotlib>=3.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "glassbox-dashboard=dashboard.app:main",
            "glassbox-api=api.server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "glassbox": ["py.typed"],
    },
    keywords=[
        "interpretability",
        "explainability",
        "transformers",
        "attention",
        "mechanistic-interpretability",
        "llm",
        "ai-safety",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourorg/glassbox/issues",
        "Documentation": "https://glassbox.readthedocs.io",
        "Source": "https://github.com/yourorg/glassbox",
    },
)
