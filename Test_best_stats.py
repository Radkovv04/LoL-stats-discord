import requests
import datetime
import time
import json
import os

API_KEY = "RGAPI-9dcaa59f-05a2-4e49-b42c-1ef69107dbc3"  # смени с твоя актуален ключ
REGION = "europe"

# ------------------- Твърдо зададени summoner-и -------------------
SUMMONERS = {
    "alek": {"name": "NSP Aspra", "tagline": "0606"},
    "radko": {"name": "NSP Shad0wBlood", "tagline": "17925"},
    "lubo": {"name": "CharFutur", "tagline": "8592"},
    "zahir": {"name": "Nonebender", "tagline": "Sokka"},
    "maykal": {"name": "Maykal2001", "tagline": "EUNE"}
}

# ------------------- Diamond benchmarks -------------------
ROLE_BENCHMARKS = {
    "KDA": 3.0,
    "KP": 70,
    "DMG/MIN": 500,
    "Gold/Min": 400,
    "Vision/Min": 1.2,
    "WardsPlaced": 15,
    "WardsKilled": 5,
    "CS@10": 70,
    "CS@15": 110
}

# ------------------- Helpers -------------------
PUUID_CACHE_FILE = "puuids.json"

def load_puuids():
    if os.path.exists(PUUID_CACHE_FILE):
        with open(PUUID_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_puuids(cache):
    with open(PUUID_CACHE_FILE, "w") as f:
        json.dump(cache, f)

def fetch_puuid(summoner_key):
    cache = load_puuids()
    if summoner_key in cache:
        return cache[summoner_key]

    summoner = SUMMONERS[summoner_key]
    url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner['name']}/{summoner['tagline']}?api_key={API_KEY}"

    while True:
        r = requests.get(url)
        if r.status_code == 429:  # Rate limit
            retry = int(r.headers.get("Retry-After", "1"))
            print(f"Rate limit hit, retrying in {retry} seconds...")
            time.sleep(retry)
            continue
        data = r.json()
        if "puuid" not in data:
            print(f"Error fetching PUUID for {summoner_key}: {data}")
            return None
        puuid = data["puuid"]
        cache[summoner_key] = puuid
        save_puuids(cache)
        return puuid

def fetch_matches(puuid, count=20):
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?type=ranked&start=0&count={count}&api_key={API_KEY}"
    while True:
        r = requests.get(url)
        if r.status_code == 429:
            retry = int(r.headers.get("Retry-After", "1"))
            print(f"Rate limit hit on fetch_matches, retrying in {retry} seconds...")
            time.sleep(retry)
            continue
        return r.json()

def fetch_match_data(match_id):
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={API_KEY}"
    while True:
        r = requests.get(url)
        if r.status_code == 429:
            retry = int(r.headers.get("Retry-After", "1"))
            print(f"Rate limit hit on fetch_match_data, retrying in {retry} seconds...")
            time.sleep(retry)
            continue
        return r.json()

def fetch_timeline(match_id):
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline?api_key={API_KEY}"
    while True:
        r = requests.get(url)
        if r.status_code == 429:
            retry = int(r.headers.get("Retry-After", "1"))
            print(f"Rate limit hit on fetch_timeline, retrying in {retry} seconds...")
            time.sleep(retry)
            continue
        return r.json()

def get_stats_at_minute(timeline, participant_index, minute):
    cs = 0
    gold = 0
    xp = 0
    frames = timeline["info"]["frames"]
    for frame in frames:
        timestamp_min = frame["timestamp"] / 1000 / 60
        if timestamp_min > minute:
            break
        p_data = frame["participantFrames"].get(str(participant_index), {})
        cs = p_data.get("minionsKilled", 0) + p_data.get("jungleMinionsKilled", 0)
        gold = p_data.get("totalGold", 0)
        xp = p_data.get("xp", 0)
    return cs, gold, xp

def calculate_level_and_xp(xp):
    xp_table = [0, 280, 660, 1140, 1720, 2400, 3180, 4060, 5040, 6120, 7300, 8580, 9960, 11440, 13020, 14700, 16480, 18360]
    level = 1
    for i, xp_needed in enumerate(xp_table):
        if xp >= xp_needed:
            level = i + 1
        else:
            break
    if level < len(xp_table):
        xp_into_level = xp - xp_table[level-1]
        next_level_xp = xp_table[level] - xp_table[level-1]
        percent_to_next = round((xp_into_level / next_level_xp) * 100, 1)
    else:
        percent_to_next = 100
    return level, percent_to_next

# ------------------- Main -------------------
def analyze_weekly_stats(puuid):
    matches = fetch_matches(puuid)
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=7)

    stats = {
        "games": 0,
        "wins": 0,
        "losses": 0,
        "KDA": [],
        "KP": [],
        "DMG/MIN": [],
        "Gold/Min": [],
        "Vision/Min": [],
        "WardsPlaced": [],
        "WardsKilled": [],
        "CtrlWardsBuy": [],
        "CtrlWardsKill": [],
        "CS@10": [],
        "Gold@10": [],
        "CS@15": [],
        "Gold@15": [],
        "Level@10": [],
        "Level@15": []
    }

    best_game = None
    worst_game = None
    best_score = -9999
    worst_score = 9999
    all_games = {}

    for match_id in matches:
        match_data = fetch_match_data(match_id)
        timeline = fetch_timeline(match_id)
        info = match_data["info"]
        game_start = datetime.datetime.utcfromtimestamp(info["gameStartTimestamp"] / 1000)
        if game_start < start_date or game_start > end_date:
            continue

        for i, p in enumerate(info["participants"], start=1):
            if p["puuid"] != puuid:
                continue

            stats["games"] += 1
            if p["win"]:
                stats["wins"] += 1
            else:
                stats["losses"] += 1

            kills, deaths, assists = p["kills"], p["deaths"], p["assists"]
            kda = (kills + assists) / (deaths if deaths > 0 else 1)
            kp = p["challenges"].get("killParticipation", 0) * 100
            dmg_min = p["challenges"].get("damagePerMinute", 0)
            gpm = p["challenges"].get("goldPerMinute", 0)
            vpm = p["challenges"].get("visionScorePerMinute", 0)

            stats["KDA"].append(kda)
            stats["KP"].append(kp)
            stats["DMG/MIN"].append(dmg_min)
            stats["Gold/Min"].append(gpm)
            stats["Vision/Min"].append(vpm)
            stats["WardsPlaced"].append(p.get("wardsPlaced", 0))
            stats["WardsKilled"].append(p.get("wardsKilled", 0))
            stats["CtrlWardsBuy"].append(p.get("visionWardsBoughtInGame", 0))
            stats["CtrlWardsKill"].append(p["challenges"].get("controlWardsDestroyed", 0))

            cs10, gold10, xp10 = get_stats_at_minute(timeline, i, 10)
            cs15, gold15, xp15 = get_stats_at_minute(timeline, i, 15)
            level10, perc10 = calculate_level_and_xp(xp10)
            level15, perc15 = calculate_level_and_xp(xp15)

            stats["CS@10"].append(cs10)
            stats["Gold@10"].append(gold10)
            stats["Level@10"].append(f"{level10} ({perc10}%)")
            stats["CS@15"].append(cs15)
            stats["Gold@15"].append(gold15)
            stats["Level@15"].append(f"{level15} ({perc15}%)")

            all_games[match_id] = {
                "Champion": p["championName"],
                "K/D/A": f"{kills}/{deaths}/{assists}",
                "KDA": round(kda,1),
                "KP": f"{round(kp,1)}%",
                "DMG/MIN": round(dmg_min,1),
                "Gold/Min": round(gpm,1),
                "Vision/Min": round(vpm,2),
                "WardsPlaced": p.get("wardsPlaced", 0),
                "WardsKilled": p.get("wardsKilled", 0),
                "CS@10": cs10,
                "Gold@10": gold10,
                "CS@15": cs15,
                "Gold@15": gold15,
                "Level@10": f"{level10} ({perc10}%)",
                "Level@15": f"{level15} ({perc15}%)",
                "Win": "Victory" if p["win"] else "Defeat"
            }

            score = kda + (kp/100) + dmg_min/100 + gpm/100
            if score > best_score:
                best_score = score
                best_game = match_id
            if score < worst_score:
                worst_score = score
                worst_game = match_id

        time.sleep(1.5)  # пауза между мачове, за да не се удари лимита

    return stats, start_date, end_date, best_game, worst_game, all_games

# ------------------- Print -------------------
def print_stats(stats, start, end, best_game, worst_game, all_games):
    print(f"--- Weekly stats --- ({start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')})\n")
    print(f"Games played: {stats['games']} | Wins: {stats['wins']} | Losses: {stats['losses']}\n")

    for key in ["KDA","KP","DMG/MIN","Gold/Min","Vision/Min","WardsPlaced","WardsKilled","CtrlWardsBuy","CtrlWardsKill","CS@10","Gold@10","CS@15","Gold@15","Level@10","Level@15"]:
        values = stats[key]
        if not values:
            continue
        avg_val = sum(v if isinstance(v,(int,float)) else 0 for v in values)/len(values)
        if key == "KP":
            print(f"{key}: {round(avg_val,1)}%")
        else:
            print(f"{key}: {round(avg_val,1)}")

# ------------------- Main -------------------
if __name__ == "__main__":
    for summoner in SUMMONERS:
        puuid = fetch_puuid(summoner)
        if not puuid:
            print(f"Skipping {summoner}, no PUUID.")
            continue
        stats, start, end, best, worst, games = analyze_weekly_stats(puuid)
        print(f"\n--- Stats for {summoner} ---")
        print_stats(stats, start, end, best, worst, games)
        time.sleep(1.5)  # пауза между summoner-и
