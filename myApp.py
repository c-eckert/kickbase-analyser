import sqlalchemy
from sqlalchemy import insert, update, MetaData
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.sql.expression import bindparam

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import pandas as pd
import plotly.express as px

from kickbase_api.kickbase import Kickbase
from kickbase_api.exceptions import KickbaseException

import threading
from datetime import datetime
import time

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


# Initialize connection.
# Uses st.experimental_singleton to only run once.
@st.experimental_singleton
def init_connection():
    return sqlalchemy.create_engine(**st.secrets["sqlalchemy"])


@st.experimental_singleton
def get_kickbase_object():
    kb = Kickbase()
    user_me, league = kb.login(st.secrets.kickbase_credentials.username, st.secrets.kickbase_credentials.password)
    league_id = kb._get_league_id(league[0])
    return kb, league_id



def get_current_matchday(_kb, league_id):
    return _kb.league_stats(league_id).current_day


@st.experimental_memo
def construct_query(positions, show_transfermarket):
    if len(positions) == 0:
        if show_transfermarket:
            return "SELECT * FROM spieler WHERE transfer = 1"
        else:
            return "SELECT * FROM spieler"
    if len(positions) == 1:
        if show_transfermarket:
            return f"""SELECT * FROM spieler WHERE position = "{positions[0]}" AND transfer = 1"""
        else:
            return f"""SELECT * FROM spieler WHERE position = "{positions[0]}" """
    
    if show_transfermarket:
        return f"SELECT * FROM spieler WHERE position IN {tuple(positions)} AND transfer = 1"

    return f"SELECT * FROM spieler WHERE position IN {tuple(positions)}"


# DataFrame (Pandas) holt sich Daten aus mysql-Datenbank
@st.experimental_memo()
def load_data(positions, show_transfermarket):
    sql_query = construct_query(positions, show_transfermarket)
    engine = init_connection()
    with engine.connect() as conn:
        df = pd.read_sql(sql_query, conn)
        df_points = pd.read_sql("SELECT * FROM punkte", conn)
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        return df, df_points, dt_string




# aus df_points wird der schnitt berechnet und df als spalte angefügt
@st.cache
def calc_average(df, df_points, next_matchday, avg_range, delete_peaks):
    first_matchday = next_matchday - avg_range
    avg_points = []
    for player_id in df['player_id'].tolist():
        lst_points = df_points[(df_points['player_id'] == player_id) & (df_points['matchday'] > first_matchday)]['points'].to_list()
        # Max und Min entfernen
        if delete_peaks and len(lst_points) >= 3:
            lst_points.remove(max(lst_points))
            lst_points.remove(min(lst_points))
        
        avg_points.append(sum(lst_points)/avg_range)
    df['avg_points'] = avg_points
    return df



####
# Update Database
####

def db_delete_all():
    engine = init_connection()
    with engine.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS spieler")
        conn.execute("DROP TABLE IF EXISTS punkte")



def db_create():
    engine = init_connection()
    with engine.connect() as conn:
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
        conn.execute(sql_command)

        sql_command = """
        CREATE TABLE IF NOT EXISTS punkte (
            matchday    INTEGER,
            points      INTEGER,
            player_id   INTEGER,
            PRIMARY KEY (matchday, player_id),
            FOREIGN KEY (player_id) REFERENCES spieler(player_id)
        )"""
        conn.execute(sql_command)
 


def get_player_info(_kb, league_id):
    players_list = []
    for team in BUNDESLIGA:
        players = _kb.team_players(team)
        for p in players:
            player_id = int(_kb._get_player_id(p))
            player_dict = {
               "d_player_id"   : player_id, 
               "d_last_name"   : p.last_name, 
               "d_first_name"  : p.first_name, 
               "d_value"       : int(p.market_value), 
               "d_value_trend" : TRENT_DICT[int(p.market_value_trend)], 
               "d_team"        : TEAM_DICT[team], 
               "d_position"    : POSITION_DICT[int(p.position)], 
               "d_status"      : STATUS_DICT[int(p.status)], 
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



def db_update_player(players_list, engine, metadata):
    table_spieler = metadata.tables["spieler"]
    #conn.execute(insert(my_table), players_list)
    u = update(table_spieler)
    u = u.where(table_spieler.c.player_id == bindparam("d_player_id"))
    u = u.values({
        "value":        bindparam("d_value"),
        "value_trend":  bindparam("d_value_trend"),
        "status":       bindparam("d_status"),
        "user":         bindparam("d_user"),
        "transfer":     bindparam("d_transfer"),
        })

    with engine.connect() as conn:
        conn.execute(u, players_list)



def get_points_info(_kb):
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



def db_update_points(points_list, engine, metadata):
    table_punkte = metadata.tables["punkte"]
    i = insert(table_punkte)
    i = i.values({
        "matchday":     bindparam("d_matchday"),
        "points":       bindparam("d_points"),
        "player_id":    bindparam("d_player_id")
        })
    i = i.on_duplicate_key_update(player_id = i.inserted.player_id)

    with engine.connect() as conn:
        conn.execute(i, points_list)



@st.experimental_singleton
def init_lock():
    lock = threading.Lock()
    return lock



def database_thread(kb, league_id):
    try:
        start = time.time()
        engine = sqlalchemy.create_engine(**st.secrets["sqlalchemy"])
        metadata = MetaData()
        metadata.reflect(bind=engine)
        print("Started thread...")
        players_list = get_player_info(kb, league_id)
        db_update_player(players_list, engine, metadata)
        points_list = get_points_info(kb)
        db_update_points(points_list, engine, metadata)
        print(f"Thread Runtime = {time.time() - start}")
    
    finally:
        print("DB Updated (thread end)")
        update_data.clear()


@st.experimental_singleton
def update_data():
    print("Running")
    kb, league_id = get_kickbase_object()
    thread = threading.Thread(target=database_thread, args=(kb, league_id))
    add_script_run_ctx(thread)
    thread.start()


def main():
    kb, league_id = get_kickbase_object()
    match_day = get_current_matchday(kb, league_id)

    st.title('Kickbase Analyzer')
    st.subheader(f'Average Points ({str(match_day)}. Matchday)')
    avg_range = st.slider("Select how many matchdays will count", 1, match_day, 5)
    positions = st.multiselect('Select whitch positions to show', ['TW', 'ABW', 'MIT', 'ANG'], [])
    show_transfermarket = st.checkbox('Show only transfermarket', False)
    delete_peaks = st.checkbox('Delete peaks in points (positive and negative)')

    data_load_state = st.text('Loading data...')
    df, df_points, now = load_data(positions, show_transfermarket)
    df = calc_average(df, df_points, match_day, avg_range, delete_peaks)

    data_load_state.text("Done! Data from " + now)

    fig = px.scatter(df, x="avg_points", y="value",
        labels={
            "avg_points": "Average Points",
            "value": "Market Value",
            "user": "User",
        },
        color="user",
        custom_data=["last_name", "first_name", "position", "status", "team"]
        )
    fig.update_traces(
        hovertemplate="<br>".join([
            "<b>%{customdata[0]}</b> (%{customdata[2]})",
            "%{customdata[1]}",
            "<i>%{customdata[3]}</i>",
            "%{customdata[4]}",
            "<b>%{y}</b>"
            ])
        )

    st.plotly_chart(fig, use_container_width=True)
    
    if st.checkbox('Show raw data'):
        st.subheader('Raw data')
        st.write(df)

    st.subheader(f'Update Database')

    if st.button('Update Marketvalue/Status'):
        update_data()
        

if __name__ == "__main__":
    start = time.time()
    main()
    print(time.time() - start)