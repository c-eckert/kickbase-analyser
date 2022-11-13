import streamlit as st
import pandas as pd
import myKickbase
import altair as alt


def player_row(player):
    st.markdown(f"""
        <table>
            <tr style="border: 0px;">
                <td width="30%" style="border: 0px; padding: 0px;">
                    <img src={player.profile_big_path}>
                </td>
                <td width="70%" style="border: 0px; padding: 0px;">
                    <div class="number">{player.number} {myKickbase.POSITION_DICT[player.position]}</div>
                    <div class="last_name">{player.last_name}</div>
                    <div class="first_name">{player.first_name}</div>
                    <div class="row_num">
                        <div class="column_left">{player.totalPoints}</div>
                        <div class="column_left">{player.average_points}</div>
                        <div class="column_right">{myKickbase.TREND_DICT[player.market_value_trend]} {int(player.market_value):,}€</div>
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

def points_diagram(kb, player):
    points_list = []
    player_id = int(kb._get_player_id(player))
    myKickbase.request_points(kb, points_list, player_id)
    df = pd.DataFrame(points_list)
    df["color"] = df.apply(lambda row: "green" if row.d_points>100 else "red", axis=1)

    if len(df) > 0:

        c = alt.Chart(df).mark_bar().encode(
            x=alt.X("d_matchday:O", axis=alt.Axis(labels=True), title=None), 
            y=alt.Y("d_points:Q", axis=alt.Axis(labels=True, domain=False, ticks=False), title=None),
            color=alt.condition(
                alt.datum.d_points > 100,
                alt.value("#22c48b"),
                alt.value("#ea5f42")
                )
            )

        text = c.mark_text(
            baseline='bottom',
        ).encode(
            text='d_points:Q'
        )

        layer = alt.layer(c, text).configure_view(stroke="transparent")
        st.altair_chart(layer, use_container_width=True)


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
    
    sort_by = st.radio(
        "Sort by", ("Position", "Value", "Points")
    )
    df = pd.DataFrame(user_players, columns=["objects"])
    df["value"] = [int(p.market_value) for p in user_players]
    df["totalPoints"] = [int(p.totalPoints) for p in user_players]
    df["average_points"] = [int(p.average_points) for p in user_players]
    df["position"] = [int(p.position) for p in user_players]
    print(df)

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

    elif sort_by == "Points":
        df = df.sort_values(by="totalPoints", ascending=False)
        for user_player in df["objects"]:
            player_row(user_player)
            #with st.expander("View Points"):
            #    points_diagram(kb, user_player)

    st.sidebar.subheader("Value of selected Players")
    sum_values = sum([a*b for a,b in zip(counting_value,values)])
    st.sidebar.text(f"{sum_values:,} €")
if __name__ == "__main__":
    main()