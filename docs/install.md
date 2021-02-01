# Installing Skill SDK for Python

## Development requirements

The Python micro-service the SDK creates is designed to run in UNIX-compatible environment: Linux or macOS. 

To run the micro-service under Windows-compatible OS, please use `--dev run` parameter, that essentially deactivates UNIX-only Gunicorn and uses integrated WSGIRefServer.

Before you start development, make sure to have the following components:

- [python 3](https://docs.python.org/3/using/index.html) interpreter (3.7 is minimum required)
- [pip](https://docs.python.org/3/library/ensurepip.html) package manager
- [venv](https://docs.python.org/3/library/venv.html) virtual environments support
- a recent version of the [SDK](https://github.com/telekom/voice-skill-sdk/):
    - either clone from the GitHub repo:<br />
      `git clone https://github.com/telekom/voice-skill-sdk.git`
    - or download and unpack a source distribution:<br /> 
      `pip download --no-deps --no-binary :all: skill-sdk && tar xzf skill-sdk-*.tar.gz`

>To compile the `.po` files [GNU gettext](https://www.gnu.org/software/gettext/) is required:
> - Linux: `[sudo] apt install gettext`
> - macOS: `brew install gettext`
> - Windows: [precompiled binary installer](https://mlocati.github.io/articles/gettext-iconv-windows.html)

>To run Docker services, you need a recent version of [Docker](https://www.docker.com/community-edition#/download).

## Development install

To install SDK for development usage:

1. Activate the virtual environment that you want to install the SDK in
2. Run the development install with `python <path-to-SDK-folder>/setup.py develop`, e.g.
`python ./voice-skill-sdk/setup.py develop`
> Alternatively, you can use `pip` to download the package from GutHub and run the development install: 
2. `python -m pip install -e git+https://github.com/telekom/voice-skill-sdk.git#egg=skill-sdk`

## Production install

When deploying your skill to production:

1. Run the production install with `python -m pip install skill-sdk`
