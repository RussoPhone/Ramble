import time
from legacy.simulation.replay import narrate

class InteractiveRunner:
    # (enter) ou 's'   -> avança 1 "passo de comando" (avanço unitário)
    #    'r N'            -> roda N ticks seguidos, renderizando a cada um (ex: 'r 20')
     #   '+' / '-'        -> aumenta/diminui quantos ticks cada 's' avança de uma vez (aceleração)
      #  'replay'         -> imprime o histórico textual completo até agora
       # 'q'              -> encerra o console

    def __init__(self, simulation, steps_per_command=1):
        self.simulation = simulation
        self.steps_per_command = steps_per_command
        self.running = True 

    def speed_up(self):
        self.steps_per_command += 1

    def speed_down(self):
        self.steps_per_command = max(1, self.steps_per_command - 1)

    def step_once(self):
        for _ in range(self.steps_per_command):
            avancou = self.simulation.advance_one(render_enabled=False)
            if not avancou:
                break

    def run_n_ticks(self, n, frame_delay=None):
        delay = self.simulation.frame_delay if frame_delay is None else frame_delay
        for _ in range(n):
            if self.simulation.gtime.mtk >= self.simulation.simulation_duration:
                break
            self.simulation.advance_one(render_enabled=True)
            time.sleep(delay)

    def handle_command(self, command):
        partes = command.strip().lower().split()
        primeiro = partes[0] if partes else ""

        if primeiro in ("", "s"):
            self.step_once()
        elif primeiro == "r":
            n = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 10 
            self.run_n_ticks(n)
        elif primeiro == "+":
            self.speed_up()
        elif primeiro == "-":
            self.speed_down() 
        elif primeiro == "replay":
            for linha in narrate(self.simulation.event_log):
                print(linha)
        elif primeiro == "q":
            self.running = False 
        else: 
            print(f"comando desconhecido: {command!r}")
    def loop(self, input_fn=input):
        while self.running and self.simulation.gtime.mtk < self.simulation.simulation_duration:
            self.simulation.render()
            comando = input_fn(
                f"[passo x{self.steps_per_command}] (s/r N/+/-/replay/q) > "
            )
            self.handle_command(comando)

