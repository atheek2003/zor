from setuptools import setup, find_packages

setup(
    name="open-code",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "google-generativeai",
        "python-dotenv",
        "typer",
        "rich",
        "pygments"
    ],
    entry_points={
        "console_scripts": [
            "ninja=open_code.main:app",
        ],
    },
)
