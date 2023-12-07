import logging
import os
import re
from pathlib import Path

blacklist = ["^\.", "\.swp$"]
whitelist = ["[^_].*\.md$"]

fw_logger = logging.getLogger("file_watch")
fw_logger.setLevel(logging.DEBUG)


def file_filter(name):
    def run_filters(name, filters):
        for regex in filters:
            if re.search(regex, name):
                return True
        return False

    if len(whitelist) > 0:
        return run_filters(name, whitelist)
    else:
        return not run_filters(name, blacklist)


def files_updated_since(path, last_mtime):
    req_path = Path(path)
    if not req_path.exists():
        raise FileNotFoundError("Path %s does not exist" % path)
    if not req_path.is_dir():
        raise NotADirectoryError("Path %s is not a directory" % path)
    # assert False, os.walk(req_path)
    for root, _, files in os.walk(req_path):
        for file_name in filter(file_filter, files):
            file_path = Path(root).joinpath(file_name)
            if not os.path.isfile(file_path):
                continue
            file_mtime = os.path.getmtime(file_path)
            if file_mtime > last_mtime:
                yield (file_path, os.path.relpath(file_path, req_path), file_mtime)
