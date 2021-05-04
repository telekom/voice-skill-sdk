#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

"""Type hints processing and intent handler invoke"""

import inspect
import logging
from typing import (
    AbstractSet,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Text,
    Type,
    Union,
)

from pydantic.utils import lenient_issubclass

from skill_sdk.util import run_in_executor
from skill_sdk.intents import entities
from skill_sdk.intents import Context, Request, Session, RequestContextVar
from skill_sdk.responses import Response, _enrich

from functools import wraps, reduce, partial


logger = logging.getLogger(__name__)
AnyType = Type[Any]
AnyFunc = Callable[..., Any]
ErrorHandlerType = Callable[[Text, "EntityValueException"], Union[Awaitable, Response]]


class EntityValueException(Exception):
    """
    Entity values conversion exception
    """

    def __init__(self, ex, value=None, func=None, *args):
        self.__cause__ = ex
        self.value = value
        self.func = func
        super().__init__(*args)


async def invoke(handler: AnyFunc, request: Request) -> Response:
    """
    Invoke intent handler:

        awaits the call if handler is a coroutine
        runs in executor if handler is `def`

    :param handler:
    :param request:
    :return:
    """

    with RequestContextVar(request=request):
        logger.debug(
            "Calling intent %s with handler: %s",
            repr(request.context.intent),
            repr(handler),
        )

        if inspect.iscoroutinefunction(handler):
            response = await handler(request)
        else:
            response = await run_in_executor(handler, request)

        result = _enrich(response)

        logger.debug("Intent call result: %s", repr(result))
        return result


def _is_subtype(cls: Any, class_or_tuple: Any) -> bool:
    """
    Return true if class is a generic subclass of class_or_tuple.

    :param cls:
    :param class_or_tuple:   a class or tuple of class objects
    :return:
    """
    return bool(
        getattr(cls, "__origin__", None)
        and lenient_issubclass(cls.__origin__, class_or_tuple)
    )


def _is_attribute_v2(annotation) -> bool:
    """
    Return true if annotation contains AttributeV2

    :param annotation:
    :return:
    """
    if isinstance(annotation, (list, tuple)):
        return _is_attribute_v2(next(iter(annotation), None))
    if _is_subtype(annotation, (List, Tuple)):
        args = getattr(annotation, "__args__", None) or annotation
        return _is_attribute_v2(next(iter(args), None))
    return _is_subtype(annotation, entities.AttributeV2) or lenient_issubclass(
        annotation, entities.AttributeV2
    )


def list_functor(annotation):
    """Convert to List of type values"""

    to_type = next(iter(annotation), None)
    if _is_subtype(to_type, entities.AttributeV2):
        return partial(map, attr_v2_functor(to_type.__args__)), list
    return partial(map, entities.converter(to_type)), list


def attr_v2_functor(annotation):
    """Convert to AttributeV2 with type value"""

    to_type = next(iter(annotation), None)
    return partial(entities.AttributeV2, mapping=entities.converter(to_type))


def _converters(annotation) -> Tuple:
    """Construct converter functions"""

    if isinstance(annotation, (list, tuple)):
        converter = list_functor(annotation)
    elif _is_subtype(annotation, (List, Tuple)):
        converter = list_functor(annotation.__args__)
    elif _is_subtype(annotation, entities.AttributeV2):
        converter = entities.get_entity, attr_v2_functor(annotation.__args__)
    elif lenient_issubclass(annotation, Context):
        converter = (lambda c: c,)  # No-op
    else:
        # Get a single attribute and convert to type
        converter = entities.get_entity, entities.converter(annotation)
    return converter


def get_converters(
    func_name: Text,
    parameters: AbstractSet[Tuple[Text, inspect.Parameter]],
    reduce_func: Callable,
) -> Dict[Text, partial]:
    """
    Helper: Constructs converter functions
        a dict of {"name": (f1, f2, ...)} where f1, f2, ... will be applied to handler arguments

    :param func_name:   function name (used just to throw the exception)
    :param parameters:  function parameters
    :param reduce_func: final reduce function
    :return:
    """
    converters = {}
    for name, param in list(parameters):
        if param.annotation == inspect.Parameter.empty:
            raise ValueError(
                f"Function {func_name} - parameter '{name}' has no type annotation"
            )

        converters[name] = partial(reduce_func, _converters(param.annotation))

    return converters


def apply(value, func: Callable[[Text], Any]) -> Optional[Any]:
    """
    Apply callable to value, returning EntityValueException if conversion error occurs

    :param value:
    :param func:
    :return:
    """
    if value is None:
        return None

    try:
        return func(value)
    except Exception as ex:  # NOSONAR
        logger.exception(
            "Exception converting %s with %s: %s ", repr(value), repr(func), repr(ex)
        )
        return EntityValueException(ex, value=value, func=func)


def is_handler(f: AnyFunc) -> bool:
    """Returns `True` if function is an intent handler"""
    return getattr(f, "__intent_handler__", False)


def get_inner(f: AnyFunc) -> AnyFunc:
    """Skip inner @intent_handler decorators"""

    try:
        return get_inner(getattr(f, "__wrapped__")) if is_handler(f) else f
    except AttributeError:
        return f


def intent_handler(
    func: AnyFunc = None,
    silent: bool = True,
    error_handler: ErrorHandlerType = None,
):
    """
    Generic intent handler decorator:
    Will check the handler parameters and supply entity values according to the type hints

        an intent handler function is supposed to have the following signature:
            handler(request: skill_sdk.Request, entity_one: typing.Any, entity_two: typing.Any, *)

        to receive a date in a handler function, use:
            @intent_handler
            handler(date: datetime.date)

        to receive an array of integer values, use:
            @intent_handler
            handler(int_list: [int])

        to suppress the conversion errors, should you want to handle exceptions, set `silent` to `True`.
        The decorator will return exception as value:
            @intent_handler(silent=True)

    :param func:    decorated function (can be `None` if decorator used without call)
    :param silent:  if `True`, an exception occurred during conversion will not be raised and returned as value
    :param error_handler:  if set, will be called if conversion error occurs, instead of a decorated function
    :return:
    """
    if isinstance(func, bool):
        silent, func = func, None

    def handler_decorator(_func: AnyFunc) -> AnyFunc:
        """The entry point to the decorator"""

        inner = get_inner(_func)
        signature = inspect.signature(inner)
        parameters = signature.parameters.items()
        converters = get_converters(inner.__name__, parameters, partial(reduce, apply))

        target = partial(  # type: ignore
            _parse_and_call,
            func=inner,
            converters=converters,
            silent=silent,
            error_handler=error_handler,
        )

        if inspect.iscoroutinefunction(inner):

            if error_handler and not inspect.iscoroutinefunction(error_handler):
                raise ValueError(
                    f"Error handler {repr(error_handler.__name__)} must be a coroutine"
                )

            @wraps(inner)
            async def wrapper(request: Request = None, *args, **kwargs) -> Response:
                """Entry point to async intent handler"""

                return await target(*(request, *args), **kwargs)

        else:

            @wraps(inner)
            def wrapper(request: Request = None, *args, **kwargs) -> Response:
                """Entry point to sync handler"""

                return target(*(request, *args), **kwargs)

        setattr(wrapper, "__intent_handler__", True)
        return wrapper

    return handler_decorator(func) if func else handler_decorator


def _parse_and_call(
    request: Request,
    *args,
    func: AnyFunc,
    converters: Dict[Text, partial],
    silent: bool,
    error_handler: ErrorHandlerType = None,
    **kwargs,
):
    """Extract parameters from invoke request and call intent handler"""

    signature = inspect.signature(func)
    parameters = signature.parameters.items()

    if isinstance(request, Request):
        # Proceed with skill invoke request if first parameter is invoke request
        kw = _parse_request(request, parameters)
        logger.debug("Collected arguments: %s", repr(kw))

        ba = signature.bind(**kw)
        arguments = {
            name: converters[name](value) for name, value in ba.arguments.items()
        }

        logger.debug("Converted arguments to: %s", repr(arguments))
        ba.arguments.update(arguments)

        # raises EntityValueException if not silent mode
        errors = _parse_errors(arguments, silent)

        return (
            _log_and_call("Normal call", func, *ba.args, **ba.kwargs)
            if not (errors and error_handler)
            else _log_and_call("Exception during conversion", error_handler, *errors)
        )

    else:
        # If we're called without invoke request as first argument, this is a direct call:
        #   we do not parse the context and simply pass arguments to the decorated function
        return _log_and_call(
            "Direct call",
            func,
            *args if request is None else (request, *args),
            **kwargs,
        )


def _log_and_call(message: Text, func: Callable, *args, **kwargs):
    """Helper to log debug message and call inner function"""

    logger.debug(
        "%s: calling %s with: %s, %s",
        message,
        repr(func.__name__),
        repr(args),
        repr(kwargs),
    )
    return func(*args, **kwargs)


def _parse_errors(arguments: Dict[Text, Any], silent: bool = True):
    """Extract type/value conversion exceptions"""
    errors = next(
        iter(
            (name, ex)
            for name, ex in arguments.items()
            if isinstance(ex, EntityValueException)
        ),
        (),
    )
    if errors and not silent:
        raise errors[1]
    return errors


def _as_attributes(attrs_v2: List[entities.AttributeV2]) -> List[Any]:
    """
    Convert entities: list of AttributesV2 to simple values list

    :param attrs_v2:
    :return:
    """
    return [_.value for _ in attrs_v2]


def _parse_request(
    request: Request, parameters: AbstractSet[Tuple[Text, inspect.Parameter]]
) -> Dict[Text, Any]:
    """
    Parse attributes from skill invoke request

    :param request:
    :param parameters:
    :return:
    """
    result = {
        # original request
        name: request if lenient_issubclass(param.annotation, Request)
        # if annotated as Context, use request.context
        else request.context if lenient_issubclass(param.annotation, Context)
        # if annotated as Session, use request.session
        else request.session if lenient_issubclass(param.annotation, Session)
        # look up attributesV2, if annotated as AttributeV2
        else request.context.attributes_v2.get(name)
        if _is_attribute_v2(param.annotation)
        # look up the standard attributes
        else request.context.attributes.get(name)
        for name, param in parameters
    }
    return result
