from src.game_constants import RobotType, Direction, Team, TileState
from src.game_state import GameState, GameInfo
from src.player import Player
from src.map import TileInfo, RobotInfo
from Decider import decider
from bots.explore_bot import explore
from bots.destroy_strategy import destroy
from bots.newmine_strategy import newmine_strategy
from bots.oldmine_strategy import oldmine_strategy
from bots.win_now_strategy_v2 import win_now_strategy
import random, time
import numpy as np

class BotPlayer(Player):
    """
    Players will write a child class that implements (notably the play_turn method)
    """

    def __init__(self, team: Team):
        self.team = team
        self.total_times = [[] for _ in range(6)]
        return

    def play_turn(self, game_state: GameState) -> None:
        self.times = [[] for _ in range(6)]
        ginfo = game_state.get_info()
        turn = ginfo.turn
        print(turn)
        # if turn > 30:
        #     return
        start = time.time()
        strategies = decider(game_state)
        self.times[0].append(time.time() - start)
        # print("\n\nListing Strategies:\n")
        for strategy in strategies:
            # print(strategy)
            # print()
            name, units, target = strategy
            if name == "Explore":
                if len(units) == 2:
                    if units[0].type != RobotType.EXPLORER:
                        units = [units[1], units[0]]
                start = time.time()
                explore(game_state, units, target)
                self.times[1].append(time.time() - start)
            elif name == "Approaching Scout":
                start = time.time()
                destroy(game_state, units, target)
                self.times[2].append(time.time() - start)
            elif name == "New Mine":
                tile = target["tile"]
                params = {"game_state" : game_state, "mine_location" : (tile.row, tile.col)}
                start = time.time()
                newmine_strategy(units, params)
                self.times[3].append(time.time() - start)
            elif name == "Old Mine":
                tile = target["tile"]
                params = {"game_state" : game_state, "mine_location" : (tile.row, tile.col)}
                start = time.time()
                newmine_strategy(units, params)
                self.times[4].append(time.time() - start)
            elif name == "Win Now":
                params = {"game_state" : game_state}
                start = time.time()
                win_now_strategy(units, params)
                self.times[5].append(time.time() - start)

        avg_times = [((round(sum(x)/len(x), 4) if len(x) > 0 else 0),len(x)) for x in self.times]
        print(avg_times)

# Total average: [0.2305, 0.0657, 0.0065, 0.0079, 0.0056, 0.4019]