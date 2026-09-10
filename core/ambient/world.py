from core.ambient.tile import GRASS

class World: #Aqui fica o mundo gerado. Diferente do renderer, esse aqui é com variaveis pra construir o mundo. Pense em geografia.
    def __init__(self, width, height, default_tile=GRASS): #pode alterar a default_tile se necessario pra outra coisa
        self.width = width
        self.height = height
        self.entities = []
        self.occupancy = {}
        self.tiles = [
            [default_tile for x in range(width)]
            for y in range(height)
            ]


    #renderizador de texto. Demonstra o tabuleiro.
    def render_text(self):
        lines = []
                
        for row in self.tiles:

            symbols = []

            for tile in row:
                symbols.append(tile.symbol)

            line = "".join(symbols)
            lines.append(line)

        return "\n".join(lines)
    
    def render_debug(self): #Aqui monta o tabuleiro + coordenadas pra debug melhor.
        y_label_width = len(str(self.height - 1))

        header = " " * (y_label_width + 1)
        header += " ".join(str(x % 10) for x in range(self.width))

        lines = [header]

        for y, row in enumerate(self.tiles):
            line = " ".join(tile.symbol for tile in row)
            lines.append(f"{y:>{y_label_width}} {line}")

        return "\n".join(lines)
    #aqui é a função onde voce coloca uma tile singular em algum canto do mundo
    def set_tile(self, x, y, tile): # x = coluna, y = linha
        if not self.is_inside(x, y):
            raise ValueError(f"posição fora do mundo: x={x}, y={y}")

        self.tiles[y][x] = tile
    #aqui já preenche varios espaços com um tile, invés de fazer tudo singular. Como uma brush.
    def fill_rect(self, x, y, width, height, tile):
        for current_y in range(y, y + height):
            for current_x in range(x, x + width):
                self.set_tile(current_x, current_y, tile)

    #aqui preenche por inteiro o mundo com uma tile. Util para biomas/regiões especificas
    def fill(self, tile):
        for y in range(self.height):
            for x in range(self.width):
                self.set_tile(x, y, tile)
    #aqui define a borda, ou do mundo ou de algum canto. Util para construção de terreno
    def border_tile(self, tile):
        for x in range(self.width):
            self.set_tile(x, 0, tile)
            self.set_tile(x, self.height - 1, tile)

            for y in range(self.height):
                self.set_tile(0, y, tile)
                self.set_tile(self.width - 1, y, tile)
    #pega a variavel tile e atribui algo a ela.
    def get_tile(self, x, y):
        if not self.is_inside(x, y): #util para debug, saber se algo não acabou sumindo por burrice nossa.
            raise ValueError(f"posição fora do mundo: x={x}, y={y}")

        return self.tiles[y][x]
    #pra saber se algo está detro do mundo.
    def is_inside(self, x, y):
        return x >= 0 and x < self.width and y >= 0 and y < self.height

    def add_entity(self, entity, allow_occupied=False):
        if not self.is_inside(entity.x, entity.y):
            raise ValueError(f"entidade fora do mundo: x={entity.x}, y={entity.y}")

        if not allow_occupied and self.get_entity_at(entity.x, entity.y) is not None:
            raise ValueError("posição já ocupada")
        self.entities.append(entity)
        self.occupancy.setdefault((entity.x, entity.y), []).append(entity)

    def get_entity_at(self, x, y):
        entities = self.occupancy.get((x, y), ())
        return entities[0] if entities else None

    def get_entities_at(self, x, y):
        return tuple(self.occupancy.get((x, y), ()))

    def remove_entity(self, entity):
        key = (entity.x, entity.y)
        occupants = self.occupancy.get(key, [])
        if entity in occupants:
            occupants.remove(entity)
        if not occupants:
            self.occupancy.pop(key, None)
        self.entities.remove(entity)

    def reindex_entity(self, entity, x, y, *, allow_occupied=False):
        if not self.is_passable(x, y, ignore_entity=entity, allow_occupied=allow_occupied):
            return False
        old_key = (entity.x, entity.y)
        occupants = self.occupancy.get(old_key, [])
        if entity in occupants:
            occupants.remove(entity)
        if not occupants:
            self.occupancy.pop(old_key, None)
        entity.x, entity.y = x, y
        self.occupancy.setdefault((x, y), []).append(entity)
        return True

    def move_entity(self, entity, dx, dy):
        new_x = entity.x + dx
        new_y = entity.y + dy

        return self.reindex_entity(entity, new_x, new_y)

    def is_passable(self, x, y, ignore_entity=None, allow_occupied=False):
        if not self.is_inside(x, y):
            return False
        tile = self.get_tile(x, y)
        if tile.blocking:
            return False
        occupants = self.get_entities_at(x, y)
        if not allow_occupied and any(entity is not ignore_entity for entity in occupants):
            return False
        return True 
