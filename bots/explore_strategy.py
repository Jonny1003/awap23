# Explore Function

from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
import random

def explore(game_state: GameState, bot_list, param_dict):
  game_info = game_state.get_info()
  ally_robots = game_state.get_ally_robots()
  enemy_robots = game_state.get_enemy_robots()
  strmap = game_state.get_str_map()
  adjacent_fog = find_fog(strmap, bot_list[0])

  # GET EXPLORER INFO
  explorer = bot_list[0]
  assert(explorer.get_type() == RobotType.EXPLORER)
  exp_name = explorer.name
  exp_row = explorer.row
  exp_col = explorer.col

  # CHECK IF EXPLORER IS ALONE
  if len(bot_list) == 1:
    terraformer_exists = False
  else:
    terraformer_exists = True
  if not terraformer_exists and explorer.battery < 10:
    dir_to_base = game_state.robot_to_base(exp_name, checkCollisions=True)[0]
    game_state.move_robot(exp_name, dir_to_base)

  # GET TERRAFORMER INFO (if exists)
  if terraformer_exists:
    terraformer = bot_list[1]
    terr_name = terraformer.name
    assert(terraformer.get_type() == RobotType.TERRAFORMER)
    terr_row = terraformer.row
    terr_col = terraformer.col

  # MOVE EXPLORER
  exp_opt_dir, exp_steps = game_state.optimal_path(exp_row, exp_col, adjacent_fog[0], adjacent_fog[1], checkCollisions=True)
  # check if we can move in this direction
  if game_state.can_move_robot(exp_name, exp_opt_dir):
    # try to not collide into robots from our team
    dest_loc = (
        exp_row + exp_opt_dir.value[0], exp_col + exp_opt_dir.value[1])
    dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]

    if dest_tile.robot is None or dest_tile.robot.team != explorer.team:
        game_state.move_robot(exp_name, exp_opt_dir)

  # MOVE TERRAFORMER (if exists)
  if terraformer_exists:
    if terraformer.battery < 20:
      dir_to_base = game_state.robot_to_base(terr_name, checkCollisions=True)[0]
      game_state.move_robot(terr_name, dir_to_base)
    else:
      terr_opt_dir, terr_steps = game_state.optimal_path(
          terr_row, terr_col, adjacent_fog[0], adjacent_fog[1], checkCollisions=True)
      # only move terraformer if it's farther from the destination than the explorer
      if terr_steps > exp_steps:
        # check if we can move in this direction
        if game_state.can_move_robot(terr_name, terr_opt_dir):
          # try to not collide into robots from our team
          dest_loc = (
              terr_row + terr_opt_dir.value[0], terr_col + terr_opt_dir.value[1])
          dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]

          if dest_tile.robot is None or dest_tile.robot.team != terraformer.team:
              game_state.move_robot(terr_name, terr_opt_dir)
  
  # TAKE ACTIONS
  if game_state.can_robot_action(exp_name):
    game_state.robot_action(exp_name)
  if terraformer_exists:
    if (terraformer.battery <= 30 or explorer.battery <= 10) and game_state.can_robot_action(terr_name):
      game_state.robot_action(terr_name)
  


def get_adjacent_fog(strmap, fog):
  # get a visible tile adjacent to fog
  i, j = fog
  unexplorable = ['I', '#']
  if i > 0 and strmap[i-1][j] not in unexplorable:
    return (i-1, j)
  elif i < len(strmap) - 1 and strmap[i+1][j] not in unexplorable:
    return (i+1, j) 
  elif j > 0 and strmap[i][j-1] not in unexplorable:
    return (i, j-1)
  elif j < len(strmap[0]) - 1 and strmap[i][j+1] not in unexplorable:
    return (i, j+1)
  return None

def find_fog(strmap, bot_loc):
  # bfs until we find a fog
  bot_row, bot_col = bot_loc
  queue = [bot_loc]
  visited = set()
  while len(queue) > 0:
    i, j = queue.pop()
    if strmap[i][j] == '#':
      fog = (i, j)
      adjacent_fog = get_adjacent_fog(strmap, fog)
      if adjacent_fog != None:
        return adjacent_fog
    visited.add((i, j))
    if i > 0 and (i-1, j) not in visited:
      queue.append((i-1, j))
    elif i < len(strmap) - 1 and (i+1, j) not in visited:
      queue.append((i+1, j))
    elif j > 0 and (i, j-1) not in visited:
      queue.append(i, j-1)
    elif j < len(strmap[0]) - 1 and (i, j+1) not in visited:
      queue.append(i, j+1)
  raise Exception("There was no fog :(")
