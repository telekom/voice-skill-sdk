# How to Use Web Services

In microservice architecture, a rare skill would work standalone without receiving data from other web services. 
Skill SDK for Python includes a number of patterns to simply access to external, internal or partner REST services.


## HTTP Client

To request and receive data from REST services, Skill SDK for Python incorporates an HTTP client with a circuit breaker support. 
The client is based on [httpx](https://www.python-httpx.org/) and supports HTTP/1.1 and can optionally support HTTP/2.0 protocols.

A circuit breaker allows shortening response times, in case the service is unavailable, 
and works like a real electrical circuit breaker: a client would try to connect to the service number of times (default 5), 
and in case of a failure, open the circuit breaker, so that all consequential connection attempts will fail fast, 
without even trying to access the service. After a timeout period (default to 60 seconds), 
the circuit breaker gets closed and connection attempts re-tried.

Additional feature of the client is that if a service is flagged as _internal_, 
distributed tracing headers (if present) are extracted from the parent request and propagated to the service request.

### Sync Client

Instantiates a client:

```python
    def __init__(
        self,
        *,
        internal: bool = False,
        circuit_breaker: CircuitBreaker = None,
        timeout: Union[int, float] = None,
        exclude: Iterable[codes] = None,
        response_hook: Callable[[httpx.Response], None] = None,
        **kwargs,
    ) -> None:
        ...
```

- **internal**: flags the client as requesting the data from _internal_ service, to propagate tracing headers.
- **circuit_breaker**: circuit breaker instance that client will use, 
  will be created with defaults: `fail_max=5`, `timeout_duration=60` (seconds).   
- **timeout**: request timeout, default: 5 seconds. 
- **exclude**: optional iterable, listing HTTP response codes that will be treated as "normal", without raising an exception. 
- **response_hook**: optional callable, will be called when response is received, with the response as parameter. 
- **kwargs**: other keyword parameters will be passed directly to parent `httpx.Client` constructor.

To instantiate clients with a shared circuit breaker:

```python
from datetime import timedelta
from skill_sdk.requests import Client, CircuitBreaker

# A circuit breaker that will allow 1 failed request before getting open, 
#   and reset to closed after 30 seconds
cb = CircuitBreaker(fail_max=1, timeout_duration=timedelta(seconds=30))

with Client(circuit_breaker=cb) as c:
    response = c.get('http://www.example.org/')

# If previous request fails, this will fail fast without waiting:
with Client(circuit_breaker=cb) as c:
    response = c.get('http://www.example.org/service')
```

> **Note:** if do not supply a circuit breaker when constructing the client, 
> it will be instantiated internally, and will only make sense for **this** particular client **instance**.


To propagate tracing headers when calling the service and ignore HTTP NOT_FOUND (404) errors:

```python
from skill_sdk.requests import codes, Client 

with Client(internal=True, exclude=(codes.NOT_FOUND,)) as c:
    response = c.get('http://www.example.org/')
```

### AsyncClient

An instance of `AsyncClient` is created with the same parameters as its synchronous counterpart.   
On the surface it also behaves pretty similar, with an exception that it can be used in `async with` operator, 
and all operations can be `await`'ed, so it must be used within a coroutine.

Here is a previous simple example used in asynchronous context:

```python
from skill_sdk.requests import codes, Client 

async def example():
  async with Client(internal=True, exclude=(codes.NOT_FOUND,)) as c:
      return await c.get('http://www.example.org/')
```


## Service Base

Other useful pattern is present in `skill_sdk.services.base` module: `class BaseService` - a base class, 
describing adapter to access internal cloud services. It can be reused to describe interface adapters to any REST service as well.      

Base service constructor signature:

```python
    def __init__(
        self,
        url: Text,
        *,
        internal: bool = True,
        timeout: float = DEFAULT_SERVICE_TIMEOUT,
        headers: Dict[Text, Text] = None,
        add_auth_header: bool = None,
        auth_token: Text = DEFAULT_AUTH_TOKEN,
    ) -> None:
        ...
```

- **url**: base URL to the service.
- **internal**: flags the service as _internal_ to propagate tracing headers.
- **timeout**: service request timeout, default: 5 seconds. 
- **headers**: custom headers (*). 
- **add_auth_header**: boolean flag used in conjunction with the next parameter telling that an authentication token
  should be fetched from the skill invoke request and propagated to "Authorization: Bearer <token>" header. 
- **auth_token**: skill [invoke request](https://htmlpreview.github.io/?https://raw.githubusercontent.com/telekom/voice-skill-sdk/blob/master/docs/skill-spi.html#_invokeskillrequestdto) may contain bearer token for authentication.
  This parameter tells the dictionary key to find the token in [request's context](https://htmlpreview.github.io/?https://raw.githubusercontent.com/telekom/voice-skill-sdk/blob/master/docs/skill-spi.html#_skillcontextdto).
  Default value is "cvi", configured in [skill manifest](skill_manifest.md#cvi).

> (*) Custom headers would overwrite the defaults:
> ```json
> {
>   "Accept": "application/json",
>   "Content-Type": "application/json"
> }
> ```


### Base Service Clients

The class defines two read-only property attributes: `BaseService.client` and `BaseService.async_client` that are
instances of [Client](#sync-client) and [Async Client](#asyncclient) correspondingly.

Both clients share a circuit breaker defined on the service instance level, 
so that **all** requests to the service use the same breaker.  

Sample usage:

```python
from skill_sdk.services.base import BaseService

service = BaseService("http://my-service.com")

def get():
    with service.client as c:
        return c.get("/data").json()

```

with async client:

```python
async def get():
    async with service.async_client as c:
        data = await c.get("/data")
        return data.json()
```


### Example: Weather Service

In this example, we are going to write an adapter to [openweathermap.com](https://openweathermap.org/) [API](https://openweathermap.org/api).

Consider two endpoints available for free accounts:

- Current weather data: `api.openweathermap.org/data/2.5/weather?q={city name}&appid={API key}`

- 5 days forecast: `api.openweathermap.org/data/2.5/forecast?q={city name}&appid={API key}`

We define the adaptor with two methods corresponding to each endpoint:

```python
from skill_sdk.services.base import BaseService


class OpenWeather(BaseService):

    APP_ID = "<secret-app-id>"

    def __init__(self):
        super().__init__("https://api.openweathermap.org/data/2.5")

    def params(self, city: str):
        return dict(appid=self.APP_ID, q=city)
    
    async def current(self, city: str):
        async with self.async_client as client:
            return (
                await client.get("weather", params=self.params(city))
            ).json()

    async def forecast(self, city: str):
        async with self.async_client as client:
            return (
                await client.get("forecast", params=self.params(city))
            ).json()
```

Sample usage:

```
>>> weather = OpenWeather()
>>> import asyncio
>>> asyncio.run(weather.current("Wien"))
{'coord': {'lon': 16.3721, 'lat': 48.2085}, 'weather': [{< skipped >}]}
```
