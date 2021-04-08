# Serverless Deployment 

You can deploy your skill to a serverless environment such as [Amazon Lambda](#deploy-to-amazon-lambda-using-zappa) or 
[Azure Function](#deploy-as-azure-function).
 
## Deploy to Amazon Lambda using Zappa

[Zappa]((https://github.com/Miserlou/Zappa)) makes it trivial to build a serverless application from an existing WSGI code (that is your skill) 
and publish it to AWS Lambda and Amazon API Gateway.

The steps below imply that you have already installed and configured the [AWS shell](https://github.com/awslabs/aws-shell) 

1. Install [zappa](https://github.com/Miserlou/Zappa) in your virtual environment:
   ```bash
   pip install zappa 
   ```
   
2. Initialize WSGI application object similar to [exposing to a WSGI server](running.md#expose-the-application-object-to-a-wsgi-server):
    ```python
    import pathlib
    from skill_sdk import skill, tell

    skill.intent_handler('HELLO_INTENT')
    def handle():
       return tell('Hello!')
       
    APP_ROOT = pathlib.Path(__file__).absolute().parent.parent

    # This statement creates "my_skill" WSGI application
    my_skill = skill.initialize(APP_ROOT / 'skill.conf')
    ```

3. Create zappa project with `zappa init` and set **app_function** (*Where is your app's function?* question) 
to point to your `my_skill` application.
    Resulting `zappa_settings.json` should look like:
    
    ```json
    {
        "dev": {
            "app_function": "impl.main.my_skill",
            "profile_name": null,
            "project_name": "skill-development",
            "runtime": "python3.7",
            "s3_bucket": "zappa-wbgz6o9jb",
            "slim_handler": true
        }
    }
   
4. `zappa deploy` to deploy your skill to Amazon Lambda!
    > Your updated Zappa deployment is live!: https://xxxxxxxxxx.execute-api.eu-central-1.amazonaws.com/dev

## Deploy as Azure Function

Deployment as an Azure Function is quite similar to [Lambda](#deploy-to-amazon-lambda-using-zappa): you 
still need to create and publish your skill as WSGI application. Yet Functions have some quirks with standard 
API endpoints and there is no *zappa-like* tool to help you. 

1. Make sure to install the latest version of [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
and [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local) (minimal version is 1.2.0)

2. Initialize your project for Azure issuing `func init --python`.
This will create `host.json`, `local.settings.json` and `.funcignore` files in your project root.
You may want to add some files that are irrelevant for function deployment to `.funcignore`:
    ```
    scripts/
    tests/
    .venv/
    **/__pycache__/
    ```

3. Next step would be defining your endpoint using `func new --name impl --template "HTTP trigger"`, 
unfortunately this procedure overwrites the whole `impl` folder where your intents handlers are. 
So you should manually create `impl/function.json` 
(supposing that your skill and intent handlers are in `impl/main.py`):

    ```json
    {
      "scriptFile": "main.py",
      "bindings": [
        {
          "authLevel": "function",
          "type": "httpTrigger",
          "direction": "in",
          "name": "req",
          "methods": [
            "get",
            "post"
          ],
          "route": "{info:alpha?}"
        },
        {
          "type": "http",
          "direction": "out",
          "name": "$return"
        }
      ]
    }
    ```

4. Azure environment is dynamically created during the deployment and Skill SDK for Python is not available for
general public (and hence not on [PyPI](https://pypi.org/)), 
so you need to copy the wheel (`skill_sdk-0.9.0-py3-none-any.whl`) to your project root
and change `requirements.txt` to install the SDK directly from the wheel file:
    ```
    azure-functions==1.2.0
    skill_sdk-0.9.0-py3-none-any.whl
    ```

5. Azure Functions Python library defines `WsgiMiddleware` class that can wrap a WSGI application and expose it 
as Azure Function-compatible object:

    ```
    import azure.functions as func

    APP_ROOT = pathlib.Path(__file__).absolute().parent.parent
    
    # This section exposes "main" object to Azure functions
    my_skill = skill.initialize(APP_ROOT / 'skill.conf')
    main = func.WsgiMiddleware(my_skill).main
    ```

6. Skill's default SPI endpoint is `/v1/<skill-name>` while Azure Functions expects it at `/api`. 
You can change the default endpoint with a setting in `skill.conf`:
    ```
    [skill]
    api_base = /api
    ```

7. Test your skill locally with `func host start`

The skill is ready to be published. Make sure you have defined the function either in 
[Azure portal](https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-azure-function) 
or from command line with:

```bash
az functionapp create --resource-group <resource-group> \
    --os-type Linux --consumption-plan-location westeurope \
    --runtime python --runtime-version 3.7 --functions-version 2 \
    --name <function-name> --storage-account <storage-account>
```

... and publish it with `func azure functionapp publish <function-name>`.
