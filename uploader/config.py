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
    '{"status_line": "%(r)s", "remote_address": "%(h)s", "method": "%(m)s", '
    '"scheme": "%(S)s", "protocol": "%(H)s", "path": "%(U)s", '
    '"query": "%(q)s", "status_code": %(s)i, '
    '"status_phrase": "%(st)s", "response_length": %(B)s, '
    '"latency_sec": %(T)i, "latency_microsec": %(D)i, "origin": "%({origin}i)s", '
    '"referer": "%(f)s", "user_agent": "%(a)s", '
    '"host": "%({host}i)s"}'
)
