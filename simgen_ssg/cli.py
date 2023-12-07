import asyncclick as click

from simgen_ssg import server


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
    qdrant_server = server.QdrantServer(cache_dir=cache_dir, model=model)
    await qdrant_server.setup_qdrant()
    await qdrant_server.fetch_model()


@cli.command()
@click.option("--dir", "-d", default=["."], help="Content directory", multiple=True)
@click.option("--bind", "-b", default="127.0.0.1:8000", help="Content directory")
@click.option("--watch", "-w", default=False, help="Content directory", is_flag=True)
@click.option("--cache-dir", "-c", default="./.simgen_cache", help="Cache directory")
@click.option("--model", "-m", default="BAAI/bge-small-en", help="Model name")
async def serve(dir, bind, watch, cache_dir, model):
    """
    SimGen SSG: A reccomendation engine for static site generators
    """

    await server.run(directories=dir, bind=bind, watch=watch, cache_dir=cache_dir, model=model)
