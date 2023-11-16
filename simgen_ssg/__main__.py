# import argparse
#
import time
from qdrant_client import QdrantClient
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

from typing import Union
from qdrant_client.http import models
from fastapi import FastAPI
from watcher import files_updated_since
from parsers import parser_for_file
from simgen_ssg import utils

# Import sqlite
import sqlite3

app = FastAPI(debug=True)
p = "./docs/"
collection_name = "simgen_ssg"
q_client = QdrantClient(path="./db/")


def setup_qdrant():
    pass
    # if collection_name not in q_client.get_collections():
    #     q_client.create_collection(collection_name=collection_name)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/{file_path:path}")
def read_item(file_path: str):
    # sync_file(file_path)
    parser = parser_for_file(file_path)
    qdrant_result = q_client.query(
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
    )
    files = [instance.metadata["file_path"] for instance in qdrant_result]
    return list(dict.fromkeys(files))


# async def sync_file(file_path: str):
#     parser = parser_for_file(file_path)
#     q_client.add(
#         collection_name=collection_name,
#         documents=utils.chunks(parser.content, 1000),
#     )


async def file_watcher():
    con = sqlite3.connect("db/indexes.db")
    con.execute(
        """
    CREATE TABLE IF NOT EXISTS indexes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        chunk_id INTEGER NOT NULL,
        UNIQUE(file_path, chunk_id)
    );
    """
    )
    # res = con.execute("INSERT INTO indexes (file_path, chunk_id) VALUES ('test', 1);")
    # print(res.fetchall())
    for file_path in files_updated_since(p, 0):
        parser = parser_for_file(file_path)
        chunks = utils.chunks(parser.content, 500)
        ids = []
        content_chunks = []
        for index, chunk in enumerate(chunks):
            ids.append(index)
            content_chunks.append(chunk)
        # Batch insert into both sqlite and qdrant
        con.execute(
            "INSERT OR IGNORE INTO indexes (file_path, chunk_id) VALUES {};".format(
                ",".join([f"('{file_path}', {index})" for index in ids])
            )
        )
        con.commit()
        res = con.execute(
            f"SELECT * FROM indexes where file_path='{file_path}' ORDER BY chunk_id"
        ).fetchall()

        qdrant_result = q_client.add(
            collection_name=collection_name,
            documents=content_chunks,
            ids=[instance[0] for instance in res],
            metadata=[{"file_path": file_path} for _ in ids],
        )
        print(qdrant_result)
        # print(file_path)
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


async def main():
    setup_qdrant()
    await asyncio.gather(serve(app, Config()), file_watcher())  # fastAPI  # Qdrant file watcher


if __name__ == "__main__":
    asyncio.run(main())
