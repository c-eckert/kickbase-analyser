from kickbase_api.kickbase import Kickbase
from kickbase_api.exceptions import KickbaseException
import sqlite3
import streamlit as st

username = st.secrets.kickbase_credentials.username
password = st.secrets.kickbase_credentials.password


connection = sqlite3.connect("database/player.db")
curser = connection.cursor()

curser.execute("DROP TABLE IF EXISTS spieler")
curser.execute("DROP TABLE IF EXISTS punkte")


bundesliga = [2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 18, 20, 24, 28, 40, 43]

team_dict = {
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

position_dict = {
    1 : "TW",
    2 : "ABW",
    3 : "MIT",
    4 : "ANG"
}

trend_dict = {
    0 : "o", 
    1 : "+", 
    2 : "-"
}

status_dict = {
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

role_dict = {
    0 : "FREI",
    1 : "TEAM",
    2 : "LIGA",
    3 : "TRANSFERMARKT"
}


def get_points(player_id):
    
    r = kickbase._do_get("/players/{}/points".format(player_id), True)

    if r.status_code != 200:
        raise KickbaseException()

    if "s" not in r.json():
        return 0
    
    if not r.json()["s"]:
        return 0 # Array is empty

    if r.json()["s"][-1]["t"] != "2022/2023":
        return 0 # no current season
    
    season = r.json()["s"][-1]["m"]
    for match in season:
        matchday = match["d"]
        points = match["p"]

        curser.execute("""
            INSERT INTO punkte 
            VALUES(?, ?, ?)
            """,
            (matchday, points, player_id)
            )
    return 1


kickbase = Kickbase()



user, league = kickbase.login(username, password)


sql_command = """
CREATE TABLE IF NOT EXISTS spieler (
    player_id   INTEGER     PRIMARY KEY,
    last_name   TEXT,
    first_name  TEXT,
    value       INTEGER,
    value_trend TEXT,
    team        TEXT,
    position    TEXT,
    status      TEXT,
    role        TEXT
)"""
curser.execute(sql_command)


sql_command = """
CREATE TABLE IF NOT EXISTS punkte (
    matchday    INTEGER,
    points      INTEGER,
    player_id   INTEGER,
    PRIMARY KEY (matchday, player_id),
    FOREIGN KEY (player_id) REFERENCES spieler(player_id)
)"""
curser.execute(sql_command)



for team in bundesliga:
    players = kickbase.team_players(team)
    for p in players:
        player_id = kickbase._get_player_id(p)
        first_name = p.first_name
        last_name = p.last_name
        position = position_dict[int(p.position)]
        market_value = int(p.market_value)
        market_value_trend = trend_dict[int(p.market_value_trend)]
        status = status_dict[int(p.status)]
        role = role_dict[0]
        team_name = team_dict[team]


        curser.execute("""
        INSERT INTO spieler 
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (player_id, 
        last_name, 
        first_name, 
        market_value, 
        market_value_trend, 
        team_name, 
        position, 
        status,
        role)
        )

        get_points(player_id)

players = kickbase.league_user_players(league[0], user)
for p in players:
    player_id = kickbase._get_player_id(p)
    curser.execute(
        "UPDATE spieler SET role = ? WHERE player_id = ?;",
        (role_dict[1], player_id)
    )

market = kickbase.market(league[0])
market_players = market.players
for p in market_players:
    player_id = kickbase._get_player_id(p)
    curser.execute(
        "UPDATE spieler SET role = ? WHERE player_id = ?;",
        (role_dict[3], player_id)
    )

connection.commit()
connection.close()



