import myDatabase
import myKickbase

engine, metadata = myDatabase.init_connection()
kb, league_id = myKickbase.get_kickbase_object()

myDatabase.drop_all()
myDatabase.create_all()

players_list = myKickbase.get_player_from_kb(kb, league_id)
myDatabase.insert_player(players_list, engine, metadata)
points_list = myKickbase.get_points_from_kb(kb)
myDatabase.update_points(points_list, engine, metadata)