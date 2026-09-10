from core.being.entity import Entity

def test_entity_comeca_com_last_action_criado():
    entity = Entity("teste", "@", 0, 0)
    assert entity.last_action == "criado"

def test_record_action_atualiza_last_action():
    entity = Entity("teste", "@", 0, 0)
    texto = entity.debug_text()
    assert "teste" in texto
    assert "criado" in texto

