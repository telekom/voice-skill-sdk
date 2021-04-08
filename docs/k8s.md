# Kubernetes Integration

## Kubernetes liveness and readiness probes

You find the skill support "Kubernetes liveness and readiness probes" at the following endpoints:

- `/k8s/liveness`
- `/k8s/readiness`

At this point, the liveness endpoint always returns `alive` with the status code `200`. If the skill notices it got in a state
where it can not answer requests, it dies.

If the skill is ready, the readiness probe returns `ready` with the status code `200`. If the skill is not ready to handle requests, it returns the status code `503` (service unavailable) and a list of the active readiness locks in the body.

## Defining readiness locks

Register a code that has to complete successfully before startup to the `K8sChecks` class. You can either do that via a decorator or manually.

### Register a code via a decorator

A function or method decorated with the `RequiredForReadiness` decorator activates the readyness lock on entry.
If the function is left properly, the lock will be released.

>If the function is left because an exception is raised, the lock will **not** be released!

**Example**

    from skill_sdk.decorators import RequiredForReadiness
    
    @RequiredForReadiness('name_for_the_lock')
    def load_something():
        'your code'
        
The parentheses are important and must not be left out. On the other hand, you can omit the name. Then, a UUID is generated.
This UUID might be less helpful when debugging readiness locks.

### Register a code manually

Alternatively, you can register the lock manually and, when finished, report that it is ready.

**Example**

     from skill_sdk.k8s import K8sChecks
     
     K8sChecks.register_ready_check('name_for_the_lock')
     
     'your code'
     
     K8sChecks.report_ready('name_for_the_lock')
     
This procedure also allows you to do special error handling for your code by using a `try` / `except` / `finally` block.