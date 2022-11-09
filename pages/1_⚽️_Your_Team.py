import streamlit as st
import numpy as np
import myKickbase



def main():
    st.set_page_config(page_title="Your Team", page_icon="📈")
    
    with open('style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("# Your Team")
    st.sidebar.header("Summe")

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
    
    for position in myKickbase.POSITION_DICT:
        st.markdown(f"## {myKickbase.POSITION_DICT[position]}")
        st.markdown("----")
        for i, user_player in enumerate(user_players):
            if user_player.position == position:
                btn = st.checkbox("Sell", key=i)
                if btn:
                    counting_value[i] = 1
                with st.container():
                    
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.image(user_player.profile_big_path)
                    
                    with col2:
                        st.markdown(f"""
                            <div class="number">{user_player.number} {myKickbase.POSITION_DICT[user_player.position]}</div>
                            <div class="last_name">{user_player.last_name}</div>
                            <div class="first_name">{user_player.first_name}</div>
                            <div class="row_num">
                                <div class="column_left">{user_player.totalPoints}</div>
                                <div class="column_left">{user_player.average_points}</div>
                                <div class="column_right">{myKickbase.TRENT_DICT[user_player.market_value_trend]} {int(user_player.market_value):,}€</div>
                            </div>
                            <div class="row_lab">
                                <div class="column_left">Pkt.</div>
                                <div class="column_left">⌀ Pkt.</div>
                                <div class="column_right">Marktwert</div>
                            </div>
                        """, unsafe_allow_html=True)
    sum_values = sum([a*b for a,b in zip(counting_value,values)])
    st.sidebar.text(f"{sum_values:,} €")
if __name__ == "__main__":
    main()