# File Structure of a Skill

## Folders and files of a skill project

A skill project contains the following folders and files:

    my_first_skill
    ├── impl
    │   └── __init__.py
    │   └── main.py
    ├── locale
    │   └── catalog.pot
    │   └── de.mo
    │   └── de.po
    ├── scripts
    │   ├── run
    │   ├── test
    │   └── version
    ├── tests
    ├── Dockerfile
    ├── manage.py
    ├── README.md
    └── requirements.txt
     
## Detailed information about specific folders and files

### `skill.conf`
        
The `skill.conf` file is the main configuration file for the microservice. See [Configuration Reference](config.md)

### `impl/`

In the `impl/` directory you can store your implementations.
Every implementation should be a Python function with the following signature:

    @intent_handler("HELLO_INTENT")
    def name_of_your_choice(context: Context, …) -> Response:
    
> `...` is a list of attributes the intent has.

**Example**

Valid signature if the intent has the attributes `location` and `date`:

    @intent_handler("WEATHER_STATUS")
    def weather_by_data(context: Context, location: Location, date: datetime.date) -> Response:
    
The actual values are injected into the keyword arguments.

### `locale/`

In the `locale` folder you can store your `gettext` translation files.
Name them `<locale>.mo`.
The element `<locale>` is the code of the locale as transmitted by the dialog manager (for example `de` or `de_DE`).

### `scripts/` 

The `scripts` folder contains some files that you need inside the Docker container.

### `tests/`

In the `tests/` folder you can store the unit tests for the unit test runner.

Use the `*_test.py` schema for naming. PyCharm discovers everything automatically. 

>If you want to invoke unit tests from the command line, check the `scripts/test/` folder.

The tests are executed during deployment and when `manage.py test` is called.

### `manage.py`

The `manage.py` script starts the skill service and provides some helper functions. For further information, click [here](running.md).

### `requirements.txt`

In the `requirements.txt` file you define your skills dependencies that the SDK does not cover.
This file is in the format as dumped by `pip freeze`.

>Pin the versions of dependencies. For example, use the `==` operator an the version number.

### `tokens.json` (optional)

If your skill requires static authentication tokens during run-time, 
you can place them to `tokens.json` file in a project root.

The file is expected to contain a JSON object with tokens as keys:

```json
{
  "oauth2": "eyJ..."
}
```

The tokens will be loaded during skill deployment and exposed to a skill as `config.tokens`:

```
>>> from skill_sdk.config import config
>>> config.tokens
{'oauth2': 'eyJ...'}
```
