"""Setup script for ProcOrg."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="procorg",
    version="0.1.0",
    author="ProcOrg",
    description="A simple process orchestration and management tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.1.0",
        "flask>=3.0.0",
        "flask-socketio>=5.3.0",
        "flask-cors>=4.0.0",
        "croniter>=2.0.0",
        "python-socketio>=5.10.0",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "procorg=procorg.cli:main",
            "procorg-web=procorg.web:run_server",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    package_data={
        "procorg": ["templates/*.html"],
    },
)
