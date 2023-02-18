from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
from collections import deque

#
# params contains game_state
# bots should all be terraform edges
#
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
                        elif (bot.battery >= bot.action_cost):
                            if (tile.terraform <= 0
                                and tile.terraform >= bestNegTerra
                                and ((myTile.terraform <= 0 and tile.terraform > myTile.terraform) or myTile.terraform > 0)):
                                dir = d
                                bestNegTerra = tile.terraform
                                positive = False
                            if (positive and tile.terraform > 0
                                and tile.terraform <= bestPosTerra
                                and tile.terraform < myTile.terraform):
                                dir = d
                                bestPosTerra = tile.terraform
            if dir is not None:
                botsToMove.append((bot, dir))
            else:
                leftoverBots.append(bot)

        for bot, dir in botsToMove:
            if (game_state.can_move_robot(bot.name, dir)
                and noCollisions(bot, dir)):
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
        # else:
        #     dir, _ = game_state.robot_to_base(bot.name)
        #     if dir:
        #         game_state.move_robot(bot.name, dir)
        #     # Do nothing...
