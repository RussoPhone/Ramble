from core.ambient.tile import FOOD, GRASS, WATER

class EnvironmentSystem:
    def __init__(self):
        pass

    #Classe pra sistema de efeitos no ambiente
    def apply(self, simulation, entity):
        current_tile = simulation.world.get_tile(
            entity.x,
            entity.y
        )

        if current_tile in (FOOD, WATER):
            entity.body.ingest(current_tile.tile_type)

        if current_tile == FOOD:
            simulation.world.set_tile(entity.x, entity.y, GRASS)
