class AffordanceSystem:
    DIRECTIONS = [(1, 0),
                 (-1, 0),
                 (0, 1),
                 (0, -1),
                 (0, 0)]

    def legal_actions(self, world, entity):
        return [
            (dx, dy) for dx, dy in self.DIRECTIONS
            if world.is_passable(entity.x + dx, entity.y + dy, ignore_entity=entity)
        ]

