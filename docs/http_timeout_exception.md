# HTTP Timeout Exception for not responding external Services

The HTTP timeout exception may occur while trying to connect to the remote server within a specified amount of time without success. 
It is also possible that the server did not send any data in the allotted amount of time.

There is a default timeout of 5 seconds for HTTP requests that do not respond. This is implemented within the special session object `CircuitBreakerSession`.

To overwrite the default value, pass it as keyword argument:

```python
with CircuitBreakerSession() as session:
    session.get('http://service-text-service/api/v1/...', timeout=10)
```

In case you do not use the special session object `CircuitBreakerSession`, set a timeout.

You can also set a request timeout globally in [skill.conf](config.md) (`[requests]` section).

