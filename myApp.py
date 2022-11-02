import sqlite3
from sqlite3 import Connection
import streamlit as st
import pandas as pd
from kickbase_api.kickbase import Kickbase
from kickbase_api.exceptions import KickbaseException
import plotly.express as px


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

DB_FILE = "database/player.db"


@st.cache(allow_output_mutation=True)
def get_sql_connection(path):
    return sqlite3.connect(path)


@st.cache(allow_output_mutation=True)
def get_kickbase_object():
    kb = Kickbase()
    user_me, league = kb.login(st.secrets.kickbase_credentials.username, st.secrets.kickbase_credentials.password)
    return kb, user_me, league


@st.cache
def get_current_matchday(kb, league):
    return kb.league_stats(kb._get_league_id(league[0])).current_day


@st.cache(hash_funcs={Connection: id})
def db_delete_all(conn):
    with conn:
        cur = conn.curser()
        cur.execute("DROP TABLE IF EXISTS spieler")
        cur.execute("DROP TABLE IF EXISTS punkte")


@st.cache(hash_funcs={Connection: id})
def db_create(conn):
    with conn:
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


@st.cache(hash_funcs={Connection: id})
def db_update(conn, kb, league, update_points, insert_all):
    with conn:
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


                if insert_all:
                    conn.execute(
                        "INSERT INTO spieler VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (player_id, last_name, first_name, market_value, market_value_trend, 
                        team_name, position, status, user, transfer)
                    )
                    db_update_points(kb, conn, player_id)

                else:
                    conn.execute(
                        "UPDATE spieler SET value = ?, value_trend = ?, status = ?, user = ?, transfer = ? WHERE player_id = ?;", 
                        (market_value, market_value_trend, status, user, transfer, player_id)
                    )
                    if update_points:
                        db_update_points(kb, conn, player_id)

        db_update_user(kb, conn, league)
        db_update_transfer(kb, conn, league)


@st.cache(hash_funcs={Connection: id})
def db_update_points(kb, conn, player_id):
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

        conn.execute(
            "INSERT OR IGNORE INTO punkte VALUES(?, ?, ?)",
            (matchday, points, player_id)
        )


@st.cache(hash_funcs={Connection: id})
def db_update_user(kb, conn, league):
    users = kb.league_users(kb._get_league_id(league[0]))
    for user in users:
        user_players = kb.league_user_players(kb._get_league_id(league[0]), user.id)
        for p in user_players:
            player_id = int(kb._get_player_id(p))
            conn.execute(
            "UPDATE spieler SET user = ? WHERE player_id = ?;",
            (user.name, player_id)
    )


@st.cache(hash_funcs={Connection: id})
def db_update_transfer(kb, conn, league):
    market = kb.market(league[0])
    market_players = market.players
    for p in market_players:
        player_id = kb._get_player_id(p)
        conn.execute(
            "UPDATE spieler SET transfer = ? WHERE player_id = ?;",
            (True, player_id)
        )


@st.cache
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


# DataFrame (Pandas) holt sich Daten aus sqlite-Datenbank
@st.cache(hash_funcs={Connection: id})
def load_data(conn, next_matchday, avg_range, positions, delete_peaks, show_transfermarket):
    with conn:
        cur = conn.cursor()
        sql_query = construct_query(positions, show_transfermarket)
        df = pd.read_sql_query(sql_query, conn)
        avg_points = []
        for player_id in df['player_id'].tolist():
            
            first_matchday = next_matchday - avg_range
            cur.execute(
                "SELECT points FROM punkte WHERE (player_id = ? AND matchday > ?)", 
                (player_id, first_matchday)
            )
            lst_points = cur.fetchall()
            lst_points = [int(x[0]) for x in lst_points]
            
            # Max und Min entfernen
            if delete_peaks and len(lst_points) >= 3:
                lst_points.remove(max(lst_points))
                lst_points.remove(min(lst_points))
            
            avg_points.append(sum(lst_points)/avg_range)
        
        df['avg_points'] = avg_points

    return df


def main():
    conn = get_sql_connection(DB_FILE)
    kb, user_me, league = get_kickbase_object()
    match_day = get_current_matchday(kb, league)

    st.title('Kickbase Analyzer')
    st.subheader(f'Average Points ({str(match_day)}. Matchday)')
    avg_range = st.slider("Select how many matchdays will count", 1, match_day, 5)
    positions = st.multiselect(
        'Select whitch positions to show',
        ['TW', 'ABW', 'MIT', 'ANG'],
        [])
    show_transfermarket = st.checkbox('Show only transfermarket', False)
    delete_peaks = st.checkbox('Delete peaks in points (positive and negative)')

    data_load_state = st.text('Loading data...')
    df = load_data(conn, match_day, avg_range, positions, delete_peaks, show_transfermarket)
    data_load_state.text("Done!")

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
    
    if st.button('Update Marketvalue'):
        db_update(conn, kb, league, False, False)

    if st.button('Update Points (ca. 1 min)'):
        db_update(conn, kb, league, True, False)
    
    if st.checkbox('Show raw data'):
        st.subheader('Raw data')
        st.write(df)


if __name__ == "__main__":
    main() 
