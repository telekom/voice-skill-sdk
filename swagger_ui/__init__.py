#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
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

from pathlib import Path
from bottle import get, static_file, redirect

here: Path = Path(__file__).absolute().parent

UI_ROOT = here / 'node_modules/swagger-ui-dist'


@get('/')
def root():
    return redirect('/swagger-ui/')


@get('/swagger-ui/')
@get('/swagger-ui/<filename:path>')
def send_static(filename=None):
    return static_file(filename or 'index.html', root=UI_ROOT)
