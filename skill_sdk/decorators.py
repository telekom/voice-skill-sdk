#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#

#
# Type hints processing
#

import inspect
import logging
from typing import AbstractSet, Any, Callable, Dict, List, Optional, Tuple, Type, Union

from . import intents
from . import entities
from . import responses

from functools import wraps, reduce, partial


logger = logging.getLogger(__name__)
AnyType = Type[Any]


def _is_subclass(cls: Any, classinfo: Union[AnyType, Tuple[AnyType, ...]]) -> bool:
    """ Permissive issubclass: does not throw TypeError

    :param cls:
    :param classinfo:   a class or tuple of class objects
    :return:
    """
    return isinstance(cls, type) and issubclass(cls, classinfo)


def _is_subtype(cls: Any, classinfo) -> bool:
    """ Return true if class is a subscripted subclass of classinfo.

    :param cls:
    :param classinfo:   a class or tuple of class objects
    :return:
    """
    return bool(getattr(cls, '__origin__', None) and _is_subclass(cls.__origin__, classinfo))


def _is_attribute_v2(annotation) -> bool:
    """ Return true if annotation contains AttributeV2

    :param annotation:
    :return:
    """
    if isinstance(annotation, (list, tuple)):
        return _is_attribute_v2(next(iter(annotation), None))
    if _is_subtype(annotation, (List, Tuple)):
        args = getattr(annotation, '__args__', None) or annotation
        return _is_attribute_v2(next(iter(args), None))
    return _is_subtype(annotation, entities.AttributeV2) or _is_subclass(annotation, entities.AttributeV2)


def list_functor(annotation):
    """ Convert to List of type values """
    to_type = next(iter(annotation), None)
    if _is_subtype(to_type, entities.AttributeV2):
        return partial(map, attr_v2_functor(to_type.__args__)), list
    return partial(map, entities.converter(to_type)), list


def attr_v2_functor(annotation):
    """ Convert to AttributeV2 with type value """
    to_type = next(iter(annotation), None)
    return partial(entities.AttributeV2, mapping=entities.converter(to_type))


def _converters(annotation) -> Tuple:
    """ Construct converter functions """
    if isinstance(annotation, (list, tuple)):
        converter = list_functor(annotation)
    elif _is_subtype(annotation, (List, Tuple)):
        converter = list_functor(annotation.__args__)
    elif _is_subtype(annotation, entities.AttributeV2):
        converter = entities.get_entity, attr_v2_functor(annotation.__args__)
    elif _is_subclass(annotation, intents.Context):
        converter = (lambda c: c,)  # No-op
    else:
        # Get a single attribute and convert to type
        converter = entities.get_entity, entities.converter(annotation)
    return converter


def get_converters(func_name: str, parameters: AbstractSet[Tuple[str, inspect.Parameter]],
                   reduce_func: Callable) -> Dict[str, partial]:
    """ Helper: Constructs converter functions
            a dict of {"name": (f1, f2, ...)} where f1, f2, ... will be applied to handler arguments

    :param func_name:   function name (used just to throw the exception)
    :param parameters:  function parameters
    :param reduce_func: final reduce function
    :return:
    """
    converters = {}
    for name, param in list(parameters):
        if param.annotation == inspect.Parameter.empty:
            raise ValueError(f"Function {func_name} - parameter '{name}' has no type hint defined")

        converters[name] = partial(reduce_func, _converters(param.annotation))

    return converters


def apply(value, func: Callable[[str], Any]) -> Optional[Any]:
    """ Apply callable to value, returning EntityValueException if conversion error occurs

    :param value:
    :param func:
    :return:
    """
    if value is None:
        return None

    try:
        return func(value)
    except Exception as ex:     # NOSONAR
        logger.error('Exception converting %s with %s: %s ', repr(value), repr(func), repr(ex))
        return intents.EntityValueException(ex, value=value, func=func)


def get_inner(f: Callable[..., Any]) -> Callable[..., Any]:
    """ Skip inner @intent_handler decorators """

    try:
        return get_inner(getattr(f, '__wrapped__')) if getattr(f, '__intent_handler__') else f
    except AttributeError:
        return f


def _call(func: Callable, context, *args, **kwargs):
    """ Helper to call inner function """
    if context is not None:
        args = context, *args
    logger.debug('Direct call: "%s" args=%s kwargs=%s', func.__name__, args, kwargs)
    return func(*args, **kwargs)


def intent_handler(func: Callable[..., Any] = None,
                   silent: bool = True,
                   error_handler: Callable[[str, Exception], Any] = None):
    """
        Generic intent handler decorator:
        Will check the handler parameters and supply entity values according to the type hints

            an intent handler function is supposed to have the following signature:
                handler(context: skill_sdk.intents.Context, entity_one: typing.Any, entity_two: typing.Any, *)

            to receive a date in a handler function, use:
                @intent_handler
                handler(context: skill_sdk.intents.Context, date: datetime.date)

            to receive an array of integer values, use:
                @intent_handler
                handler(context: skill_sdk.intents.Context, int_list: [int])

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

    def handler_decorator(_func: Callable[..., Any]) -> Callable[..., Any]:
        """ The entry point to the decorator """

        _reduce = partial(reduce, apply)

        inner = get_inner(_func)
        signature = inspect.signature(inner)
        parameters = signature.parameters.items()
        converters = get_converters(inner.__name__, parameters, _reduce)

        @wraps(inner)
        def wrapper(context=None, *args, **kwargs) -> responses.Response:
            """ The entry point to intent handler """

            # If we're called without context as first argument, this is a direct call:
            #   we do not parse the context and simply pass arguments to the decorated function
            if not isinstance(context, intents.Context):
                return _call(inner, context, *args, **kwargs)

            # Otherwise proceed with skill invocation context
            kw = _parse_context(context, parameters)
            logger.debug('Collected arguments: %s', repr(kw))

            ba = signature.bind(**kw)
            arguments = {name: converters[name](value) for name, value in ba.arguments.items()}

            # Pre-check: if not silent mode, raise EntityValueException or call `error_handler` if set
            error = next(iter((name, ex) for name, ex in arguments.items()
                              if isinstance(ex, intents.EntityValueException)), None)

            if error and not silent:
                raise error[1]

            if error and error_handler:
                logger.debug('Exception during conversion, calling error_handler: %s', repr(error_handler))
                return error_handler(*error)

            logger.debug('Converted arguments to: %s', repr(arguments))
            ba.arguments.update(arguments)

            return inner(*ba.args, **ba.kwargs)

        setattr(wrapper, '__intent_handler__', True)
        return wrapper

    return handler_decorator(func) if func else handler_decorator


def _parse_context(context: intents.Context, parameters: AbstractSet[Tuple[str, inspect.Parameter]]) -> Dict[str, Any]:
    """ This function parses attributes from the invocation context

    :param context:
    :param parameters:
    :return:
    """
    result = {
        # use "context" as argument, if annotated as Context
        name: context if _is_subclass(param.annotation, intents.Context)
        # look up attributesV2, if annotated as AttributeV2
        else context.attributesV2.get(name) if _is_attribute_v2(param.annotation) and context.attributesV2
        # look up the standard attributes
        else context.attributes.get(name) if context.attributes
        # get from pre-parsed keyword arguments
        else None
        for name, param in parameters
    }
    return result
