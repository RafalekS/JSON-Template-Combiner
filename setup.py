from setuptools import setup, find_packages

setup(
    name="json-template-combiner",
    version="1.0.0",
    description="JSON Template Combiner - Python Application",
    author="RLS",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # Add your dependencies here
    ],
    entry_points={
        'console_scripts': [
            'json template combiner=main:main',
        ],
    },
)