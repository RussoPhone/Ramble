from typing import Optional

class Navigator:

    @staticmethod
    def directions_toward(dx, dy):
        eixo_x: Optional[tuple[int, int]] = (1, 0) if dx > 0 else (-1, 0) if dx < 0 else None
        eixo_y: Optional[tuple[int, int]] = (0, 1) if dy > 0 else (0, -1) if dy < 0 else None 

        if eixo_x is not None and (eixo_y is None or abs(dx) >= abs(dy)):
            primaria, secundaria = eixo_x, eixo_y 
        else:
            primaria, secundaria = eixo_y, eixo_x 

        eixo_e_horizontal = primaria is not None and primaria[1] == 0
        perpendiculares: list[tuple[int, int]] = [(0, 1), (0, -1)] if primaria in ((1, 0), (-1, 0)) else [(1, 0), (-1, 0)]

        ordem: list[tuple[int, int]] =[d for d in (primaria, secundaria) if d is not None]
        for perp in perpendiculares:
            if perp not in ordem:
                ordem.append(perp)

        ordem.append((0, 0))
        return ordem 
