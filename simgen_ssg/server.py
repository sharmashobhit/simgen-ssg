import asyncio
import os
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

from hypercorn.asyncio import serve as hypercorn_serve
from hypercorn.config import Config
from qdrant_client import AsyncQdrantClient

from simgen_ssg import simgen_http as simgen_http
from simgen_ssg import utils
from simgen_ssg.parsers import parser_for_file
from simgen_ssg.watcher import files_updated_since

logger = utils.get_logger(__name__)


class QdrantServer:
    QDRANT_COLLECTION_NAME = "simgen"

    def __init__(self, cache_dir, model):
        self.cache_dir = cache_dir
        self.model = model
        self.qdrant_client: Optional[AsyncQdrantClient] = None
        self.sql_client: Optional[sqlite3.Connection] = None

    async def setup_qdrant(self, force=False):
        if force or self.qdrant_client is None:
            cache_dir = Path(self.cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            qdrant_db_path = cache_dir.joinpath("qdrant_db")
            sqlite_db_path = cache_dir.joinpath("indexes.db")
            os.makedirs(qdrant_db_path, exist_ok=True)
            self.qdrant_client = AsyncQdrantClient(path=qdrant_db_path)
            self.sql_client = sqlite3.connect(sqlite_db_path)

            self.sql_client.execute(
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
            return True
        return False

    async def fetch_model(self):
        await self.setup_qdrant()
        if self.qdrant_client is None:
            raise Exception("Qdrant client not initialized")
        self.qdrant_client.set_model(self.model)
        existing_collections = await self.qdrant_client.get_collections()
        logger.info(f"Existing collections: {existing_collections.collections}")
        if all(
            [
                collection.name != self.QDRANT_COLLECTION_NAME
                for collection in existing_collections.collections
            ]
        ):
            logger.info(
                f"Could not find collection: {self.QDRANT_COLLECTION_NAME}. Creating new collection"
            )
            # TODO: Check the request model and create collection if the vector_config is different
            await self.qdrant_client.create_collection(
                collection_name=self.QDRANT_COLLECTION_NAME,
                vectors_config=self.qdrant_client.get_fastembed_vector_params(),
            )

    async def save_content_to_db(self, id, content, collection_name, m_time):
        content_chunks = list(utils.chunks(content, 500))
        # Batch insert into both sqlite and qdrant
        logger.debug(f"Saving content to db: {id}. Found chunks: {len(content_chunks)}")
        if self.sql_client is None or self.qdrant_client is None:
            raise Exception("Databases not initialized")
        self.sql_client.execute(
            "INSERT OR IGNORE INTO indexes (file_path, chunk_id, updated_at) VALUES {};".format(
                ",".join(
                    [f"('{id}', {index}, {m_time})" for index in range(1, len(content_chunks) + 1)]
                )
            )
        )
        self.sql_client.commit()
        res = self.sql_client.execute(
            f"SELECT * FROM indexes where file_path='{id}' ORDER BY chunk_id"
        ).fetchall()
        if len(res) > len(content_chunks):
            # The existing content sync'd is more than the new content. Delete the extra content
            logger.debug(f"Deleting extra content for ID: {id}")
            self.sql_client.execute(
                f"DELETE FROM indexes where file_path='{id}' AND chunk_id>{len(content_chunks)}"
            )
            res = res[: len(content_chunks)]
        logger.debug(f"Saving content to qdrant: {id}")
        await self.qdrant_client.add(
            collection_name=self.QDRANT_COLLECTION_NAME,
            documents=content_chunks,
            ids=[instance[0] for instance in res],
            metadata=[
                {"file_path": id, "collection": collection_name, "id": instance[0]}
                for instance in res
            ],
        )

    async def _file_watcher(self, dir_path):
        if self.sql_client is None:
            raise Exception("Databases not initialized")
        res = self.sql_client.execute(
            "SELECT updated_at from indexes ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        last_mtime = res[0] if (res and len(res) > 0) else 0
        logger.info(f"Last updated time: {last_mtime}")
        for file_path, rel_path, file_mtime in files_updated_since(dir_path, last_mtime):
            file_path = Path(file_path)
            logger.debug(f"File updated {rel_path}. Last updated time: {file_mtime}")

            rel_path = os.path.relpath(file_path, dir_path)
            parser = parser_for_file(file_path)
            logger.debug(f"Found parser for the file: {rel_path}. {parser.__class__}")
            await self.save_content_to_db(
                rel_path, parser.content, file_path.parent.name, file_mtime
            )

    async def serve(self, directories: List[str], queue: asyncio.Queue, watch: bool = False):
        await queue.put({"ready": False})
        logger.info("Initializing File watcher. This may take a while...")
        await asyncio.gather(*[self._file_watcher(dir) for dir in directories])
        await queue.put({"ready": True})


async def mark_ready(app, queue):
    while True:
        resp = await queue.get()
        if isinstance(resp, dict) and "ready" in resp:
            app.ready = resp["ready"]
            if app.ready:
                return


async def run(directories, bind, watch, cache_dir, model):
    app = simgen_http.app
    qdrant_server = QdrantServer(cache_dir=cache_dir, model=model)
    await qdrant_server.setup_qdrant()
    await qdrant_server.fetch_model()
    app.content_dirs = directories
    app.qdrant_server = qdrant_server
    try:
        hypercorn_config = Config()
        hypercorn_config.bind = bind
        queue: asyncio.Queue = asyncio.Queue()
        app.queue = queue
        await asyncio.gather(
            hypercorn_serve(app, hypercorn_config),
            mark_ready(app, queue),
            qdrant_server.serve(directories, queue, watch),
        )  # fastAPI  # Qdrant file watcher
    except KeyboardInterrupt:
        sys.exit(1)
