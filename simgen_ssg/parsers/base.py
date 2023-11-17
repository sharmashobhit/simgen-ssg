from abc import ABC, abstractmethod

# , abstractproperty


class AbstractBaseParser(ABC):
    def __init__(self, file_path):
        self.file_path = file_path
        self.last_processed = None
        self._content = None

    @abstractmethod
    def parse(self):
        pass

    @property
    def content(self):
        if self._content is None:
            self.parse()
        return self._content


class BaseParser(AbstractBaseParser):
    def parse(self):
        pass
