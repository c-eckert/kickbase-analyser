import streamlit as st
import pandas as pd
import myKickbase
from myFrontend import player_row_short

from kickbase_api.models import player



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


    #feeds = kb.league_feed(0, league_id)
    #for feed in feeds:
    #    if feed.type == feed_item.FeedType.BUY or feed.type == feed_item.FeedType.SALE:
    #        print("---------------------")
    #        print(feed.type)
    #        print(feed.date)
    #        print(f"{feed.meta.seller_name} --> {feed.meta.buyer_name}")
    #        print(feed.meta.player_last_name)
    #        print(int(feed.meta.buy_price))
    #        print(feed.meta.buyer_id)
            

    for user in user_dict:

        user_players = kb.league_user_players(league_id, user_dict[user])
        user_profile = kb.league_user_profile(league_id, user_dict[user])
        user_stats = kb.league_user_stats(league_id, user_dict[user])
        print(user_stats.seasons)
        
        df = pd.DataFrame(user_players, columns=["objects"])
        df["value"] = [int(p.market_value) for p in user_players]
        df["totalPoints"] = [int(p.totalPoints) for p in user_players]
        df["average_points"] = [int(p.average_points) for p in user_players]
        df["position"] = [int(p.position) for p in user_players]

        st.sidebar.subheader(user)
        st.sidebar.text(f"Wert:  {df['value'].sum():,} €")
        st.sidebar.text(f"Pkt:   {df['totalPoints'].sum():,}")
        st.sidebar.text(f"⌀ Pkt: {df['average_points'].sum():,}")

        team_dict = {
            "status": 0,
            "number": 0,
            "position": player.PlayerPosition.UNKNOWN,
            "last_name": user,
            "totalPoints": df['totalPoints'].sum(),
            "average_points": df['average_points'].sum(),
            "market_value_trend": 0,
            "market_value": df['value'].sum()
        }
        team_obj = player.Player(team_dict)
        player_row_short(team_obj)

        with st.expander("See Player"):
            df = df.sort_values(by="value", ascending=False)
            for user_player in df["objects"]:
                player_row_short(user_player)


if __name__ == "__main__":
    main()