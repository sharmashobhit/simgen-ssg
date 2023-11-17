from pathlib import Path

from simgen_ssg.parsers.base import BaseParser
from simgen_ssg.parsers.markdown import MarkdownParser


def parser_for_file(file_path: Path) -> BaseParser:
    def identify_parser(file_path: Path):
        if file_path.is_file():
            _, ext = file_path.name.rsplit(".", 1)
            if ext == "md":
                return MarkdownParser
            else:
                return BaseParser
        raise Exception("Not a file")

    return identify_parser(file_path)(file_path)
