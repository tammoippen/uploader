import logging.config
import os

from uploader.logger import configure_logging


logconfig_dict = configure_logging(os.environ.get("LOG_LEVEL", "DEBUG"))
logconfig_dict["loggers"]["hypercorn.error"] = {
    "handlers": ["default"],
    "level": "INFO",
    "propagate": False,
}
logconfig_dict["loggers"]["hypercorn.access"] = {
    "handlers": ["default"],
    "level": "INFO",
    "propagate": False,
}
logging.config.dictConfig(logconfig_dict)

bind = [f"{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '80')}"]
accesslog = "-"
access_log_format = (
    '{"status_line": "%(r)s", "remoteIp": "%(h)s", "requestMethod": "%(m)s", '
    '"protocol": "%(S)s/%(H)s", "path": "%(U)s", '
    '"query": "%(q)s", "status": %(s)i, '
    '"status_phrase": "%(st)s", "responseSize": %(B)s, '
    '"latency": "%(L)s", "origin": "%({origin}i)s", '
    '"referer": "%(f)s", "userAgent": "%(a)s", '
    '"host": "%({host}i)s"}'
)
