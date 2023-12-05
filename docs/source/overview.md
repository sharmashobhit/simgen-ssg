# Overview

`simgen-ssg` provides an easy way for you to generate similar pages for your static site. It uses Qdrant vector database along with [fastembed](https://qdrant.github.io/fastembed/) under the hood to generate vector embeddings for the chunks in your site.

# Usage Guide

## Installation

### Docker installation

The image is available on Github Container Registry. You can pull the image using:

```bash
docker pull ghcr.io/sharmashobhit/simgen-ssg:latest
```

You can then run using the following command:

```bash
docker run -v .:/docs/ -p 8000:8000 ghcr.io/sharmashobhit/simgen-ssg:latest
```
