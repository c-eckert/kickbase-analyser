import streamlit as st
import pandas as pd
import myKickbase
from myFrontend import player_row, points_diagram


def main():
    st.set_page_config(page_title="Teams", page_icon="⚽️")
    
    with open('style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("# Teams")
    st.sidebar.subheader("Team value")

    kb, league_id = myKickbase.get_kickbase_object()
    users = kb.league_users(league_id)
    user_names = [user.name for user in users]
    user_ids = [user.id for user in users]
    user_dict = dict(zip(user_names, user_ids))
    selcted_user = st.selectbox(
        'Which team do you want to see?',
        user_dict
    )

    user_players = kb.league_user_players(league_id, user_dict[selcted_user])
    counting_value = [0]*len(user_players)
    values = [int(p.market_value) for p in user_players]
    
    st.sidebar.text(f"{sum(values):,} €")
    
    
    df = pd.DataFrame(user_players, columns=["objects"])
    df["value"] = [int(p.market_value) for p in user_players]
    df["totalPoints"] = [int(p.totalPoints) for p in user_players]
    df["average_points"] = [int(p.average_points) for p in user_players]
    df["position"] = [int(p.position) for p in user_players]

    sort_by = st.radio(
        "Sort by", ("Position", "Value", "Avg Points", "Total Points")
    )

    if sort_by == "Position":
        for position in myKickbase.POSITION_DICT:
            st.subheader(myKickbase.POSITION_DICT[position])
            for i, user_player in enumerate(user_players):
                if user_player.position == position:
                    #btn = st.checkbox("Sell", key=i)
                    #if btn:
                    #    counting_value[i] = 1
                    
                    player_row(user_player)

    elif sort_by == "Value":
        df = df.sort_values(by="value", ascending=False)
        for user_player in df["objects"]:
            player_row(user_player)

    elif sort_by == "Avg Points":
        df = df.sort_values(by="average_points", ascending=False)
        for user_player in df["objects"]:
            player_row(user_player)
            with st.expander("View Points"):
                points_diagram(kb, user_player)

    elif sort_by == "Total Points":
        df = df.sort_values(by="totalPoints", ascending=False)
        for user_player in df["objects"]:
            player_row(user_player)
            with st.expander("View Points"):
                points_diagram(kb, user_player)

    st.sidebar.subheader("Value of selected Players")
    sum_values = sum([a*b for a,b in zip(counting_value,values)])
    st.sidebar.text(f"{sum_values:,} €")
if __name__ == "__main__":
    main()