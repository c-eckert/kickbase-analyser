import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import pandas as pd
import plotly.express as px
from kickbase_api.exceptions import KickbaseException
from threading import Thread, Lock
from queue import Queue
from time import time

import os

import myKickbase

@st.experimental_memo
def replace_df(df):
    df["value_trend"] = df["value_trend"].map(myKickbase.TREND_DICT)
    df["team"] = df["team"].map(myKickbase.TEAM_DICT)
    df["position"] = df["position"].map(myKickbase.POSITION_DICT)
    df["status"] = df["status"].map(myKickbase.STATUS_DICT)
    return df


@st.experimental_memo
def filter_df(df, positions, show_transfermarket):
    if show_transfermarket:
        df = df[df["transfer"] == 1]
    
    if len(positions) == 0:
        return df
    else:
        return df[df["position"].isin(positions)]


# aus df_points wird der schnitt berechnet und df als spalte angefügt
@st.experimental_memo
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


class MyQueue(object):
    def __init__(self) -> None:
        self.lock = Lock()
        self.items = []
    
    def add(self, item):
        with self.lock:
            self.items.append(item)

    def getAll(self):
        return self.items

def consumer(kb, queue, points_list):
    while True:
        player_id = queue.get()
        if player_id is None:
            break
        try:
            getPoints(kb, player_id, points_list)
        finally:
            queue.task_done()
    

def getPoints(kb, player_id, points_list):
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
        player_dict = {
            "d_matchday"  : matchday,
            "d_points"    : points,
            "d_player_id" : player_id,
        }
        points_list.add(player_dict)


@st.experimental_memo(ttl=60*30)
def get_points_from_kb(_kb, player_ids, no_threads):
    queue = Queue() # queue mit allen PlayerIDs
    points_list = MyQueue()
    
    for _ in range(no_threads):
        consumer_thread = Thread(target=consumer, args=[_kb, queue, points_list])
        add_script_run_ctx(consumer_thread)
        consumer_thread.start()

    _ = [queue.put(player_id) for player_id in player_ids]
    queue.join()
    return points_list.getAll()


def main():
    st.set_page_config(
        page_title="Marktwertanalyse", 
        page_icon="📈"
    )

    kb, league_id = myKickbase.get_kickbase_object()
    match_day = myKickbase.get_current_matchday()

    st.title('Kickbase Analyzer')
    st.subheader(f'Average Points ({str(match_day)}. Matchday)')
    avg_range = st.slider("Select how many matchdays will count", 1, match_day, 5)
    positions = st.multiselect('Select whitch positions to show', ['TW', 'ABW', 'MIT', 'ANG'], [])
    show_transfermarket = st.checkbox('Show only transfermarket', False)
    delete_peaks = st.checkbox('Delete peaks in points (positive and negative)')
    data_load_state = st.text('Loading data...')
    
    t_A = f"UI:  {time() - start}"
    
    no_threads = st.number_input("Threads", 1, 120, 24)

    players_list = myKickbase.get_player_from_kb(kb, league_id)
    df = pd.DataFrame(players_list)
    df = df.rename({
        'd_player_id': 'player_id', 
        'd_last_name': 'last_name', 
        'd_first_name': 'first_name', 
        'd_value': 'value', 
        'd_value_trend': 'value_trend', 
        'd_team': 'team',
        'd_position': 'position',
        'd_status': 'status',
        'd_user': 'user',
        'd_transfer': 'transfer'}, axis=1)
    
    t_B = f"Pla: {time() - start}"

    points_list = get_points_from_kb(kb, df['player_id'], no_threads)

    df_points = pd.DataFrame(points_list)
    df_points = df_points.rename({
        'd_matchday': 'matchday',
        'd_points': 'points',
        'd_player_id': 'player_id'}, axis=1)
    
    t_C = f"Poi: {time() - start}"


    df = replace_df(df)
    df = filter_df(df, positions, show_transfermarket)
    df = calc_average(df, df_points, match_day, avg_range, delete_peaks)
    data_load_state.text("Done!")
    
    fig = px.scatter(df, x="avg_points", y="value",
        labels={
            "avg_points": "Average Points",
            "value": "Market Value",
            "user": "User",
        },
        color="user",
        custom_data=["last_name", "first_name", "position", "status", "team"],
        trendline="ols",
        trendline_scope="overall"
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
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", 
        #plot_bgcolor="rgba(0,0,0,0)",
        margin = dict(l=0, r=0, b=0, t=0, pad=0),
        #yaxis_visible=False,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="left",
            x=0
        )
        )
    st.plotly_chart(fig, use_container_width=True)
    
    if st.checkbox('Show raw data'):
        st.subheader('Raw data')
        st.write(df)

    t_D = f"END: {time() - start}"
    st.text(str(t_A))
    st.text(str(t_B))
    st.text(str(t_C))
    st.text(str(t_D))

if __name__ == "__main__":
    print("----------------------")
    start = time()
    main()
    print(f"END: {time() - start}")