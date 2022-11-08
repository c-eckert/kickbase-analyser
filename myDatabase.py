import sqlalchemy
from sqlalchemy import insert, update, MetaData
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.sql.expression import bindparam

import streamlit as st
import pandas as pd

from datetime import datetime


# Initialize connection.
# Uses st.experimental_singleton to only run once.
@st.experimental_singleton
def init_connection():
    engine = sqlalchemy.create_engine(**st.secrets["sqlalchemy"])
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return engine, metadata
    

def drop_all():
    engine, metadata = init_connection()
    with engine.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS spieler")
        conn.execute("DROP TABLE IF EXISTS punkte")


def create_all():
    engine, metadata = init_connection()
    with engine.connect() as conn:
        sql_command = """
        CREATE TABLE IF NOT EXISTS spieler (
            player_id   INTEGER     PRIMARY KEY,
            last_name   TEXT,
            first_name  TEXT,
            value       INTEGER,
            value_trend TEXT,
            team        TEXT,
            position    TEXT,
            status      TEXT,
            user        TEXT,
            transfer    BOOL
        )"""
        conn.execute(sql_command)

        sql_command = """
        CREATE TABLE IF NOT EXISTS punkte (
            matchday    INTEGER,
            points      INTEGER,
            player_id   INTEGER,
            PRIMARY KEY (matchday, player_id),
            FOREIGN KEY (player_id) REFERENCES spieler(player_id)
        )"""
        conn.execute(sql_command)


# DataFrame (Pandas) holt sich Daten aus mysql-Datenbank
@st.experimental_memo
def select_all():
    engine, metadata = init_connection()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM spieler", conn)
        df_points = pd.read_sql("SELECT * FROM punkte", conn)
        now = datetime.now()
        dt_str = now.strftime("%d/%m/%Y %H:%M:%S")
        return df, df_points, dt_str


def update_player(players_list, engine, metadata):
    table_spieler = metadata.tables["spieler"]
    #conn.execute(insert(my_table), players_list)
    u = update(table_spieler)
    u = u.where(table_spieler.c.player_id == bindparam("d_player_id"))
    u = u.values({
        "value":        bindparam("d_value"),
        "value_trend":  bindparam("d_value_trend"),
        "status":       bindparam("d_status"),
        "user":         bindparam("d_user"),
        "transfer":     bindparam("d_transfer"),
        })

    with engine.connect() as conn:
        conn.execute(u, players_list)



def update_points(points_list, engine, metadata):
    table_punkte = metadata.tables["punkte"]
    i = insert(table_punkte)
    i = i.values({
        "matchday":     bindparam("d_matchday"),
        "points":       bindparam("d_points"),
        "player_id":    bindparam("d_player_id")
        })
    i = i.on_duplicate_key_update(player_id = i.inserted.player_id)

    with engine.connect() as conn:
        conn.execute(i, points_list)

