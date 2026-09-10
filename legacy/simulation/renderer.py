class Renderer: #aqui é onde se configura os paraetros da renderização.
    def render_lit(self, world, light): #função de renderizção de iluminação nas tiles
        lines = []

        for y, row in enumerate(world.tiles):
            symbols = []

            for x, tile in enumerate(row):
                entity = world.get_entity_at(x, y)

                #if light < 0.25: #aqui é a função de renderização da luz.
                #    symbols.append(" ")
                #elif light <0.50:
                #    symbols.append(".")
                if entity is not None: #também renderiza a entidade junto a luz
                    symbols.append(entity.symbol)
                else:
                    symbols.append(tile.symbol)

            line = " ".join(symbols)
            lines.append(line) #junta tudo

        return "\n".join(lines)
