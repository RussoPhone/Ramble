class Gtime: #Classe de tempo
    def __init__(self, mtksptk):
        self.mtk = 0 # microticks #Menor unidade de tempo até então
        self.mtksptk = mtksptk # microticks por tick, tk são ticks #ticks é o resultado da soma de microticks

    def adv(self): #avanço do tempo é microticks + 1
        self.mtk = self.mtk + 1

    def get_tk(self): #Um tick é a divisão inteira entre microticks e microtick-por-ticks
        return self.mtk // self.mtksptk

    def get_pos(self): #a posição atual referente ao microtick no tick. Ele serve para debug.
        return self.mtk % self.mtksptk

    def get_progress(self): #Mostra o progresso do tempo até o começo/fim de um tick. Divisão entre a posição e o microtick por tick
        return self.get_pos() / self.mtksptk

    def debug_text(self): #apenas texto pra debug do tempo. Util se quiser fazer alguma parada gradual sla
        return f"MTK: {self.mtk}, TK: {self.get_tk()}, POS: {self.get_pos()}, PROGRESS: {self.get_progress(): .0%}"
