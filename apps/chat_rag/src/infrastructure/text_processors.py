import re
from src.domain.interfaces import TextCleaner

class HyphenationCleaner(TextCleaner):
    def clean(self, text: str) -> str:
        return re.sub(r"(\w)-\n(\w)", r"\1\2", text)

class NewlineCleaner(TextCleaner):
    def clean(self, text: str) -> str:
        return re.sub(r"(?<!\n)\n(?!\n)", " ", text)

class MultipleNewlineCleaner(TextCleaner):
    def clean(self, text: str) -> str:
        return re.sub(r"\n{2,}", "\n", text)