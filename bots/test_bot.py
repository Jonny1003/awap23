from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
import random
from bots.direction_strategy import direction_strategy

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

        # find un-ocupied ally tile
        ally_tiles = []
        # find mine tiles
        mine_tiles = []
        for row in range(height):
            for col in range(width):
                # get the tile at (row, col)
                tile = ginfo.map[row][col]
                # skip fogged tiles
                if tile is not None: # ignore fogged tiles
                    if tile.robot is None: # ignore occupied tiles
                        if tile.terraform > 0: # ensure tile is ally-terraformed
                            ally_tiles += [tile]
                    if tile.mining:
                        mine_tiles.append((row, col))

        # if len(mine_tiles) and len(game_state.get_ally_robots()) > 2:
        #     params = {
        #         "game_state" : game_state,
        #         "mine_location" : mine_tiles[0],
        #     }
        #     print(f"My metal {game_state.get_metal()}")
        #     bots = []
        #     for rname, rob in game_state.get_ally_robots().items():
        #         if rob.type != RobotType.EXPLORER:
        #             bots.append(rob)
        #     direction_strategy(bots, params)
        # else:

        print("Ally tiles", ally_tiles)

        # spawn on a random tile
        print(f"My metal {game_state.get_metal()}")
        if len(ally_tiles) > 0:
            # pick a random one to spawn on
            spawn_loc = random.choice(ally_tiles)
            spawn_type = random.choice([RobotType.TERRAFORMER])
            if len(game_state.get_ally_robots()) > 1:
                spawn_type = RobotType.EXPLORER
            # spawn the robot
            print(f"Spawning robot at {spawn_loc.row, spawn_loc.col}")
            # check if we can spawn here (checks if we can afford, tile is empty, and tile is ours)
            if game_state.can_spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col):
                game_state.spawn_robot(spawn_type, spawn_loc.row, spawn_loc.col)


        # move robots
        robots = game_state.get_ally_robots()

        # iterate through dictionary of robots
        for rname, rob in robots.items():
            print(f"Robot {rname} at {rob.row, rob.col}")

            if (rob.type == RobotType.EXPLORER):
                direction_strategy(rob, {"game_state" : game_state, "direction" : Direction.UP_LEFT})
            else:
                # randomly move if possible
                all_dirs = [dir for dir in Direction]
                move_dir = random.choice(all_dirs)

                # check if we can move in this direction
                if game_state.can_move_robot(rname, move_dir):
                    # try to not collide into robots from our team
                    dest_loc = (rob.row + move_dir.value[0], rob.col + move_dir.value[1])
                    dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]

                    if dest_tile.robot is None or dest_tile.robot.team != self.team:
                        game_state.move_robot(rname, move_dir)

                # action if possible
                if game_state.can_robot_action(rname):
                    game_state.robot_action(rname)



