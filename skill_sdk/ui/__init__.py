#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Skill Designer UI"""

import time
import asyncio
import inspect
from json import dumps
import logging.handlers
from pathlib import Path
from typing import Any, Callable, Dict, List, Text, Tuple
import datetime

from jinja2 import Environment, FileSystemLoader
from fastapi import responses, FastAPI, Request, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from pydantic import validator

from skill_sdk.util import CamelModel
from skill_sdk.intents.entities import AttributeV2, TimeRange, TimeSet

logger = logging.getLogger()

UI_ROOT = Path(__file__).absolute().parent
DEFAULT_MODULE = "impl"
DESIGNER = "Designer endpoints"
TEMPLATES = "templates"

#
#   Sample values for intent handlers
#

SAMPLE_BOOL = True
SAMPLE_INT = 42
SAMPLE_FLOAT = 42.0242
SAMPLE_COMPLEX = complex(42.02, 0.42)
SAMPLE_STRING = "string value"
SAMPLE_ATTR_V2: AttributeV2 = AttributeV2(id=1, value=SAMPLE_STRING)
SAMPLE_TIME_RANGE = TimeRange("2002-02-02T12:42:02Z/2022-02-02T00:12:42Z")
SAMPLE_TIME_SET = TimeSet("(XXXX-WXX-1,XXXX-WXX-5,P4D)")


def samples(type_=None):
    """
    Return a sample value for particular type (if specified), or list of supported types otherwise

    :param type_:
    :return:
    """
    _ = {
        "bool": SAMPLE_BOOL,
        "int": SAMPLE_INT,
        "float": SAMPLE_FLOAT,
        "complex": SAMPLE_COMPLEX,
        "str": SAMPLE_STRING,
        "timedelta": datetime.timedelta(),
        "datetime": datetime.datetime.now(),
        "date": datetime.date.today(),
        "time": datetime.datetime.now().time(),
        "TimeRange": SAMPLE_TIME_RANGE,
        "TimeSet": SAMPLE_TIME_SET,
        "AttributeV2": SAMPLE_ATTR_V2,
        "typing.List[str]": [SAMPLE_STRING],
    }
    return _.get(type_, None) if type_ is not None else list(_)


class Parameter(CamelModel):
    """Parameter record format"""

    # Parameter name
    name: Text

    # Parameter type
    type: Text

    # Required if non-empty and has no default
    required: bool = False

    # Sample value
    sample: Any

    # Values array
    values: List[Any] = []

    @validator("values", pre=True, always=True)
    def default(cls, v):  # pylint: disable=E0213
        return [v] if not isinstance(v, (list, tuple, type(None))) else (v or [])

    @property
    def as_code(self) -> Text:
        """
        Return string representation as Python parameter with type annotation

        :return:
        """
        value = f" = {repr(self.values[0])}" if self.values else None
        default = "" if self.required else " = None"
        return f"{self.name}: {self.type}{value or default}".replace("'", '"')

    @staticmethod
    def from_signature(name: Text, type_: Text, default: Any = None) -> "Parameter":
        """
        Create an instance from function signature

        :param name:
        :param type_:
        :param default:
        :return:
        """
        return Parameter(
            name=name,
            type=type_,
            required=default == inspect.Parameter.empty,
            sample=samples(type_),
            values=[default] if default not in (None, inspect.Parameter.empty) else [],
        )


class Intent(CamelModel):
    """Intent record format"""

    # Intent name
    name: Text

    # Handler (implementation) name as tuple (<module>, <function>)
    implementation: Tuple = ()

    @property
    def module(self):
        return self.implementation[0]

    @property
    def function(self):
        return self.implementation[1].lower()

    @validator("implementation", pre=True, always=True)
    def generate_name(cls, v, *, values):  # pylint: disable=E0213
        return v or (DEFAULT_MODULE, f"handle_{values['name']}")

    # List of intent handler parameters (entities)
    parameters: List[Parameter] = []

    @staticmethod
    def from_callable(name: Text, func: Callable) -> "Intent":
        """
        Create an instance from intent handler

        :param name:    intent name
        :param func:    handler function
        :return:
        """

        __params = inspect.signature(func).parameters
        parameters = [
            Parameter.from_signature(p_name, param.annotation.__name__, param.default)
            for p_name, param in __params.items()
        ]

        return Intent(
            name=name,
            implementation=(getattr(func, "__module__", DEFAULT_MODULE), func.__name__),
            parameters=parameters or [],
        )


def _signature_changed(intent: Intent, intents: Dict[Text, Callable]) -> bool:
    """
    Denotes if function signature has been altered in the UI

    :param intent:  an intent from UI
    :param intents: dictionary of intent implementations
    :return:
    """
    return (
        intent.json() != Intent.from_callable(intent.name, intents[intent.name]).json()
    )


async def get_types():
    """
    List supported attribute types
    """

    return responses.JSONResponse(content=[_ for _ in samples()])


async def get_intents(request: Request):
    """
    List intents and entity samples
    """

    return [
        Intent.from_callable(name, func) for name, func in request.app.intents.items()
    ]


class Notifier:
    """Notifies subscribed clients"""

    def __init__(self):
        self.connections: List[WebSocket] = []
        self.generator = self.get_notification_generator()

    async def get_notification_generator(self):
        while True:
            message = yield
            await self._notify(message)

    async def push(self, msg: Text):
        await self.generator.asend(msg)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def remove(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def _notify(self, message: Text):
        living_connections = []
        while len(self.connections) > 0:
            # Looping is necessary in case a disconnection is handled
            # during await websocket.send_text(message)
            websocket = self.connections.pop()
            await websocket.send_text(message)
            living_connections.append(websocket)
        self.connections = living_connections

    async def worker(self, queue):
        """
        Async worker: waits for a log record and sends to subscribed clients

        :param queue:
        :return:
        """
        while True:
            record: logging.LogRecord = await queue.get()
            await self.push(dumps(record.__dict__))


notifier = Notifier()


async def ws_endpoint(websocket: WebSocket):
    """
    Dump logs output to websocket

    :param websocket:
    :return:
    """
    await notifier.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        try:
            notifier.remove(websocket)
        except ValueError:
            pass  # Shutting down (?)


def log_changes(app_intents: Dict[Text, Callable], intents: List[Intent]) -> bool:
    """
    Log differences between the running skill intents and a list received from the UI

    :param app_intents: running skill's intents (request.app.intents)
    :param intents:     intents list from UI editor
    :return:            True if there are changes in intents
    """

    # List of new intents from UI
    to_add = [_ for _ in intents if _.name not in app_intents]

    # List of intents missing in UI request (deleted)
    to_delete = [
        Intent.from_callable(name, func)
        for name, func in app_intents.items()
        if name not in [_.name for _ in intents]
    ]

    # List of intents those signatures are different from original
    to_update = [
        intent
        for intent in intents
        if intent.name in app_intents and _signature_changed(intent, app_intents)
    ]

    if len(to_add):
        logger.debug("Will create %s intent handler(s): %s", len(to_add), repr(to_add))

    if len(to_delete):
        logger.debug(
            "Will delete %s intent handler(s): %s", len(to_delete), repr(to_delete)
        )

    if len(to_update):
        logger.debug(
            "Will modify %s intent handler(s): %s", len(to_update), repr(to_update)
        )

    return any((to_add, to_delete, to_update))


def render_impl(intents: List[Intent]) -> Text:
    """
    Render Python code for intent handlers implementation

    :param intents:
    :return:
    """

    imports = []

    # Collect datetime related parameter types
    dt_types = [
        _.type
        for intent in intents
        for _ in intent.parameters
        if _.type in ("date", "time", "datetime", "timedelta")
    ]
    if dt_types:
        imports.append(f"from datetime import {', '.join(dt_types)}")

    # Collect SDK entities types
    sdk_types = [
        _.type
        for intent in intents
        for _ in intent.parameters
        if _.type in ("AttributeV2", "TimeRange", "TimeSet")
    ]
    if sdk_types:
        imports.append(f"from skill_sdk.entities import {', '.join(sdk_types)}")

    imports.append("from skill_sdk import skill, Response")

    return (
        Environment(loader=FileSystemLoader(UI_ROOT / TEMPLATES))
        .get_template("impl.j2")
        .render(imports=imports, intents=intents)
    )


def render_tests(intents: List[Intent]) -> Text:
    """
    Render unit tests code

    :param intents:
    :return:
    """

    return (
        Environment(loader=FileSystemLoader(UI_ROOT / TEMPLATES))
        .get_template("tests.j2")
        .render(intents=intents)
    )


def render_runner(intents: List[Intent]) -> Text:
    """
    Render runner ("app.py")

    :param intents:
    :return:
    """

    return (
        Environment(loader=FileSystemLoader(UI_ROOT / TEMPLATES))
        .get_template("app.j2")
        .render(intents=intents)
    )


def save(content: Text, path: Path, suffix: Text) -> Path:
    """
    Save the content to the file specified by path parameter,
    backup previously existing file

    :param content: file content
    :param path:    file name
    :param suffix:  backup file suffix
    :return:        absolute file path
    """
    if path.exists():
        backup = path.with_suffix(f".{suffix}")
        logger.info("File %s exists, backing up to %s", path, backup)
        backup.write_text(path.read_text())

    path.write_text(content)

    logger.info("Dump content to %s", path.absolute())
    return path.absolute()


async def post_intents(request: Request, intents: List[Intent]):
    """
    Generator: main entry point
    """

    if not log_changes(request.app.intents, intents):
        return responses.JSONResponse(
            content=dict(message="No changes"), status_code=204
        )

    # Render Python modules from templates
    suffix = str(time.time())
    impl = save(render_impl(intents), Path(DEFAULT_MODULE) / "__init__.py", suffix)
    tests = save(render_tests(intents), Path(DEFAULT_MODULE) / "test_impl.py", suffix)
    runner = save(render_runner(intents), Path("app.py"), suffix)

    # TODO: Restart the server.
    #  Looks like we need to re-implement uvicorn's BaseReload with threading instead of multiprocessing,
    #  because the integrated re-loader breaks logging functionality in UI:
    #  somehow the worker in the child subprocesses does not receive notifications from the logger
    #  (or the logger does not receive them?)

    return responses.JSONResponse(
        content=dict(impl=str(impl), tests=str(tests), runner=str(runner))
    )


def setup(app: FastAPI):
    """
    Install skill designer UI routes and CORS middleware

    :param app:
    :return:
    """

    # CORS middleware to allow requests from dev and prod UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:4242",
            "http://127.0.0.1:4242",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # List types route
    app.add_api_route(
        "/types",
        get_types,
        name="List types",
        tags=[DESIGNER],
    )

    # List intents route
    app.add_api_route(
        "/intents",
        get_intents,
        name="List intents",
        tags=[DESIGNER],
    )

    # Generator route
    app.add_api_route(
        "/intents",
        post_intents,
        methods=["POST"],
        name="Generate intent handlers",
        tags=[DESIGNER],
    )

    # Websocket logs push
    app.add_websocket_route(
        "/logs",
        ws_endpoint,
        name="Skill Logs",
    )

    @app.on_event("startup")
    async def startup():
        """Initializes websocket listener"""

        # Prime the push notification generator
        await notifier.generator.asend(None)

        # Silence the websocket.protocol logger
        logging.getLogger("websockets").setLevel(logging.CRITICAL)

        # Setup a queue that passes log records to websockets
        queue = asyncio.Queue()

        # Default format of the log record in front-end
        formatter = logging.Formatter("%(levelname)-8s %(name)s - %(message)s")

        handler = logging.handlers.QueueHandler(queue)
        handler.setLevel(logger.level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Start the notifier's worker
        asyncio.ensure_future(notifier.worker(queue))

    # Root UI
    app.mount("/", StaticFiles(directory=str(UI_ROOT), html=True), name="Skill UI")
