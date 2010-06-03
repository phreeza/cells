#!/usr/bin/env python
#TODO:
# - Add more actions: PASS, LIFT, DROP,etc...
# - fractal terrain generation
# - Split into several files.
# - limit frame rate
# - response objects for outcome of action

import ConfigParser
import random
import sys
import time

import numpy
import pygame, pygame.locals


try:
    import psyco
    psyco.full()
except ImportError:
    pass


def get_mind(name):
    full_name = 'minds.' + name
    __import__(full_name)
    mind = sys.modules[full_name]
    mind.name = name
    return mind


STARTING_ENERGY  = 25
SCATTERED_ENERGY = 5 
PLANT_MAX_OUTPUT = 11
PLANT_MIN_OUTPUT = 4

ATTACK_POWER = 20
DEATH_DROP   = 25
ENERGY_CAP   = 500

SPAWN_COST      = 20
SUSTAIN_COST    = 1
MOVE_COST       = 1    

# This must be a function of DEATH_DROP and SPAWN_COST. Why?
# Consider a cell with SPAWN_MIN_ENERGY that spawns.
# It creates two cells, each with (SPAWN_MIN_ENERGY - SPAWN_COST) / 2 energy,
# that will yield DEATH_DROP energy when killed.
# If (SPAWN_MIN_ENERGY - SPAWN_COST) / 2 < DEATH_DROP, energy is created, so
# we need SPAWN_MIN_ENERGY - SPAWN_COST) / 2 >= DEATH_DROP, or
# SPAWN_MIN_ENERGY >= 2 * DEATH_DROP + SPAWN_COST.
SPAWN_MIN_ENERGY = 2 * DEATH_DROP + SPAWN_COST

TIMEOUT = None

config = ConfigParser.RawConfigParser()


def get_next_move(old_x, old_y, x, y):
    dx = numpy.sign(x - old_x)
    dy = numpy.sign(y - old_y)
    return (old_x + dx, old_y + dy)


class Game(object):
    def __init__(self, bounds, mind_list, symmetric, max_time):
        self.size = self.width, self.height = (bounds, bounds)
        self.mind_list = mind_list
        self.messages = [MessageQueue() for x in mind_list]
        self.disp = Display(self.size, scale=2)
        self.time = 0
        self.max_time = max_time
        self.tic = time.time()
        self.terr = ScalarMapLayer(self.size)
        self.terr.set_random(5)
        self.minds = [m[1].AgentMind for m in mind_list]

        self.energy_map = ScalarMapLayer(self.size)
        self.energy_map.set_random(SCATTERED_ENERGY)

        self.plant_map = ObjectMapLayer(self.size, None)
        self.plant_population = []

        self.agent_map = ObjectMapLayer(self.size, None)
        self.agent_population = []
        self.winner = None
        if symmetric:
            self.n_plants = 7
        else:
            self.n_plants = 14

        for x in xrange(self.n_plants):
            mx = random.randrange(1, self.width - 1)
            my = random.randrange(1, self.height - 1)
            eff = random.randrange(PLANT_MIN_OUTPUT, PLANT_MAX_OUTPUT)
            p = Plant(mx, my, eff)
            self.plant_population.append(p)
            if symmetric:
                p = Plant(my, mx, eff)
                self.plant_population.append(p)
        self.plant_map.insert(self.plant_population)

        for idx in xrange(len(self.minds)):
            (mx, my) = self.plant_population[idx].get_pos()
            fuzzed_x = mx + random.randrange(-1, 2)
            fuzzed_y = my + random.randrange(-1, 2)
            self.agent_population.append(Agent(fuzzed_x, fuzzed_y, STARTING_ENERGY, idx,
                                               self.minds[idx], None))
            self.agent_map.insert(self.agent_population)

    def run_plants(self):
        for p in self.plant_population:
            (x, y) = p.get_pos()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    adj_x = x + dx
                    adj_y = y + dy
                    if self.energy_map.in_range(adj_x, adj_y):
                        self.energy_map.change(adj_x, adj_y, p.get_eff())

    def add_agent(self, a):
        self.agent_population.append(a)
        self.agent_map.set(a.x, a.y, a)

    def del_agent(self, a):
        self.agent_population.remove(a)
        self.agent_map.set(a.x, a.y, None)
        a.alive = False
        if a.loaded:
            a.loaded = False
            self.terr.change(a.x, a.y, 1)

    def move_agent(self, a, x, y):
        if abs(self.terr.get(x, y)-self.terr.get(a.x, a.y)) <= 4:
            self.agent_map.set(a.x, a.y, None)
            self.agent_map.set(x, y, a)
            a.x = x
            a.y = y

    def run_agents(self):
        views = []
        agent_map_get_small_view_fast = self.agent_map.get_small_view_fast
        plant_map_get_small_view_fast = self.plant_map.get_small_view_fast
        energy_map = self.energy_map
        WV = WorldView
        views_append = views.append
        for a in self.agent_population:
            x = a.x
            y = a.y
            agent_view = agent_map_get_small_view_fast(x, y)
            plant_view = plant_map_get_small_view_fast(x, y)
            world_view = WV(a, agent_view, plant_view, energy_map)
            views_append((a, world_view))

        #get actions
        messages = self.messages
        actions = [(a, a.act(v, messages[a.team])) for (a, v) in views]
        actions_dict = dict(actions)
        random.shuffle(actions)

        #apply agent actions
        for (agent, action) in actions:
            #This is the cost of mere survival
            agent.energy -= SUSTAIN_COST

            if action.type == ACT_MOVE:
                act_x, act_y = action.get_data()
                (new_x, new_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                #Only move if the target field is free
                if (self.agent_map.in_range(new_x, new_y) and
                    not self.agent_map.get(new_x, new_y)):
                    self.move_agent(agent, new_x, new_y)
                    agent.energy -= MOVE_COST
            elif action.type == ACT_SPAWN:
                act_x, act_y = action.get_data()[:2]
                (new_x, new_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                if (self.agent_map.in_range(new_x, new_y) and
                    not self.agent_map.get(new_x, new_y) and
                    agent.energy >= SPAWN_MIN_ENERGY):
                    agent.energy -= SPAWN_COST
                    agent.energy /= 2
                    a = Agent(new_x, new_y, agent.energy, agent.get_team(),
                              self.minds[agent.get_team()],
                              action.get_data()[2:])
                    self.add_agent(a)
            elif action.type == ACT_EAT:
                #Eat only as much as possible.
                intake = min(self.energy_map.get(agent.x, agent.y),
                            ENERGY_CAP - agent.energy)
                agent.energy += intake
                self.energy_map.change(agent.x, agent.y, -intake)
            elif action.type == ACT_RELEASE:
                #Dump some energy onto an adjacent field
                #No Seppuku
                output = action.get_data()[2]
                output = min(agent.energy - 1, output) 
                act_x, act_y = action.get_data()[:2]
                #Use get_next_move to simplyfy things if you know 
                #where the energy is supposed to end up.
                (out_x, out_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                if (self.agent_map.in_range(out_x, out_y) and
                    agent.energy >= 1):
                    agent.energy -= output
                    self.energy_map.change(new_x,new_y,output)
            elif action.type == ACT_ATTACK:
                #Make sure agent is attacking an adjacent field.
                act_x, act_y = act_data = action.get_data()
                next_pos = get_next_move(agent.x, agent.y, act_x, act_y)
                new_x, new_y = next_pos
                victim = self.agent_map.get(act_x, act_y)
                if (victim is not None and victim.alive and
                    next_pos == act_data):
                    agent.attack(victim)
                    #If both agents attack each other, both loose double energy
                    #Think twice before attacking 
                    if actions_dict[victim].type == ACT_ATTACK:
                        victim.attack(agent)
                     
            elif action.type == ACT_LIFT:
                if not agent.loaded and self.terr.get(agent.x, agent.y) > 0:
                    agent.loaded = True
                    self.terr.change(agent.x, agent.y, -1)
            elif action.type == ACT_DROP:
                if agent.loaded:
                    agent.loaded = False
                    self.terr.change(agent.x, agent.y, 1)

        #let agents die if their energy is too low
        team = [0 for n in self.minds]
        for (agent, action) in actions:
            if agent.energy < 0 and agent.alive:
                self.energy_map.change(agent.x, agent.y, DEATH_DROP)
                self.del_agent(agent)
            else :
                team[agent.team] += 1

        if not team[0]:
            print "Winner is %s (blue) in: %s" % (self.mind_list[1][1].name,
                                                  str(self.time))
            self.winner = 1
        if not team[1]:
            print "Winner is %s (red) in: %s" % (self.mind_list[0][1].name,
                                               str(self.time))
            self.winner = 0
        if self.max_time > 0 and self.time > self.max_time:
            print "It's a draw!"
            self.winner = -1

    def tick(self):
        self.disp.update(self.terr, self.agent_population,
                         self.plant_population, self.energy_map)
        self.disp.flip()
        
        # test for spacebar pressed - if yes, restart
        for event in pygame.event.get():
            if (event.type == pygame.locals.KEYUP and
                event.key == pygame.locals.K_SPACE):
                self.winner = -1

        self.run_agents()
        self.run_plants()
        for msg in self.messages:
            msg.update()
        self.time += 1
        self.tic = time.time()


class MapLayer(object):
    def __init__(self, size, val=0):
        self.size = self.width, self.height = size
        self.values = numpy.zeros(size, numpy.object_)
        self.values[:] = val

    def get(self, x, y):
        if y >= 0 and x >= 0:
            try:
                return self.values[x, y]
            except IndexError:
                return None
        return None

    def set(self, x, y, val):
        self.values[x, y] = val

    def in_range(self, x, y):
        return (0 <= x < self.width and 0 <= y < self.height)


class ScalarMapLayer(MapLayer):
    def set_random(self, range):
        self.values = numpy.random.random_integers(0, range - 1, self.size)

    def change(self, x, y, val):
        self.values[x, y] += val


class ObjectMapLayer(MapLayer):
    def get_small_view_fast(self, x, y):
        ret = []
        get = self.get
        append = ret.append
        width = self.width
        height = self.height
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not (dx or dy):
                    continue
                try:
                    adj_x = x + dx
                    if not 0 <= adj_x < width:
                        continue
                    adj_y = y + dy
                    if not 0 <= adj_y < height:
                        continue
                    a = self.values[adj_x, adj_y]
                    if a is not None:
                        append(a.get_view())
                except IndexError:
                    pass
        return ret

    def get_view(self, x, y, r):
        ret = []
        for x_off in xrange(-r, r + 1):
            for y_off in xrange(-r, r + 1):
                if x_off == 0 and y_off == 0:
                    continue
                a = self.get(x + x_off, y + y_off)
                if a is not None:
                    ret.append(a.get_view())
        return ret

    def insert(self, list):
        for o in list:
            self.set(o.x, o.y, o)

# Use Cython version of get_small_view_fast if available.
# Otherwise, don't bother folks about it.
try:
    import cells_helpers
    import types
    ObjectMapLayer.get_small_view_fast = types.MethodType(
        cells_helpers.get_small_view_fast, None, ObjectMapLayer)
except ImportError:
    pass


class Agent(object):
    __slots__ = ['x', 'y', 'mind', 'energy', 'alive', 'team', 'loaded', 'color',
                 'act']
    def __init__(self, x, y, energy, team, AgentMind, cargs):
        self.x = x
        self.y = y
        self.mind = AgentMind(cargs)
        self.energy = energy
        self.alive = True
        self.team = team
        self.loaded = False
        colors = [(255, 0, 0), (0, 0, 255), (255, 0, 255), (255, 255, 0)]
        self.color = colors[team % len(colors)]
        self.act = self.mind.act

    def attack(self, other):
        if not other:
            return False
        other.energy -= ATTACK_POWER
        return other.energy <= 0

    def get_team(self):
        return self.team

    def get_pos(self):
        return (self.x, self.y)

    def set_pos(self, x, y):
        self.x = x
        self.y = y

    def get_view(self):
        return AgentView(self)


ACT_SPAWN, ACT_MOVE, ACT_EAT, ACT_RELEASE, ACT_ATTACK, ACT_LIFT, ACT_DROP = range(7)


class Action(object):
    '''
    A class for passing an action around.
    '''
    def __init__(self, action_type, data=None):
        self.type = action_type
        self.data = data

    def get_data(self):
        return self.data

    def get_type(self):
        return self.type


class PlantView(object):
    def __init__(self, p):
        self.x = p.x
        self.y = p.y
        self.eff = p.get_eff()

    def get_pos(self):
        return (self.x, self.y)

    def get_eff(self):
        return self.eff


class AgentView(object):
    def __init__(self, agent):
        (self.x, self.y) = agent.get_pos()
        self.team = agent.get_team()

    def get_pos(self):
        return (self.x, self.y)

    def get_team(self):
        return self.team


class WorldView(object):
    def __init__(self, me, agent_views, plant_views, energy_map):
        self.agent_views = agent_views
        self.plant_views = plant_views
        self.energy_map = energy_map
        self.me = me

    def get_me(self):
        return self.me

    def get_agents(self):
        return self.agent_views

    def get_plants(self):
        return self.plant_views

    def get_energy(self):
        return self.energy_map


class Display(object):
    black = (0, 0, 0)
    red = (255, 0, 0)
    green = (0, 255, 0)
    yellow = (255, 255, 0)

    def __init__(self, size, scale=5):
        self.width, self.height = size
        self.scale = scale
        self.size = (self.width * scale, self.height * scale)
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)

    def update(self, terr, pop, plants, energy_map):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
        
        limit = 150 * numpy.ones_like(terr.values)

        r = numpy.minimum(limit, 20 * terr.values)
        g = numpy.minimum(limit, 10 * terr.values + 10 * energy_map.values)
        b = numpy.zeros_like(terr.values)

        img = numpy.dstack((r, g, b))

        for a in pop:
            img[a.get_pos()] = a.color

        for a in plants:
            img[a.get_pos()] = self.green

        scale = self.scale
        pygame.transform.scale(pygame.surfarray.make_surface(img),
                               self.size, self.screen)

    def flip(self):
        pygame.display.flip()


class Plant(object):
    def __init__(self, x, y, eff):
        self.x = x
        self.y = y
        self.eff = eff

    def get_pos(self):
        return (self.x, self.y)

    def get_eff(self):
        return self.eff

    def get_view(self):
        return PlantView(self)


class MessageQueue(object):
    def __init__(self):
        self.__inlist = []
        self.__outlist = []

    def update(self):
        self.__outlist = self.__inlist
        self.__inlist = []

    def send_message(self, m):
        self.__inlist.append(m)

    def get_messages(self):
        return self.__outlist


class Message(object):
    def __init__(self, message):
        self.message = message
    def get_message(self):
        return self.message


def main():
    global bounds, symmetric, mind_list
    
    try:
        config.read('default.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))
    except Exception as e:
        print 'Got error: %s' % e
        config.add_section('minds')
        config.set('minds', 'minds', 'mind1,mind2')
        config.add_section('terrain')
        config.set('terrain', 'bounds', '300')
        config.set('terrain', 'symmetric', 'true')

        with open('default.cfg', 'wb') as configfile:
            config.write(configfile)

        config.read('default.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))
    mind_list = [(n, get_mind(n)) for n in minds_str.split(',')]

    # accept command line arguments for the minds over those in the config
    try:
        if len(sys.argv)>2:
            mind_list = [get_mind(n) for n in sys.argv[1:] ]
    except (ImportError, IndexError):
        pass


if __name__ == "__main__":
    main()
    while True:
        game = Game(bounds, mind_list, symmetric, -1)
        while game.winner == None:
            game.tick()
