def calculate_summary(all_games):

    summary = {
        "games": 0,
        "accuracy": 0,
        "inaccuracies": 0,
        "mistakes": 0,
        "blunders": 0
    }

    if not all_games:
        return summary

    summary["games"] = len(all_games)

    for game in all_games:

        summary["accuracy"] += game["accuracy"]
        summary["inaccuracies"] += game["statistics"]["inaccuracies"]
        summary["mistakes"] += game["statistics"]["mistakes"]
        summary["blunders"] += game["statistics"]["blunders"]

    summary["accuracy"] /= len(all_games)

    return summary