#
# voice-skill-sdk
#
# (C) 2021, Deutsche Telekom AG
#
# Deutsche Telekom AG and all other contributors /
# copyright owners license this file to you under the MIT
# License (the "License"); you may not use this file
# except in compliance with the License.
# You may obtain a copy of the License at
#
# https://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

"""Magenta Voice Skill SDK for Python"""

from .__version__ import __version__

from skill_sdk.skill import init_app, Skill

from skill_sdk.responses import (
    Card,
    CardAction,
    Response,
    ResponseType,
    Reprompt,
    SkillInfoResponse,
    SkillInvokeResponse,
    ask,
    ask_freetext,
    tell,
)

from skill_sdk.intents import Request
