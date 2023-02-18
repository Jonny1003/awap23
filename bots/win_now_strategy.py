from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
from collections import deque

#
# params contains game_state
# bots should all be terraform edges
#
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
                            # print("here")
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
                # print("ending")

                # Make a random legal move
                for dir in Direction:
                    # print(bot, dir)
                    if game_state.can_move_robot(bot.name, dir) and noCollisions(bot, dir):
                        game_state.move_robot(bot.name, dir)
                        break
                if game_state.can_robot_action(bot.name):
                    game_state.robot_action(bot.name)

