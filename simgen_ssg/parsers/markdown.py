from simgen_ssg.parsers.base import AbstractBaseParser


class MarkdownParser(AbstractBaseParser):
    def parse(self):
        with open(self.file_path, "r") as f:
            self._content = f.read()
