from simgen_ssg.parsers.base import BaseParser
from simgen_ssg.parsers.markdown import MarkdownParser


def parser_for_file(file_path) -> BaseParser:
    def identify_parser(file_path):
        if file_path.endswith(".md"):
            return MarkdownParser
        else:
            return BaseParser

    return identify_parser(file_path)(file_path)
