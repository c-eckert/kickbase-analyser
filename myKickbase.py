import streamlit as st
from kickbase_api.kickbase import Kickbase
from kickbase_api.exceptions import KickbaseException


BUNDESLIGA = [2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 18, 20, 24, 28, 40, 43]

TEAM_DICT = {
    2:  "Bayern",
    3:  "Dortmund",
    4:  "Frankfurt", # 4
    5:  "Freiburg", # 5
    7:  "Leverkusen", # 7
    8:  "Schalke", # 8
    9:  "Stuttgart", # 9
    10: "Bremen", # 10
    11: "Wolfsburg", # 11
    13: "Augsburg", # 13
    14: "Hoffenheim", # 14
    15: "Gladbach", # 15
    18: "Mainz", # 18
    20: "Hertha", # 20
    24: "Bochum", # 24
    28: "Koeln", # 28
    40: "Union", # 40
    43: "Leibzig" # 43
}

POSITION_DICT = {
    1 : "TW",
    2 : "ABW",
    3 : "MIT",
    4 : "ANG"
}


TRENT_DICT = {
    0 : "➡️", 
    1 : "↗️", 
    2 : "↘️"
}

STATUS_DICT = {
    0 : "FIT",
    1 : "VERLETZT",
    2 : "ANGESCHLAGEN",
    4 : "AUFBAUTRAINING",
    8 : "ROT-GESPERRT",
    16 : "GELB-ROT-GESPERRT",
    32 : "GELB_GESPERRT",
    64 : "NICHT_IM_KADER",
    128 : "NICHT_IN_LIGA",
    256 : "ABWESEND",
    9999999999 : "UNBEKANNT"
}



@st.experimental_singleton
def get_kickbase_object():
    kb = Kickbase()
    user_me, league = kb.login(st.secrets.kickbase_credentials.username, st.secrets.kickbase_credentials.password)
    league_id = kb._get_league_id(league[0])
    return kb, league_id



def get_current_matchday():
    kb, league_id = get_kickbase_object()
    return kb.league_stats(league_id).current_day



def get_player_from_kb(_kb, league_id):
    players_list = []
    for team in BUNDESLIGA:
        players = _kb.team_players(team)
        for p in players:
            player_dict = {
               "d_player_id"   : int(_kb._get_player_id(p)), 
               "d_last_name"   : p.last_name, 
               "d_first_name"  : p.first_name, 
               "d_value"       : int(p.market_value), 
               "d_value_trend" : int(p.market_value_trend), 
               "d_team"        : int(team), 
               "d_position"    : int(p.position), 
               "d_status"      : int(p.status), 
               "d_user"        : "Free", 
               "d_transfer"    : False
            }
            players_list.append(player_dict)

    players_list = update_user(_kb, league_id, players_list)
    players_list = update_transfer(_kb, league_id, players_list)
    return players_list



def update_user(_kb, league_id, players_list):
    users = _kb.league_users(league_id)
    for user in users:
        user_players = _kb.league_user_players(league_id, user.id)
        for user_player in user_players:
            user_player_id = int(_kb._get_player_id(user_player))
            for p in players_list:
                if p["d_player_id"] == user_player_id:
                    p["d_user"] = user.name
    return players_list



def update_transfer(_kb, league_id, players_list):
    market = _kb.market(league_id)
    market_players = market.players
    for market_player in market_players:
        market_player_id = int(_kb._get_player_id(market_player))
        for p in players_list:
            if p["d_player_id"] == market_player_id:
                p["d_transfer"] = True
    return players_list



def get_points_from_kb(_kb):
    points_list = []
    for team in BUNDESLIGA:
        players = _kb.team_players(team)
        for p in players:
            player_id = int(_kb._get_player_id(p))
            request_points(_kb, points_list, player_id)
    return points_list



def request_points(_kb, points_list, player_id):
    r = _kb._do_get("/players/{}/points".format(player_id), True)

    if r.status_code != 200:
        raise KickbaseException()

    if "s" not in r.json(): 
        return
    
    if not r.json()["s"]: 
        return # Array is empty

    if r.json()["s"][-1]["t"] != "2022/2023":
        return # no current season
    
    season = r.json()["s"][-1]["m"]
    
    for match in season:
        matchday = match["d"]
        points = match["p"]
        player_dict = {
            "d_matchday"  : matchday,
            "d_points"    : points,
            "d_player_id" : player_id,
        }
        points_list.append(player_dict)


