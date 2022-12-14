import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import plotly.express as px

from threading import Timer
from datetime import datetime, timedelta
import time

import myDatabase
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



@st.experimental_singleton
def init_time():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    return dt_string



def database_thread(kb, league_id):
    try:
        players_list = myKickbase.get_player_from_kb(kb, league_id)
        points_list = myKickbase.get_points_from_kb(kb)
        
        
        engine, metadata = myDatabase.init_connection()
        myDatabase.update_player(players_list, engine, metadata)
        myDatabase.update_points(points_list, engine, metadata)
    
    finally:
        engine.dispose()
        start_timer.clear()
        myDatabase.select_all.clear()
        start_timer()



# Start update thread every hour
@st.experimental_singleton
def start_timer():
    kb, league_id = myKickbase.get_kickbase_object()
    now = datetime.today()
    then = now.replace(day=now.day, hour=now.hour, minute=0, second=0, microsecond=0) + timedelta(hours=1)
    delta_t = then - now
    secs = delta_t.total_seconds()

    t = Timer(secs,
        database_thread, 
        args=(kb, league_id)
    )
    add_script_run_ctx(t)
    t.start()



def main():
    st.set_page_config(
        page_title="Spieler Analyse",
        page_icon="🧐"
    )
    #start_timer()
    st.sidebar.success("Select a demo above.")
    
    match_day = myKickbase.get_current_matchday()
    str_time = init_time()

    st.title('Kickbase Analyzer')

    st.subheader(f'Average Points ({str(match_day)}. Matchday)')

    avg_range = st.slider("Select how many matchdays will count", 1, match_day, 5)

    positions = st.multiselect('Select whitch positions to show', ['TW', 'ABW', 'MIT', 'ANG'], [])

    show_transfermarket = st.checkbox('Show only transfermarket', False)

    delete_peaks = st.checkbox('Delete peaks in points (positive and negative)')

    data_load_state = st.text('Loading data...')
    df, df_points, str_time = myDatabase.select_all()
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
       # plot_bgcolor="rgba(0,0,0,0)",
        margin = dict(
            l=0,
            r=0,
            b=0,
            t=0,
            pad=0
        ),
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

    st.text("Last load from db: " + str_time)
    
    if st.checkbox('Show raw data'):
        st.subheader('Raw data')
        st.write(df)

        
if __name__ == "__main__":
    start = time.time()
    main()
    print(time.time() - start)
