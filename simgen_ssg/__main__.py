import asyncio
import logging
import os

# Import sqlite
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from qdrant_client.http import models

from simgen_ssg import utils
from simgen_ssg.cli import cli

fw_logger = logging.getLogger("file_watch")
http_logger = logging.getLogger("http")
fw_logger.setLevel(logging.INFO)
http_logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter(
        "[%(asctime)s.%(msecs)03d] [%(process)s] (%(name)s) [%(levelname)s] - %(message)s"
    )
)
fw_logger.addHandler(stream_handler)


# async def file_watcher(should_watch=False, dirs=[]):
#     fw_logger.info("Initializing File watcher. This may take a while...")
#     await asyncio.gather(*[_file_watcher(dir) for dir in dirs])
#     app.ready = True
#     fw_logger.info("Files synchronized. The server is ready to accept connections")
#     if should_watch:
#         fw_logger.info("Watching files for changes")
#         while True:
#             await asyncio.sleep(3)
#             await asyncio.gather(*[_file_watcher(dir) for dir in dirs])


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
