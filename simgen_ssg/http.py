import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from qdrant_client.http import models

from simgen_ssg import utils
from simgen_ssg.parsers import parser_for_file

logger = utils.get_logger(__name__)

app = FastAPI()
app.ready = False
app.qdrant_server = None


@app.get("/")
async def index():
    response = {"ready": app.ready}
    if not app.ready:
        return JSONResponse(response)
    q_client = app.qdrant_server.qdrant_client
    collection_instance = await q_client.get_collection(app.qdrant_server.QDRANT_COLLECTION_NAME)
    response.update({"vectors": collection_instance.vectors_count})
    return JSONResponse(response)


@app.post("/add")
async def save_content(id: str, body: str, collection_name: str):
    await app.qdrant_server.save_content_to_db(id, body, collection_name, time.time())


@app.get("/recommend")
async def get_recommendations(
    id: Optional[str] = "", q: Optional[str] = "", limit: Optional[int] = 1
):
    """
    Add vectors to the collection
    """
    q_client = app.qdrant_server.qdrant_client
    content = ""
    if id:
        file_path = id
        logger.info(f"Getting recommendations for {file_path}")
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
    elif q:
        content = q
    qdrant_result = await q_client.query(
        collection_name=app.qdrant_server.QDRANT_COLLECTION_NAME,
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
    # Convert response list of dictionary to unique by file_path
    unique_response = []
    unique_keys = set()
    for item in response:
        key = item.get("file_path")
        if key not in unique_keys:
            unique_response.append(item)
            unique_keys.add(key)
    return JSONResponse(unique_response)
