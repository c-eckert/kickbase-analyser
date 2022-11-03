from kickbase_api.kickbase import Kickbase
from kickbase_api.exceptions import KickbaseException
import streamlit as st
import mysql.connector

username = st.secrets.kickbase_credentials.username
password = st.secrets.kickbase_credentials.password

kb = Kickbase()
user, league = kb.login(username, password)

# Initialize connection.
# Uses st.experimental_singleton to only run once.
@st.experimental_singleton
def init_connection():
    return mysql.connector.connect(**st.secrets["mysql"])

conn = init_connection()

# Perform query.
# Uses st.experimental_memo to only rerun when the query changes or after 10 min.
@st.experimental_memo(ttl=600)
def run_query(query, attr=None):
    with conn.cursor() as cur:
        cur.execute(query, attr)
        return cur.fetchall()


run_query("DROP TABLE IF EXISTS spieler, punkte")


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
    0 : "o", 
    1 : "+", 
    2 : "-"
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


def get_points(player_id):
    
    r = kb._do_get("/players/{}/points".format(player_id), True)

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

        run_query("""
            INSERT INTO punkte 
            VALUES(%s, %s, %s)
            """,
            (matchday, points, player_id)
            )


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
    user        TEXT,
    transfer    BOOL
)"""
run_query(sql_command)


sql_command = """
CREATE TABLE IF NOT EXISTS punkte (
    matchday    INTEGER,
    points      INTEGER,
    player_id   INTEGER,
    PRIMARY KEY (matchday, player_id),
    FOREIGN KEY (player_id) REFERENCES spieler(player_id)
)"""
run_query(sql_command)


for team in BUNDESLIGA:
    players = kb.team_players(team)
    for p in players:
        player_id = kb._get_player_id(p)
        first_name = p.first_name
        last_name = p.last_name
        market_value = int(p.market_value)
        market_value_trend = TRENT_DICT[int(p.market_value_trend)]
        team_name = TEAM_DICT[team]
        position = POSITION_DICT[int(p.position)]
        status = STATUS_DICT[int(p.status)]
        user = "Free"
        transfer = False
        

        run_query("""
        INSERT INTO spieler 
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (player_id, 
        last_name, 
        first_name, 
        market_value, 
        market_value_trend, 
        team_name, 
        position, 
        status,
        user,
        transfer)
        )

        get_points(player_id)


users = kb.league_users(kb._get_league_id(league[0]))
for user in users:
    user_players = kb.league_user_players(kb._get_league_id(league[0]), user.id)
    for p in user_players:
        player_id = int(kb._get_player_id(p))
        run_query(
        "UPDATE spieler SET user = %s WHERE player_id = %s;",
        (user.name, player_id)
    )


market = kb.market(league[0])
market_players = market.players
for p in market_players:
    player_id = kb._get_player_id(p)
    run_query(
        "UPDATE spieler SET transfer = %s WHERE player_id = %s;",
        (True, player_id)
    )

conn.commit()
conn.close()


