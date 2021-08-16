#  uploader - take control of files send to you
#  Copyright (C) 2019  Tammo Ippen <tammo.ippen@posteo.de>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import secrets
from typing import Optional

from pydantic import BaseSettings, ConstrainedStr, SecretStr


class GCSPath(ConstrainedStr):
    regex = r"gs://[^/]+/.*"


class Settings(BaseSettings):
    jwt_secret: SecretStr = SecretStr(secrets.token_urlsafe(16))
    admin_secret: SecretStr
    local_path: Optional[str] = None
    gcs_path: Optional[GCSPath] = None

    class Config:
        case_sensitive = False
        env_prefix = "UPLDR_"
