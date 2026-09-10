import math

class Sky: #Aqui fica funções relacionadas a iluminação. Céu.
    def __init__(self, cycle_length=24): #ciclo atual configuravel de iluminação
        self.cycle_length = cycle_length

    def get_phase(self, gtime): #definição de fase de iluminação. Microtick com restante da divisão da largura do ciclo dividido por ele mesmo.
        return (gtime.mtk % self.cycle_length) / self.cycle_length

    def get_light(self, gtime): #função de luz. Pega a "fase do dia" e aplica a variavel light que é o resultado de dessa equação aí. Nâo mexe por enquanto.
        phase = self.get_phase(gtime)
        #Nn mexe na equação
        light = (1 - math.cos(phase * 2 * math.pi)) / 2

        return light

    def get_darkness(self, gtime): #função de definir a escuridão uuuuu oele é continuo junto com light
        return 1 - self.get_light(gtime)

    def get_state(self, gtime): #aqui estão os estados do "dia". Sâo valores simples, parametros de menor que.
        phase = self.get_phase(gtime)
        #pode escalonar se precisar.
        if phase < 0.25:
            return "DAWN"
        elif phase < 0.50:
            return "DAY"
        elif phase < 0.75:
            return "DUSK"
        else:
            return "NIGHT"

    #apenas a função de gerar o texto pro debug.
    def debug_text(self, gtime):
        light = self.get_light(gtime)
        darkness = self.get_darkness(gtime)
        state = self.get_state(gtime)

        return f"SKY: {state}, LIGHT: {light:.0%}, DARKNESS: {darkness:.0%}"
