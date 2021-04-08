
# Circuit Breakers and Tracing

## Circuit breakers

If the service fails several times in a row (the call raises an exception or results in a response code >= 400), circuit breakers disable an external service temporarily.

### How a circuit breaker works

If an execution fails a given number of times in a row, the circuit breaker opens. In this case, all the calls that are protected by it are not executed. Instead, a `CircuitBreakerError` raises.

After a given time, the circuit breaker changes into half-open mode and allows one execution.
If this execution succeeds, the circuit breaker closes. If the execution fails, the circuit breaker opens again.

### Default vs. special circuit breakers

By default, there is one circuit breaker instance by skill as  `skill_sdk.circuit_breaker.DEFAULT_CIRCUIT_BREAKER`.
You can configure the circuit breaker via the `skill.conf`:

    [circuit_breakers]
    threshold = 5
    timeout = 30

You can set the circuit breaker as follows:

- **threshold**: Sets how many failed executions in a row open the circuit breaker.
- **timeout**: Sets after how many seconds the circuit breaker goes into half-open state.

Usually, it is not desirable to have only one circuit breaker for all executions in a skill. Therefore, create multiple instances of `skill_sdk.circuit_breaker.SkillCircuitBreaker`.
This is a subclass of `CircuitBreaker`. For futher information, click [here](https://github.com/fabfuel/circuitbreaker).

### Simple integration with requests library

You can use a special session object as a replacement for the session in requests:

    from skill_sdk.requests import CircuitBreakerSession
    
    with CircuitBreakerSession() as session:
        session.get('http://localhost/')
        
This session replacement also provides Zipkin integration and reports the HTTP calls to a zipkin server.

The class accepts four optional arguments on instantiation:

- **internal**: The session calls our internal services only (do not use this argument for external calls). This argument does not add Zipkin headers to HTTP requests.
- **circuit_breaker**: Use this `CircuitBreaker` instance instead of the default one.
- **good_codes**: These HTTP response codes are considered good.
- **bad_codes**: These HTTP response codes are considered bad. They raise a `BadHttpResponseCodeException` that triggers the ciruit breaker. The `bad_codes` are only taken into account if `good_codes` is *not* set.

Both, `good_codes` and `bad_codes`, can be given as `tuple` or `int` and `range()` items or a single `range()`.

### Usage of circuit breakers as a decorator

You can use any circuit breaker instance as a decorator.

**Example**

    my_circuit_breaker = CircuitBreaker()
    
    @my_circuit_breaker
    def some_service_call():
        pass

## Tracing

Skill SDK for Python is equipped with [opentracing](https://opentracing.io/docs/overview/what-is-tracing/) adapter
to support distributed tracing and logging.

Tracing spans are automatically created for the whole intent call and `CircuitBreakerSession`.
For more detailed tracing, it might be desirable to add additional sub-spans.

#### Start span as decorator

To start a new span with function call, decorate the function with @start_span decorator:

    from skill_sdk.tracing import start_span

    @start_span(span_name='fancy name')
    def your_function():
        pass

Replace *fancy_name* with a useful name to identify the span.

The span covers the execution of the decorated function until it returns.

#### Start span as context manager

If the intent call `context` is available, you can start a tracing span with:

    with context.tracer.start_span('fancy_name') as span:
        pass

In any other case, the call is similar to the decorator:

    with start_span(span_name='fancy name') as span:
        pass

The span covers the execution of the code in the `with` block.

#### Adding additional information to trace

When the span is created in a context manager, it is available as the variable named via `as span` in the examples above.
You can add additional information to the span via tags. A tag is a key-value pair that provides certain metadata about the span
that apply to the whole duration of the span.

For example, if a span represents a HTTP request, the URL of the request should be recorded as a tag because it remains constant throughout the lifetime of a span.

To add tags, use `span.set_tag(key, value)` function:

    span.set_tag('http_status_code', str(result.status_code))

You can also log key-value data to a span and have it associated with a particular timestamp:

    span.log_kv({'event': 'token_check_done'}, time.time())

A log is similar to a regular log statement, it contains a timestamp and some data, but is associated with span from which it was logged.

## Tracing Clients

Skill SDK for Python supports two tracing client implementations: Zipkin and Jaeger.  

### Zipkin

To activate Zipkin reporter, add the following section to `skill.conf`:

    [zipkin]
    sample_rate = 100
    server_url = https://zipkin-skill-edge.smartvoicehub.de/api/v1/spans
    service_name = your-service-name

If sample rate set to `100`, 100% percent of spans will be sampled and reported.
To decrease high volume of tracing in a high-load web application, lower the sampling percentage.

Server url defaults to `http://zipkin.opentracing.svc.cluster.local:9411/api/v1/spans` if not overwritten by the config.

Tracing spans will be automatically reported to the zipkin server.

### Jaeger

To activate Jaeger client, add the following section to `skill.conf`:

    [jaeger]
    service_name = your-service-name

Client configuration can be set by [environment variables](https://github.com/jaegertracing/jaeger-kubernetes#configure-udphttp-senders). 
