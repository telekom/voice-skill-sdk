#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#

"""Geolocation service"""

import logging
from json import JSONDecodeError
from typing import Dict, List, Optional, Text

import httpx

from skill_sdk.util import CamelModel, root_validator
from skill_sdk.services.base import BaseService

logger = logging.getLogger(__name__)


#
#   The models below reflect location service's response structure
#


class GeoLocation(CamelModel):
    """Geo-location: latitude/longitude"""

    lat: float
    lng: float


class AddressComponents(CamelModel):
    """Address components: city and postal code"""

    city: Text
    postal_code: Text


class Address(CamelModel):
    """Address: country with address components"""

    country: Text
    address_components: AddressComponents


class Location(CamelModel):
    """Location consists of an address and time-zone"""

    address: Address
    timezone: Text = "Europe/Berlin"


class FullLocation(GeoLocation, Location):
    """Full location consists of an address component and geographical coordinates"""

    ...


class FullAddress(CamelModel):
    """Complete address including geo-coordinates"""

    lat: Optional[float]
    lon: Optional[float]  # ATTN: "lon" not "lng" (!)

    country: Optional[Text]
    city: Optional[Text]
    postal_code: Optional[Text]
    street_name: Optional[Text]
    street_number: Optional[Text]

    def __bool__(self):
        return any(
            (
                self.country,
                self.city,
                self.postal_code,
                self.street_name,
                self.street_number,
            )
        )


class FullAddressList(CamelModel):
    """Result of address lookup service: list of FullAddress"""

    __root__: List[Optional[FullAddress]]

    def __bool__(self):
        return bool(self.__root__)


class AddressLookupQuery(CamelModel):
    """Query to address lookup service"""

    country: Optional[Text]
    postalcode: Optional[Text]  # noqa
    street_name: Optional[Text]
    street_number: Optional[Text]

    lang: Optional[Text]

    # Max number of search results
    limit: int

    @root_validator(pre=True)
    def query_required(cls, values: Dict):  # pylint: disable=E0213
        if not any(
            (
                values.get("country"),
                values.get("postalcode"),
                values.get("street_name"),
                values.get("street_number"),
            )
        ):
            raise ValueError("Query is missing or empty!")
        return values


class GeoLookupQuery(CamelModel):
    """Request to location service"""

    country: Optional[Text]
    city: Optional[Text]
    postalcode: Optional[Text]  # noqa

    lang: Optional[Text]

    @root_validator(pre=True)
    def query_required(cls, values: Dict):  # pylint: disable=E0213
        if not any(
            (values.get("country"), values.get("city"), values.get("postalcode"))
        ):
            raise ValueError("Query is missing or empty!")
        return values


class LocationService(BaseService):
    """Location service with geo-coding"""

    VERSION = 1
    NAME = "location"

    async def forward_lookup(
        self,
        *,
        country: Text = None,
        city: Text = None,
        postalcode: Text = None,  # noqa
        lang: Text = None,
    ) -> FullLocation:
        """
        Forward lookup: resolve geo-coordinates from textual address components

        :param country:
        :param city:
        :param postalcode:
        :param lang:
        :return:
        """
        async with self.async_client as client:
            params = GeoLookupQuery(
                country=country, city=city, postalcode=postalcode, lang=lang
            )

            data = await client.get(f"{self.url}/geo", params=params.dict())
            return FullLocation(**data.json())

    async def reverse_lookup(self, lat: float, lng: float) -> Address:
        """
        Reverse lookup: resolve address components from geo-coordinates

        :param lat:
        :param lng:
        :return:
        """

        async with self.async_client as client:
            location = GeoLocation(lat=lat, lng=lng)

            data = await client.get(f"{self.url}/reversegeo", params=location.dict())
            return Address(**data.json())

    async def address_lookup(
        self,
        *,
        country: Text = None,
        postalcode: Text = None,  # noqa
        street_name: Text = None,
        street_number: Text = None,
        lang: Text = None,
        limit: int = 1,
    ) -> Optional[FullAddressList]:
        """
        Address lookup: get a list of addresses (with geo-coordinates) for a given query

        :param country:
        :param postalcode:
        :param street_name:
        :param street_number:
        :param lang:
        :param limit:
        :return:
        """
        async with self.async_client as client:
            params = AddressLookupQuery(
                country=country,
                postalcode=postalcode,
                street_name=street_name,
                street_number=street_number,
                lang=lang,
                limit=limit,
            )

            data = await client.request(
                "GET",
                f"{self.url}/address",
                params=params.dict(),
                exclude=[httpx.codes.NOT_FOUND],
            )
            return FullAddressList.parse_obj(data.json() if data.text else [])

    async def device_location(self) -> FullAddress:
        """
        Retrieves device location: whatever user has setup in cApp, plus geo coordinates

        (device serial number gets decoded from the service token,
         so in order to use this function, parent request must contain the service token)

        @return:
        """

        async with self.async_client as client:
            data = await client.request(
                "GET", f"{self.url}/device-location", exclude=[httpx.codes.NOT_FOUND]
            )
            return FullAddress(**data.json() if data.text else {})
