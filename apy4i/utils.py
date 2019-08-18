from statistics import mean


def elo(team_a, team_b, outcome, k=16):
    if isinstance(team_a, int) and isinstance(team_b, int):
        team_a, team_b = [team_a], [team_b]
    # TODO: figure out what to do when the teams are unequal
    assert len(team_a) == len(team_b)

    S_x, S_y = {"a": (1, 0), "b": (0, 1), "draw": (0.5, 0.5)}[outcome]

    R_x, R_y = 10 ** (mean(team_a) / 400), 10 ** (mean(team_b) / 400)

    return (k * (S_x - (R_x / (R_x + R_y))), k * (S_y - (R_y / (R_x + R_y))))
