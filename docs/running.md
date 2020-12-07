# Deploy the Skill

The skill can be deployed using one of the built-in web server adapters (Gunicorn, Tornado, [etc.](https://bottlepy.org/docs/dev/deployment.html)).
To simplify deployment, there is a `manage.py` script that can start the skill service and provides additional features.

Alternative option is to expose the application object to a WSGI-compatible server such as Google Application Engine or uWSGI.

## Deploy the skill with the `manage.py` script

To deploy the skill with `manage.py`, issue the command `python[3] manage.py run`

Hereafter, you find a full overview of the commands' syntax:

    python[3]  manage.py [-h] [-l] [-t] [-d] {run,test,version,translate}

	positional arguments:
	  {run,test,version,intents}
	    run                 Run the HTTP server
	    test                Runs tests
	    version             Print version
	    translate           Extract translations
	
	optional arguments:
	  -h, --help            show this help message and exit
	  -l, --local           use local services
	  -t, --dev             start in "development" mode
	  -d, --no-cache        disable local caches

### Subcommands (positional arguments)

#### Subcommand `run`

The subcommand `run` spawns the webserver and begins to serve the skill.

The following environmental variables modify the behavior:

- **`SPAN_TAG_ENVIRONMENT`**:  Sets the log depending on the deployment environment.
- **`LOG_FORMAT`**:  Sets the log format to GELF (JSON) or human readable (default: *"gelf"*, values: *"gelf", "human"*).
- **`LOG_LEVEL`**:  Sets the logging level (default: *"ERROR"* , values: *"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"*).
This environment variable overrides the log level set by **`SPAN_TAG_ENVIRONMENT`** variable.

>To stop the server, press `Ctrl` + `C`.

#### Subcommand `test`

`python[3] manage.py test` run unit tests suite (equivalent to `python[3] -m unittest discover -v -s tests -p "*_test.py"`)

`python[3] manage.py test -f` will run integrated functional tests along with unit tests (see [Test your skill](howtos/testing.md))  

#### Subcommand `version`

`python[3] manage.py version` prints the skill and SDK version.

### Optional arguments

#### Global argument `--help` (`-h`)

The global argument `--help` (`-h`) shows the help message.

#### Global argument `--local` (`-l`)

The global argument `--local` (or short `-l`) injects a proxy configuration into service REST calls. For further information, click [here](howtos/local_services.md).

#### Global argument `--dev` (`-t`)

The global argument `--dev` (or short `-t`) activates the development mode. 
This mode is using integrated WSGIRefServer for deployment so the micro-service can be developed in Windows environment.

#### Global argument `--no-cache` (`-d`)

Disable local cache adapters (intended mainly for debugging purposes) 

## Expose the application object to a WSGI-server

Some hosted environments or application servers can use the application object directly for deployment.
Here is an example of how to deploy the skill using the uWSGI application server:

1. Create the `app.py` script:
    ```python
    from skill_sdk.skill import initialize, intent_handler
    
    # Define your intent handlers:
    @intent_handler('My_Intent')
    def handle():
       ...
   
    # Create WSGI application object
    application = initialize()
    ```
2. Start uWSGI supplying `app.py` as `--wsgi-file` parameter:
    ```
    uwsgi --master --http :4242 --wsgi-file app.py
    ```
3. You can also use the skill configuration file `skill.conf` to configure uWSGI:
    ```ini
    [uwsgi]
    http = :4242
    workers = 2
    gevent = 3
    master = true
    ```
4. ... and use the configuration file when starting app server:
    ```
    uwsgi --ini skill.conf --wsgi-file app.py
    ```
