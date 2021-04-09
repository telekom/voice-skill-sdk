
# Skill Configuration Reference

Skill application has a number of configuration settings, 
these are made available as attributes of `skill_sdk.config.settings` object.

When you import this object in your code, the model constructor will attempt to determine the values of any fields 
not passed as keyword arguments by reading from the environment. 

(Default values will still be used if the matching environment variable is not set.)

## Settings

- **settings.API_BASE**: Base path of the skill API. If not set, defaults to `/v<skill version>/<skill name>`.
  

- **settings.SKILL_NAME**: Name of the skill. It is the second element of the endpoint URL. 
  Default: "skill-noname".
  

- **settings.SKILL_TITLE**: Skill title to be shown in Swagger UI. 
  Default: "Magenta Skill SDK Python".
  

- **settings.SKILL_DESCRIPTION**: Long skill description to be shown in Swagger UI. 
  Default: "Magenta Voice Skill SDK for Python".


- **settings.SKILL_VERSION**: Skill version. Default: "1".


- **settings.SKILL_DEBUG**: Boolean value identifying if skill runs in debug mode. Default: False.


### Basic Authentication

- **settings.SKILL_API_USER**: Text string identifying the user. Default: "cvi".


- **settings.SKILL_API_KEY**: Text string identifying the password. Default: none, 
  if value is empty, skill routes will not require authentication. 


### Default HTTP Port

- **settings.HTTP_PORT**: Integer value to set the HTTP port for the service. Default: 4242.


### Health Endpoints

- **settings.K8S_READINESS**: Kubernetes readiness probe endpoint. Default: "/k8s/readiness".


- **settings.K8S_LIVENESS**: Kubernetes liveness probe endpoint. Default: "/k8s/liveness".


### Metrics Endpoints


- **settings.PROMETHEUS_ENDPOINT**: Prometheus metrics scraper endpoint. Default: "/prometheus".


### Requests 


- **settings.REQUESTS_TIMEOUT**: Float value to set a default timeout (in seconds) 
  when requesting data with `skill_sdk.request.Client/AsyncClient`. Default: 5 (seconds).

### Logging Settings

- **settings.LOG_FORMAT**: Logging record format, either "human" for human-readable form, 
  or "gelf" for JSON GrayLog-compatible form. Default: "gelf".


- **settings.LOG_LEVEL**: Logging level. Default: logging.DEBUG.


- **settings.LOG_ENTRY_MAX_STRING**: Maximal length of a string field in the log record. Default: 150.


## Custom Settings

Custom setting can be added inheriting the `skill_sdk.config.Settings` class:

```python
from skill_sdk.config import Settings

class MySettings(Settings):

    MY_PARTNER_SERVICE_URL: str = "https://partner-service.com" 
```

Now when you instantiate `MySettings` class in your code, 
`MY_PARTNER_SERVICE_URL` value is read from the environment, 
or defaults to "https://partner-service.com" if no environment variable with such a name exists.    

## ConfigParser File

For backward compatibility, the configuration setting can be read from a configuration file, 
named `skill.conf` per convention. The file is expected to be in a format similar to what’s found in Microsoft Windows INI files.

It consists of `[sections]` and `option = value` pairs.  

Option values can be expanded from environment variables if option is defined in the following format:   
```ini
option = ${ENV_VAR:default}
```

In the case above the option `option` will be assigned a value from `ENV_VAR` environment variable. 
If `ENV_VAR` variable is not set OR has a value that can be evaluated to boolean `False` by interpreter (0, ''), 
the option `option` will be assigned the value `default`.

When you import `skill_sdk.config.settings` object, the SDK searches this file in the current directory 
(or the container root), and reads its content, joining section names with option keys using underscore ("_") symbol, 
replacing dashes with underscores and converting the result to upper case.

> **Note**: Settings from `skill.conf` file will replace those defined in `skill_sdk.config.Settings` class 

### Sections

`skill.conf` consists of the following sections:

#### `[skill]` 

`[skill]` section describes basic skill parameters: skill name, version, title, etc.

- **[skill] → name**: Name of the skill. Becomes **settings.SKILL_NAME**.
- **[skill] → title**: Skill title. Becomes **settings.SKILL_TITLE**.
- **[skill] → description**: Long skill description. Becomes **settings.SKILL_DESCRIPTION**.
- **[skill] → version**: Skill version. Becomes **settings.SKILL_VERSION**. 
- **[skill] → debug**: Run the server in debug mode. Becomes **settings.SKILL_DEBUG**.
- **[skill] → api_key**: Skill API key. Becomes **settings.SKILL_API_KEY**.

#### `[http]`

The value in this section are forwarded to the ASGI server adapter.  
 
**Example**

The value defined here:

```ini
[http]
port = 4242
```

... becomes **settings.HTTP_PORT**.
 