class Tile: #aqui fica os tiles. As peças no tabuleiro.
    def __init__(self, tile_type, symbol, blocking=False, appearance=(0, 0, 0)): #aparência independe de efeitos físicos
        self.tile_type = tile_type
        self.symbol = symbol
        self.blocking = blocking 
        self.appearance = appearance
#as tiles. Tipo e simbolo.
GRASS = Tile("grass", ".", appearance=(1, 1, 1))
STONE = Tile("stone", "^", blocking=True, appearance=(2, 2, 2))
WATER = Tile("water", "~", appearance=(3, 3, 3))
FOOD = Tile("food", "*", appearance=(4, 4, 4))
