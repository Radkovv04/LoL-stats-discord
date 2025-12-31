import requests
import time

API_KEY = "RGAPI-9a3c5b4a-e8c2-42ec-962f-0fc83e1956ce" # my user API
REGION = "europe"
SUMMONER_NAME = "NSP Shad0wBlood"
TAGLINE = "17925"

# Diamond benchmark(u.gg/op.gg)
diamond_benchmark = {
    "KDA": 3.0,
    "KP": 70,
    "DMG/MIN": 500,
    "Gold/Min": 400,
    "Vision/Min": 1.2,
    "CS@10": 70,
    "Gold@10": 1500,
    "XP@10": 3000,
    "CS@15": 110,
    "Gold@15": 2500,
    "XP@15": 5000
}

def get_puuid(summoner_name, tagline):
    url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}?api_key={API_KEY}" # network connect
    return requests.get(url).json()["puuid"]

def get_match_ids(puuid, days=7, count=100, queue=420):   #420 - SoloQ #430 - SwiftPlay #440 - Flex #450 - ARAM #700 - Clash #720 - ARAM clash
    now = int(time.time())
    start_time = now - days * 24 * 60 * 60
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?startTime={start_time}&queue={queue}&count={count}&api_key={API_KEY}"
    return requests.get(url).json()

def get_match_data(match_id):
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
    return requests.get(url).json()

def get_match_timeline(match_id):
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={API_KEY}"
    return requests.get(url).json()

def get_stats_at_minute(timeline, participant_index, minute):
    frames = timeline.get("info", {}).get("frames", [])
    if not frames:
        return 0, 0, 0
    frame_index = min(minute, len(frames)-1)
    frame = frames[frame_index]["participantFrames"]
    pf = frame[str(participant_index)]
    cs = pf.get("minionsKilled", 0) + pf.get("jungleMinionsKilled", 0)
    gold = pf.get("totalGold", 0)
    xp = pf.get("xp", 0)
    return round(cs,1), round(gold,1), round(xp,1)


# LoL leveling system
def calculate_level_and_xp(xp):
    xp_per_level = [144, 144, 192, 240, 336, 432, 528, 624, 720, 816, 912, 984, 1056, 1128, 1344, 1440, 1536, 1680, 1824, 1968, 2112, 2208, 2304, 2304, 2496, 2496, 2592, 2688, 2688]
    total_xp = 0
    level = 1
    for xp_needed in xp_per_level:
        total_xp += xp_needed
        if xp < total_xp:
            break
        level += 1
    xp_to_next_level = total_xp - xp
    xp_percentage = (xp / total_xp) * 100 if total_xp > 0 else 0
    return level, round(xp_percentage,1), xp_to_next_level

def calculate_stats(match, timeline, puuid):
    participant_index = None
    for i, p in enumerate(match["info"]["participants"]):
        if p["puuid"] == puuid:
            participant_index = i + 1
            player = p
            break
    if participant_index is None:
        return None

    team_id = player.get("teamId", None)
    if team_id is not None:
        team_kills = sum(p.get("kills",0) for p in match["info"]["participants"] if p.get("teamId") == team_id)
    else:
        team_kills = 0

    game_minutes = match["info"].get("gameDuration",0)/60

    cs10, gold10, xp10 = get_stats_at_minute(timeline, participant_index, 10)
    cs15, gold15, xp15 = get_stats_at_minute(timeline, participant_index, 15)

    level10, perc10, xp_remain10 = calculate_level_and_xp(xp10)
    level15, perc15, xp_remain15 = calculate_level_and_xp(xp15)

    win = player.get("win", False)

    stats = {
        "Champion": player.get("championName","Unknown"),
        "K/D/A": f"{player.get('kills',0)}/{player.get('deaths',0)}/{player.get('assists',0)}",
        "KDA": round((player.get("kills",0)+player.get("assists",0))/max(1,player.get("deaths",0)),1),
        "KP": round((player.get("kills",0)+player.get("assists",0))/max(1,team_kills),1) if team_kills>0 else 0,
        "DMG/MIN": round(player.get("totalDamageDealtToChampions",0)/max(1,game_minutes),1),
        "Gold/Min": round(player.get("goldEarned",0)/max(1,game_minutes),1),
        "Vision/Min": round(player.get("visionScore",0)/max(1,game_minutes),1),
        "WardsPlaced": player.get("wardsPlaced",0),
        "WardsKilled": player.get("wardsKilled",0),
        "CS@10": cs10,
        "Gold@10": gold10,
        "XP@10": xp10,
        "Level@10": f"{level10} ({perc10}%)",
        "CS@15": cs15,
        "Gold@15": gold15,
        "XP@15": xp15,
        "Level@15": f"{level15} ({perc15}%)",
        "Win": "Victory" if win else "Defeat"
    }
    return stats

def average_stats(stats_list):
    avg = {}
    keys = stats_list[0].keys()
    for k in keys:
        if k in ["Champion", "Level@10", "Level@15", "K/D/A", "Win"]:
            continue
        avg[k] = round(sum(s[k] for s in stats_list)/len(stats_list),1)
    return avg

def compare_with_benchmark(stats, benchmark):
    comparison = {key: {"above": 0, "below": 0} for key in benchmark.keys()}
    for game in stats:
        for key, value in benchmark.items():
            if game[key] >= value:
                comparison[key]["above"] += 1
            else:
                comparison[key]["below"] += 1
    return comparison

if __name__ == "__main__":
    puuid = get_puuid(SUMMONER_NAME, TAGLINE)
    match_ids = get_match_ids(puuid, days=7, count=100, queue=440)

    total_matches = 0
    all_stats = []
    wins = 0
    losses = 0

    for mid in match_ids:
        match = get_match_data(mid)
        timeline = get_match_timeline(mid)
        stats = calculate_stats(match, timeline, puuid)
        if stats:
            total_matches += 1
            all_stats.append(stats)
            if stats["Win"] == "Victory":
                wins += 1
            else:
                losses += 1
            # All stats and games
            print(f"{mid}: {stats}")

    avg = average_stats(all_stats)
    comparison = compare_with_benchmark(all_stats, diamond_benchmark)

    # Best and Worst game(KDA)
    best_game = max(all_stats, key=lambda x:x["KDA"])
    worst_game = min(all_stats, key=lambda x:x["KDA"])

    # --- weekly stats ---
    print("\n**--- weekly stats ---**\n")
    print(f"Games played: {total_matches}")
    print(f"Wins: {wins}")
    print(f"Loses: {losses}\n")
    print(f"{SUMMONER_NAME}#{TAGLINE}\n")
    print("Average Stats (and compared to Diamond):")
    for stat, value in avg.items():
        if stat in comparison:
            print(f"{stat}: {value}   Above = {comparison[stat]['above']}, Below = {comparison[stat]['below']}")
        else:
            print(f"{stat}: {value}  ")

    print("\nWorst game: {} {} KDA: {} KP: {} DMG/MIN: {} Gold/Min: {} Vision/Min: {} WardsPlaced: {} WardsKilled: {} CS@10: {} Gold@10: {} Level@10: {} CS@15: {} Gold@15: {} Level@15: {} Win: {}".format(
        worst_game["Champion"], worst_game["K/D/A"], worst_game["KDA"], worst_game["KP"], worst_game["DMG/MIN"], worst_game["Gold/Min"],
        worst_game["Vision/Min"], worst_game["WardsPlaced"], worst_game["WardsKilled"], worst_game["CS@10"], worst_game["Gold@10"], worst_game["Level@10"],
        worst_game["CS@15"], worst_game["Gold@15"], worst_game["Level@15"], worst_game["Win"]
    ))

    print("\nBest game: {} {} KDA: {} KP: {} DMG/MIN: {} Gold/Min: {} Vision/Min: {} WardsPlaced: {} WardsKilled: {} CS@10: {} Gold@10: {} Level@10: {} CS@15: {} Gold@15: {} Level@15: {} Win: {}".format(
        best_game["Champion"], best_game["K/D/A"], best_game["KDA"], best_game["KP"], best_game["DMG/MIN"], best_game["Gold/Min"],
        best_game["Vision/Min"], best_game["WardsPlaced"], best_game["WardsKilled"], best_game["CS@10"], best_game["Gold@10"], best_game["Level@10"],
        best_game["CS@15"], best_game["Gold@15"], best_game["Level@15"], best_game["Win"]
    ))
