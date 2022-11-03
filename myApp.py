import sqlalchemy
from sqlalchemy.orm import Session
import streamlit as st
import pandas as pd
from kickbase_api.kickbase import Kickbase
from kickbase_api.exceptions import KickbaseException
import plotly.express as px
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
    return kb, user_me, league_id


def get_current_matchday(_kb, league_id):
    return _kb.league_stats(league_id).current_day


@st.experimental_memo
def db_delete_all():
    engine = init_connection()
    with engine.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS spieler")
        conn.execute("DROP TABLE IF EXISTS punkte")


@st.experimental_memo
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


@st.experimental_memo
def db_update(_kb, league_id, update_points, insert_all):
    engine = init_connection()
    with engine.connect() as conn:
        for team in BUNDESLIGA:
            players = _kb.team_players(team)
            for p in players:
                player_id = _kb._get_player_id(p)
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
                        "INSERT INTO spieler VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (player_id, last_name, first_name, market_value, market_value_trend, 
                        team_name, position, status, user, transfer)
                    )
                    db_update_points(_kb, conn, player_id)

                else:
                    conn.execute(
                        "UPDATE spieler SET value = %s, value_trend = %s, status = %s, user = %s, transfer = %s WHERE player_id = %s;", 
                        (market_value, market_value_trend, status, user, transfer, player_id)
                    )
                    if update_points:
                        db_update_points(_kb, conn, player_id)

        db_update_user(_kb, conn, league_id)
        db_update_transfer(_kb, conn, league_id)
        

@st.experimental_memo
def db_update_points(_kb, _conn, player_id):
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

        _conn.execute(
            "INSERT INTO punkte VALUES(%s, %s, %s) ON DUPLICATE KEY UPDATE player_id=player_id",
            (matchday, points, player_id)
        )


@st.experimental_memo
def db_update_user(_kb, _conn, league_id):
    users = _kb.league_users(league_id)
    for user in users:
        user_players = _kb.league_user_players(league_id, user.id)
        for p in user_players:
            player_id = int(_kb._get_player_id(p))
            _conn.execute(
                "UPDATE spieler SET user = %s WHERE player_id = %s;",
                (user.name, player_id)
            )


@st.experimental_memo
def db_update_transfer(_kb, _conn, league_id):
    market = _kb.market(league_id)
    market_players = market.players
    for p in market_players:
        player_id = _kb._get_player_id(p)
        _conn.execute(
            "UPDATE spieler SET transfer = %s WHERE player_id = %s;",
            (True, player_id)
        )


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
@st.experimental_memo
def load_data(positions, show_transfermarket):
    sql_query = construct_query(positions, show_transfermarket)
    engine = init_connection()
    with engine.connect() as conn:
        df = pd.read_sql(sql_query, conn)
        df_points = pd.read_sql("SELECT * FROM punkte", conn)
        return df, df_points




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


def main():
    kb, user_me, league_id = get_kickbase_object()
    match_day = get_current_matchday(kb, league_id)

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
    df, df_points = load_data(positions, show_transfermarket)
    df = calc_average(df, df_points, match_day, avg_range, delete_peaks)
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
    
    if st.button('Update Marketvalue/Status (ca. 20 s)'):
        db_update(kb, league_id, False, False)

    if st.button('Update Points (ca. 150 s)'):
        db_update(kb, league_id, True, False)
    
    if st.checkbox('Show raw data'):
        st.subheader('Raw data')
        st.write(df)
    


if __name__ == "__main__":
    start = time.time()
    main()
    print(time.time() - start)
