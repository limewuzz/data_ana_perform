from app.services.pairwise import pairwise_from_groups, to_groups


def test_to_groups_prefers_ranking_groups():
    groups = to_groups(ranking=[1, 2, 3], ranking_groups=[[1, 2], [3]])
    assert groups == [[1, 2], [3]]


def test_pairwise_skip_tie_only_cross_group():
    pairs = pairwise_from_groups(groups=[[1, 2], [3]], tie_handling="skip", seed="s")
    got = {(p.chosen_id, p.rejected_id, p.rel) for p in pairs}
    assert got == {(1, 3, "ordered"), (2, 3, "ordered")}


def test_pairwise_random_is_deterministic():
    p1 = pairwise_from_groups(groups=[[1, 2], [3]], tie_handling="random", seed="seed1")
    p2 = pairwise_from_groups(groups=[[1, 2], [3]], tie_handling="random", seed="seed1")
    assert [(p.chosen_id, p.rejected_id, p.rel) for p in p1] == [(p.chosen_id, p.rejected_id, p.rel) for p in p2]
    p3 = pairwise_from_groups(groups=[[1, 2], [3]], tie_handling="random", seed="seed2")
    p4 = pairwise_from_groups(groups=[[1, 2], [3]], tie_handling="random", seed="seed2")
    assert [(p.chosen_id, p.rejected_id, p.rel) for p in p3] == [(p.chosen_id, p.rejected_id, p.rel) for p in p4]
