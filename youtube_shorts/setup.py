from setuptools import setup, find_packages

setup(
    name="youtube_shorts",
    version="2.0",
    packages=find_packages(),
    install_requires=[
        "ollama",
        "gtts",
        "pydub",
        "pillow",
        "google-auth",
        "google-auth-oauthlib",
        "google-api-python-client",
        "pyyaml",
    ],
    entry_points={
        'console_scripts': [
            'youtube-shorts=youtube_shorts.main:main',
        ],
    },
)
