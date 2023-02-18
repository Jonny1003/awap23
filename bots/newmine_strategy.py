from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo

#
# params must be a dict with 2 keys:
# "game_state"      --> game state
# "mine_location"   --> tuple of (row,col)
#
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
                print(bot, dir, steps)
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






