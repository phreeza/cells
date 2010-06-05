import numpy
import random

# TODO: do something about the lack of symmetric

class terrain_generator():
    def create_random(self, size, range):
        """Creates a random terrain map"""
        return numpy.random.random_integers(0, range - 1, size)

    def create_streak(self, size, range):
        """Creates a terrain map containing streaks that run from north-west to south-east"""
        ret = [[0]]
        for x in xrange(size[0] - 1):
            pos_west = ret[0][-1]
            if not pos_west:
              ret[0].append(pos_west + random.randrange(0, 2))
            elif pos_west == range - 1:
              ret[0].append(pos_west + random.randrange(-1, 1))
            else:
              ret[0].append(pos_west + random.randrange(-1, 2))

        for y in xrange(size[1] - 1):
            pos_north = ret[0][-1]
            if not pos_north:
                next_row = [pos_north + random.randrange(0, 2)]
            elif pos_north == range - 1:
                next_row = [pos_north + random.randrange(-1, 1)]
            else:
                next_row = [pos_north + random.randrange(-1, 2)]

            for x in xrange(size[0] - 1):
                pos_north = ret[-1][x+1]
                pos_west = next_row[-1]
                if pos_west == pos_north:
                    if not pos_west or not pos_north:
                        next_row.append(pos_west + random.randrange(0, 2))
                    elif next_row[-1] == range - 1 or pos_north == range - 1:
                        next_row.append(pos_west + random.randrange(-1, 1))
                    else:
                        next_row.append(pos_west + random.randrange(-1, 2))
                elif abs(pos_west - pos_north) == 2:
                    next_row.append((pos_west + pos_north)/2)
                else:
                    next_row.append(random.choice((pos_west, pos_north)))
            ret.append(next_row)

        return numpy.array(ret)

    def create_simple(self, size, range):
        """Creates a procedural terrain map"""
        ret = [[random.randrange(0, range - 1), random.randrange(0, range - 1)], [random.randrange(0, range - 1), random.randrange(0, range - 1)]]

        while len(ret) <= size[0]:
            new_ret = []

            for key_x, x in enumerate(ret):
                new_ret.append(x)

                if key_x != len(ret) - 1:
                    next_row = []
                    for key_y, pos_south in enumerate(x):
                        pos_north = ret[key_x+1][key_y]
                        pos_avg = (pos_north + pos_south)/2
                        if not pos_avg:
                            next_row.append(pos_avg + random.randrange(0, 2))
                        elif pos_avg == range - 1:
                            next_row.append(pos_avg + random.randrange(-1, 1))
                        else:
                            next_row.append(pos_avg + random.randrange(-1, 2))
                    new_ret.append(next_row)
            ret = new_ret

            new_ret = []
            for key_x, x in enumerate(ret):
                next_row = [x[0]]
                for key_y, pos_east in enumerate(x[1:]):
                    pos_west = next_row[-1]
                    if key_x % 2 and not key_y % 2:
                        pos_north = ret[key_x-1][key_y+1]
                        pos_south = ret[key_x+1][key_y+1]
                        pos_avg = (pos_north + pos_south + pos_east + pos_west)/4
                        if not pos_avg:
                            next_row.append(pos_avg + random.randrange(0, 2))
                        elif pos_avg == range - 1:
                            next_row.append(pos_avg + random.randrange(-1, 1))
                        else:
                            next_row.append(pos_avg + random.randrange(-1, 2))
                    else:
                        pos_avg = (pos_east + pos_west)/2
                        if not pos_avg:
                            next_row.append(pos_avg + random.randrange(0, 2))
                        elif pos_avg == range - 1:
                            next_row.append(pos_avg + random.randrange(-1, 1))
                        else:
                            next_row.append(pos_avg + random.randrange(-1, 2))
                    next_row.append(pos_east)
                new_ret.append(next_row)
            ret = new_ret

        ret = [x[:size[0]] for x in ret][:size[0]]           
        return numpy.array(ret)
