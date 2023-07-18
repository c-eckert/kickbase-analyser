import streamlit as st
import myKickbase
import altair as alt
import pandas as pd

def player_row(player):
    if player.status == 0:
        color = "#22c48b" # green
    else:
        color = "#ea5f42" # red
    st.markdown(f"""
        <table>
            <tr style="border: 0px;">
                <td width="30%" style="border: 0px; padding: 1%;">
                    <img src={player.profile_big_path}>
                </td>
                <td width="70%" style="border: 0px; padding: 1%;">
                    <div class="parallelogram">{player.number}</div>
                    <div class="parallelogram">{myKickbase.POSITION_DICT[player.position]}</div>
                    <div class="parallelogram" style="background: {color};">{myKickbase.STATUS_DICT[player.status]}</div>
                    <div class="last_name">{player.last_name}</div>
                    <div style = "height: 5px;"></div>
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
    """, unsafe_allow_html=True)

def player_row_short(player):
    if player.status == 0:
        color = "#22c48b" # green
    else:
        color = "#ea5f42" # red

    st.markdown(f"""
        <div class="short_player_row">
            <table>
                <tr style="border: 0px;">
                    <td width="40%" style="border: 0px; padding: 0.3% 1%;">   
                        <div class="parallelogram">{player.number}</div>
                        <div class="parallelogram">{myKickbase.POSITION_DICT[player.position]}</div>
                        <div class="parallelogram" style="background: {color};">{myKickbase.STATUS_DICT[player.status]}</div>
                        <div class="last_name">{player.last_name}</div>
                    </td>
                    <td width="60%" style="border: 0px; padding: 1%;">
                        <div class="row_num">
                            <div class="column_left">{player.totalPoints}</div>
                            <div class="column_left">{player.average_points}</div>
                            <div class="column_right" style="color:{myKickbase.TREND_COLOR_DICT[player.market_value_trend]} ;">{int(player.market_value):,}€</div>
                        </div>
                        <div class="row_lab">
                            <div class="column_left">Pkt.</div>
                            <div class="column_left">⌀ Pkt.</div>
                            <div class="column_right">Marktwert</div>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)

def points_diagram(kb, player):
    points_list = []
    player_id = int(kb._get_player_id(player))
    myKickbase.request_points(kb, points_list, player_id)
    df = pd.DataFrame(points_list)
    df["color"] = df.apply(lambda row: "green" if row.d_points>100 else "red", axis=1)
    
    if len(df) > 0:
        c = alt.Chart(df).mark_bar(size=10).encode(
            x=alt.X("d_matchday:O", axis=alt.Axis(labels=True), title=None), 
            y=alt.Y("d_points:Q", axis=alt.Axis(labels=True, domain=False, ticks=False), title=None),
            color=alt.condition(
                alt.datum.d_points > 100,
                alt.value("#22c48b"),
                alt.value("#ea5f42")
                )
            ).properties(
                height=150
            )

        text = c.mark_text(
            baseline='bottom',
        ).encode(
            text='d_points:Q'
        )

        layer = alt.layer(c, text).configure_view(stroke="transparent")
        st.altair_chart(layer, use_container_width=True)
