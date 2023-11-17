# from qdrant_client.async_qdrant_fastembed import SUPPORTED_EMBEDDING_MODELS
import asyncio
import logging
import os

# Import sqlite
import sqlite3
import sys
from pathlib import Path

import asyncclick as click
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from hypercorn.asyncio import serve as hypercorn_serve
from hypercorn.config import Config
from qdrant_client import AsyncQdrantClient

# from typing import Union
from qdrant_client.http import models

from simgen_ssg import utils
from simgen_ssg.parsers import parser_for_file
from simgen_ssg.watcher import files_updated_since

fw_logger = logging.getLogger("file_watch")
fw_logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter(
        "[%(asctime)s.%(msecs)03d] [%(process)s] (%(name)s) [%(levelname)s] - %(message)s"
    )
)
fw_logger.addHandler(stream_handler)


app = FastAPI(debug=True)
app.ready = False
collection_name = "simgen_ssg"
global q_client
global con


def setup_qdrant(cache_dir):
    global q_client
    global con
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    qdrant_db_path = cache_dir.joinpath("db")
    sqlite_db_path = cache_dir.joinpath("indexes.db")
    os.makedirs(cache_dir.joinpath("db"), exist_ok=True)
    q_client = AsyncQdrantClient(path=qdrant_db_path)
    con = sqlite3.connect(sqlite_db_path)

    # q_client.set_model()
    # if collection_name not in q_client.get_collections():
    #     q_client.create_collection(collection_name=collection_name)


@app.get("/")
async def read_root():
    response = {"ready": app.ready}
    if not app.ready:
        return JSONResponse(response)
    collection_instance = await q_client.get_collection(collection_name)
    response.update({"vectors": collection_instance.vectors_count})
    return JSONResponse(response)


@app.get("/{req_file_path:path}")
async def read_item(req_file_path: str):
    file_path = req_file_path
    for dir in app.content_dirs:
        new_path = os.path.join(dir, req_file_path)
        if os.path.exists(new_path):
            file_path = os.path.abspath(new_path)
            break
    else:
        return JSONResponse({"error": "File not found"}, status_code=404)
    file_path = Path(file_path)
    try:
        parser = parser_for_file(file_path)
        content = parser.content
    except FileNotFoundError:
        # Return 404
        return JSONResponse({"error": "File not found"}, status_code=404)
    else:
        qdrant_result = await q_client.query(
            collection_name=collection_name,
            query_text=content,
            query_filter=models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="file_path",
                        match=models.MatchValue(value=req_file_path),
                    ),
                ]
            ),
            limit=1,
        )
        response = list()
        for result in qdrant_result:
            result.metadata.update({"score": result.score})
            result.metadata.pop("document")
            response.append(result.metadata)
        # COnvert response list of dictionary to unique by file_path
        unique_response = []
        unique_keys = set()
        for item in response:
            key = item.get("file_path")
            if key not in unique_keys:
                unique_response.append(item)
                unique_keys.add(key)
        return JSONResponse(unique_response)


async def _file_watcher(dir_path):
    res = con.execute("SELECT updated_at from indexes ORDER BY updated_at DESC LIMIT 1").fetchone()
    last_mtime = res[0] if (res and len(res) > 0) else 0
    fw_logger.info(last_mtime)
    for file_path, file_mtime in files_updated_since(dir_path, last_mtime):
        file_path = Path(file_path)
        fw_logger.debug("File updated: %s" % file_path)
        if not os.path.isfile(file_path):
            continue
        file_mtime = os.path.getmtime(file_path)
        rel_path = os.path.relpath(file_path, dir_path)
        fw_logger.info(f"Syncing {file_path}")
        parser = parser_for_file(file_path)
        chunks = utils.chunks(parser.content, 500)
        ids = []
        content_chunks = []
        for index, chunk in enumerate(chunks):
            ids.append(index)
            content_chunks.append(chunk)
        # Batch insert into both sqlite and qdrant
        con.execute(
            "INSERT OR IGNORE INTO indexes (file_path, chunk_id, updated_at) VALUES {};".format(
                ",".join([f"('{file_path}', {index}, {file_mtime})" for index in ids])
            )
        )
        con.commit()
        res = con.execute(
            f"SELECT * FROM indexes where file_path='{file_path}' ORDER BY chunk_id"
        ).fetchall()
        if len(res) > len(content_chunks):
            # The existing content sync'd is more than the new content. Delete the extra content
            con.execute(
                f"DELETE FROM indexes where file_path='{file_path}' AND chunk_id>{len(content_chunks)}"
            )
            res = res[: len(content_chunks)]
        await q_client.add(
            collection_name=collection_name,
            documents=content_chunks,
            ids=[instance[0] for instance in res],
            metadata=[
                {"file_path": rel_path, "collection": file_path.parent.name, "id": file_path.name}
                for _ in ids
            ],
        )


async def file_watcher(should_watch=False, dirs=[]):
    fw_logger.info("Processing files")
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS indexes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        chunk_id INTEGER NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(file_path, chunk_id)
    );
    """
    )
    await asyncio.gather(*[_file_watcher(dir) for dir in dirs])
    app.ready = True
    if should_watch:
        fw_logger.info("Watching files for changes")
        while True:
            await asyncio.sleep(3)
            await asyncio.gather(*[_file_watcher(dir) for dir in dirs])


@click.group()
async def cli():
    pass


@cli.command()
@click.option("--cache-dir", "-c", default="./.simgen_cache", help="Cache directory")
@click.option("--model", "-m", default="BAAI/bge-small-en", help="Model name")
async def fetch_model(cache_dir, model):
    """
    Set the model to use for embeddings
    """
    setup_qdrant(cache_dir)
    global q_client
    q_client.set_model(model)


@cli.command()
@click.option("--dir", "-d", default=["."], help="Content directory")
@click.option("--bind", "-b", default="127.0.0.1:8000", help="Content directory")
@click.option("--watch", "-w", default=False, help="Content directory", is_flag=True)
@click.option("--cache-dir", "-c", default="./.simgen_cache", help="Cache directory")
@click.option("--model", "-m", default="BAAI/bge-small-en", help="Model name")
async def serve(dir, bind, watch, cache_dir, model):
    """
    SimGen SSG: A reccomendation engine for static site generators
    """
    # loop = asyncio.get_running_loop()
    setup_qdrant(cache_dir)
    global q_client
    q_client.set_model(model)
    app.content_dirs = [dir]
    try:
        hypercorn_config = Config()
        hypercorn_config.bind = bind
        await asyncio.gather(
            hypercorn_serve(app, hypercorn_config),
            file_watcher(watch, dirs=app.content_dirs),
        )  # fastAPI  # Qdrant file watcher
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
