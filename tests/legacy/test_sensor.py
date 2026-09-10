from legacy.sense.sensor import Sensor
from legacy.sense.spatial import Spatial

def test_percebe_algo_na_frente():
    sensor = Sensor(range_=5)
    orientation = (0, -1)
    na_frente = Spatial(5, 5, 5, 2)

    resultado = sensor.can_perceive(na_frente, orientation)

    assert resultado == True
