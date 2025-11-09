class TokenStore:

    def __init__(self):
        self._map = {}

    def register(self, token, value):
        self._map[token] = value

    def reveal(self, text):
        for token, value in self._map.items():
            text = text.replace(token, value)
        return text
