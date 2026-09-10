
class Entity:
    def __init__(self, name, symbol, x, y):
        self.name = name
        self.symbol = symbol
        self.x = x
        self.y = y
        self.last_action = "criado"

    def record_action(self, action):
        self.last_action = action

    def debug_text(self):
        return f"name={self.name} | pos=({self.x}, {self.y}) | last_action={self.last_action}"
