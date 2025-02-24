from setuptools import setup, find_packages

setup(
    name='genat_iso_parser',
    version='3.0',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={"iso_res": ["*.json"]},
    include_package_data=True,
    install_requires=[

    ]
)