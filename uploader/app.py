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

from functools import lru_cache
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
from time import time
from typing import Any, Optional

import aiofiles
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
import jwt
from loguru import logger
import pydantic as pyd
from starlette.responses import PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates


class GCSPath(pyd.ConstrainedStr):
    regex = re.compile(r"gs://[^/]+/.*")


class Settings(pyd.BaseSettings):
    jwt_secret: pyd.SecretStr = pyd.SecretStr(secrets.token_urlsafe(16))
    admin_secret: pyd.SecretStr
    local_path: Optional[Path] = None
    temp_path: Path = Path("/tmp")
    gcs_path: Optional[GCSPath] = None

    class Config:
        case_sensitive = False
        env_prefix = "UPLDR_"

    @classmethod
    @lru_cache
    def get(cls) -> "Settings":
        return cls()


app = FastAPI()
app.mount("/static", StaticFiles(packages=["uploader"]), name="static")
templates = Jinja2Templates(
    directory=f"{os.path.dirname(os.path.realpath(__file__))}/templates"
)


@app.get("/")
async def index(request: Request) -> Response:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/token")
async def get_token(request: Request) -> Response:
    return templates.TemplateResponse("get_token.html", {"request": request})


@app.post("/token")
async def post_token(
    request: Request,
    password: str = Form(...),
    duration: int = Form(...),
    folder: str = Form(...),
    settings: Settings = Depends(Settings.get),
) -> Response:
    if secrets.compare_digest(password, settings.admin_secret.get_secret_value()):
        token = jwt.encode(
            {"exp": round(time()) + duration, "folder": folder},
            settings.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        return templates.TemplateResponse(
            "token.html", {"request": request, "token": token}
        )
    raise HTTPException(status_code=401)


@app.get("/upload")
async def get_upload(request: Request, token: str) -> Response:
    return templates.TemplateResponse(
        "upload.html", {"request": request, "token": token}
    )


async def save_chunk(
    file: UploadFile,
    dzuuid: pyd.UUID4,
    dzchunkindex: int,
    dztotalchunkcount: int,
    settings: Settings,
) -> bool:
    logger.debug("Store chunk:", file.filename, dzuuid, dzchunkindex, dztotalchunkcount)
    dest = settings.temp_path / "uploader" / str(dzuuid)
    dest.mkdir(parents=True, exist_ok=True)
    chars = len(str(dztotalchunkcount))
    async with aiofiles.open(dest / f"{dzchunkindex:0{chars}d}.part", "wb") as f:
        while True:
            data = await file.read(4096)
            if not data:
                break
            assert isinstance(data, bytes)
            await f.write(data)
    if dzchunkindex == dztotalchunkcount - 1:
        async with aiofiles.open(dest / file.filename, "wb") as out_f:
            for i in range(dztotalchunkcount):
                async with aiofiles.open(dest / f"{i:0{chars}d}.part", "rb") as in_f:
                    await out_f.write(await in_f.read())
        return True
    return False


async def save_local_file(
    filename: str, folder: str, dzuuid: pyd.UUID4, settings: Settings
) -> None:
    assert settings.local_path
    assert folder
    assert filename
    src = settings.temp_path / "uploader" / str(dzuuid)
    dest = settings.local_path / folder
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / filename, dest / filename)
    shutil.rmtree(src)


try:
    from google.cloud import storage

    def get_bucket(settings: Settings = Depends(Settings.get)) -> Any:
        assert settings.gcs_path
        parts = settings.gcs_path.split("/")
        bucket_name = parts[2]
        client = storage.Client()
        return client.bucket(bucket_name)

    async def upload_gcs(
        filename: str,
        folder: str,
        dzuuid: pyd.UUID4,
        bucket: Any,
        settings: Settings,
    ) -> None:
        assert settings.gcs_path
        assert isinstance(bucket, storage.Bucket)
        parts = settings.gcs_path.split("/")
        path = "/".join(parts[3:] + [folder, filename])
        blob = bucket.blob(path)
        src = settings.temp_path / "uploader" / str(dzuuid)
        logger.debug(f"Uploading {src / filename} to gs://{bucket.name}/{path} ... ")
        with open(src / filename, "rb") as f:
            blob.upload_from_file(
                f, content_type=mimetypes.guess_type(src / filename)[0]
            )
        logger.debug(
            f"Uploading {src / filename} to gs://{bucket.name}/{path} ... Done"
        )
        shutil.rmtree(src)


except ImportError:

    def get_bucket(settings: Settings = Depends(Settings.get)) -> Any:
        return None

    async def upload_gcs(
        filename: str,
        folder: str,
        dzuuid: pyd.UUID4,
        bucket: Any,
        settings: Settings,
    ) -> None:
        raise NotImplementedError()


@app.post("/upload")
async def post_upload(
    *,
    file: UploadFile = File(...),
    token: str = Form(...),
    dzuuid: pyd.UUID4 = Form(...),
    dzchunkindex: int = Form(...),
    dztotalchunkcount: int = Form(...),
    # dzchunkbyteoffset: int = Form(...),
    # dztotalfilesize: int = Form(...),
    # dzchunksize: int = Form(...),
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(Settings.get),
    bucket: Any = Depends(get_bucket),
) -> PlainTextResponse:
    try:
        folder = jwt.decode(
            token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"]
        )["folder"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired.")
    except Exception:
        logger.exception("Some token error:")
        raise HTTPException(
            status_code=400, detail="Something is wrong with your token."
        )
    try:
        if await save_chunk(file, dzuuid, dzchunkindex, dztotalchunkcount, settings):
            if settings.gcs_path:
                background_tasks.add_task(
                    upload_gcs, file.filename, folder, dzuuid, bucket, settings
                )
            elif settings.local_path:
                await save_local_file(file.filename, folder, dzuuid, settings)
    except Exception:
        logger.exception("Some error while saving:")
        raise HTTPException(status_code=500, detail="Cannot save the file.")
    return PlainTextResponse(status_code=204)
