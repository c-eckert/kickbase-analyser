import streamlit as st
import pandas as pd
import plotly.express as px
import myKickbase
import altair as alt



def main():
    st.set_page_config(page_title="Your Team", page_icon="📈")
    
    with open('style.css') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.markdown("# Your Team")
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
    
    for position in myKickbase.POSITION_DICT:
        st.subheader(myKickbase.POSITION_DICT[position])
        for i, user_player in enumerate(user_players):
            if user_player.position == position:
                #btn = st.checkbox("Sell", key=i)
                #if btn:
                #    counting_value[i] = 1
                st.markdown(f"""
                    <table style="padding: 1%;">
                        <tr style="border: 0px;">
                            <td width="30%" style="border: 0px; padding: 0px;">
                                <img src={user_player.profile_big_path}>
                            </td>
                            <td width="70%" style="border: 0px; padding: 0px;">
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
                            </td>
                        </tr>
                    </table>
                    <div height="10"></div>
                """, unsafe_allow_html=True)
                
                with st.expander("View Points"):
                    points_list = []
                    player_id = int(kb._get_player_id(user_player))
                    myKickbase.request_points(kb, points_list, player_id)
                    df = pd.DataFrame(points_list)
                    df["color"] = df.apply(lambda row: "green" if row.d_points>100 else "red", axis=1)

                    if len(df) > 0:

                        c = alt.Chart(df).mark_bar().encode(
                            x=alt.X("d_matchday:O", axis=alt.Axis(labels=True), title=None), 
                            y=alt.Y("d_points:Q", axis=alt.Axis(labels=True, domain=False, ticks=False), title=None),
                            color=alt.condition(
                                alt.datum.d_points > 100,
                                alt.value("green"),
                                alt.value("red")
                                )
                            )

                        text = c.mark_text(
                            baseline='bottom',
                        ).encode(
                            text='d_points:Q'
                        )

                        layer = alt.layer(c, text).configure_view(stroke="transparent")


                        st.altair_chart(layer, use_container_width=True)


                        #fig = px.bar(
                        #    df, x="d_matchday", y="d_points", text_auto=True,
                        #    labels={
                        #        "d_points": "Points",
                        #        "d_matchday": "Matchday",
                        #        "user": "User",
                        #    }
                        #)
                        #fig.update_traces(marker_color=df["color"])
                        #fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
                       # 
                       # st.plotly_chart(fig, use_container_width=True)
                        
    st.sidebar.subheader("Value of selected Players")
    sum_values = sum([a*b for a,b in zip(counting_value,values)])
    st.sidebar.text(f"{sum_values:,} €")
if __name__ == "__main__":
    main()