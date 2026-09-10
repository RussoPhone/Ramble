from legacy.simulation.config import ScenarioConfig
from legacy.simulation.scenario import build_scenario
from legacy.simulation.interactive_runner import InteractiveRunner


def build_runner(duration=50):
    config = ScenarioConfig(seed=9, num_organism=3, simulation_duration=duration, frame_delay=0)
    simulation = build_scenario(config)
    return InteractiveRunner(simulation)


def make_input(comandos):
    #simula o input() do usuário: cada chamada devolve o próximo comando da lista.
    fila = list(comandos)

    def fake_input(prompt=""):
        return fila.pop(0)

    return fake_input


def test_comando_s_avanca_um_passo_por_vez():
    runner = build_runner()

    runner.loop(input_fn=make_input(["s", "s", "q"]))

    assert runner.simulation.gtime.mtk == 2
    assert runner.running is False


def test_aceleracao_com_mais_multiplica_o_passo():
    runner = build_runner()

    runner.loop(input_fn=make_input(["+", "+", "s", "q"]))
    #steps_per_command começa em 1, dois '+' levam a 3; um 's' avança 3 ticks
    assert runner.steps_per_command == 3
    assert runner.simulation.gtime.mtk == 3


def test_comando_r_roda_n_ticks_seguidos(capsys):
    runner = build_runner()

    runner.loop(input_fn=make_input(["r 5", "q"]))

    assert runner.simulation.gtime.mtk == 5


def test_comando_replay_imprime_historico(capsys):
    #com fome/sede começando em 0, precisamos de ticks suficientes pra ter
    #pelo menos um evento (de céu, se não de ação) no histórico.
    runner = build_runner(duration=40)

    runner.loop(input_fn=make_input(["r 30", "replay", "q"]))

    saida = capsys.readouterr().out
    assert len(runner.simulation.event_log.events) > 0
    assert "tick" in saida


def test_loop_para_sozinho_quando_simulacao_termina():
    runner = build_runner(duration=2)

    #manda muito mais comandos 's' do que ticks disponíveis; o loop tem que
    #parar assim que a simulação acabar, sem precisar consumir tudo.
    runner.loop(input_fn=make_input(["s", "s", "s", "s", "s"]))

    assert runner.simulation.gtime.mtk == 2
