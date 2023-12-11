from datetime import date
from pathlib import Path
from yfpy import models
from yfpy.data import Data
from yfpy.query import YahooFantasySportsQuery
import os

print("Starting Up...")

data = Data(Path("./cache"), True)
query = YahooFantasySportsQuery(Path("./"), "####", "nba")
team_id = ""
stats_map = {}
important_stats = ["GP", "FGA", "FGM", "FTA", "FTM", "3PTM", "PTS", "REB", "AST", "ST", "BLK", "TO"]
display_stats = ["FG%", "FT%", "3PTM", "PTS", "REB", "AST", "ST", "BLK", "TO"]
current_week = 0

def set_league_id(name: str):
    game: models.Game = None
    try:
        game = data.load("game_info", models.Game)
    except:
        game = data.save("game_info", query.get_current_game_info)

    try:
        leagues = data.load("user_leagues", list[models.League])
    except:
        leagues = data.save("user_leagues", query.get_user_leagues_by_game_key, { 'game_key': game.game_key })

    for league in leagues:
        if str(league.name) == name:
            query.league_id = league.league_id
            query.game_id = game.game_id
            return league.league_id
    return ""

def set_team_id():
    try:
        games = data.load("user_teams", list[models.Game])
    except:
        games = data.save("user_teams", query.get_user_teams)
    nba_game = None
    for game in games:
        if game.code == "nba" and game.season == date.today().year:
            nba_game = game
            break
    if nba_game is None:
        return ""
    for team in game.teams:
        if team.team_key.split(".")[2] == query.league_id:
            return team.team_id
    return ""

def map_stats():
    try:
        stat_cats = data.load("stat_cats", models.StatCategories)
    except:
        stat_cats = data.save("stat_cats", query.get_game_stat_categories_by_game_id, { 'game_id': query.game_id })
    for stat in stat_cats.stats:
        stats_map[stat.stat_id] = stat.display_name

def print_team_stats():
    print("The players currently on your team are:")
    for player in team_players_names:
        print(player)

    print("\nYour team's average weekly stats are:")
    for stat in display_stats:
        print(stat + ": " + str(team_stats[stat]))

if set_league_id("b'balla balla'") == "":
    print("Error setting league ID")

team_id = set_team_id()
if team_id == "":
    print("Error setting team ID")

map_stats()
if stats_map == {}:
    print("Error mapping stats")

for league in data.load("user_leagues", list[models.League]):
    if league.league_id == query.league_id:
        current_week = league.current_week

players: list[models.Player] = []
team_players = []

stats: dict[str, dict[str, float]] = {}

roster: models.Roster = None

for i in range(12):
    try: 
        roster = data.load("team_roster_" + str(i + 1), models.Roster)
    except:
        roster = data.save("team_roster_" + str(i + 1), query.get_team_roster_by_week, { 'team_id': i + 1, 'chosen_week': current_week })
    if i + 1 == team_id:
        team_players = roster.players
    players = players + roster.players 

for file in os.listdir("./cache"):
    if file.endswith("-player.json") and not file.startswith(str(date.today())):
        os.remove(file)


for player in players:
    filename = str(date.today()) + "-" + player.player_key + "-player" 
    stats[player.name.full] = {}
    try:
        player_stats = data.load(filename, models.Player)
    except:
        player_stats = data.save(filename, query.get_player_stats_for_season, { 'player_key': player.player_key, 'limit_to_league_stats': False })
    for stat in player_stats.player_stats.stats:
        if stat.stat_id in stats_map:
            stats[player.name.full][stats_map[stat.stat_id]] = stat.value

    if stats[player.name.full]['GP'] != 0:
        for stat_name in stats[player.name.full]:
            if stat_name != "GP":
                stats[player.name.full][stat_name] /= stats[player.name.full]['GP']
    
    if stats[player.name.full]['FT%'] != 0:
        stats[player.name.full]["FT%"] = stats[player.name.full]["FTM"] / stats[player.name.full]["FTA"]
    if stats[player.name.full]['FG%'] != 0:
        stats[player.name.full]["FG%"] = stats[player.name.full]["FGM"] / stats[player.name.full]["FGA"]

team_stats = {}
team_players_names = []

for player in team_players:
    team_players_names.append(player.name.full)
    if player.selected_position.position in [None, "IL", "IL+"]:
        continue
    for stat in important_stats:
        if not stat in team_stats:
            team_stats[stat] = 0
        team_stats[stat] += (stats[player.name.full][stat] * 3)

team_stats["FT%"] = team_stats["FTM"] / team_stats["FTA"]
team_stats["FG%"] = team_stats["FGM"] / team_stats["FGA"]

print("Welcome to Yahoo Basketball Fantasy Calculator!")
print_team_stats()
old_player = input("\nPlease enter the name of the player you would like to remove from your team or -1 to quit: ")
while old_player != "-1":
    if old_player in team_players_names:
        new_player = input("\nPlease enter the name of the player you would like to add to your team: ")
        if new_player in stats:
            for stat in important_stats:
                team_stats[stat] += (stats[new_player][stat] * 3)
                team_stats[stat] -= (stats[old_player][stat] * 3)
            team_stats["FT%"] = team_stats["FTM"] / team_stats["FTA"]
            team_stats["FG%"] = team_stats["FGM"] / team_stats["FGA"]
            team_players_names.remove(old_player)
            team_players_names.append(new_player)
            print_team_stats()
        else:
            print(new_player + " not found!")
    else:
        print(old_player + " not found!")
    old_player = input("\nPlease enter the name of the player you would like to remove from your team or -1 to quit: ")