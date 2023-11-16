def chunks(content, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(content), n):
        yield content[i : i + n]
