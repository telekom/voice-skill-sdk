<h1 align="center">
    telekom voice-skill-sdk
</h1>

<p align="center">
    <a href="https://github.com/telekom/voice-skill-sdk/commits/" title="Last Commit"><img src="https://img.shields.io/github/last-commit/telekom/voice-skill-sdk?style=flat"></a>
    <a href="https://github.com/telekom/voice-skill-sdk/issues" title="Open Issues"><img src="https://img.shields.io/github/issues/telekom/voice-skill-sdk?style=flat"></a>
    <a href="https://github.com/telekom/voice-skill-sdk/blob/master/LICENSE" title="License"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat"></a>
</p>

<p align="center">
  <a href="#development">Development</a> •
  <a href="#support-and-feedback">Support</a> •
  <a href="#how-to-contribute">Contribute</a> •
  <a href="#contributors">Contributors</a> •
  <a href="#licensing">Licensing</a>
</p>

The goal of this project is to help build voice applications and integrate voice into other applications.

## About this component

The Magenta Voice Skill SDK for Python is a package that assists in creating skill implementations for the Voice Applications built using the Magenta Voice Platform.

## Development

The overview documentation for the Telekom Voicification Suite can be found [here](docs/tvs.md).

The full documentation on how to use this software development kit is available [here](docs/README.md).

- The [installation guide](docs/install.md) for technical details. 
- Have a look at the [Contribution Guide](CONTRIBUTING.md)
- [End-to-end documentation](docs/external_developers.md) on how to build skills
- [Working with Demo Skill](docs/articles/demo_skill.md)
- [Creating a Custom Weather Skill](docs/articles/weather_skill.md)

Requires Python 3.7! [Type hints](https://docs.python.org/3/library/typing.html) FTW!
* [PEP 526: Syntax for variable annotations](https://docs.python.org/3.6/whatsnew/3.6.html#whatsnew36-pep526)
* [PEP 484: Type Hints](https://docs.python.org/3.5/whatsnew/3.5.html#whatsnew-pep-484)

**Remark**

This repository uses the `*_test.py` naming schema. 
PyCharm discovers everything automatically, yet if you like to invoke unit tests from the command line, 
please use `scripts/test`.

### Quickstart

Make sure to have an current version of <a href="https://docs.python.org/3/">**Python 3**</a> (3.7 is minimum required)
and <a href="https://pip.pypa.io/en/stable/">**pip**</a> installed. Use
`apt-get install python3-pip` on Ubuntu (or any other Debian-based distro) or `brew install python3` on MacOS.

> _Note:_ Some distros might require `python3-venv` package installed.
> Run `apt-get install python3-venv` if you encounter difficulties when creating virtual environments for new projects. 

1. Clone the repo: `https://github.com/telekom/voice-skill-sdk.git`
2. Change to SDK dir: `cd voice-skill-sdk`
3. Run *new-skill* install:  `python setup.py new_skill`

> Alternatively, a one-liner for [@4thel00z](https://github.com/4thel00z)
>
> `pip download --no-deps --no-binary :all: skill-sdk && tar xzf skill-sdk-*.tar.gz && python skill-sdk-*/setup.py new_skill`
>


You'll be prompted for:
- The skill name. Give it an awesome Name! 
- Programming language. Python is awesome!
- The directory where the project will be created. Make sure it's writable. 

This script will:
- Create a new project in the directory of your choice.
- Add a virtual environment to `.venv` inside your project.
- Install required dependencies.
 
You may now open your skill directory as a project in PyCharm. 

> If you get an error `This package requires Python version >= 3.7 and Python's setuptools`, you happen to have an outdated Python version.
> Check it with `python --version` and make sure it is >= 3.7

*Happy coding!*

## Code of Conduct

This project has adopted the [Contributor Covenant](https://www.contributor-covenant.org/) in version 2.0 as our code of conduct. Please see the details in our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). All contributors must abide by the code of conduct.

## Working Language

We decided to apply _English_ as the primary project language.  

Consequently, all content will be made available primarily in English. We also ask all interested people to use English as language to create issues, in their code (comments, documentation etc.) and when you send requests to us. The application itself and all end-user facing content will be made available in other languages as needed.

## Support and Feedback
The following channels are available for discussions, feedback, and support requests:

| Type                     | Channel                                                |
| ------------------------ | ------------------------------------------------------ |
| **Issues**   | <a href="https://github.com/telekom/voice-skill-sdk/issues/new/choose" title="General Discussion"><img src="https://img.shields.io/github/issues/telekom/voice-skill-sdk?style=flat-square"></a> </a>   |
| **Other Requests**    | <a href="mailto:opensource@telekom.de" title="Email Open Source Team"><img src="https://img.shields.io/badge/email-Open%20Source%20Team-green?logo=mail.ru&style=flat-square&logoColor=white"></a>   |

## How to Contribute

Contribution and feedback is encouraged and always welcome. For more information about how to contribute, the project structure, as well as additional contribution information, see our [Contribution Guidelines](./CONTRIBUTING.md). By participating in this project, you agree to abide by its [Code of Conduct](./CODE_OF_CONDUCT.md) at all times.

## Contributors

Our commitment to open source means that we are enabling -in fact encouraging- all interested parties to contribute and become part of its developer community.

## Licensing

Copyright (c) 2020 Deutsche Telekom AG.

Licensed under the **MIT License** (the "License"); you may not use this file except in compliance with the License.

You may obtain a copy of the License by reviewing the file [LICENSE](./LICENSE) in the repository.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the [LICENSE](./LICENSE) for the specific language governing permissions and limitations under the License.
