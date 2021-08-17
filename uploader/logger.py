import inspect
import json
import os
import sys
from typing import Any, Union
from typing import Mapping
from typing import MutableMapping

import structlog
from structlog._frames import _find_first_app_frame_and_name
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer


def _show_module_info_processor(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    f, name = _find_first_app_frame_and_name(additional_ignores=["logging", __name__])
    if not f:
        return event_dict
    frameinfo = inspect.getframeinfo(f)
    assert frameinfo
    module = inspect.getmodule(f)
    if not module:
        return event_dict

    event_dict["module"] = module.__name__
    event_dict["lineno"] = frameinfo.lineno
    event_dict["pathname"] = frameinfo.filename
    event_dict["funcName"] = frameinfo.function
    return event_dict


def _parse_access_log(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    if event_dict["logger"] == "hypercorn.access":
        al = json.loads(event_dict["event"])
        event_dict["http_request"] = al
        event_dict[
            "event"
        ] = f'"{al.pop("status_line")}" {al["status_code"]} {al["status_phrase"]}'

    return event_dict


def configure_logging(log_level: str = "DEBUG") -> dict[str, Any]:
    renderer: Union[JSONRenderer, ConsoleRenderer]
    if not os.isatty(sys.stdout.fileno()):
        renderer = JSONRenderer()
    else:
        renderer = ConsoleRenderer(colors=True)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            _show_module_info_processor,
            _parse_access_log,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper("iso"),
            structlog.processors.UnicodeDecoder(),
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    pre_chain = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        _show_module_info_processor,
        _parse_access_log,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper("iso"),
        structlog.contextvars.merge_contextvars,
    ]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": renderer,
                "foreign_pre_chain": pre_chain,
            },
            "uploader": {"format": "%(message)s"},
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  # Default is stderr
            },
            "uploader": {
                "formatter": "uploader",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",  # Default is stderr
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": True,
            },
            "uploader": {
                "handlers": ["uploader"],
                "level": log_level,
                "propagate": False,
            },
        },
    }
