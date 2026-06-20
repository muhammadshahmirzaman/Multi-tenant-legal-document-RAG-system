import logging
import structlog


def setup_logging():
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    pre_chain = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
    ]
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            *pre_chain,
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def get_logger(name: str = __name__):
    return structlog.get_logger(name)
