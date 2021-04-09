<h1 align="center">
    Magenta Voice Skill SDK
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

Magenta Voice Skill SDK for Python is a package that assists in creating Voice Applications for Magenta Voice Platform.

## About

This is a reworked stack with explicit `async/await` concurrency 
and based on [**FastAPI**](https://fastapi.tiangolo.com/) ASGI framework.

Old stable (Bottle/Gevent) [0.xx branch](https://github.com/telekom/voice-skill-sdk/tree/stable)

## Installation

### Runtime
Runtime installation: `python -m pip install skill-sdk`.

### Runtime (full)
Runtime installation with Prometheus metrics exporter and distributed tracing adapter: `python -m pip install skill-sdk[all]`.

### Development
Development installation: `python -m pip install skill-sdk[dev]`.

## Quickstart
To bootstrap a new project, install SDK for development:
```
pip install skill-sdk[dev]
```

Initialize a new project with `vs` command:
```
vs init
```

Run the skill in development mode:
```
vs develop
```

Click [http://localhost:4242](http://localhost:4242) to access Designer UI.


## Hello World

```python
from skill_sdk import skill, Response


@skill.intent_handler("HELLO_WORLD__INTENT")
async def handler() -> Response:
    return Response("Hello World!")

app = skill.init_app()

app.include(handler=handler)
```

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

Copyright (c) 2021 Deutsche Telekom AG.

Licensed under the **MIT License** (the "License"); you may not use this file except in compliance with the License.

You may obtain a copy of the License by reviewing the file [LICENSE](./LICENSE) in the repository.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the [LICENSE](./LICENSE) for the specific language governing permissions and limitations under the License.
