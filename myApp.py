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

st.title('Kickbase Analyzer')

kb = Kickbase()
user_me, league = kb.login(st.secrets.kickbase_credentials.username, st.secrets.kickbase_credentials.password)

DB_FILE = "database/player.db"

def update_database():
    

    conn = sqlite3.connect(DB_FILE)

    with conn:
        cur = conn.cursor()
        for team in bundesliga:
            players = kb.team_players(team)
            for p in players:
                player_id = kb._get_player_id(p)
                market_value = int(p.market_value)
                market_value_trend = trend_dict[int(p.market_value_trend)]
                status = status_dict[int(p.status)]

                cur.execute(
                    "UPDATE spieler SET value = ?, value_trend = ?, status = ?, role = ? WHERE player_id = ?;", 
                    (market_value, market_value_trend, status, role_dict[0], player_id)
                    )
        
        market = kb.market(league[0])
        market_players = market.players
        for p in market_players:
            player_id = kb._get_player_id(p)
            cur.execute(
                "UPDATE spieler SET role = ? WHERE player_id = ?;",
                (role_dict[3], player_id)
                )

        users = kb.league_users(kb._get_league_id(league[0]))
        for user in users:
            print(user.name)
            print(user.id)
            print(user_me.id)
            players = kb.league_user_players(league[0], user.id)
            for p in players:
                player_id = kb._get_player_id(p)
                if(user.id == user_me.id):
                    cur.execute(
                        "UPDATE spieler SET role = ? WHERE player_id = ?;", 
                        (role_dict[1], player_id)
                        )
                else:
                    cur.execute(
                        "UPDATE spieler SET role = ? WHERE player_id = ?;", 
                        (role_dict[2], player_id)
                        )

        



def construct_query(positions):
    if len(positions) == 0:
        return "SELECT * FROM spieler"
    if len(positions) == 1:
        return f"""SELECT * FROM spieler WHERE position = "{positions[0]}";"""
    
    return f"SELECT * FROM spieler WHERE position IN {tuple(positions)};"


# DataFrame (Pandas) holt sich Daten aus sqlite-Datenbank
#@st.cache
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


match_day = kb.league_stats(kb._get_league_id(league[0])).current_day
st.write(f"### {str(match_day)}. Matchday")

avg_range = st.slider("Select how many matchdays will count", 1, match_day, 5)

positions = st.multiselect(
    'Positions to show',
    ['TW', 'ABW', 'MIT', 'ANG'],
    [])

delete_peaks = st.checkbox('Delete peaks')

data_load_state = st.text('Loading data...')
df = load_data(match_day, avg_range, positions, delete_peaks)
data_load_state.text("Done! (using st.cache)")

if st.button('Update Database'):
    update_database()

if st.checkbox('Show raw data'):
    st.subheader('Raw data')
    st.write(df)

st.subheader(f'Average Points of last {avg_range} matchdays')
fig = px.scatter(df, x="avg_points", y="value",
    labels={
        "avg_points": "Average Points",
        "value": "Market Value",
        "role": "Role"
    },
    color="role",
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
