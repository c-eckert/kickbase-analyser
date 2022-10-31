import sqlite3
import streamlit as st
import pandas as pd
from kickbase_api.kickbase import Kickbase
import plotly.express as px


bundesliga = [2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 18, 20, 24, 28, 40, 43]

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

st.title('Uber pickups in NYC')

DB_FILE = "database/player.db"



def update_database(username, password):
    kickbase = Kickbase()
    user, league = kickbase.login(username, password)
    conn = sqlite3.connect(DB_FILE)
    with conn:
        cur = conn.cursor()
        for team in bundesliga:
            players = kickbase.team_players(team)
            for p in players:
                player_id = kickbase._get_player_id(p)
                market_value = int(p.market_value)
                market_value_trend = trend_dict[int(p.market_value_trend)]
                status = status_dict[int(p.status)]

                cur.execute("""
                UPDATE spieler 
                SET value = ?,
                    value_trend = ?,
                    status = ?,
                    role = ?
                WHERE player_id = ?;
                """, 
                (market_value, market_value_trend, status, role_dict[0], player_id)
            )

        players = kickbase.league_user_players(league[0], user)
        for p in players:
            player_id = kickbase._get_player_id(p)
            cur.execute("""
            UPDATE spieler 
            SET role = ? 
            WHERE player_id = ?;
            """, 
            (role_dict[1], player_id)
            )

        market = kickbase.market(league[0])
        market_players = market.players
        for p in market_players:
            player_id = kickbase._get_player_id(p)
            cur.execute("""
            UPDATE spieler 
            SET role = ? 
            WHERE player_id = ?;
            """,
            (role_dict[3], player_id)
            )



def construct_query(positions):
    if len(positions) == 0:
        return "SELECT * FROM spieler"
    if len(positions) == 1:
        return f"""SELECT * FROM spieler WHERE position = "{positions[0]}";"""
    
    return f"SELECT * FROM spieler WHERE position IN {tuple(positions)};"



@st.cache
def load_data(next_matchday, avg_range, positions, delete_peaks):
    conn = sqlite3.connect(DB_FILE)

    with conn:
        sql_query = construct_query(positions)
        df = pd.read_sql_query(sql_query, conn)
        avg_points = []
        for player_id in df['player_id'].tolist():
            cur = conn.cursor()
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

    conn.close()
    print(df)
    return df

st.write("## Average Points")
avg_range = st.slider("Select how many matchdays will count", 1, 11, 5)

positions = st.multiselect(
    'Positions to show',
    ['TW', 'ABW', 'MIT', 'ANG'],
    [])

delete_peaks = st.checkbox('Delete peaks')

data_load_state = st.text('Loading data...')
df = load_data(11, avg_range, positions, delete_peaks)
data_load_state.text("Done! (using st.cache)")

if st.button('Update Database'):
    update_database(st.secrets.kickbase_credentials.username, st.secrets.kickbase_credentials.password)

if st.checkbox('Show raw data'):
    st.subheader('Raw data')
    st.write(df)

st.subheader('Number of pickups by hour')
fig = px.scatter(
    df, 
    x="avg_points", 
    y="value", 
    color="role", 
    symbol="status", 
    hover_data=["last_name", "first_name", "position", "team"]
    )
st.plotly_chart(fig, use_container_width=True)
