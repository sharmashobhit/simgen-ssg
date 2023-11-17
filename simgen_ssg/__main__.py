import os
import sys
import time
from qdrant_client import AsyncQdrantClient
from qdrant_client.async_qdrant_fastembed import SUPPORTED_EMBEDDING_MODELS
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve as hypercorn_serve

from typing import Union
from qdrant_client.http import models
from fastapi import FastAPI
from simgen_ssg.watcher import files_updated_since
from simgen_ssg.parsers import parser_for_file
from simgen_ssg import utils
import asyncclick as click

# Import sqlite
import sqlite3

app = FastAPI(debug=True)
collection_name = "simgen_ssg"
global q_client
global con


def setup_qdrant():
    global q_client
    global con
    os.makedirs("./db/", exist_ok=True)
    q_client = AsyncQdrantClient(path="./db/")
    con = sqlite3.connect("db/indexes.db")
    # q_client.set_model()
    # if collection_name not in q_client.get_collections():
    #     q_client.create_collection(collection_name=collection_name)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/{file_path:path}")
async def read_item(file_path: str):
    parser = parser_for_file(file_path)
    qdrant_result = await q_client.query(
        collection_name=collection_name,
        query_text=parser.content,
        query_filter=models.Filter(
            must_not=[
                models.FieldCondition(
                    key="file_path",
                    match=models.MatchValue(value=file_path),
                ),
            ]
        ),
        limit=10,
    )
    files = [instance.metadata["file_path"] for instance in qdrant_result]
    return list(dict.fromkeys(files))


# async def sync_file(file_path: str):
#     parser = parser_for_file(file_path)
#     q_client.add(
#         collection_name=collection_name,
#         documents=utils.chunks(parser.content, 1000),
#     )


async def _file_watcher(dir_path):
    res = con.execute("SELECT updated_at from indexes ORDER BY updated_at DESC LIMIT 1").fetchone()
    last_mtime = res[0] if (res and len(res) > 0) else 0
    for file_path, file_mtime in files_updated_since(dir_path, last_mtime):
        print(os.path.relpath(file_path, dir_path))
        print(f"Syncing {file_path}")
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
            metadata=[{"file_path": file_path} for _ in ids],
        )


async def file_watcher(should_watch=False, dirs=[]):
    print("Processing files")
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
    # for dir in dirs:
    #     await _file_watcher(dirs)
    if should_watch:
        print("Watching files for changes")
        while True:
            await asyncio.sleep(3)
            await asyncio.gather(*[_file_watcher(dir) for dir in dirs])
    # while True:
    #     try:
    #         await _file_watcher()
    #         await asyncio.sleep(3)
    #     except KeyboardInterrupt:
    #         print("Exiting!")
    #         return

    # con.cursor()
    # for file_path in
    # for file_path in file_times(p):
    #     await sync_file(file_path)
    #     break
    # pass
    # last_mtime = max(file_times(p))
    # while True:
    #     print(max(file_times(p)))
    #     await asyncio.sleep(5)
    # try:
    #     while True:
    #         print("Watching files")
    #         await asyncio.sleep(5)
    # except KeyboardInterrupt:
    #     print("Exiting!")
    #     return


@click.group()
async def cli():
    pass


@cli.command()
@click.option("--dir", "-d", default=["."], help="Content directory", multiple=True)
@click.option("--watch", "-w", default=False, help="Content directory", is_flag=True)
async def serve(dir, watch):
    """
    SimGen SSG: A reccomendation engine for static site generators
    """
    # loop = asyncio.get_running_loop()
    setup_qdrant()
    try:
        await asyncio.gather(
            hypercorn_serve(app, Config()),
            file_watcher(watch, dirs=dir),
        )  # fastAPI  # Qdrant file watcher
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    cli(_anyio_backend="asyncio")
