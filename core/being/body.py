class Body:
    def __init__(self):
        self.hunger = 0
        self.thirst = 0
        self.alive = True
        

    def update_needs(self):
        if not self.alive:
            return


        self.hunger += 1
        self.thirst += 2

        if self.hunger >= 100 or self.thirst >= 100:
            self.alive = False

    def ingest(self, resource_type):
        if not self.alive:
            return

        if resource_type == "food":
            self.hunger = max(0, self.hunger - 30)
        elif resource_type == "water":
            self.thirst = max(0, self.thirst - 30)

    def needs_action(self): #função que desperta ação
        if not self.alive:
            return False

        return self.hunger >= 50 or self.thirst >= 50
