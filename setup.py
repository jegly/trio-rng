from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="trio-rng",
    version="1.0.0",
    author="JEGLY",
    description="Triple-cascade random number generator using OpenSSL, Qiskit, and Cirq",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jegly/trio-rng",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "qiskit>=0.45.0",
        "qiskit-aer>=0.13.0",
        "cirq>=1.3.0",
    ],
    entry_points={
        "console_scripts": [
            "quantum-rng=trio_rng.cli:main",
        ],
    },
)
