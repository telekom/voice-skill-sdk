
# Changelog
All notable changes to this project will be documented in this file.

## [v0.10.4] - 2021-01-19  

**Features**

-   `skill->debug` [config option](docs/config.md#skill) is introduced. 
    Skill running with _debug_ **on** returns exception details and traceback in a response. 
    Starting the skill in development mode activates the _debug_ flag.    

**Bugfixes**

-   Add `skill_genedrator` package to the source distribution.
    
-   Remove `__add__/__radd__` magic from "l10n.Message" as confusing.

**Miscellaneous**

-   Rewrite [installation guide](docs/install.md).

-   Log debug messages when running `install/new_skill` commands (suppress with standard `--quiet (-q)`) parameter.


## [v0.10.3] - 2021-01-13  

**Bugfixes**

- Disable `l10n.Message` dictionary serialization in response.  
  
## [v0.10.2] - 2021-01-06  

**Bugfixes**

- Development/production requirements merged for backward compatibility with existing CI/CD pipelines.  
  
## [v0.10.1] - 2021-01-04  

**Miscellaneous**

- Swagger UI is updated to v3.38.0 
  
- Requirements bump:
    - coverage from 5.3 to 5.3.1
    - gevent from 20.9.0 to 20.12.1
    - opentracing from 2.3.0 to 2.4.0  
    - requests from 2.25.0 to 2.25.1

## [v0.10.0] - 2020-12-18  

**Features**

-   Client kits and actions API added to the responses.

**Bugfixes**

-   Log an error if device timezone is missing or invalid in intent context.
    Sample configuration added to [context.md](docs/context.md). 

-   Fix card attribute names conversion from snake_case to camelCase.

**Miscellaneous**

-   Skill SPI has been bumped to version 1.2. 

## [v0.9.2] - 2020-11-27  

**Bugfixes**

-   Add Pycharm project and run-time configurations to skill template.


## [v0.9.1] - 2020-11-24  

**Bugfixes**

-   Thread-local request leak closed.


## [v0.9.0] - 2020-11-13 

Initial release
