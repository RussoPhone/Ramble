class Sensor:
    def __init__(self, range_, requires_light=True):
        self.range_ = range_
        self.requires_light = requires_light


    def can_perceive(self, spatial, orientation, light=1.0):
        effective_range = self.range_ * light if self.requires_light else self.range_

        if spatial.distance() > effective_range:
            return False

        if spatial.same_position():
            return True

        facing_dot = spatial.dx * orientation[0] + spatial.dy * orientation[1]
        return facing_dot >= 0
