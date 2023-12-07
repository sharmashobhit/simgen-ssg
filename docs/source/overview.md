# Overview

`simgen-ssg` provides an easy way for you to generate similar pages for your static site. It uses Qdrant vector database along with [fastembed](https://qdrant.github.io/fastembed/) under the hood to generate vector embeddings for the chunks in your site.

# Prerequisites

Check out the [Installation](installation.md) guide to get the system ready with `simgen-ssg`.

# Usage

`simgen-ssg` iterates over your static files and generates vector embeddings for each file. It then uses these embeddings to generate similar pages recommendation for each page.

`simgen-ssg` exposes an HTTP API which can be used to get recommendations for a given page or a given chunk of text.

## Generating embeddings

### Content files

To generate embeddings for your static site, run the following command:

```bash
simgen serve --dir /path/to/directory
```

This command will generate embeddings for the provided directory and start an HTTP server on port `8000`.

### Dynamic content/HTTP endpoint

If you have dynamic content and you want to generate bindings for it, you can use the endpoint `/embed` to manually embed the content. The endpoint accepts a `POST` request with the following body:

```bash
curl -X POST \
-H "Content-Type: application/json" \
-d '{"text": "Content document"}' \
http://localhost:8000/embed

```

## Retrieve recommendations

### For a given page

Once you have generated the embeddings, you can retrieve recommendations for a given page using the endpoint `/recommend`. The endpoint accepts a `GET` request with the following query parameters:

- `id`: The ID of the page for which you want to retrieve recommendations. File path relative to the root directory is used as the ID.
- `limit` [Optional] [Default: 3]: The maximum number of recommendations you want to retrieve.

```bash
curl 'http://127.0.0.1:8000/recommend?id=path/to/file.md&limit=3'
```

The response will be a JSON array of recommendations. Each recommendation will have the following fields:

```json
[
  {
    "file_path": "source/CONTRIBUTING.md",
    "collection": "source",
    "id": 8,
    "score": 0.9284217639217309
  },
  {
    "file_path": "source/installation.md",
    "collection": "source",
    "id": 1,
    "score": 0.9251359276636962
  },
  {
    "file_path": "source/CHANGELOG.md",
    "collection": "source",
    "id": 23,
    "score": 0.9235673105214043
  }
]
```

### For a given text

You can also retrieve recommendations for a given text using the endpoint `/recommend`. The endpoint accepts a `GET` request with the following query parameters:

- `q`: The query text for which you want to retrieve recommendations.
- `limit` [Optional] [Default: 3]: The maximum number of recommendations you want to retrieve.

```bash
curl 'http://127.0.0.1:8000/recommend?q=This%20is%20a%20sample%20text&limit=2'
```

The response will be a JSON array of recommendations. Each recommendation will have the following fields:

```json
[
  {
    "file_path": "source/CONTRIBUTING.md",
    "collection": "source",
    "id": 8,
    "score": 0.9284217639217309
  },
  {
    "file_path": "source/installation.md",
    "collection": "source",
    "id": 1,
    "score": 0.9251359276636962
  }
]
```

## Deployment

`simgen-ssg` is available as a Docker image. The easiest way to get started is to use `docker-compose` to deploy it alongside your app.

```docker-compose.yml
version: '3.3'

services:
  simgen:
    image: ghcr.io/sharmashobhit/simgen-ssg:latest
    ports:
      - 8000:8000
    volumes:
      - ./docs:/app/docs
  web:
    ...
```

In your app you can now use the endpoint `http://simgen:8000/recommend` to get recommendations for a given page or text.
