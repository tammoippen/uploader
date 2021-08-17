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

import os
from pathlib import Path
import secrets
from time import sleep, time

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
import jwt
from loguru import logger
from pydantic.types import UUID4
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from ._gcs import upload_gcs
from ._settings import Settings

app = FastAPI()
app.mount("/static", StaticFiles(packages=["uploader"]), name="static")
templates = Jinja2Templates(
    directory=f"{os.path.dirname(os.path.realpath(__file__))}/templates"
)
settings = Settings()


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/token")
async def get_token(request: Request):
    return templates.TemplateResponse("get_token.html", {"request": request})


@app.post("/token")
async def post_token(
    request: Request,
    password: str = Form(...),
    duration: int = Form(...),
    folder: str = Form(...),
):
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
async def get_upload(request: Request, token: str):
    return templates.TemplateResponse(
        "upload.html", {"request": request, "token": token}
    )


@app.post("/upload")
async def post_upload(*,
    file: UploadFile = File(...),
    token: str = Form(...),
    dzuuid: UUID4 = Form(...),
    dzchunkindex: int = Form(...),
    dztotalchunkcount: int = Form(...),
    dzchunkbyteoffset: int = Form(...),
    dztotalfilesize: int = Form(...),
    dzchunksize: int = Form(...),
):
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
        await save_file(file, folder)
    except Exception:
        logger.exception("Some error while saving:")
        raise HTTPException(status_code=500, detail="Cannot save the file.")
    return PlainTextResponse(status_code=204)


async def save_file(upload_file: UploadFile, folder: str) -> None:
    if settings.gcs_path:
        await upload_gcs(upload_file, folder, settings)
    elif settings.local_path:
        dest = Path(settings.local_path) / folder
        dest.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest / upload_file.filename, "ab") as f:
            while True:
                data = await upload_file.read(10 * 2 ** 20)
                if not data:
                    break
                await f.write(data)
