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

```O

## Retrieve recommendations

Once you have generated the embeddings, you can retrieve recommendations for a given page using the endpoint `/recommend`. The endpoint accepts a `GET` request with the following body
