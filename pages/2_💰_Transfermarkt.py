import streamlit as st
import numpy as np
import myKickbase



def main():
    st.set_page_config(page_title="Transfermarkt", page_icon="📈")
    
    with open('style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("# Plotting Demo")
    st.sidebar.header("Plotting Demo")
    st.write(
        """This demo illustrates a combination of plotting and animation with
    Streamlit. We're generating a bunch of random numbers in a loop for around
    5 seconds. Enjoy!"""
    )

    kb, league_id = myKickbase.get_kickbase_object()
    market = kb.market(league_id)
    market_players = market.players

    for position in myKickbase.POSITION_DICT:
        st.markdown(f"## {myKickbase.POSITION_DICT[position]}")
        st.markdown("----")
        for i, user_player in enumerate(market_players):
            if user_player.position == position:
                
                with st.container():
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        img_url = user_player.profile_big_path
                        if img_url != None:
                            st.image(img_url)
                    
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


if __name__ == "__main__":
    main()