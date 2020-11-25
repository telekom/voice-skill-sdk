#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

#
# Notification service
#

import json
import logging
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, replace
from datetime import datetime
import requests

from skill_sdk.config import config
from skill_sdk.entities import camel_to_snake, snake_to_camel
from skill_sdk.services.prometheus import prometheus_latency, partner_call
from skill_sdk.services.base import BaseService, MalformedResponseException
from skill_sdk.requests import RequestException

logger = logging.getLogger(__name__)

# Default timeout when accessing the service
DEFAULT_SERVICE_TIMEOUT = 10

# Text service URL
config.read_environment('SERVICE_NOTIFICATION_URL', 'service-notification', 'url')
# Timeout when accessing text service
config.read_environment('SERVICE_NOTIFICATION_TIMEOUT', 'service-notification', 'timeout')


class NotificationMode(str, Enum):
    """ Push notification mode:

                    |   "push_soft"     |   "push_hard"
            ---------------------------------------------
            LED     |   color=orange    |   color=orange
                    |   style=moving    |   style=moving
            ---------------------------------------------
            Speaker |   quiet           |   output message

    """
    push_soft = 'push_soft'
    push_hard = 'push_hard'

    def __str__(self):
        return str(self.value)


class NotificationService(BaseService):
    """ Notification service: service to send simple notifications to a device """

    VERSION = 1
    NAME = 'notification'

    def __init__(self):
        super().__init__(add_auth_header=True)
        self.BASE_URL = config.get("service-notification", "url", fallback="http://service-notification-service:1555")

    @property
    def timeout(self):
        return config.get("service-notification", "timeout", fallback=DEFAULT_SERVICE_TIMEOUT)

    @property
    def provider(self):
        return config.get("service-notification", "provider",
                          fallback=config.get('skill', 'name', fallback='unnamed-skill'))

    @prometheus_latency('service-notification.get')
    def _get(self, read: bool = None, provider: str = None) -> Dict[str, 'Notification']:
        """ Get all user notifications

        :param read:        if set, only read (if True) or not read (if False) notifications returned
        :param provider:    get notification for a provider (otherwise, notifications for current returned)

        :return:            {id: Notification} dictionary or empty dict if error occurs
        """
        with self.session as session:
            params = dict({'provider': provider or self.provider}, **{"read": read} if read else {})

            try:
                with partner_call(session.get, NotificationService.NAME) as get:
                    data = get(self.url, params=params).json()

                return {record['id']: Notification.construct(**record) for record in data}

            except (KeyError, TypeError, json.decoder.JSONDecodeError) as ex:
                logger.error("%s responded with error: %s", self.url, repr(ex))
                raise MalformedResponseException(ex, self)

            except RequestException as ex:
                logger.error("Cannot get notifications from %s: %s", self.url, repr(ex))
                raise

    def get(self, read: bool = None) -> Dict[str, 'Notification']:
        """ Get user notification by id, or all notifications for the current scope (provider)

        :param read:    if set, only read (if True) or not read (if False) notifications returned

        :return:        {id: Notification} dictionary or empty dict if error occurs
        """
        return self._get(read=read)

    @prometheus_latency('service-notification.post')
    def add(self, notification: 'Notification') -> Dict[str, 'Notification']:
        """ Add a new notification:
                issues POST to notification service

        :param notification:    notification instance to set
        :return:                {id: Notification} dictionary or empty dict if error occurs
        """
        with self.session as session:

            try:
                with partner_call(session.post, NotificationService.NAME) as post:
                    n = replace(notification, provider=self.provider)
                    data = post(self.url, json=n.dict()).json()

                return {data['id']: data}

            except (KeyError, TypeError, json.decoder.JSONDecodeError) as ex:
                logger.error("%s responded with error. Data not available: %s", self.url, repr(ex))
                raise MalformedResponseException(ex, self)

            except RequestException as ex:
                logger.error("Cannot add notification [%s] to %s: %s", notification, self.url, repr(ex))
                raise

    @prometheus_latency('service-notification.patch')
    def _mark_as_read(self, id_, *, read: bool = True, provider: str = None) -> requests.Response:
        """ Mark notifications as read:
                issues PATCH to notification service

        :param id_:         notification id
        :param read:        set as "read" (default) or "unread"
        :param provider:    change notification for a provider (otherwise, notifications for the current)
        :return:
        """
        with self.session as session:
            try:
                params = {'provider': provider or self.provider}

                with partner_call(session.patch, NotificationService.NAME) as patch:
                    url = self.url + (f"/{id_}" if id_ else '')
                    return patch(url, params=params, json={"read": read} if read is not None else {})

            except RequestException as ex:
                logger.error("Cannot set one or more notifications as read %s: %s", self.url, repr(ex))
                raise

    def mark_as_read(self, id_: str = None, *, read: bool = True):
        """ Mark notification as "read"

        :param id_:
        :param read:        if False the notification is marked as "unread"
        :return:
        """
        return self._mark_as_read(id_=id_, read=read)

    @prometheus_latency('service-notification.delete')
    def _delete(self, id_: str = None, *, read: bool = None, provider: str = None) -> requests.Response:
        """ Delete notification by id or delete all read/unread notifications:
                issues DELETE to notification service

        :param id_:
        :param read:        if set, deletes all read (if True), or unread (if False) notifications
        :param provider:    delete notification for a provider (otherwise, notifications for current returned)
        :return:
        """
        with self.session as session:
            params: Dict[str, Any] = {"read": read} if read else {}
            if not id_:
                params.update({'provider': provider or self.provider})

            try:
                with partner_call(session.delete, NotificationService.NAME) as delete:
                    url = self.url + (f"/{id_}" if id_ else '')
                    return delete(url, params=params)

            except RequestException as ex:
                logger.error("Cannot delete one or more notifications from %s: %s", self.url, repr(ex))
                raise

    def delete(self, id_: str = None, *, read: bool = None):
        """ Delete notification by id or delete all read/unread notifications

        :param id_:
        :param read:        if set, deletes all read (if True), or unread (if False) notifications
        :return:
        """
        return self._delete(id_, read=read)


@dataclass(frozen=True)
class Notification:
    """ Notification service record """

    add_up_text: str

    provider: Optional[str] = None
    mode: NotificationMode = NotificationMode.push_soft
    valid_by: datetime = datetime.max
    provider_enabler_setting: Optional[str] = None
    read: bool = False
    id: Optional[str] = None

    def add(self):
        """ Create new notification """
        return NotificationService().add(self)

    def mark_as_read(self, read: bool = False):
        """ Mark notification as "read" """
        return NotificationService().mark_as_read(self.id, read=read)

    def delete(self):
        """ Delete notification """
        return NotificationService().delete(self.id)

    def dict(self) -> Dict:
        """ Export as dictionary """
        camel_cased = {snake_to_camel(key): str(value) for key, value in self.__dict__.items() if value is not None}
        return dict(**camel_cased)

    @staticmethod
    def construct(**kwargs) -> 'Notification':
        """ Factory to create an instance from dictionary

        :param kwargs:
        :return:
        """
        snake_cased = {camel_to_snake(key): value for key, value in kwargs.items()}
        return Notification(**snake_cased)
