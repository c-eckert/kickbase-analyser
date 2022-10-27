import streamlit as st
from kickbase_api.kickbase import Kickbase
from kickbase_api.exceptions import KickbaseException
import numpy as np
import plotly.graph_objects as go

bundesliga = [2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 18, 20, 24, 28, 40, 43]

def calc_regression(x, y):
    regression = LinearRegression()
    res = regression.fit(x.reshape(-1,1), y)
    return res.predict(x.reshape(-1,1))


def last_avg(player, next_matchday, counting_matchdays):
    
    player_id = kickbase._get_player_id(player)
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
    punkte_summe = 0
    for matchday in season:
        if (matchday["d"] > next_matchday - counting_matchdays):
            punkte_summe += matchday["p"]

    return int(punkte_summe/counting_matchdays)


def calc_avg(players, next_matchday, counting_matchdays):
    avg_array = np.array([])
    for p in players:
        avg_array = np.append(avg_array, int(last_avg(p, next_matchday, counting_matchdays)))
    return avg_array

kickbase = Kickbase()

username = st.text_input('Username')
password = st.text_input('Password')

user, league = kickbase.login(username, password)


# market player
market_value = np.array([])
tot_points = np.array([])
names = np.array([])

market = kickbase.market(league[0])
market_players = market.players

for p in market_players:
    market_value = np.append(market_value, int(p.market_value))
    tot_points = np.append(tot_points, int(p.totalPoints))
    names = np.append(names, p.last_name + ", " + p.first_name)


# team player
team_market_value = np.array([])
team_tot_points = np.array([])
team_names = np.array([])

team_players = kickbase.league_user_players(league[0], user)

for p in team_players:
    team_market_value = np.append(team_market_value, int(p.market_value))
    team_tot_points = np.append(team_tot_points, int(p.totalPoints))
    team_names = np.append(team_names, p.last_name + ", " + p.first_name)


#############
# STREAMLIT #
#############


st.write("""
# My first app
Hello world
""")

st.write("## Average Points")
number = st.slider("Select how many matchdays will count", 1, 11, 5)
market_avg_points = calc_avg(market_players, 11, number)
team_avg_points = calc_avg(team_players, 11, number)

# Create traces
fig = go.Figure()
#fig.add_trace(go.Scatter(x=all_avg5_points, y=all_market_value, name="Bundesliga", mode="markers", text=all_names))
fig.add_trace(go.Scatter(x=market_avg_points, y=market_value, name="Transfermarkt", mode="markers", text=names, marker_symbol=3))
fig.add_trace(go.Scatter(x=team_avg_points, y=team_market_value, name="Team", mode="markers", text=team_names, marker_symbol=3))
#fig.add_trace(go.Scatter(x=avg_regression, y=all_market_value, name="Durchschnittsmarktwert", mode = "lines", marker_color = "lightgreen"))

st.plotly_chart(fig, use_container_width=True)
