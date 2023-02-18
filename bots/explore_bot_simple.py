from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo

import random, time
import numpy as np
from collections import deque

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        # self.explore_params = {'fog_frontier':set(), 'first_fog_frontier':True}
        self.explore_params = {'prev_moves': dict()}
        return

    def play_turn(self, game_state: GameState) -> None:
        ginfo = game_state.get_info()
        turn = ginfo.turn
        print(turn)
        # if turn > 30:
        #     return
        strategies = decider(game_state)
        # # print("\n\nListing Strategies:\n")
        for strategy in strategies:
            # # print(strategy)
            # # print()
            name, units, target = strategy
            if name == "Explore":
                if len(units) == 2:
                    if units[0].type != RobotType.EXPLORER:
                        units = [units[1], units[0]]
                explore(game_state, units, self.explore_params)
            elif name == "Approaching Scout":
                destroy(game_state, units, target)
            elif name == "New Mine":
                tile = target["tile"]
                params = {"game_state" : game_state, "mine_location" : (tile.row, tile.col)}
                newmine_strategy(units, params)
            elif name == "Old Mine":
                tile = target["tile"]
                params = {"game_state" : game_state, "mine_location" : (tile.row, tile.col)}
                newmine_strategy(units, params)
            elif name == "Win Now":
                params = {"game_state" : game_state}
                win_now_strategy(units, params)


MAX_ITER = 100
def win_now_strategy(bots, params):
    game_state = params.get('game_state')
    map = game_state.get_map()
    def noCollisions(rob, dir):
        # if game_state.can_move_robot(rob.name, dir):
        # try to not collide into robots
        dest_loc = (rob.row + dir.value[0], rob.col + dir.value[1])
        dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]
        return dest_tile.robot is None

    # def noCollision(rob, dir):
    #     dest_loc = (rob.row + dir.value[0], rob.col + dir.value[1])
    #     dest_tile = map[dest_loc[0]][dest_loc[1]]
    #     return dest_tile.robot == None
    for bot in bots:
        tile = map[bot.row][bot.col]
        if (bot.battery < bot.action_cost
            and tile.state == TileState.TERRAFORMABLE
            and tile.terraform <= 0):
            dir, _ = game_state.robot_to_base(bot.name)
            if dir is None:
                # sadge
                pass
            else:
                game_state.move_robot(bot.name, dir)
        else:
            # this should be a BFS
            queue = deque()
            queue.append((bot.row, bot.col))
            seen = set(queue[0])
            idealPath = False
            while len(queue):
                r, c = queue.popleft()
                if 0 <= r and r < len(map) and 0 <= c and c < len(map[0]):
                    tile = map[r][c]
                    if (tile != None
                        and tile.state == TileState.TERRAFORMABLE
                        and tile.terraform <= 0
                        and tile.robot is None):
                        # found a location to travel to
                        dir, _ = game_state.optimal_path(bot.row, bot.col, r, c)
                        if dir is None:
                            # Sadge...
                            pass
                        else:
                            # # print("here")
                            game_state.move_robot(bot.name, dir)
                            if game_state.can_robot_action(bot.name):
                                game_state.robot_action(bot.name)
                            idealPath = True
                        break
                    for i in range(-1, 2):
                        for j in range(-1, 2):
                            newRC = (r+i, c+j)
                            if newRC not in seen:
                                seen.add(newRC)
                                queue.append(newRC)
            if not idealPath:
                # # print("ending")

                # Make a random legal move
                for dir in Direction:
                    # # print(bot, dir)
                    if game_state.can_move_robot(bot.name, dir) and noCollisions(bot, dir):
                        game_state.move_robot(bot.name, dir)
                        break
                if game_state.can_robot_action(bot.name):
                    game_state.robot_action(bot.name)

def newmine_strategy(bots, params):
    game_state = params.get('game_state')
    map = game_state.get_info().map
    mine_loc = params.get('mine_location')
    def noCollision(rob, dir):
        dest_loc = (rob.row + dir.value[0], rob.col + dir.value[1])
        return game_state.check_for_collision(dest_loc[0], dest_loc[1]) == None

    fueled_mine_bots = []
    tired_bots = []
    fueled_terra_bots = []
    for bot in bots:
        if bot.type == RobotType.MINER and bot.battery >= bot.action_cost:
            fueled_mine_bots.append((bot.name,bot))
        elif bot.type == RobotType.TERRAFORMER and bot.battery >= bot.action_cost:
            fueled_terra_bots.append((bot.name,bot))
        elif bot.type == RobotType.TERRAFORMER or bot.type == RobotType.MINER:
            tired_bots.append((bot.name,bot))
        else:
            assert(0 and "oldmine_strategy cannot handle EXPLORER bots")

    for botName, bot in tired_bots:
        dir, steps = game_state.robot_to_base(botName)
        if steps <= 0:
            pass # sadge... do nothing
        else:
            if game_state.can_move_robot(botName, dir) and noCollision(bot, dir):
                game_state.move_robot(botName, dir)

    # Route the mine bots so that at least one is mining each turn
    hasMiner = False
    for botName, bot in fueled_mine_bots:
        if game_state.can_robot_action(botName):
            game_state.robot_action(botName)
            hasMiner = True
            # # print("Mining", bot)
        else:
            dir, steps = game_state.optimal_path(
                bot.row, bot.col, mine_loc[0], mine_loc[1])
            if steps == 0 and not hasMiner:
                if game_state.can_robot_action(botName):
                    game_state.robot_action(botName)
                    hasMiner = True
            elif steps == 1 and not hasMiner:
                if game_state.can_move_robot(botName, dir):
                    game_state.move_robot(botName, dir)
                if game_state.can_robot_action(botName):
                    game_state.robot_action(botName)
                    hasMiner = True
            else:
                # Get near mine if possible
                if game_state.can_move_robot(botName, dir):
                    game_state.move_robot(botName, dir)

    # Route these bots around the mine location
    aroundMine = [(mine_loc[0] + d.value[0], mine_loc[1] + d.value[1]) for d in Direction]
    terraSquares = []
    # # print(aroundMine)
    # Filter out only locations that we may want to move to
    for loc in aroundMine:
        if 0 <= loc[0] and loc[0] < len(map) and 0 <= loc[1] and loc[1] < len(map[0]):
            tile = map[loc[0]][loc[1]]
            if tile != None and tile.terraform < 2 and tile.robot is None and tile.state != TileState.IMPASSABLE:
                terraSquares.append(loc)
    for botName, bot in fueled_terra_bots:
        # # print(loc[0], loc[1])
        # # print(map[bot.row][bot.col].terraform)
        if (bot.row, bot.col) in aroundMine and map[bot.row][bot.col].terraform < 2:
            # stay on square
            if game_state.can_robot_action(botName):
                game_state.robot_action(botName)
        else:
            bestDist = 10000000000000000000
            bestLoc = None
            for loc in terraSquares:
                dist = abs(loc[0] - bot.row) + abs(loc[1] - bot.col)
                if dist < bestDist:
                    bestDist = dist
                    bestLoc = loc
            if bestLoc != None:
                terraSquares.remove(bestLoc)
                # Route to this square
                dir, steps = game_state.optimal_path(bot.row, bot.col, bestLoc[0], bestLoc[1])
                # # print(bot, dir, steps)
                if steps <= 0:
                    # sadge
                    pass
                elif steps == 1:
                    # we can immediately do action
                    game_state.move_robot(botName, dir)
                    if game_state.can_robot_action(botName):
                        game_state.robot_action(botName)
                else: # move closer to the mine
                    game_state.move_robot(botName, dir)

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
    # # print(tile, dest_locs)
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
        # # print(cur_assigned)
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
        # # print(f"Producing {spawn_type, spawn_loc_row, spawn_loc_col}")
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
    objectives.append(("Win Now", {"tile" : tile}, 2 / (1.2 - turn/200)**2))

    # Have another one for starting a new scouting mission
    for tile in ally_tiles:
        break
    objectives.append(("Explore", {"tile" : tile}, 1))

    # Place to dump everything
    for tile in ally_tiles:
        break
    objectives.append(("Nothing", {"tile" : tile}, 0))

    # Look for mines to produce from
    for mine in mines:
        total_control = 0
        row, col = mine.row, mine.col
        for adj in get_adj_tiles((row, col), game_state)[0]:
            tile = game_state.get_map()[adj[0]][adj[1]]
            if tile != None:
                total_control += tile.terraform

        if total_control > 8:
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

    n_exps = 0
    exp_frac = len(unknown_tiles) / (width * height)
    for rname, rob in a_robots.items():
        if rob.type == RobotType.EXPLORER:
            n_exps += 1
            score = (1 + exp_frac) / (n_exps - 0.5) * (1 - turn/200) * 25
            tile = ginfo.map[rob.row][rob.col]
            objectives.append(("Explore", {"tile" : tile}, score))

    # Now, assign units to assignments
    objectives.sort(key=lambda x: -x[2])
    # # print(f"\nCurrent Objectives under consideration:")
    # for o in objectives:
    #     # print("    ",o)
    total_metal = game_state.get_metal()
    # # print(F"Ally tiles: {ally_tiles}")
    can_produce = min(len(ally_tiles), total_metal // 50)
    # # print("Available Robots:")
    # # print(a_robots)
    available_robots = list(a_robots.values())
    # # print(available_robots)
    assignments = [[] for _ in objectives]
    # If this is way to slow, here is a speedup
    # - Keep a standing 2D matrix of scores for each objective/unit combo
    # - Insteaad of recomputing everything each time a combo is selected,
    #   only recompute the values for the other units and that objectives
    while (len(available_robots) + can_produce) > 0:
        high_score = -np.inf
        best_robot, best_assignment = None, None
        # # print("", end = "    ")
        # # print((available_robots + (["New Robot"] if can_produce else [])))
        for robot in (available_robots + (["New Robot"] if can_produce else [])):
            for i, objective in enumerate(objectives):
                score, new_bot = evaluate_use(objective, assignments[i], robot, ally_tiles)
                if score > high_score:
                    high_score = score
                    best_robot = new_bot
                    best_assignment = i

        # # print(best_robot)
        # # print(objectives[best_assignment])
        # # print()

        if type(best_robot) == list:
            can_produce -= 1
            best_robot = produce_now(game_state, best_robot)
            tile = ginfo.map[best_robot.row][best_robot.col]
            ally_tiles.remove(tile)
            # # print(best_robot)
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

def destroy(game_state: GameState, bot_list, param_dict):
    bot = bot_list[0]
    target = param_dict["tile"]
    best_dir, _ = game_state.optimal_path(bot.row, bot.col, target.row, target.col)

    rname = bot.name

    if game_state.can_move_robot(rname, best_dir):
        # try to not collide into robots from our team
        dest_loc = (bot.row + best_dir.value[0], bot.col + best_dir.value[1])
        dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]

        if dest_tile.robot is None or dest_tile.robot.team != bot.team:
            game_state.move_robot(rname, best_dir)
            
'''
START EXPLORE FUNCTIONALITY FROM HERE DOWN
'''

def get_nearby_directions(current_dir):
    all_dirs = [Direction.UP, Direction.UP_RIGHT, Direction.RIGHT, Direction.DOWN_RIGHT, Direction.DOWN, Direction.DOWN_LEFT, Direction.LEFT, Direction.UP_LEFT]
    all_dirs.extend(all_dirs)
    i = all_dirs[4:].index(current_dir) + 4
    result = all_dirs[i-2:i+3]
    result.remove(current_dir)
    return result

# nearby_directions = {
#     "UP": ['UP_LEFT', 'UP_RIGHT', 'LEFT', 'RIGHT'],
#     'UP_LEFT': ['UP', 'LEFT', 'UP_RIGHT', 'DOWN_LEFT'],
#     'UP_RIGHT': ['UP', 'RIGHT', 'UP_LEFT', 'DOWN_RIGHT'],
#     'RIGHT': ['UP_RIGHT', 'DOWN_RIGHT', 'UP', 'DOWN'],
#     'DOWN_RIGHT': ['DOWN', 'RIGHT', 'DOWN_LEFT', 'UP_RIGHT'],
#     'DOWN_LEFT' : ['LEFT', 'DOWN', 'DOWN_RIGHT', 'UP_LEFT'],
#     'DOWN': ['DOWN_LEFT', 'DOWN_RIGHT', 'LEFT', 'RIGHT'],
#     'LEFT': ['UP_LEFT', 'DOWN_LEFT', 'UP', 'DOWN'],
# }

def explore(game_state: GameState, bot_list, param_dict):
    explorer = bot_list[0]
    if explorer.battery < 10:
        dir_to_base = game_state.robot_to_base(explorer.name, checkCollisions=True)[0]
        if dir_to_base is not None and game_state.can_move_robot(explorer.name, dir_to_base):
                game_state.move_robot(explorer.name, dir_to_base)
        return
    forward_prob = 0.9
    prev_moves = param_dict['prev_moves']
    directions = get_possible_directions(game_state, explorer, prev_moves)
    print(explorer.name)
    print(f"robot {explorer.row, explorer.col}")
    print('directions', directions)
    if len(directions) == 0:
        return
    probs = []
    if explorer.name in prev_moves and prev_moves[explorer.name] is not None and prev_moves[explorer.name] in directions:
        explorer_prev_move = prev_moves[explorer.name]
        for d in directions:
            if d == explorer_prev_move:
                probs.append(forward_prob)
            else:
                probs.append((1 - forward_prob) / (len(directions) - 1))
        explorer_next_move = random.choices(directions, weights=probs)[0]
    else:
        explorer_next_move = random.choice(directions)
    print('next move', explorer_next_move)
    if game_state.can_move_robot(explorer.name, explorer_next_move):
        game_state.move_robot(explorer.name, explorer_next_move)
        prev_moves[explorer.name] = explorer_next_move
    if game_state.can_robot_action(explorer.name):
        game_state.robot_action(explorer.name)
    param_dict['prev_moves'] = prev_moves

def get_possible_directions(game_state, bot, prev_moves):
    possible_dirs = []
    for d in Direction:
        next_loc = (bot.row + d.value[0], bot.col + d.value[1])
        if game_state.can_move_robot(bot.name, d) and game_state.check_for_collision(next_loc[0], next_loc[1]) is None:
            possible_dirs.append(d)
    if bot.name not in prev_moves:
        return possible_dirs
    else:
        good_dirs = []
        nearby_dirs = get_nearby_directions(prev_moves[bot.name])
        for d in possible_dirs:
            if d in nearby_dirs:
                good_dirs.append(d)
        return good_dirs
