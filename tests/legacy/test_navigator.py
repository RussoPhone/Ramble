from legacy.being.navigator import Navigator


def test_prioriza_eixo_dominante_horizontal():
    ordem = Navigator.directions_toward(5, 1)
    assert ordem[0] == (1, 0)

def test_prioriza_eixo_dominante_vertical():
    ordem = Navigator.directions_toward(1, 5)
    assert ordem[0] == (0, 1)

def test_direcao_negativa_no_eixo_dominante():
    ordem = Navigator.directions_toward(-5, 1)
    assert ordem[0] == (-1, 0)

def test_inclui_perpendiculares_pra_contornar():
    ordem = Navigator.directions_toward(3, 0)
    assert (0, 1) in ordem
    assert (0, -1) in ordem

def test_termina_com_esperar():
    ordem = Navigator.directions_toward(4, 2)
    assert ordem[-1] == (0, 0)

def test_alvo_na_mesma_celula_nao_quebra():
    ordem = Navigator.directions_toward(0, 0)
    assert (0, 0) in ordem

def test_retorno_nao_tem_direcoes_duplicadas():
    ordem = Navigator.directions_toward(3, 2)
    assert len(ordem) == len(set(ordem))
