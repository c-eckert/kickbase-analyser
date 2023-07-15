import streamlit as st
import pandas as pd
import myKickbase
from myFrontend import player_row_short


def main():
    st.set_page_config(page_title="Compare", page_icon="⚽️")
    
    with open('style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("# Teams")

    kb, league_id = myKickbase.get_kickbase_object()
    users = kb.league_users(league_id)
    user_names = [user.name for user in users]
    user_ids = [user.id for user in users]
    user_dict = dict(zip(user_names, user_ids))

    users = {}

    for user in user_dict:

        user_players = kb.league_user_players(league_id, user_dict[user])
        
        df = pd.DataFrame(user_players, columns=["objects"])
        df["value"] = [int(p.market_value) for p in user_players]
        df["totalPoints"] = [int(p.totalPoints) for p in user_players]
        df["average_points"] = [int(p.average_points) for p in user_players]
        df["position"] = [int(p.position) for p in user_players]

        st.sidebar.subheader(user)
        st.sidebar.text(f"Wert:  {df['value'].sum():,} €")
        st.sidebar.text(f"Pkt:   {df['totalPoints'].sum():,}")
        st.sidebar.text(f"⌀ Pkt: {df['average_points'].sum():,}")

        st.subheader(user)
        st.text(f"Wert:  {df['value'].sum():,} €")
        st.text(f"Pkt:   {df['totalPoints'].sum()}")
        st.text(f"⌀ Pkt: {df['average_points'].sum()}")

        df = df.sort_values(by="value", ascending=False)
        for user_player in df["objects"]:
            player_row_short(user_player)


if __name__ == "__main__":
    main()