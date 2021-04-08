# How to make HTTP Requests

In our distributed microservice architecture, certain technical requirements allow the operators and us to trace calls through the system and to respond smartly to errors.

This includes tracing with the help of Zipkin and the use of circuit breakers. They prevent long running failing calls to not responsive systems.

## Implementation in the SDK

The Python SDK already incorporates Zipkin tracing and circuit breakers. For further information, click [here](../tracing.md).

In order to simplify making HTTP and HTTPS calls to other systems while fulfilling these requirements, a wrapper around 
the `request` library has been included as `skill_sdk.requests.CircuitBreakerSession`. 
It is an enhanced replacement for the `session` from the requests library and you can use it the same way.

## A simple request

In the following, a simple request in a session is shown.

```python
from skill_sdk.requests import CircuitBreakerSession

with CircuitBreakerSession() as session:
    response = session.get('http://www.example.org/')
```

This commands open a session that handles the relations between calls (like cookies) automatically as long as you are in the `with` block.
You can see all features of the session and requests in general in the [Requests Documentation](http://docs.python-requests.org/en/latest/user/advanced/). 

In the following, you find a few features that extend the `CircuitBreakerSession`:

### Circuit breakers

A circuit breaker secures every call in the session. Because it is not useful to start a session that is going to fail (that might lead to inconsistencies only), the circuit breaker is the same for the whole session.

By default, the `DEFAULT_CIRCUIT_BREAKER` of the skill is used. But it is possible to use another one.
To use another circuit breaker, give `SkillCircuitBreaker` instance as the `circuit_breaker` keyword argument.

**Example**

 ```python
from skill_sdk.circuit_breaker import SkillCircuitBreaker
from skill_sdk.requests import CircuitBreakerSession

my_own_circuit_breaker = SkillCircuitBreaker(failure_threshold=10)

with CircuitBreakerSession(circuit_breaker=my_own_circuit_breaker) as session:
    response = session.get('http://www.exaple.org/')
```

> Do not to use a new circuit breaker for every session. It will not do its job then.

### Zipkin traces

A Zipkin span surrounds all HTTP calls automatically.

#### Sending Zipkin header

To have Zipkin related headers included, internal services require the HTTP reuqest.
When the keyword argument `internal` is true, this happens automatically.

**Example**

```python
with CircuitBreakerSession(internal=True) as session:
    session.get('http://service-text-service/api/v1/...')
```

>Do not make internal and external calls in one session!

## Error code handling

To get the circuit breakers to work requires that a failing request raises an exception.

This is not the `default` for the requests library, so the `CircuitBreakerSession` includes an error handler that
raises an error on request with a response code in the 4xx and 5xx area.

This behaviour can be fine-tuned with the `good_codes` and `bad_codes` keyword arguments.
Both accept an iterable of integers (for example `[400, 403]` or `range(400, 500)`).

If `good_codes` is set and "truthy", only these codes are accepted. Other ones raise an exception.
If `good_codes` are not set or not "truthy", any code in `bad_codes` raises an exception.

**Examples**

Accept only 200:

```python
with CircuitBreakerSession(good_codes=[200]) as session:
    session.get('http://service-text-service/api/v1/...')
```

Raise on all codes between 500 and 599:

```python
with CircuitBreakerSession(bad_codes=range(500, 600)) as session:
    session.get('http://service-text-service/api/v1/...')
```

## Timeout

If you do not set an explicit time for a request, the `CircuitBreakerSession` adds a timeout of 5 seconds.

To overwrite the default timeout of 5 seconds, proceed as shown below:

```python
with CircuitBreakerSession() as session:
    session.get('http://service-text-service/api/v1/...', timeout=10)
```

## Header based caching

Caching that bases on HTTP headers is done automatically.
By default, the cached elements are stored in a 1000 items `CacheControlLocalLRUCache`.

You have the option to overwrite the size. To do so, set `skill_sdk.requests.DEFAULT_HTTP_CACHE.max_size`.

You can also use a different cache. To do so, supply another `CacheControlLocalLRUCache` instance as the `cache` argument to
a `CircuitBreakerSession`.

>Share one instance between requests. If you create a new instance for every request, no caching can take place.

## Useful hints

>Always use the `CircuitBreakerSession`. 

>Do not use the session from requests for the `get()`, `post()` and so on convenience functions.

>Do not forget to instantiate the session `CircuitBreakerSession` → `CircuitBreakerSession()`.
