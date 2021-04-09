# Deploying the Skill

Suppose, we have a "Hello, World!" skill defined in `app.py`:

```python
from skill_sdk import skill, Response

@skill.intent_handler("HELLO_INTENT")
def hello() -> Response:
    return Response("Hello, World!")

app = skill.init_app()
app.include(handler=hello)
```

Deploy the skill with built-in [Uvicorn](https://www.uvicorn.org/) server:

`vs run app.py`

Here is a sample startup log (beginning of the log is skipped for readability):
```log
...
INFO:     Started server process [11175]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:4242 (Press CTRL+C to quit)
```

# Deploying with Gunicorn

[Gunicorn](https://gunicorn.org/) is the simplest way to deploy the skill in a production setting. 
Uvicorn includes a gunicorn worker class that means you can get set up with very little configuration.

Deploy the skill with Gunicorn on port 4242 using two workers:

`gunicorn -b :4242 -w 2 -k uvicorn.workers.UvicornWorker app:app`

The sample startup log, notifying about successful startup:

```
[2021-04-09 10:14:42 +0200] [12520] [INFO] Starting gunicorn 20.1.0
[2021-04-09 10:14:42 +0200] [12520] [INFO] Listening at: http://0.0.0.0:4242 (12520)
[2021-04-09 10:14:42 +0200] [12520] [INFO] Using worker: uvicorn.workers.UvicornWorker
[2021-04-09 10:14:42 +0200] [12522] [INFO] Booting worker with pid: 12522
[2021-04-09 10:14:42 +0200] [12523] [INFO] Booting worker with pid: 12523
[2021-04-09 10:14:42 +0200] [12522] [INFO] Started server process [12522]
[2021-04-09 10:14:42 +0200] [12522] [INFO] Waiting for application startup.
[2021-04-09 10:14:42 +0200] [12522] [INFO] Application startup complete.
[2021-04-09 10:14:42 +0200] [12523] [INFO] Started server process [12523]
[2021-04-09 10:14:42 +0200] [12523] [INFO] Waiting for application startup.
[2021-04-09 10:14:42 +0200] [12523] [INFO] Application startup complete.
```

# Development Mode

Deploy the skill in _development mode_ with built-in [Uvicorn](https://www.uvicorn.org/) server:

`vs develop app.py`
