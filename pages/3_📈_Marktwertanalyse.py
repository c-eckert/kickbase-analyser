import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import myKickbase
from kickbase_api.exceptions import KickbaseException
import pandas as pd
from datetime import datetime
import plotly.express as px
from threading import Thread, Lock
import concurrent
from queue import Queue
import time


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


def get_points(kb, player_id):
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
        return player_dict

def get_threadpool(_kb):
    print("Start")
    points_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for team in myKickbase.BUNDESLIGA:
            players = _kb.team_players(team)
            for p in players:
                player_id = int(_kb._get_player_id(p))
                futures.append(pool.submit(get_points, _kb, player_id))
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                points_list.append(result)
    return points_list

# Variant 1
@st.experimental_memo(ttl=60*30)
def get_points_from_kb_1(_kb):
    print("Start")
    print(time.time() - start)
    queue = Queue()
    threads = []
    for team in myKickbase.BUNDESLIGA:
        players = _kb.team_players(team)
        for p in players:
            player_id = int(_kb._get_player_id(p))
            worker = DownloadWorker(queue, _kb, player_id)
            add_script_run_ctx(worker)
            threads.append(worker)
    print("Initialised")
    print(time.time() - start)   
    for t in threads:
        t.start()
    print("Started")
    print(time.time() - start)
    for t in threads:
        t.join()
    print("Joined")
    print(time.time() - start)
    points_list = []

    while not queue.empty():
        item = queue.get()
        if item is not None:
            points_list.append(item)

    return points_list

class DownloadWorker(Thread):
    def __init__(self, queue, kb, player_id):
        Thread.__init__(self)
        self.queue = queue
        self.kb = kb
        self.player_id = player_id

    def run(self):
        r = self.kb._do_get("/players/{}/points".format(self.player_id), True)

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
                "d_player_id" : self.player_id,
            }
            self.queue.put(player_dict)




# Variant 2


class ItemStore(object):
    def __init__(self) -> None:
        self.lock = Lock()
        self.items = []
    
    def add(self, item):
        with self.lock:
            self.items.append(item)

    def getAll(self):
        return self.items


concurrent = 24
locked_list = ItemStore()
q_id = Queue()

def doWork(kb):
    while True:
        player_id = q_id.get()
        getPoints(kb, player_id)
        q_id.task_done()
    

def getPoints(kb, player_id):
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
        locked_list.add(player_dict)




@st.experimental_memo(ttl=60*30)
def get_points_from_kb_2(_kb):
    for i in range(concurrent):
        t = Thread(target=doWork, args=[_kb])
        add_script_run_ctx(t)
        t.daemon = True
        t.start()

    for team in myKickbase.BUNDESLIGA:
        players = _kb.team_players(team)
        for p in players:
            player_id = int(_kb._get_player_id(p))
            q_id.put(player_id)
    q_id.join()
    
    points_list = locked_list.getAll()

    return points_list






def main():
    st.set_page_config(page_title="Marktwertanalyse", page_icon="📈")

    kb, league_id = myKickbase.get_kickbase_object()

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

    points_list = get_points_from_kb_2(kb)
    #points_list = get_threadpool(kb)
    #print(points_list)
    df_points = pd.DataFrame(points_list)
    df_points = df_points.rename({
        'd_matchday': 'matchday',
        'd_points': 'points',
        'd_player_id': 'player_id'}, axis=1)
    #print(df_points)

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