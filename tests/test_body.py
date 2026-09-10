from core.being.body import Body

def test_update_needs_aumenta_fome_e_sede():
    body = Body()
    body.update_needs()
    assert body.hunger == 1
    assert body.thirst == 2
    assert body.alive is True

def test_morre_quando_fome_estoura_o_limite():
    body = Body()
    body.hunger = 99
    body.update_needs()
    assert body.hunger == 100
    assert body.alive is False

def test_corpo_morto_nao_atualiza_mais_necessidades():
    body = Body()
    body.alive = False
    body.hunger = 10
    body.thirst = 10
    body.update_needs()
    assert body.hunger == 10
    assert body.thirst == 10

def test_ingest_food_reduz_apenas_fome():
    body = Body()
    body.hunger = 50
    body.thirst = 50
    body.ingest("food")
    assert body.hunger == 20
    assert body.thirst == 50

def test_ingest_water_reduz_apenas_sede():
    body = Body()
    body.hunger = 50
    body.thirst = 50
    body.ingest("water")
    assert body.hunger == 50
    assert body.thirst == 20

def test_corpo_morto_nao_ingere_recurso():
    body = Body()
    body.alive = False
    body.hunger = 50
    body.thirst = 50
    body.ingest("food")
    body.ingest("water")
    assert body.hunger == 50
    assert body.thirst == 50

def test_needs_action_verdadeiro_acima_de_50():
    body = Body()
    body.hunger = 50
    assert body.needs_action() is True

def test_needs_action_falso_corpo_morto():
    body = Body()
    body.alive = False
    body.hunger = 90
    assert body.needs_action() is False

