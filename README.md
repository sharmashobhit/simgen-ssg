# simgen-ssg

## What is this?

This project aims to provide a build time API for statically generated sites. It helps you build a recommendation engine for your static site to help you link your content together.

## How does it work?

The project uses Qdrant vector search under the hood to generate vector embeddings for the chunks in your site. It then provides an API to query the vector embeddings across the database to generate related content recommendations.

## How do I use it?

### Installation

#### Dev environment

1. Install the package using `pip install simgen-ssg`
2. Run the server using `simgen-ssg
