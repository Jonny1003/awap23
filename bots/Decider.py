from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
import random
import numpy as np

def get_adj_tiles(tile, game_state):
    ginfo = game_state.get_info()
    width, height = len(ginfo.map), len(ginfo.map[0])
    all_dirs = [dir for dir in Direction]
    dest_locs = []
    valid_dirs = []
    for move_dir in all_dirs:
        new_tile = (tile[0] + move_dir.value[0], tile[1] + move_dir.value[1])
        if (0 <= new_tile[0] < width) and (0 <= new_tile[1] < height):
            dest_locs.append(new_tile)
            valid_dirs.append(move_dir)
    # print(tile, dest_locs)
    return dest_locs, valid_dirs

def get_closest_spawn(target, ally_tiles):
    best, best_dist = None, np.inf
    for tile in ally_tiles:
        dist = get_move_dist(tile.row, tile.col, target.row, target.col)
        if dist < best_dist:
            best_dist = dist
            best = tile
    return best, best_dist

# Assumes no obstacles
def get_move_dist(row1, col1, row2, col2):
    return max(abs(row1 - row2), abs(col1 - col2))

def evaluate_use(objective, cur_assigned, new_rob, ally_tiles):
    obj_type, tile, score = objective
    tile = tile["tile"]
    if new_rob != "New Robot":
        dist = get_move_dist(new_rob.row, new_rob.col, tile.row, tile.col)
    if obj_type == "Win Now":
        if new_rob == "New Robot":
            spawn, dist = get_closest_spawn(tile, ally_tiles)
            return score - dist - 1, [RobotType.TERRAFORMER, spawn.row, spawn.col]
        if new_rob.type == RobotType.TERRAFORMER:
            return score - dist, new_rob
        else:
            return -1, new_rob
    elif obj_type == "Old Mine":
        assigned_miners = 0
        for rob in cur_assigned:
            if rob.type == RobotType.MINER:
                assigned_miners += 1
        if new_rob == "New Robot":
            spawn, dist = get_closest_spawn(tile, ally_tiles)
            if assigned_miners >= 2:
                return -1, [RobotType.MINER, spawn.row, spawn.col]
            else:
                return score - dist/2 - 1, [RobotType.MINER, spawn.row, spawn.col]
        elif new_rob.type == RobotType.MINER:
            if assigned_miners >= 2:
                return -1, new_rob
            else:
                return score - dist/2, new_rob
        else:
            return -1, new_rob
    elif obj_type == "New Mine":
        assigned_miners = 0
        assigned_terras = 0
        for rob in cur_assigned:
            if rob.type == RobotType.MINER:
                assigned_miners += 1
            if rob.type == RobotType.TERRAFORMER:
                assigned_terras += 1
        if new_rob == "New Robot":
            spawn, dist = get_closest_spawn(tile, ally_tiles)
            if (assigned_miners >= 2) and (assigned_terras >= 2):
                return -1, [RobotType.MINER, spawn.row, spawn.col]
            elif assigned_terras > assigned_miners:
                return score - dist/2 - 1, [RobotType.MINER, spawn.row, spawn.col]
            else:
                return score - dist/2 - 1, [RobotType.TERRAFORMER, spawn.row, spawn.col]
        elif new_rob.type == RobotType.MINER:
            if assigned_miners >= 2:
                return -1, new_rob
            else:
                return score - dist/2, new_rob
        elif new_rob.type == RobotType.TERRAFORMER:
            if assigned_terras >= 2:
                return -1, new_rob
            else:
                return score - dist/2, new_rob
        else:
            return -1, new_rob
    elif obj_type == "Explore":
        # print(cur_assigned)
        assigned_terras = 0
        assigned_exps = 0
        for rob in cur_assigned:
            if rob.type == RobotType.TERRAFORMER:
                assigned_terras += 1
            if rob.type == RobotType.EXPLORER:
                assigned_exps += 1
        if new_rob == "New Robot":
            spawn, dist = get_closest_spawn(tile, ally_tiles)
            if (assigned_terras >= 1) and (assigned_exps >= 1):
                return -1, [RobotType.EXPLORER, spawn.row, spawn.col]
            elif assigned_exps > assigned_terras:
                return 2*score - dist - 1, [RobotType.TERRAFORMER, spawn.row, spawn.col]
            else:
                return score - dist - 1, [RobotType.EXPLORER, spawn.row, spawn.col]
        elif new_rob.type == RobotType.TERRAFORMER:
            if (assigned_terras >= 1) or (assigned_exps == 0):
                return -1, new_rob
            else:
                return 2*score - dist, new_rob
        elif new_rob.type == RobotType.EXPLORER:
            if assigned_exps >= 1:
                return -1, new_rob
            else:
                return score - dist, new_rob
        else:
            return -1, new_rob
    elif obj_type == "Approaching Scout":
        tackled = (len(cur_assigned) > 0)
        if new_rob == "New Robot":
            spawn, dist = get_closest_spawn(tile, ally_tiles)
            if tackled:
                return -1, [RobotType.TERRAFORMER, spawn.row, spawn.col]
            else:
                return score - 2*dist, [RobotType.TERRAFORMER, spawn.row, spawn.col]
        else:
            if tackled:
                return -1, new_rob
            else:
                return score - 2*dist, new_rob
    elif obj_type == "Nothing":
        if new_rob == "New Robot":
            spawn, dist = get_closest_spawn(tile, ally_tiles)
            return 0, [RobotType.TERRAFORMER, spawn.row, spawn.col]
        else:
            return 0, new_rob
        

def produce_now(game_state, best_robot):
    spawn_type, spawn_loc_row, spawn_loc_col = best_robot
    if game_state.can_spawn_robot(spawn_type, spawn_loc_row, spawn_loc_col):
        # print(f"Producing {spawn_type, spawn_loc_row, spawn_loc_col}")
        return game_state.spawn_robot(spawn_type, spawn_loc_row, spawn_loc_col) 

def decider(game_state):
    # First, create a list of objectives
    # - Scouts within range of a mine (eventually consider they've already seen it)
    # - All mines
    # - All explorers (either transform them or put them on explore)
    objectives = [] #[("type", {info}, score)]

    ginfo = game_state.get_info()
    width, height = len(ginfo.map), len(ginfo.map[0])
    turn = ginfo.turn

    mines = []
    ally_tiles = []
    used_mines = []
    unknown_tiles = []
    known_tiles = []
    border_tiles = []
    for row in range(height):
        for col in range(width):
            # get the tile at (row, col)
            tile = ginfo.map[row][col]
            # skip fogged tiles
            if tile is not None: # ignore fogged tiles
                known_tiles.append(tile)
                if tile.mining > 0:
                    mines.append(tile)
                    if tile.robot is not None: # ignore occupied tiles
                        used_mines.append(tile)
                if (tile.terraform > 0) and (tile.robot is None):
                    ally_tiles.append(tile)
                if (tile.terraform > 0):
                    for adj in get_adj_tiles((tile.row, tile.col), game_state)[0]:
                        other = game_state.get_map()[adj[0]][adj[1]]
                        if (other != None) and (other.terraform <= 0):
                            if tile not in border_tiles:
                                border_tiles.append(tile)
            else:
                unknown_tiles.append(tile)

    # n_exps = 0
    a_robots = game_state.get_ally_robots()
    # for rname, rob in a_robots.items():
    #     if rob.type == RobotType.EXPLORER:
    #             n_exps += 1

    # Have an arbitrary, fixed objective for "win now mode"
    for tile in known_tiles:
        if tile not in ally_tiles:
            break
    objectives.append(("Win Now", {"tile" : random.choice(border_tiles)}, 2 / (1.2 - turn/200)**2))

    # Have another one for starting a new scouting mission
    if len(unknown_tiles):
        for tile in ally_tiles:
            break
        exp_frac = len(unknown_tiles) / (width * height)
        score = (1 + exp_frac)**2 * (1 - turn/200) * 15
        objectives.append(("Explore", {"tile" : tile}, score))

    # Place to dump everything
    for tile in ally_tiles:
        break
    objectives.append(("Nothing", {"tile" : tile}, 0))

    # Look for mines to produce from
    for mine in mines:
        total_control = 0
        row, col = mine.row, mine.col
        total_tiles = 0
        for adj in get_adj_tiles((row, col), game_state)[0]:
            tile = game_state.get_map()[adj[0]][adj[1]]
            if tile != None:
                total_control += tile.terraform
                total_tiles += 1

        if total_control >= total_tiles * 2:
            objectives.append(("Old Mine", {"tile" : mine}, mine.mining * 10))
        else:
            objectives.append(("New Mine", {"tile" : mine}, mine.mining * 5))

    # Look for enemy scouts that are too close for comfort
    e_robots = game_state.get_enemy_robots()
    for rname, rob in e_robots.items():
        if rob.type == RobotType.EXPLORER:
            min_dist = np.inf
            for mine in used_mines:
                row, col = mine.row, mine.col
                dist = get_move_dist(row, col, rob.row, rob.col)
                if dist < min_dist:
                    min_dist = dist
            if min_dist <= 4:
                tile = ginfo.map[rob.row][rob.col]
                objectives.append(("Approaching Scout", {"tile" : tile}, 60 - 3*min_dist**2))

    total_metal = game_state.get_metal()

    if len(unknown_tiles):
        n_exps = 0
        for rname, rob in a_robots.items():
            if rob.type == RobotType.EXPLORER:
                n_exps += 1
                score = (1 + exp_frac) / (n_exps - 0.5) * (1 - turn/200) * 25
                tile = ginfo.map[rob.row][rob.col]
                objectives.append(("Explore", {"tile" : tile}, score))
    else:
        for rname, rob in a_robots.items():
            if rob.type == RobotType.EXPLORER:
                if total_metal > 40:
                    if game_state.can_transform_robot(rob.name, rob.type):
                        game_state.transform_robot(rob.name, RobotType.TERRAFORMER)
                        total_metal -= 40

    # Now, assign units to assignments
    objectives.sort(key=lambda x: -x[2])
    # print(f"\nCurrent Objectives under consideration:")
    # for o in objectives:
    #     print("    ",o)
    # print(F"Ally tiles: {ally_tiles}")
    can_produce = min(len(ally_tiles), total_metal // 50)
    # print("Available Robots:")
    # print(a_robots)
    available_robots = list(a_robots.values())
    # print(available_robots)
    assignments = [[] for _ in objectives]
    # If this is way to slow, here is a speedup
    # - Keep a standing 2D matrix of scores for each objective/unit combo
    # - Insteaad of recomputing everything each time a combo is selected,
    #   only recompute the values for the other units and that objectives
    while (len(available_robots) + can_produce) > 0:
        high_score = -np.inf
        best_robot, best_assignment = None, None
        # print("", end = "    ")
        # print((available_robots + (["New Robot"] if can_produce else [])))
        for robot in (available_robots + (["New Robot"] if can_produce else [])):
            for i, objective in enumerate(objectives):
                score, new_bot = evaluate_use(objective, assignments[i], robot, ally_tiles)
                if score > high_score:
                    high_score = score
                    best_robot = new_bot
                    best_assignment = i

        # print(best_robot)
        # print(objectives[best_assignment])
        # print()

        if type(best_robot) == list:
            can_produce -= 1
            best_robot = produce_now(game_state, best_robot)
            tile = ginfo.map[best_robot.row][best_robot.col]
            ally_tiles.remove(tile)
            # print(best_robot)
        else:
            available_robots.remove(best_robot)
        assignments[best_assignment].append(best_robot)

        if len(ally_tiles) == 0:
            can_produce = 0

    strategies = []
    for i,objective in enumerate(objectives):
        if len(assignments[i]) > 0:
            strategies.append([objective[0], assignments[i], {"tile": objective[1]["tile"]}])

    return strategies