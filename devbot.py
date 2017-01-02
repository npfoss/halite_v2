import hlt
from hlt import NORTH, EAST, SOUTH, WEST, STILL, Move, Square
import sys
from bisect import insort_left
from time import time

#-----------constants to be optimized-----------------------------
ACCUM_MOD = 1

# maybe this one too -- nah not yet, it's not in use
AVG_STREN_DIVISOR = 4
#-----------other globals-----------------------------------------
myID, game_map = hlt.get_init()
orderedDestinations = None
out = open('gamelog.txt', 'w')
average_strength = sum(sq.strength for sq in game_map)/(game_map.width*game_map.height)
out.write('avg strength = ' + str(average_strength) + '\n')
min_strength = min(sq.strength for sq in game_map)

#-----------precomputation function definitions-------------------
def generate_destinations():
    # TODO: generates priority list of destinations for every tile
    # massive amount of optimization to be done here, including even how far away to look based on other stuff
    # ---TEST--- make everything go for (1,1)
    orderedDestinations = [[[(3, 15)] for x in range(game_map.width)] for y in range(game_map.height)]






    return orderedDestinations

#-----------precomputation----------------------------------------
orderedDestinations = generate_destinations()



hlt.send_init("devbot")

#-----------turn functions----------------------------------------
def find_nearest_enemy_direction(square):
    # INCLUDES NEUTRALS
    direction = NORTH
    max_distance = min(game_map.width, game_map.height) / 2
    for d in (NORTH, EAST, SOUTH, WEST):
        distance = 0
        current = square
        while current.owner == myID and distance < max_distance:
            distance += 1
            current = game_map.get_target(current, d)
        if distance < max_distance:
            direction = d
            max_distance = distance
    return direction

def heuristic(square):
    if square.owner == 0 and square.strength > 0:
        return square.production / square.strength
    else:
        # return total potential damage caused by overkill when attacking this square
        return sum(neighbor.strength for neighbor in game_map.neighbors(square) if neighbor.owner not in (0, myID))

def find_path_of_least_resistance(square, destination):
    # edge case
    if destination in game_map.neighbors(square, include_self=True):
        return game_map.get_directions(square, curr[2][-1])[0], square.strength, -1 if destination.owner == myID else destination.strength 
    # TODO: returns  direction , accumulation_to_first_enemy , strength_of_first_enemy
    # TODO: memoize this method???
    c = lambda sq: sq.production + sq.strength if sq.owner != myID else int(-sq.strength/ACCUM_MOD)
    pathes = []
    pathes = [[min_strength*game_map.get_distance(square, destination), [square.strength,-1], [square]]]
    #         [heuristic (cost + estimate),          [accumulation to first enemy, strength], [path there]]
    seen = []
    #out.write(' start: ' + str(square) + '\n')
    #out.write(' end: ' + str(destination) + '\n')
    while pathes:
        #out.write('  %d '%len(pathes) + str(pathes) + '\n')
        curr = pathes.pop(0)
        if curr[2][0] == destination:
            return game_map.get_directions(square, curr[2][-2])[0], curr[1][0], curr[1][1]
        seen.append(curr[2][0])
        for d in game_map.get_directions(curr[2][0], destination):
            newsq = game_map.get_target(curr[2][0], d)
            if newsq in seen:
                continue
            #out.write('  try: ' + str(newsq) + '\n')
            newaccu = ([curr[1][0] + newsq.strength, -1] if newsq.owner == myID else [curr[1][0], newsq.strength] ) if curr[1][1] < -1 else curr[1]
            newcost = c(newsq) + curr[0] - min_strength # TODO: maybe... also subtract prod*distance away and see if it improves
            insort_left(pathes, [newcost, newaccu, [newsq] + curr[2]])

def get_next_destination(square):
    for (x,y) in orderedDestinations[square.y][square.x]:
        if game_map.contents[y][x].owner == 0: #only go for neutrals TODO: test if making this !=myID is better (to still go for enemy)
            return game_map.contents[y][x]
    return None

def get_move(square):
    if square.strength < 2 * square.production: return Move(square, STILL)
    inCombat = False
    if inCombat:
        # old overkill bot stuff
        target, direction = max(((neighbor, direction) for direction, neighbor in enumerate(game_map.neighbors(square))
                                    if neighbor.owner != myID),
                                    default = (None, None),
                                    key = lambda t: heuristic(t[0]))
        if target is not None and target.strength < square.strength and (target.strength or square.strength >= 2 * square.production):
            return Move(square, direction)
        elif square.strength < square.production * 5:
            return Move(square, STILL)
        else:
            #wait until we are strong enough to attack
            return Move(square, STILL)
    else:
        # not in combat, optimize econ
        dest = get_next_destination(square)
        if dest:
            # have a target
            if game_map.get_distance(square, dest) == 1:
                if square.strength > dest.strength:
                    return Move(square, game_map.get_directions(square, dest)[0]) #NOTE: may have to recast as list
                # TODO: check if friends can help instead of just giving up here
                return Move(square, STILL)
            else:
                direction , accumulation_to_first_enemy , strength_of_first_enemy = find_path_of_least_resistance(square, dest)
                return Move(square, direction) if square.strength >= 5*square.production else Move(square, STILL)
                # TODO: see if this is better
                return Move(square, direction) if accumulation_to_first_enemy * ACCUM_MOD > strength_of_first_enemy else Move(square, STILL)
        else:
            # all targets already taken over...
            # default: go for "nearest" enemy/neutral
            return Move(square, find_nearest_enemy_direction(square))
            # TODO: go for POIs or something

turn = 1
while True:
    start = time()
    game_map.get_frame()
    moves = [get_move(square) for square in game_map if square.owner == myID]
    hlt.send_frame(moves)
    out.write('Turn %4d duration: %f\n'%(turn, time()-start)+ '\n')
    turn += 1