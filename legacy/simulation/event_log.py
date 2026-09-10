class EventLog:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)

    def at_tick(self, tick):
        return [e for e in self.events if e.tick == tick]

    def for_entity(self, entity_name):
        return [e for e in self.events if e.entity_name == entity_name]
