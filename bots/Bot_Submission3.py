from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo

import random, time
import numpy as np

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.total_times = [0 for _ in range(6)]
        self.explore_params = {"fog_frontier" : set(), "first_fog_frontier" : True}
        return

    def play_turn(self, game_state: GameState) -> None:
        if game_state.get_time_left() < 5:
            return
        self.times = [[] for _ in range(6)]
        ginfo = game_state.get_info()
        turn = ginfo.turn
        print(turn)
        # if turn > 30:
        #     return
        strategies = decider(game_state)
        # print("\n\nListing Strategies:\n")
        for strategy in strategies:
            # print(strategy)
            # print()
            name, units, target = strategy
            if name == "Explore":
                if len(units) == 2:
                    if units[0].type != RobotType.EXPLORER:
                        units = [units[1], units[0]]
                explore(game_state, units, self.explore_params)
            elif name == "Approaching Scout":
                destroy(game_state, units, target)
            elif name == "New Mine":
                # for rob in units:
                #     print(f"Doing mining for {rob}")
                tile = target["tile"]
                params = {"game_state" : game_state, "mine_location" : (tile.row, tile.col)}
                newmine_strategy(units, params)
            elif name == "Old Mine":
                # for rob in units:
                #     print(f"Doing mining now for {rob}")
                tile = target["tile"]
                params = {"game_state" : game_state, "mine_location" : (tile.row, tile.col)}
                newmine_strategy(units, params)
            elif name == "Win Now":
                # for rob in units:
                #     print(f"Doing win now for {rob}")
                params = {"game_state" : game_state}
                win_now_strategy(units, params)
            elif name == "Nothing":
                for rob in units:
                    all_dirs = [dir for dir in Direction]
                    move_dir = random.choice(all_dirs)

                    # check if we can move in this direction
                    if game_state.can_move_robot(rob.name, move_dir):
                        # try to not collide into robots from our team
                        dest_loc = (rob.row + move_dir.value[0], rob.col + move_dir.value[1])
                        dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]

                        if dest_tile.robot is None or dest_tile.robot.team != self.team:
                            game_state.move_robot(rob.name, move_dir)

                    if game_state.can_robot_action(rob.name):
                        game_state.robot_action(rob.name)

def win_now_strategy(bots, params):
    game_state = params.get('game_state')
    def withinMap(r,c):
        return (0 <= r and 0 <= c and
            r < len(game_state.get_map()) and
            c < len(game_state.get_map()[0]))
    def noCollisions(rob, dir):
        # if game_state.can_move_robot(rob.name, dir):
        # try to not collide into robots
        dest_loc = (rob.row + dir.value[0], rob.col + dir.value[1])
        dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]
        return dest_tile.robot is None

    # TODO: TUNE LOWER IF SLOW
    MAX_NUM_ITERS = 5
    change = 1
    i = 0
    while change > 0 and i < MAX_NUM_ITERS:
        i += 1
        botsToMove = []
        leftoverBots = []
        for bot in bots:
            myTile = game_state.get_map()[bot.row][bot.col]
            bestNegTerra = -10
            bestPosTerra = 10
            dir = None
            positive = myTile.terraform > 0
            for d in Direction:
                row = bot.row + d.value[0]
                col = bot.col + d.value[1]
                if withinMap(row, col):
                    tile = game_state.get_map()[row][col]
                    if (# Validate if we can go to this tile
                        tile != None
                        and tile.state == TileState.TERRAFORMABLE
                        and tile.robot is None):
                        if (bot.battery < bot.action_cost
                            and tile.terraform > 0):
                            # Locally found a place to recharge
                            dir = d
                        elif myTile.state == TileState.MINING:
                            # Remove a bot from mine if possible
                            dir = d
                        elif (bot.battery >= bot.action_cost):
                            if (tile.terraform <= 0
                                and tile.terraform >= bestNegTerra
                                and ((myTile.terraform <= 0 and tile.terraform >= myTile.terraform) or myTile.terraform > 0)):
                                dir = d
                                bestNegTerra = tile.terraform
                                positive = False
                            if (positive and tile.terraform > 0
                                and tile.terraform <= bestPosTerra
                                and tile.terraform <= myTile.terraform):
                                dir = d
                                bestPosTerra = tile.terraform
            if dir is not None:
                botsToMove.append((bot, dir))
            else:
                leftoverBots.append(bot)

        for bot, dir in botsToMove:
            if (game_state.can_move_robot(bot.name, dir)
                and noCollisions(bot, dir)
                and game_state.get_map()[bot.row + dir.value[0]][bot.col + dir.value[1]].state != TileState.MINING):
                game_state.move_robot(bot.name, dir)
                if (game_state.can_robot_action(bot.name)):
                    game_state.robot_action(bot.name)
            else:
                leftoverBots.append(bot)
        change = len(bots) - len(leftoverBots)
        bots = leftoverBots
        if len(bots) == 0:
            # We can discontinue looping
            break
    # Remaining bots need to be recharged (probably)
    for bot in bots:
        if (game_state.can_robot_action(bot.name)):
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

    # Route the mine bots so that at least one is mining each turn
    hasMiner = False
    for botName, bot in fueled_mine_bots:
        if game_state.can_robot_action(botName):
            game_state.robot_action(botName)
            hasMiner = True
            # print("Mining", bot)
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
    # print(aroundMine)
    # Filter out only locations that we may want to move to
    for loc in aroundMine:
        if 0 <= loc[0] and loc[0] < len(map) and 0 <= loc[1] and loc[1] < len(map[0]):
            tile = map[loc[0]][loc[1]]
            if tile != None and tile.terraform < 2 and tile.robot is None and tile.state != TileState.IMPASSABLE:
                terraSquares.append(loc)
    for botName, bot in fueled_terra_bots:
        # print(loc[0], loc[1])
        # print(map[bot.row][bot.col].terraform)
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
                # print(bot, dir, steps)
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

    for botName, bot in tired_bots:
        if bot.row == mine_loc[0] and bot.col == mine_loc[1]:
            # Get this bot off the mineral location immediately
            for dir in Direction:
                if game_state.can_move_robot(botName, dir) and noCollision(bot, dir):
                    game_state.move_robot(botName, dir)
                    break
        else: # normal scheduling
            dir, steps = game_state.robot_to_base(botName)
            if steps <= 0:
                pass # sadge... do nothing
            else:
                if (game_state.can_move_robot(botName, dir) and noCollision(bot, dir)
                    and map[bot.row + dir.value[0]][bot.col + dir.value[1]].state != TileState.MINING):
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

def evaluate_use(objective, cur_assigned, new_rob, ally_tiles, size):
    obj_type, tile, score = objective
    tile = tile["tile"]
    if new_rob != "New Robot":
        dist = get_move_dist(new_rob.row, new_rob.col, tile.row, tile.col)
    if obj_type == "Win Now":
        if len(cur_assigned) > 2*size:
            score = 0
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

    start = time.time()

    mines = []
    ally_tiles = []
    used_mines = []
    unknown_tiles = 0
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
                            if (other.state != TileState.IMPASSABLE) and (other.mining == 0):
                                border_tiles.append(tile)
                                break
            else:
                unknown_tiles += 1

    print(time.time() - start)

    n_terras = 0
    n_exps = 0
    a_robots = game_state.get_ally_robots()
    for rname, rob in a_robots.items():
        if rob.type == RobotType.TERRAFORMER:
            n_terras += 1
        elif rob.type == RobotType.EXPLORER:
            n_exps += 1

    # Have an arbitrary, fixed objective for "win now mode"
    for tile in known_tiles:
        if tile not in ally_tiles:
            break
    objectives.append(("Win Now", {"tile" : random.choice(ally_tiles)}, 2 / (1.2 - turn/200)**2))

    # Have another one for starting a new scouting mission
    if unknown_tiles:
        for tile in ally_tiles:
            break
        exp_frac = unknown_tiles / (width * height)
        score = (1 + exp_frac)**2 * (1 - turn/100) * 15 / (1 + n_exps/2)
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
            if tile != None and (tile.state != TileState.IMPASSABLE) and (tile.mining == 0):
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
    print(f"Total metal: {total_metal}")

    if unknown_tiles and turn <= 100:
        n_exps = 0
        for rname, rob in a_robots.items():
            if rob.type == RobotType.EXPLORER:
                n_exps += 1
                score = (1 + exp_frac)**2 / (n_exps - 0.5) * (1 - turn/150) * 25
                tile = ginfo.map[rob.row][rob.col]
                objectives.append(("Explore", {"tile" : tile}, score))
    else:
        for rname, rob in a_robots.items():
            if rob.type == RobotType.EXPLORER:
                if total_metal > 40:
                    if game_state.can_transform_robot(rob.name, rob.type):
                        game_state.transform_robot(rob.name, RobotType.TERRAFORMER)
                        total_metal -= 40
    # for rname, rob in a_robots.items():
    #     if rob.type != RobotType.Miner:
            

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
    robot_set = (available_robots + (["New Robot"] * can_produce))
    # print(assignments)
    # print(robot_set)
    all_scores = np.array([[evaluate_use(objective, assignments[i], robot, ally_tiles, width)[0] for robot in robot_set] for i,objective in enumerate(objectives)])
    # print(all_scores)
    while (len(available_robots) + can_produce) > 0:
        best_assignment, best_robot_n = np.unravel_index(all_scores.argmax(), all_scores.shape)
        score = all_scores[best_assignment][best_robot_n]
        if score < 1:
            break
        best_robot = robot_set[best_robot_n]
        _, best_robot = evaluate_use(objectives[best_assignment], assignments[best_assignment], best_robot, ally_tiles, width)

        # high_score = -np.inf
        # best_robot, best_assignment = None, None
        # for robot in (available_robots + (["New Robot"] if can_produce else [])):
        #     for i, objective in enumerate(objectives):
        #         score, new_bot = evaluate_use(objective, assignments[i], robot, ally_tiles)
        #         if score > high_score:
        #             high_score = score
        #             best_robot = new_bot
        #             best_assignment = i

        # print(best_robot)
        # print(objectives[best_assignment])
        # print()

        if type(best_robot) == list:
            can_produce -= 1
            if (n_terras < 2*width) or (best_robot[0] != RobotType.TERRAFORMER):
                best_robot = produce_now(game_state, best_robot)
                tile = ginfo.map[best_robot.row][best_robot.col]
                ally_tiles.remove(tile)
                assignments[best_assignment].append(best_robot)
            # print(best_robot)
        else:
            available_robots.remove(best_robot)
            assignments[best_assignment].append(best_robot)

        if len(ally_tiles) == 0:
            can_produce = 0

        # print(best_assignment, best_robot_n)
        all_scores = np.delete(all_scores, best_robot_n, axis = 1)
        new_scores = []
        robot_set = (available_robots + (["New Robot"] * can_produce))
        for robot in robot_set:
            new_scores.append(evaluate_use(objectives[best_assignment], assignments[best_assignment], robot, ally_tiles, width)[0])
        all_scores[best_assignment] = new_scores
        # print(all_scores)

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

def explore(game_state: GameState, bot_list, param_dict):
    game_info = game_state.get_info()
    ally_robots = game_state.get_ally_robots()
    enemy_robots = game_state.get_enemy_robots()
    strmap = game_state.get_str_map()
    # adjacent_fog = self.find_fog(strmap, (bot_list[0].row, bot_list[0].col))
    fog_frontier = param_dict['fog_frontier']
    first_fog_frontier = param_dict['first_fog_frontier']
    if (first_fog_frontier):
        param_dict['fog_frontier'] = get_explored_unexplored(game_state)[0]
        param_dict['first_fog_frontier'] = False
    adjacent_fog, exp_dir, exp_dist = find_fog(game_state, bot_list[0].row, bot_list[0].col, fog_frontier)

    # GET EXPLORER INFO
    explorer = bot_list[0]
    assert(explorer.type == RobotType.EXPLORER)
    exp_name = explorer.name
    exp_row = explorer.row
    exp_col = explorer.col

    # CHECK IF EXPLORER IS ALONE
    if len(bot_list) == 1:
        terraformer_exists = False
    else:
        terraformer_exists = True
    
    # Check if explorer needs to recharge
    if explorer.battery < 10:
        dir_to_base = game_state.robot_to_base(exp_name, checkCollisions=True)[0]
        if dir_to_base is not None and game_state.can_move_robot(exp_name, dir_to_base):
            game_state.move_robot(exp_name, dir_to_base)

    # GET TERRAFORMER INFO (if exists)
    if terraformer_exists:
        terraformer = bot_list[1]
        # # print('terraformer', terraformer)
        assert(terraformer.type == RobotType.TERRAFORMER)
        terr_name = terraformer.name
        terr_row = terraformer.row
        terr_col = terraformer.col

    # MOVE EXPLORER
    # exp_opt_dir, exp_steps = game_state.optimal_path(exp_row, exp_col, adjacent_fog[0], adjacent_fog[1], checkCollisions=True)
    # check if we can move in this direction
    if game_state.can_move_robot(exp_name, exp_dir):
        # try to not collide into robots from our team
        dest_loc = (
            exp_row + exp_dir.value[0], exp_col + exp_dir.value[1])
        dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]

        if dest_tile.robot is None or dest_tile.robot.team != explorer.team:
            game_state.move_robot(exp_name, exp_dir)

    # MOVE TERRAFORMER (if exists)
    if terraformer_exists:
        if terraformer.battery < terraformer.action_cost:
            dir_to_base = game_state.robot_to_base(terr_name, checkCollisions=True)[0]
            game_state.move_robot(terr_name, dir_to_base)
        else:
            terr_move_options, _ = get_adj_tiles(adjacent_fog, game_state)
            terr_dest = None
            for tile_option in terr_move_options:
                tile_obj = game_state.get_map()[tile_option[0]][tile_option[1]]
                if tile_obj is None:
                    continue
                if tile_obj.robot is None:
                    terr_dest = tile_option
                    break
            if terr_dest is not None:
                terr_opt_dir, terr_dist = game_state.optimal_path(
                    terr_row, terr_col, terr_dest[0], terr_dest[1], checkCollisions=True)
                
                # only move terraformer if it's farther from the destination than the explorer
                # check if we can move in this direction
                if game_state.can_move_robot(terr_name, terr_opt_dir):
                    # try to not collide into robots from our team
                    dest_loc = (
                        terr_row + terr_opt_dir.value[0], terr_col + terr_opt_dir.value[1])
                    dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]

                    if dest_tile.robot is None:
                        game_state.move_robot(terr_name, terr_opt_dir)

    # TAKE ACTIONS
    # # print(explorer)
    if game_state.can_robot_action(exp_name):
        game_state.robot_action(exp_name)
        explorer_adjacents = get_adj_tiles((explorer.row, explorer.col), game_state)[0]
        for adj in explorer_adjacents:
            # print("adj", adj)
            if check_is_fog_frontier(game_state, adj):
                # print("Success->", fog_frontier)
                fog_frontier.add(adj)
            else:
                # print("End->", fog_frontier)
                fog_frontier.discard(adj)
                    
    if terraformer_exists:
        # if (terraformer.battery <= 30 or explorer.battery <= 10) and game_state.can_robot_action(terr_name):
        if game_state.can_robot_action(terr_name):
            game_state.robot_action(terr_name) 
    # print('full explore time', time.time() - start)

def check_is_fog_frontier(game_state, tile):
    # # print("this thing", game_state.get_map()[tile[0]][tile[1]])
    if game_state.get_map()[tile[0]][tile[1]] is None:
        # print('fail1')
        return False 
    the_tile = game_state.get_map()[tile[0]][tile[1]]
    if the_tile.state != TileState.TERRAFORMABLE and the_tile.state != TileState.MINING:
        # print('fail2')
        return False
    adjacents, _ = get_adj_tiles(tile, game_state)
    for adj in adjacents:
        if game_state.get_map()[adj[0]][adj[1]] is None or game_state.get_map()[adj[0]][adj[1]].state == TileState.ILLEGAL:
            # print('success1')
            return True
    # print('fail4')
    return False

def find_fog(game_state, bot_row, bot_col, fog_frontier):
    # # print(f"Looking at bot on {bot_row, bot_col}")
    # find a nearby fog
    min_dist = None
    best_tile = None
    best_dir = None
    
    # edge_tiles_dist = dict()
    # edge_tiles_move_dirs = dict()
    adjacent_time = 0
    score_time = 0
    # print('fog-frontier', fog_frontier)
    discard_tiles = []
    for tile in fog_frontier:
        # print('tilea', tile)
        if check_is_fog_frontier(game_state, tile):
            # print('TRUEA')
            # fog_frontier.add(tile)
            dist = score_tile(game_state, bot_row, bot_col, tile[0], tile[1])
            # print('dist', dist)
            # # print(tile, adj, dist)
            if min_dist == None or dist < min_dist:
                min_dist = dist
                best_tile = tile
        else:
            # print('FALSEA')
            discard_tiles.append(tile)
        # print("after else")
    for dtile in discard_tiles:
        fog_frontier.discard(dtile)
    # print('find fog for loop', time.time() - start2)
    # print('best_tile', best_tile)
    best_dir = game_state.optimal_path(
        bot_row, bot_col, best_tile[0], best_tile[1], checkCollisions=True)[0]
    # print('find_fog', time.time() - start)
    # print('adjacent time', adjacent_time)
    # print('score time', score_time)
    return best_tile, best_dir, min_dist
            

def score_tile(game_state, bot_row, bot_col, tile_row, tile_col):
    penalty_multiplier = .01
    dist = max(abs(bot_row - tile_row), abs(bot_col - tile_col))
    penalty_squared_sum = 0
    ally_robots = game_state.get_ally_robots()
    # explorers = [robot for robot in ally_robots if robot.type == RobotType.EXPLORER]
    explorers = []
    for robot_name in ally_robots:
        robot = ally_robots[robot_name]
        if robot.type == RobotType.EXPLORER:
            explorers.append(robot)
    for explorer in explorers:
        if explorer.row == bot_row and explorer.col == bot_col:
            continue
        explorer_dist = max(abs(explorer.row - bot_row), abs(explorer.col - bot_col))
        squared_dist = explorer_dist ** 2
        penalty_squared_sum += squared_dist
    score = dist - penalty_multiplier * penalty_squared_sum
    return score
                

def get_adj_tiles(tile, game_state):
    # tile = row, col
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

def get_explored_unexplored(game_state):
    unknown_tiles = set()
    known_tiles = set()
    ginfo = game_state.get_info()
    width, height = len(ginfo.map), len(ginfo.map[0])
    for row in range(height):
        for col in range(width):
            # get the tile at (row, col)
            tile = ginfo.map[row][col]
            # skip fogged tiles
            if tile is not None: # ignore fogged tiles
                known_tiles.add((row, col))
            else:
                unknown_tiles.add((row, col))
    return known_tiles, unknown_tiles

