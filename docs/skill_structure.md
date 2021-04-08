# File Structure of a Skill

## Folders and files of a skill project

A skill project consists of the following folders and files:

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
    ├── app.py
    ├── README.md
    └── requirements.txt
     
## Detailed information about specific folders and files

### `skill.conf`
        
`skill.conf` file is the main configuration file for the microservice. See [Configuration Reference](config.md)

### `impl/`

`impl/` folder is the default location for intent handlers.

### `locale/`

`locale` folder is a default location for translation files.

### `scripts/` 

The `scripts` folder contains the helper scripts.

### `tests/`

`tests/` folder contains your unit tests.

### `app.py`

`app.py` contains your skill application instance.

### `requirements.txt`

In the `requirements.txt` file you add your skills dependencies.

> Pin the versions of dependencies: use the `==` operator, and the version number.
