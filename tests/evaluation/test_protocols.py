def test_sparse_controls_are_few_disjoint_and_cover_the_rest() -> None:
    import numpy as np

    from depthwizard.evaluation.protocols import sparse_control_split

    valid = np.ones((20, 20), dtype=bool)
    valid[0, :] = False
    control, evaluation = sparse_control_split((20, 20), valid, 10)
    assert int(control.sum()) == 10
    assert not bool((control & evaluation).any())
    assert bool(((control | evaluation) == valid).all())


def test_sparse_controls_need_enough_points() -> None:
    import numpy as np
    import pytest

    from depthwizard.evaluation.protocols import sparse_control_split

    with pytest.raises(ValueError, match=">= 3"):
        sparse_control_split((4, 4), np.ones((4, 4), dtype=bool), 2)
