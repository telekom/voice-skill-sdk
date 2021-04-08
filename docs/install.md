# Installing Skill SDK for Python

## Development requirements

Before you start development, make sure to have the following components:

- [python 3](https://docs.python.org/3/using/index.html) interpreter (3.7 is minimum required).
- [pip](https://docs.python.org/3/library/ensurepip.html) package manager.
- [venv](https://docs.python.org/3/library/venv.html) virtual environments support.
- a recent version of the [SDK](https://github.com/telekom/voice-skill-sdk/):
    - either clone from the GitHub repo:<br />
      `git clone https://github.com/telekom/voice-skill-sdk.git`
    - or download and unpack a source distribution:<br /> 
      `pip download --no-deps --no-binary :all: skill-sdk && tar xzf skill-sdk-*.tar.gz`

>To run the skill in a Docker container, you need a recent version of [Docker](https://www.docker.com/community-edition#/download).

## Development install

To install SDK for development usage:

1. Activate the virtual environment that you want to install the SDK in.
2. Run the development install with `pip install -e <path-to-SDK-folder>[dev]`, e.g.
`pip install -e python ../voice-skill-sdk[dev]`.
> Alternatively, you can use `pip` to download the package from GutHub and run the development install: 
2. `pip install -e git+https://github.com/telekom/voice-skill-sdk.git#egg=skill-sdk[dev]`.

## Production install

When deploying your skill to production:

`python -m pip install skill-sdk`

To activate Prometheus metrics exporter and distributed tracing adapter:

`python -m pip install skill-sdk[all]`
