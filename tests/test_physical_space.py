from core.ambient.physical_space import PhysicalSpace, Shape


def test_shape_occupies_multiple_microcells_inside_its_anchor_tile():
    space = PhysicalSpace(4, 3, scale=3)
    shape = Shape(((1, 0), (0, 1), (1, 1), (2, 1), (1, 2)))

    space.place("agent", 7, 2, 1, shape, blocks=True)

    assert space.cells_for("agent", 7) == (
        (7, 3),
        (6, 4),
        (7, 4),
        (8, 4),
        (7, 5),
    )
    assert space.tokens_at_tile(2, 1) == (("agent", 7),)


def test_shape_movement_releases_old_microcells_and_preserves_bounds():
    space = PhysicalSpace(4, 3, scale=3)
    shape = Shape(((0, 0), (1, 0), (2, 0)))
    space.place("object", 4, 1, 1, shape)

    assert space.move("object", 4, 2, 1)
    assert space.tokens_at_tile(1, 1) == ()
    assert space.tokens_at_tile(2, 1) == (("object", 4),)
    assert not space.move("object", 4, 4, 1)
    assert space.tokens_at_tile(2, 1) == (("object", 4),)


def test_blocking_shapes_prevent_overlap_without_blocking_their_owner():
    space = PhysicalSpace(3, 3, scale=3)
    shape = Shape(((1, 1),))
    space.place("agent", 1, 1, 1, shape, blocks=True)

    assert not space.can_place(2, 1, 1, shape)
    assert space.can_place(1, 1, 1, shape, ignore=("agent", 1))


def test_visible_parts_return_only_microcells_not_hidden_by_blockers():
    space = PhysicalSpace(5, 3, scale=3)
    wide = Shape(((0, 0), (1, 1), (2, 2)))
    space.place("object", 10, 3, 1, wide)
    space.place("object", 20, 2, 1, Shape(((1, 1),)), blocks=True)

    visible = space.visible_parts(1, 1, "object", 10)

    assert visible
    assert visible != wide.cells


def test_absolute_cells_move_atomically_across_tile_boundaries():
    space = PhysicalSpace(2, 1, scale=3)
    space.place_cells("agent", 1, ((2, 1), (3, 1)), blocks=True)

    assert space.cells_for("agent", 1) == ((2, 1), (3, 1))

    space.place_cells("agent", 2, ((4, 1),), blocks=True)
    assert not space.move_cells("agent", 1, ((3, 1), (4, 1)))
    assert space.cells_for("agent", 1) == ((2, 1), (3, 1))


def test_absolute_cells_keep_visible_shape_separate_from_occupancy():
    space = PhysicalSpace(2, 1, scale=3)
    space.place_cells(
        "agent", 1, ((2, 1), (3, 1)), blocks=True,
        visible_cells=((0, 0), (1, 0)),
    )

    assert space.local_cells_for("agent", 1) == ((0, 0), (1, 0))
    assert space.tokens_at_tile(0, 0) == (("agent", 1),)
    assert space.tokens_at_tile(1, 0) == (("agent", 1),)
