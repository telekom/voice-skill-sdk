
# Skill Configuration Reference

Skill microservice has a number of configuration settings. These setting are stored in a configuration file, 
named `skill.conf` per convention. 

During a skill startup, the SDK searches this file in the following well-known locations: 
the current directory, parent directory, the container root and current users' home.

**Warning:**    While it is generally possible to import the global `config` object and modify its values **after** 
skill has already been started, it is highly recommended to treat the `config` as _immutable_, 
especially inside of an intent handler.

## File Format

Configuration file is expected to be in a basic configuration language similar to what’s found in Microsoft Windows INI files.
It consists of `[sections]` and `option = value` pairs.  

Option values can be expanded from environment variables if option is defined in the following format:   
```ini
option = ${ENV_VAR:default}
```

In the case above the option `option` will be assigned a value from `ENV_VAR` environment variable. 
If `ENV_VAR` variable is not set OR has a value that can be evaluated to boolean `False` by interpreter (0, ''), 
the option `option` will be assigned the value `default`.

## Sections

`skill.conf` consists of the following sestions:

### `[skill]` 

`[skill]` section describes basic skill parameters: skill name and version, 
name of the service (if different from skill name). For backward compatibility, it can contain the intent definitions
as JSON properties or as file glob.       

- **[skill] → name**: Name of the skill. It is the second element of the endpoint URL.
- **[skill] → version**: Skill version.
- **[skill] → id** (optional, default: name): Skill's ID as reported back on the `info` call.
- **[skill] → api_base** (optional, default: `/v1/<skill name>`): Base URL of endpoint.

#### Caller Authentication

A skill can validate incoming request using basic access authentication. If CVI 

- **[skill] → api_key**: API key is used as password in authorization header: `Authorization: Basic <cvi:api_key>`
- **[skill] → auth**: Authentication level (currently only `basic` is supported) 

#### Request Size

- **[skill] → max_request_size**: Maximum size of memory buffer for request body (in bytes). _new in v1.3.11_

**Example**

```ini
[skill]
name = my_first_skill
version = 1
id = myfirstskill

api_key = fbbf6768-000a-41c5-a63e-42b1566168e1
auth = basic

max_request_size = 1048576
```

### `[http]`

The `server` value in this section defines what WSGI server will be used to run the microservice.
It can be one of the servers supported by Python's [`bottle`](http://bottlepy.org/). 
All other parameters are forwarded to the server adapter.  
 
**Example**

```ini
[http]
server = gunicorn
port = 4242
workers = 1
threads = 2
```

### `[circuit_breakers]`

This section sets defaults for the `skill_sdk.circuit_breaker.SkillCircuitBreaker`:
You can configure the circuit breaker via the `skill.conf`:

- **[circuit_breakers] → threshold**: Recovery threshold - specifies number of failures to open the breaker
(5 failures by default).
- **[circuit_breakers] → timeout**: Recovery timeout in seconds (30 seconds by default).

**Example**

```ini
[circuit_breakers]
threshold = 5
timeout = 30
```

### `[requests]`

This section sets default values for `skill_sdk.requests.CircuitBreakerSession` object.

- **[requests] → timeout**: Connect timeout when requesting data using `CircuitBreakerSession` 
(5 seconds if not set).

**Example**

```ini
[requests]
timeout = 20
```

### `[zipkin]` 
To activate Zipkin reporter, add the following section to `skill.conf`:

- **[zipkin] → sample_rate**: How many intent calls are to be sampled (percentage). Has no effect ff the `X-B3-Sampled` header is set in the request.
- **[zipkin] → server_url**: Server URL to send spans to. 
- **[zipkin] → service_name**: The service name to be reported. If not set, falls back to `[service]` → `name` or `'unnamed_service'`. 

**Example:**

```ini
[zipkin]
sample_rate = 100
server_url = https://zipkin-skill-edge.smartvoicehub.de/api/v1/spans
service_name = your-service-name
```

### `[jaeger]` 
Activates Jaeger tracing client:

- **[jaeger] → service_name**: The service name to be reported. If not set, falls back to `[service]` → `name` or `'unnamed_service'`. 

**Example:**

```ini
[jaeger]
service_name = your-service-name
```

### `[service-text]`

The text service is configured in `[service-text]` section:

```ini
[service-text]
url = http://service-text-service:1555
active = [true | false]             (true)
auth_header = [false | true]        (false)
load = [startup | auto | delayed]   (startup)
```

The text services endpoint URL is set by `url` parameter. Default value for locally deployed skill is `http://service-text-service:1555`.

To explicitly deactivate the service, set the `active` parameter to `false`. Default value is `true`. So if you have just 
added the `[service-text]` section to your skill configuration file, the service is activated during the skill deployment.

If the `auth_header` value is `true`, an additional HTTP header `Authorization: Bearer {cvi_token}` is added to every request to the text services. 
This header is necessary if skill running outside of DTAG cloud wants to access the text services via device gateway.

The `load` parameter defines how the translations are loaded from the text services. 
`startup` is a default value: skill tries to load translations on startup and exists if text services are unavailable.
If set to `auto`, the skill runs with local translations and keeps trying to contact the text services. 
With `delayed` load the translations are requested on a first skill invocation.    

### `[service-location]`

The location service is configured in `[service-location]` section:

- **[service-location] → active**: Boolean value to activate/deactivate the location service (default is `true` ).
- **[service-location] → url**: The location services endpoint URL.

**Example:**

```ini
[service-location]
active = true
url = http://service-location-service:1555
```

### `[service-persistence]`

The persistence service is configured in `[service-persistence]` section:

- **[service-persistence] → active**: Boolean value to activate/deactivate the persistence service (default is `true` ).
- **[service-persistence] → url**: The persistence services endpoint URL.

**Example:**

```ini
[service-persistence]
active = true
url = http://service-persistence-service:1555
```

### `[tests]`

When using automated functional test facility, the default values for testing the intent handler can be overwritten in `[tests]` section the `skill.conf`.
For example, to test the skill with FREETEXT entity values `[None], ['Schlafzimmer'], ['Haupteingang']`, add this line to `skill.conf`:

```ini
[tests]
FREETEXT = [None], ['Schlafzimmer'], ['Haupteingang']
```

### `[uwsgi]`

You can run the skill using [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) server. 
That is what `[uwsgi]` section  is for. All parameters are forwarded to uWSGI server adapter.

**Example:**

```ini
[uwsgi]
http = :4242
workers = 2
gevent = 3
master = true
```
