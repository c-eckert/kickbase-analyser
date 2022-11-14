import streamlit as st
import myKickbase
import pandas as pd
from myFrontend import player_row, points_diagram



def main():
    st.set_page_config(page_title="Transfermarket", page_icon="📈")
    
    with open('style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("# Transfermarket")
    st.sidebar.subheader("Team value")

    kb, league_id = myKickbase.get_kickbase_object()
    market = kb.market(league_id)
    market_players = market.players

    counting_value = [0]*len(market_players)
    values = [int(p.market_value) for p in market_players]

    
    df = pd.DataFrame(market_players, columns=["objects"])
    df["value"] = [int(p.market_value) for p in market_players]
    df["totalPoints"] = [int(p.totalPoints) for p in market_players]
    df["average_points"] = [int(p.average_points) for p in market_players]
    df["position"] = [int(p.position) for p in market_players]
    
    sort_by = st.radio(
        "Sort by", ("Position", "Value", "Avg Points", "Total Points")
    )

    if sort_by == "Position":
        for position in myKickbase.POSITION_DICT:
            st.subheader(myKickbase.POSITION_DICT[position])
            for i, user_player in enumerate(market_players):
                if user_player.position == position:
                    btn = st.checkbox("Sell", key=i)
                    if btn:
                        counting_value[i] = 1
                    
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