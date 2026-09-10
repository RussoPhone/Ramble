import random 

class NaivePolicy:
    def __init__(self, rng=None):
        self.rng = rng if rng is not None else random.Random()

    DIRECTIONS = [
        (1,0),
        (-1, 0),
        (0, 1),
        (0, -1), 
        (0, 0)
    ]

    def decide(self, entity, perception):
        opcoes = self.DIRECTIONS.copy()
        self.rng.shuffle(opcoes)
        return opcoes 
