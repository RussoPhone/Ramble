class Spatial:
    def __init__(self, origin_x, origin_y, target_x, target_y):
        self.dx = target_x - origin_x
        self.dy = target_y - origin_y

    def distance(self):
        return abs(self.dx) + abs(self.dy) #passos no grid

    def same_position(self):
        return self.dx == 0 and self.dy == 0
