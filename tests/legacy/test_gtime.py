from legacy.simulation.gtime import Gtime

def test_gtime_comeca_zerado():
    gtime = Gtime(mtksptk=24)
    assert gtime.mtk == 0
    assert gtime.get_tk() == 0
    assert gtime.get_pos() == 0

def test_adv_avanca_um_microtick():
    gtime = Gtime(mtksptk=24)
    gtime.adv()
    assert gtime.mtk == 1

def test_get_tk_contra_ticks_completos():
    gtime = Gtime(mtksptk=24)
    for _ in range(30):
        gtime.adv()
    assert gtime.get_tk() == 1
    assert gtime.get_pos() == 6

def test_get_progress_entre_zero_e_um():
    gtime = Gtime(mtksptk=24)
    for _ in range(12):
        gtime.adv()
    assert gtime.get_progress() == 0.5
