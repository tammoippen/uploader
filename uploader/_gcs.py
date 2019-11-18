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

import asyncio
from multiprocessing import Pool

from loguru import logger

try:
    from google.cloud import storage

    _POOL = None

    def get_pool():
        global _POOL
        if _POOL is None:
            _POOL = Pool(1, maxtasksperchild=50)
        return _POOL

    def read(upload_file, size):
        data = asyncio.get_event_loop().run_until_complete(upload_file.read(size))
        return data

    class GCSFile:
        def __init__(self, upload_file):
            self.upload_file = upload_file
            self.tell_counter = 0

        def tell(self):
            return self.tell_counter

        def read(self, size=-1):
            data = get_pool().apply(read, (self.upload_file, size))
            self.tell_counter += len(data)
            return data

    async def upload_gcs(upload_file, folder, settings):
        parts = settings.gcs_path.split("/")
        bucket_name = parts[2]
        path = "/".join(parts[3:] + [folder, upload_file.filename])
        logger.info(f"Save to gs://{bucket_name}/{path}")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(path)
        blob.upload_from_file(
            GCSFile(upload_file), content_type=upload_file.content_type
        )


except ImportError:

    async def upload_gcs(file, folder, settings):
        raise NotImplementedError()
