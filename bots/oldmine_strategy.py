from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo

#
# params must be a dict with 2 keys:
# "game_state"      --> game state
# "mine_location"   --> tuple of (row,col)
#
def oldmine_strategy(bots, params):
    game_state = params.get('game_state')
    mine_loc = params.get('mine_location')
    def noCollision(rob, dir):
        dest_loc = (rob.row + dir.value[0], rob.col + dir.value[1])
        dest_tile = game_state.get_map()[dest_loc[0]][dest_loc[1]]
        return dest_tile != None and dest_tile.robot is None

    assert(len(mine_loc) == 2)

    mine_bots = []
    terra_bots = []
    for bot in bots:
        if bot.type == RobotType.MINER:
            mine_bots.append((bot.name,bot))
        elif bot.type == RobotType.TERRAFORMER:
            terra_bots.append((bot.name,bot))
        else:
            assert(0 and "oldmine_strategy cannot handle EXPLORER bots")
    # print(len(mine_bots))

    # Ensure one mine bot is on the mine
    amtBattery = -1
    bestBotName = "fake"
    bestBot = None
    noMoves = False
    for botName, bot in mine_bots:
        if bot.battery > amtBattery:
            if (bot.row == mine_loc[0] and bot.col == mine_loc[1]):
                # print("hello")
                if game_state.can_robot_action(bestBotName):
                    game_state.robot_action(bestBotName)
                    noMoves = True
            amtBattery = bot.battery
            bestBotName = botName
            bestBot = bot
    if noMoves:
        pass
    else:
        for botName, bot in mine_bots:
            if botName != bestBotName:
                dir, steps = game_state.robot_to_base(botName)
                if steps == 0:
                    pass # bot can rest
                elif steps < 0:
                    pass # TODO:temporary
                    # assert(0 and f"miner bot cannot get to base")
                else:
                    # move bot to base to recharge (steps should be 1)
                    # assert(steps == 1) # probably true... # TODO: temporary
                    if (game_state.can_move_robot(botName, dir)):
                        game_state.move_robot(botName, dir)

        if bestBot != None:
            # print(bestBot)
            # Have bot do action
            dir, steps = game_state.optimal_path(bestBot.row, bestBot.col, mine_loc[0], mine_loc[1])
            if steps == 0:
                if game_state.can_robot_action(bestBotName):
                    game_state.robot_action(bestBotName)
            elif steps < 0:
                assert(0 and f"cannot mine row {mine_loc[0]} col {mine_loc[1]}")
            else:
                assert(game_state.can_move_robot(bestBotName, dir)) # TODO: remove later
                game_state.move_robot(bestBotName, dir)
                if game_state.can_robot_action(bestBotName):
                    game_state.robot_action(bestBotName)
        else:
            # TODO: temporary
            # assert(0 and f"no bot is available to mine")
            pass

    # Move terra bots somewhere useful
    map = game_state.get_map()
    for botName, bot in terra_bots:
        if (game_state.can_robot_action(botName)):
            if map[bot.row][bot.col].terraform < 2:
                game_state.robot_action(botName)
            else:
                # select a nearby direction to goto
                for dir in Direction:
                    if (game_state.can_move_robot(botName, dir)
                        and noCollision(bot, dir)
                        and map[bot.row + dir.value[0]][bot.col + dir.value[1]].mining == 0
                        and map[bot.row + dir.value[0]][bot.col + dir.value[1]].terraform < 2):
                        game_state.move_robot(botName, dir)
                        if (game_state.can_robot_action(botName)):
                            game_state.robot_action(botName)
                # Do nothing if cannot find nearby tile to work on...
        else:
            dir, steps = game_state.robot_to_base(botName)
            if steps == 0:
                pass # bot can rest here
            elif (game_state.can_move_robot(botName, dir)):
                # move bot to nearby base to recharge
                game_state.move_robot(botName, dir)




