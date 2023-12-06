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
from qdrant_client.http import models

from simgen_ssg import utils
from simgen_ssg.parsers import parser_for_file
from simgen_ssg.watcher import files_updated_since

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


app = FastAPI()
app.ready = False
QDRANT_COLLECTION_NAME = "simgen"

q_client: AsyncQdrantClient
con: sqlite3.Connection


async def setup_qdrant(cache_dir):
    global q_client
    global con
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    qdrant_db_path = cache_dir.joinpath("db")
    sqlite_db_path = cache_dir.joinpath("indexes.db")
    os.makedirs(cache_dir.joinpath("db"), exist_ok=True)
    q_client = AsyncQdrantClient(path=qdrant_db_path)
    con = sqlite3.connect(sqlite_db_path)

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


@app.get("/")
async def index():
    response = {"ready": app.ready}
    if not app.ready:
        return JSONResponse(response)
    collection_instance = await q_client.get_collection(QDRANT_COLLECTION_NAME)
    response.update({"vectors": collection_instance.vectors_count})
    return JSONResponse(response)


@app.post("/add")
async def save_content(id: str, body: str, collection_name: str):
    await save_content_to_db(id, body, collection_name, file_mtime)


@app.get("/recommend")
async def get_recommendations(id: str, limit: int = 1):
    """
    Add vectors to the collection
    """
    file_path = id
    http_logger.info(f"Getting recommendations for {file_path}")
    for dir in app.content_dirs:
        new_path = os.path.join(dir, id)

        if os.path.exists(new_path):
            file_path = os.path.abspath(new_path)
            break
    else:
        return JSONResponse({"error": "File1 not found"}, status_code=404)
    try:
        parser = parser_for_file(Path(file_path))
        content = parser.content
    except FileNotFoundError:
        # Return 404
        return JSONResponse({"error": "File2 not found"}, status_code=404)
    else:
        qdrant_result = await q_client.query(
            collection_name=QDRANT_COLLECTION_NAME,
            query_text=content,
            query_filter=models.Filter(
                must_not=[
                    models.FieldCondition(
                        key="file_path",
                        match=models.MatchValue(value=id),
                    ),
                ]
            ),
            limit=limit,
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


async def save_content_to_db(id, content, collection_name, m_time):
    content_chunks = list(utils.chunks(content, 500))
    # Batch insert into both sqlite and qdrant
    fw_logger.debug(f"Saving content to db: {id}. Found chunks: {len(content_chunks)}")
    con.execute(
        "INSERT OR IGNORE INTO indexes (file_path, chunk_id, updated_at) VALUES {};".format(
            ",".join(
                [f"('{id}', {index}, {m_time})" for index in range(1, len(content_chunks) + 1)]
            )
        )
    )
    con.commit()
    res = con.execute(f"SELECT * FROM indexes where file_path='{id}' ORDER BY chunk_id").fetchall()
    if len(res) > len(content_chunks):
        # The existing content sync'd is more than the new content. Delete the extra content
        fw_logger.debug(f"Deleting extra content for ID: {id}")
        con.execute(
            f"DELETE FROM indexes where file_path='{id}' AND chunk_id>{len(content_chunks)}"
        )
        res = res[: len(content_chunks)]
    fw_logger.debug(f"Saving content to qdrant: {id}")
    await q_client.add(
        collection_name=QDRANT_COLLECTION_NAME,
        documents=content_chunks,
        ids=[instance[0] for instance in res],
        metadata=[
            {"file_path": id, "collection": collection_name, "id": instance[0]} for instance in res
        ],
    )
    pass


async def _file_watcher(dir_path):
    global con
    res = con.execute("SELECT updated_at from indexes ORDER BY updated_at DESC LIMIT 1").fetchone()
    last_mtime = res[0] if (res and len(res) > 0) else 0
    fw_logger.info(f"Last updated time: {last_mtime}")
    for file_path, rel_path, file_mtime in files_updated_since(dir_path, last_mtime):
        file_path = Path(file_path)
        fw_logger.debug(f"File updated {rel_path}. Last updated time: {file_mtime}")

        rel_path = os.path.relpath(file_path, dir_path)
        parser = parser_for_file(file_path)
        fw_logger.debug(f"Found parser for the file: {rel_path}. {parser.__class__}")
        await save_content_to_db(rel_path, parser.content, file_path.parent.name, file_mtime)


async def file_watcher(should_watch=False, dirs=[]):
    fw_logger.info("Initializing File watcher. This may take a while...")
    await asyncio.gather(*[_file_watcher(dir) for dir in dirs])
    app.ready = True
    fw_logger.info("Files synchronized. The server is ready to accept connections")
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
    await setup_qdrant(cache_dir)
    global q_client
    fw_logger.info(f"Model set to {model}")
    q_client.set_model(model)
    fw_logger.info(f"Model downloaded and ready to be served")


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
    await setup_qdrant(cache_dir)
    global q_client
    q_client.set_model(model)
    existing_collections = await q_client.get_collections()
    fw_logger.info(f"Existing collections: {existing_collections.collections}")
    if all(
        [
            collection.name != QDRANT_COLLECTION_NAME
            for collection in existing_collections.collections
        ]
    ):
        fw_logger.info(
            f"Could not find collection: {QDRANT_COLLECTION_NAME}. Creating new collection"
        )
        # TODO: Check the request model and create collection if the vector_config is different
        await q_client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=q_client.get_fastembed_vector_params(),
        )

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
