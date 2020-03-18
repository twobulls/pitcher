import os, sys
from loguru import logger
from typing import Any, Mapping

from pitcher import Application, Request, Route
from pitcher.middleware import Middleware, CORSMiddleware, AllowedHostMiddleware


cold_start = True  # instantiated once


def is_cold_start():
    result = False
    global cold_start
    if cold_start:
        result = True
        cold_start = False
    return result


logger.add(sys.stdout, level=os.getenv("LOG_LEVEL", "INFO"), serialize=True)

logger_configured = False


def configure_logger(event: Mapping[str, Any], context: Any, app: Application):
    global logger_configured
    if not logger_configured:
        app.logger = logger.bind(
            lambda_request_id=context.aws_request_id,
            lambda_function_name=context.function_name,
            lambda_function_arn=context.invoked_function_arn,
            lambda_function_memory_size=context.memory_limit_in_mb,
            cold_start=is_cold_start(),
        )
        logger_configured = True


def hello_world(request: Request, app: Any) -> dict:
    name = request.params["name"]
    data = {"message": f"hello {name}"}
    return data


routes = [Route("/hello/{name}", hello_world, methods=["GET"])]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_headers=["authorization", "content-type"],
        allow_methods=["*"],
    ),
]

app = Application(
    name="hello",
    routes=routes,
    middleware=middleware,
    logger=logger,
    on_invocation=[configure_logger],
)
