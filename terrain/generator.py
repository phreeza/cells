import numpy
import random
import math

class terrain_generator():
    def create_random(self, size, range, symmetric=False):
        """Creates a random terrain map"""
        ret = numpy.random.random_integers(0, range, size)

        if symmetric:
            ret = self.make_symmetric(ret)
        return ret

    def create_streak(self, size, range, symmetric=False):
        """Creates a terrain map containing streaks that run from north-west to south-east

           Starts with a single point [[a]] and converts it into [[a, b], [c, d]]
           where:
           b = a + (random change)
           c = a + (random change)
           d = b + (random change) and c + (random change)

           Repeat untill size matches required size"""
        add_random_range = self.add_random_range

        # Creates the top row
        ret = [[add_random_range(0, 0, range)]]
        for x in xrange(size[0] - 1):
            pos_west = ret[0][-1]
            if pos_west <= 0:
              ret[0].append(add_random_range(pos_west, 0, 1))
            elif pos_west >= range:
              ret[0].append(add_random_range(pos_west, -1, 0))
            else:
              ret[0].append(add_random_range(pos_west, -1, 1))

        # Create the next row down
        for y in xrange(size[1] - 1):
            pos_north = ret[-1][0]
            if pos_north <= 0:
                next_row = [add_random_range(pos_north, 0, 1)]
            elif pos_north >= range:
                next_row = [add_random_range(pos_north,-1, 0)]
            else:
                next_row = [add_random_range(pos_north, -1, 1)]

            for x in xrange(size[0] - 1):
                pos_north = ret[-1][x+1]
                pos_west = next_row[-1]
                if pos_west == pos_north:
                    if pos_west <= 0:
                        next_row.append(add_random_range(pos_west, 0, 1))
                    elif pos_west >= range:
                        next_row.append(add_random_range(pos_west, -1, 0))
                    else:
                        next_row.append(add_random_range(pos_west, -1, 1))
                elif abs(pos_west - pos_north) == 2:
                    next_row.append((pos_west + pos_north)/2)
                else:
                    next_row.append(random.choice((pos_west, pos_north)))
            ret.append(next_row)

        if symmetric:
            ret = self.make_symmetric(ret)
        return numpy.array(ret)

    def create_simple(self, size, range, symmetric=False):
        """Creates a procedural terrain map

           Starts with corner points [[a, b], [c, d]] and converts it into [[a, e, b], [f, g, h], [c, i, d]]
           where:
           e = (a+b)/2 + (random change)
           f = (a+c)/2 + (random change)
           g = (a+b+c+d)/4 + (random change)
           h = (b+d)/2 + (random change)
           i = (c+d)/2 + (random change)

           Repeat untill size is greater than required and truncate"""
        add_random_range = self.add_random_range

        ret = [[add_random_range(0, 0, range), add_random_range(0, 0, range)], [add_random_range(0, 0, range), add_random_range(0, 0, range)]]

        while len(ret) <= size[0]:
            new_ret = []

            for key_x, x in enumerate(ret):
                new_ret.append(x)

                if key_x != len(ret) - 1:
                    next_row = []
                    for key_y, pos_south in enumerate(x):
                        pos_north = ret[key_x+1][key_y]
                        pos_avg = (pos_north + pos_south)/2
                        if pos_avg <= 0:
                            next_row.append(add_random_range(pos_avg, 0, 1))
                        elif pos_avg >= range:
                            next_row.append(add_random_range(pos_avg, -1, 0))
                        else:
                            next_row.append(add_random_range(pos_avg, -1, 1))
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
                        if pos_avg <= 0:
                            next_row.append(add_random_range(pos_avg, 0, 1))
                        elif pos_avg >= range:
                            next_row.append(add_random_range(pos_avg, -1, 0))
                        else:
                            next_row.append(add_random_range(pos_avg, -1, 1))
                    else:
                        pos_avg = (pos_east + pos_west)/2
                        if pos_avg <= 0:
                            next_row.append(add_random_range(pos_avg, 0, 1))
                        elif pos_avg >= range:
                            next_row.append(add_random_range(pos_avg, -1, 0))
                        else:
                            next_row.append(add_random_range(pos_avg, -1, 1))
                    next_row.append(pos_east)
                new_ret.append(next_row)
            ret = new_ret

        ret = [x[:size[0]] for x in ret][:size[0]]

        if symmetric:
            ret = self.make_symmetric(ret)
        return numpy.array(ret)
    
    def create_perlin(self, size, roughness, symmetric = False):
        (width, height) = size
        values = numpy.zeros(size)
        noise = numpy.random.random_sample((width+1, height+1))
        octaves = (256, 8, 2)
        for y in range(height):
            for x in range(width):
                if symmetric and x < y:
                    values[x][y] = values[y][x]
                    continue
                nr = 1
                for i in octaves:
                    top = y/i
                    left = x/i
                    my = float(y % i) / i
                    mx = float(x % i) / i
                    values[x][y] += self.interpolate(noise[top][left], noise[top][left+1], noise[top+1][left], noise[top+1][left+1], mx, my) * math.pow(0.5, nr)
                    nr += 1
                values[x][y] = int(values[x][y] * roughness)
        return numpy.array(values,dtype=int)
    
    #Some helper functions.
    def interpolate(self, p1, p2, p3, p4, x, y):
        top = self.interpolate1d(p1, p2, x)
        bottom = self.interpolate1d(p3, p4, x)
        return self.interpolate1d(top, bottom, y)
        
    def interpolate1d(self, p1, p2, mu):
        return p1*(1-mu)+p2*mu

    def add_random_range(self, x, rand_min, rand_max):
        """Returns a number that is between x + rand_min and x + rand_max (inclusive)"""
        return x + random.randrange(rand_min, rand_max + 1)

    def make_symmetric(self, ret):
        """Takes a 2-dimentional list and makes it symmetrical about the north-west / south-east axis"""
        for x in xrange(len(ret)):
            for y in xrange(x):
                ret[x][y] = ret[y][x]

        return ret
