from setuptools import setup, find_packages

setup(
    name="pip-aide",
    version="1.0.2",
    description="AI-powered pip install helper",
    author="不做了睡大觉",
    author_email="stakeswky@gmail.com",
    packages=find_packages(),
    install_requires=[
        "requests",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "pip-aide=pip_aide.cli:main"
        ]
    },
    include_package_data=True,
    license="MIT",
)
