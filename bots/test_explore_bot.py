from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
import random

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        return

    def play_turn(self, game_state: GameState) -> None:

        # get info
        ginfo = game_state.get_info()

        # get turn/team info
        width, height = len(ginfo.map), len(ginfo.map[0])

        # print info about the game
        print(f"Turn {ginfo.turn}, team {ginfo.team}")
        print("Map height", height)
        print("Map width", width)

        # find un-occupied ally tile
        ally_tiles = []
        for row in range(height):
            for col in range(width):
                # get the tile at (row, col)
                tile = ginfo.map[row][col]
                # skip fogged tiles
                if tile is not None: # ignore fogged tiles
                    if tile.robot is None: # ignore occupied tiles
                        if tile.terraform > 0: # ensure tile is ally-terraformed
                            ally_tiles += [tile]

        print("Ally tiles", ally_tiles)

        # spawn on a random tile
        print(f"My metal {game_state.get_metal()}")
        if len(ally_tiles) > 0:
            # pick a random one to spawn on
            spawn_loc = random.choice(ally_tiles)
            spawn_type = random.choice([RobotType.EXPLORER, RobotType.TERRAFORMER])
            # spawn the robot
            print(f"Spawning robot at {spawn_loc.row, spawn_loc.col}")
            # check if we can spawn here (checks if we can afford, tile is empty, and tile is ours)
            if game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)


        # move robots
        robots = game_state.get_ally_robots()

        # iterate through dictionary of robots
        explorers = []
        terraformers = []
        for rname, rob in robots.items():
            # print('rob', rob)
            print(f"Robot {rname} at {rob.row, rob.col}")
            if rob.type == RobotType.EXPLORER:
                explorers.append(rob)
            else: # TERRAFORMER
                terraformers.append(rob)
        for i in range(len(explorers)):
            bot_list = [explorers[i]]
            if i < len(terraformers):
                bot_list.append(terraformers[i])
            self.explore(game_state, bot_list, dict())


    def explore(self, game_state: GameState, bot_list, param_dict):
        game_info = game_state.get_info()
        ally_robots = game_state.get_ally_robots()
        enemy_robots = game_state.get_enemy_robots()
        strmap = game_state.get_str_map()
        # adjacent_fog = self.find_fog(strmap, (bot_list[0].row, bot_list[0].col))
        adjacent_fog, exp_dir, exp_dist = self.find_fog(game_state, bot_list[0].row, bot_list[0].col)

        # GET EXPLORER INFO
        explorer = bot_list[0]
        assert(explorer.type == RobotType.EXPLORER)
        exp_name = explorer.name
        exp_row = explorer.row
        exp_col = explorer.col
        # print('calling explore. explorer at', exp_row, ',', exp_col)

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
            # print('terraformer', terraformer)
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
            if terraformer.battery < 20:
                dir_to_base = game_state.robot_to_base(terr_name, checkCollisions=True)[0]
                game_state.move_robot(terr_name, dir_to_base)
            else:
                terr_opt_dir, terr_dist = game_state.optimal_path(
                    terr_row, terr_col, adjacent_fog[0], adjacent_fog[1], checkCollisions=True)
                # only move terraformer if it's farther from the destination than the explorer
                # if terr_dist > exp_dist:
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

    def find_fog(self, game_state, bot_row, bot_col):
        # print(f"Looking at bot on {bot_row, bot_col}")
        # find a nearby fog
        known_tiles, unknown_tiles = self.get_explored_unexplored(game_state)
        # edge_tiles_dist = dict()
        # edge_tiles_move_dirs = dict()
        if len(unknown_tiles) == 0:
            raise Exception("No unknown tiles")
        min_dist = None
        best_tile = None
        best_dir = None
        for tile in known_tiles:
            adjacents, _ = self.get_adj_tiles(tile, game_state)
            for adj in adjacents:
                if adj in unknown_tiles:
                    dist = max(abs(bot_row - tile[0]), abs(bot_col - tile[1]))
                    print(tile, adj, dist)
                    if game_state.get_str_map()[tile[0]][tile[1]] == 'I':
                        continue
                    if min_dist == None or dist < min_dist:
                        min_dist = dist
                        best_tile = tile
        print(best_tile)
        best_dir = game_state.optimal_path(
            bot_row, bot_col, best_tile[0], best_tile[1], checkCollisions=True)[0]
        return best_tile, best_dir, min_dist
                    

    def get_adj_tiles(self, tile, game_state):
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
        # print(tile, dest_locs)
        return dest_locs, valid_dirs
    
    def get_explored_unexplored(self, game_state):
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

    # def get_adjacent_fog(self, strmap, fog):
    #     # get a visible tile adjacent to fog
    #     i, j = fog
    #     unexplorable = ['I', '#']
    #     if i > 0 and strmap[i-1][j] not in unexplorable:
    #         return (i-1, j)
    #     elif i < len(strmap) - 1 and strmap[i+1][j] not in unexplorable:
    #         return (i+1, j) 
    #     elif j > 0 and strmap[i][j-1] not in unexplorable:
    #         return (i, j-1)
    #     elif j < len(strmap[0]) - 1 and strmap[i][j+1] not in unexplorable:
    #         return (i, j+1)
    #     return None

    # def find_fog(self, strmap, bot_loc):
    #     # bfs until we find a fog
    #     bot_row, bot_col = bot_loc
    #     queue = [bot_loc]
    #     visited = set()
    #     while len(queue) > 0:
    #         i, j = queue.pop()
    #         if strmap[i][j] == '#':
    #             fog = (i, j)
    #             adjacent_fog = self.get_adjacent_fog(strmap, fog)
    #             if adjacent_fog != None:
    #                 return adjacent_fog
    #         visited.add((i, j))
    #         if i > 0 and (i-1, j) not in visited:
    #             queue.append((i-1, j))
    #         elif i < len(strmap) - 1 and (i+1, j) not in visited:
    #             queue.append((i+1, j))
    #         elif j > 0 and (i, j-1) not in visited:
    #             queue.append((i, j-1))
    #         elif j < len(strmap[0]) - 1 and (i, j+1) not in visited:
    #             queue.append((i, j+1))
    #     raise Exception("There was no fog :(")
            

