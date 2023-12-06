def chunks(content, maxlength):
    """Yield successive n-sized chunks from lst."""
    start = 0
    end = 0
    if not content or len(content) == 0:
        return ""
    while start + maxlength < len(content) and end != -1:
        end = content.rfind(" ", start, start + maxlength + 1)
        yield content[start:end]
        start = end + 1
    yield content[start:]
