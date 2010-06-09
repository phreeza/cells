#!/usr/bin/env python

import ConfigParser
import random
import sys
import time

import numpy
import pygame, pygame.locals

from terrain.generator import terrain_generator

if not pygame.font: print 'Warning, fonts disabled'

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



STARTING_ENERGY = 20
SCATTERED_ENERGY = 10 

#Plant energy output. Remember, this should always be less
#than ATTACK_POWER, because otherwise cells sitting on the plant edge
#might become invincible.
PLANT_MAX_OUTPUT = 20
PLANT_MIN_OUTPUT = 5

#BODY_ENERGY is the amount of energy that a cells body contains
#It can not be accessed by the cells, think of it as: they can't
#eat their own body. It is released again at death.
BODY_ENERGY  = 25
ATTACK_POWER = 30
#Amount by which attack power is modified for each 1 height difference.
ATTACK_TERR_CHANGE = 2
ENERGY_CAP   = 2500

#SPAWN_COST is the energy it takes to seperate two cells from each other.
#It is lost forever, not to be confused with the BODY_ENERGY of the new cell.
SPAWN_LOST_ENERGY = 20
SUSTAIN_COST      = 0
MOVE_COST         = 1    
#MESSAGE_COST    = 0    

#BODY_ENERGY + SPAWN_COST is invested to create a new cell. What remains is split evenly.
#With this model we only need to make sure a cell can't commit suicide by spawning.
SPAWN_TOTAL_ENERGY = BODY_ENERGY + SPAWN_LOST_ENERGY

TIMEOUT = None

config = ConfigParser.RawConfigParser()


def get_next_move(old_x, old_y, x, y):
    ''' Takes the current position, old_x and old_y, and a desired future position, x and y,
    and returns the position (x,y) resulting from a unit move toward the future position.'''
    dx = numpy.sign(x - old_x)
    dy = numpy.sign(y - old_y)
    return (old_x + dx, old_y + dy)


class Game(object):
    ''' Represents a game between different minds. '''
    def __init__(self, bounds, mind_list, symmetric, max_time, headless = False):
        self.size = self.width, self.height = (bounds, bounds)
        self.mind_list = mind_list
        self.messages = [MessageQueue() for x in mind_list]
        self.headless = headless
        if not self.headless:
            self.disp = Display(self.size, scale=2)
        self.time = 0
        self.clock = pygame.time.Clock()
        self.max_time = max_time
        self.tic = time.time()
        self.terr = ScalarMapLayer(self.size)
        self.terr.set_perlin(10, symmetric)
        self.minds = [m[1].AgentMind for m in mind_list]

        self.show_energy = True
        self.show_agents = True

        self.energy_map = ScalarMapLayer(self.size)
        self.energy_map.set_streak(SCATTERED_ENERGY, symmetric)

        self.plant_map = ObjectMapLayer(self.size)
        self.plant_population = []

        self.agent_map = ObjectMapLayer(self.size)
        self.agent_population = []
        self.winner = None
        if symmetric:
            self.n_plants = 7
        else:
            self.n_plants = 14
            
        # Add some randomly placed plants to the map. 
        for x in xrange(self.n_plants):
            mx = random.randrange(1, self.width - 1)
            my = random.randrange(1, self.height - 1)
            eff = random.randrange(PLANT_MIN_OUTPUT, PLANT_MAX_OUTPUT)
            p = Plant(mx, my, eff)
            self.plant_population.append(p)
            if symmetric:
                p = Plant(my, mx, eff)
                self.plant_population.append(p)
        self.plant_map.lock()
        self.plant_map.insert(self.plant_population)
        self.plant_map.unlock()

        # Create an agent for each mind and place on map at a different plant.
        self.agent_map.lock()
        for idx in xrange(len(self.minds)):
            # BUG: Number of minds could exceed number of plants?
            (mx, my) = self.plant_population[idx].get_pos()
            fuzzed_x = mx
            fuzzed_y = my
            while fuzzed_x == mx and fuzzed_y == my:
                fuzzed_x = mx + random.randrange(-1, 2)
                fuzzed_y = my + random.randrange(-1, 2)
            self.agent_population.append(Agent(fuzzed_x, fuzzed_y, STARTING_ENERGY, idx,
                                               self.minds[idx], None))
            self.agent_map.insert(self.agent_population)
        self.agent_map.unlock()

    def run_plants(self):
        ''' Increases energy at and around (adjacent position) for each plant.
        Increase in energy is equal to the eff(?) value of each the plant.'''
        for p in self.plant_population:
            (x, y) = p.get_pos()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    adj_x = x + dx
                    adj_y = y + dy
                    if self.energy_map.in_range(adj_x, adj_y):
                        self.energy_map.change(adj_x, adj_y, p.get_eff())


    def add_agent(self, a):
        ''' Adds an agent to the game. '''
        self.agent_population.append(a)
        self.agent_map.set(a.x, a.y, a)

    def del_agent(self, a):
        ''' Kills the agent (if not already dead), removes them from the game and
        drops any load they were carrying in there previously occupied position. '''
        self.agent_population.remove(a)
        self.agent_map.set(a.x, a.y, None)
        a.alive = False
        if a.loaded:
            a.loaded = False
            self.terr.change(a.x, a.y, 1)

    def move_agent(self, a, x, y):
        ''' Moves agent, a, to new position (x,y) unless difference in terrain levels between
        its current position and new position is greater than 4.'''
        if abs(self.terr.get(x, y)-self.terr.get(a.x, a.y)) <= 4:
            self.agent_map.set(a.x, a.y, None)
            self.agent_map.set(x, y, a)
            a.x = x
            a.y = y

    def run_agents(self):
        # Create a list containing the view for each agent in the population.
        views = []
        agent_map_get_small_view_fast = self.agent_map.get_small_view_fast
        plant_map_get_small_view_fast = self.plant_map.get_small_view_fast
        energy_map = self.energy_map
        terr_map = self.terr
        WV = WorldView
        views_append = views.append
        for a in self.agent_population:
            x = a.x
            y = a.y
            agent_view = agent_map_get_small_view_fast(x, y)
            plant_view = plant_map_get_small_view_fast(x, y)
            world_view = WV(a, agent_view, plant_view, terr_map, energy_map)
            views_append((a, world_view))

        # Create a list containing the action for each agent, where each agent
        # determines its actions based on its view of the world and messages 
        # from its team.
        messages = self.messages
        actions = [(a, a.act(v, messages[a.team])) for (a, v) in views]
        actions_dict = dict(actions)
        random.shuffle(actions)

        self.agent_map.lock()
        # Apply the action for each agent - in doing so agent uses up 1 energy unit.
        for (agent, action) in actions:
            #This is the cost of mere survival
            agent.energy -= SUSTAIN_COST

            if action.type == ACT_MOVE: # Changes position of agent.
                act_x, act_y = action.get_data()
                (new_x, new_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                # Move to the new position if it is in range and it's not 
                #currently occupied by another agent.
                if (self.agent_map.in_range(new_x, new_y) and
                    not self.agent_map.get(new_x, new_y)):
                    self.move_agent(agent, new_x, new_y)
                    agent.energy -= MOVE_COST
            elif action.type == ACT_SPAWN: # Creates new agents and uses additional 50 energy units.
                act_x, act_y = action.get_data()[:2]
                (new_x, new_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                if (self.agent_map.in_range(new_x, new_y) and
                    not self.agent_map.get(new_x, new_y) and
                    agent.energy >= SPAWN_TOTAL_ENERGY):
                    agent.energy -= SPAWN_TOTAL_ENERGY
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
                    self.energy_map.change(out_x, out_y, output)
            elif action.type == ACT_ATTACK:
                #Make sure agent is attacking an adjacent field.
                act_x, act_y = act_data = action.get_data()
                next_pos = get_next_move(agent.x, agent.y, act_x, act_y)
                new_x, new_y = next_pos
                victim = self.agent_map.get(act_x, act_y)
                terr_delta = (self.terr.get(agent.x, agent.y) 
                            - self.terr.get(act_x, act_y))
                if (victim is not None and victim.alive and
                    next_pos == act_data):
                    #If both agents attack each other, both loose double energy
                    #Think twice before attacking 
                    try:
                        contested = (actions_dict[victim].type == ACT_ATTACK)
                    except:
                        contested = False
                    agent.attack(victim, terr_delta, contested)
                    if contested:
                        victim.attack(agent, -terr_delta, True)
                     
            elif action.type == ACT_LIFT:
                if not agent.loaded and self.terr.get(agent.x, agent.y) > 0:
                    agent.loaded = True
                    self.terr.change(agent.x, agent.y, -1)
                    
            elif action.type == ACT_DROP:
                if agent.loaded:
                    agent.loaded = False
                    self.terr.change(agent.x, agent.y, 1)

        # Kill all agents with negative energy.
        team = [0 for n in self.minds]
        for (agent, action) in actions:
            if agent.energy < 0 and agent.alive:
                self.energy_map.change(agent.x, agent.y, BODY_ENERGY)
                self.del_agent(agent)
            else :
                team[agent.team] += 1
            
        # Team wins (and game ends) if opposition team has 0 agents remaining.
        # Draw if time exceeds time limit.
        winner = 0
        alive = 0
        for t in team:
            if t != 0:
                alive += 1
            else:
                if alive == 0:
                    winner += 1
        
        if alive == 1:
            colors = ["red", "white", "purple", "yellow"]
            print "Winner is %s (%s) in %s" % (self.mind_list[winner][1].name, 
                                                colors[winner], str(self.time))
            self.winner = winner
        
        if alive == 0 or (self.max_time > 0 and self.time > self.max_time):
            print "It's a draw!"
            self.winner = -1

        self.agent_map.unlock()
        
    def tick(self):
        if not self.headless:
            # Space starts new game
            # q or close button will quit the game
            for event in pygame.event.get():
                if event.type == pygame.locals.KEYUP:
                    if event.key == pygame.locals.K_SPACE:
                        self.winner = -1
                    elif event.key == pygame.locals.K_q:
                         sys.exit()
                    elif event.key == pygame.locals.K_e:
                         self.show_energy = not self.show_energy
                    elif event.key == pygame.locals.K_a:
                         self.show_agents = not self.show_agents
                elif event.type == pygame.locals.MOUSEBUTTONUP:
                    if event.button == 1:
                        print self.agent_map.get(event.pos[0]/2,
                                                 event.pos[1]/2)
                elif event.type == pygame.QUIT:
                    sys.exit()
            self.disp.update(self.terr, self.agent_population,
                             self.plant_population, self.agent_map,
                             self.plant_map, self.energy_map, self.time,
                             len(self.minds), self.show_energy,
                             self.show_agents)
            
            # test for spacebar pressed - if yes, restart
            for event in pygame.event.get(pygame.locals.KEYUP):
                if event.key == pygame.locals.K_SPACE:
                    self.winner = -1
            if pygame.event.get(pygame.locals.QUIT):
                sys.exit()
            pygame.event.pump()
            self.disp.flip()

        self.run_agents()
        self.run_plants()
        for msg in self.messages:
            msg.update()
        self.time += 1
        self.tic = time.time()
        self.clock.tick()
        if self.time % 100 == 0:
            print 'FPS: %f' % self.clock.get_fps()


class MapLayer(object):
    def __init__(self, size, val=0, valtype=numpy.object_):
        self.size = self.width, self.height = size
        self.values = numpy.empty(size, valtype)
        self.values.fill(val)

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
    def set_random(self, range, symmetric = True):
        self.values = terrain_generator().create_random(self.size, range, 
                                                        symmetric)

    def set_streak(self, range, symmetric = True):
        self.values = terrain_generator().create_streak(self.size, range,
                                                        symmetric)

    def set_simple(self, range, symmetric = True):
        self.values = terrain_generator().create_simple(self.size, range,
                                                        symmetric)
    
    def set_perlin(self, range, symmetric = True):
        self.values = terrain_generator().create_perlin(self.size, range,
                                                        symmetric)


    def change(self, x, y, val):
        self.values[x, y] += val


class ObjectMapLayer(MapLayer):
    def __init__(self, size):
        MapLayer.__init__(self, size, None, numpy.object_)
        self.surf = pygame.Surface(size)
        self.surf.set_colorkey((0,0,0))
        self.surf.fill((0,0,0))
        self.pixels = None
#        self.pixels = pygame.PixelArray(self.surf)

    def lock(self):
        self.pixels = pygame.surfarray.pixels2d(self.surf)

    def unlock(self):
        self.pixels = None

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

    def set(self, x, y, val):
        MapLayer.set(self, x, y, val)
        if val is None:
            self.pixels[x][y] = 0
#            self.surf.set_at((x, y), 0)
        else:
            self.pixels[x][y] = val.color
#            self.surf.set_at((x, y), val.color)


# Use Cython version of get_small_view_fast if available.
# Otherwise, don't bother folks about it.
try:
    import cells_helpers
    import types
    ObjectMapLayer.get_small_view_fast = types.MethodType(
        cells_helpers.get_small_view_fast, None, ObjectMapLayer)
except ImportError:
    pass

TEAM_COLORS = [(255, 0, 0), (255, 255, 255), (255, 0, 255), (255, 255, 0)]
TEAM_COLORS_FAST = [0xFF0000, 0xFFFFFF, 0xFF00FF, 0xFFFF00]

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
        self.color = TEAM_COLORS_FAST[team % len(TEAM_COLORS_FAST)]
        self.act = self.mind.act
    def __str__(self):
        return "Agent from team %i, energy %i" % (self.team,self.energy)
    def attack(self, other, offset = 0, contested = False):
        if not other:
            return False
        max_power = ATTACK_POWER + ATTACK_TERR_CHANGE * offset
        if contested:
            other.energy -= min(self.energy, max_power)
        else:
            other.energy -= max_power
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

# Actions available to an agent on each turn.
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
    def __init__(self, me, agent_views, plant_views, terr_map, energy_map):
        self.agent_views = agent_views
        self.plant_views = plant_views
        self.energy_map = energy_map
        self.terr_map = terr_map
        self.me = me

    def get_me(self):
        return self.me

    def get_agents(self):
        return self.agent_views

    def get_plants(self):
        return self.plant_views

    def get_terr(self):
        return self.terr_map
    
    def get_energy(self):
        return self.energy_map


class Display(object):
    black = (0, 0, 0)
    red = (255, 0, 0)
    green = (0, 255, 0)
    yellow = (255, 255, 0)

    def __init__(self, size, scale=2):
        self.width, self.height = size
        self.scale = scale
        self.size = (self.width * scale, self.height * scale)
        pygame.init()
        self.screen  = pygame.display.set_mode(self.size)
        self.surface = self.screen
        pygame.display.set_caption("Cells")

        self.background = pygame.Surface(self.screen.get_size())
        self.background = self.background.convert()
        self.background.fill((150,150,150))

        self.text = []

    if pygame.font:
        def show_text(self, text, color, topleft):
            font = pygame.font.Font(None, 24)
            text = font.render(text, 1, color)
            textpos = text.get_rect()
            textpos.topleft = topleft
            self.text.append((text, textpos))
    else:
        def show_text(self, text, color, topleft):
            pass

    def update(self, terr, pop, plants, agent_map, plant_map, energy_map,
               ticks, nteams, show_energy, show_agents):
        # Slower version:
        # img = ((numpy.minimum(150, 20 * terr.values) << 16) +
        #       ((numpy.minimum(150, 10 * terr.values + 10.energy_map.values)) << 8))
         
        r = numpy.minimum(150, 20 * terr.values)
        r <<= 16

#        g = numpy.minimum(150, 10 * terr.values + 10 * energy_map.values)
        if show_energy:
            g = terr.values + energy_map.values
            g *= 10
            g = numpy.minimum(150, g)
            g <<= 8

        img = r
        if show_energy:
            img += g
 #       b = numpy.zeros_like(terr.values)

        img_surf = pygame.Surface((self.width, self.height))
        pygame.surfarray.blit_array(img_surf, img)
        if show_agents:
            img_surf.blit(agent_map.surf, (0,0))
        img_surf.blit(plant_map.surf, (0,0))

        scale = self.scale
        pygame.transform.scale(img_surf,
                               self.size, self.screen)
        if not ticks % 60:
            #todo: find out how many teams are playing
            team_pop = [0] * nteams

            for team in xrange(nteams):
                team_pop[team] = sum(1 for a in pop if a.team == team)

            self.text = []
            drawTop = 0
            for t in xrange(nteams):
                drawTop += 20
                self.show_text(str(team_pop[t]), TEAM_COLORS[t], (10, drawTop))

        for text, textpos in self.text:
            self.surface.blit(text, textpos)

    def flip(self):
        pygame.display.flip()


class Plant(object):
    color = 0x00FF00
 
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
            mind_list = [(n,get_mind(n)) for n in sys.argv[1:] ]
    except (ImportError, IndexError):
        pass


if __name__ == "__main__":
    main()
    while True:
        game = Game(bounds, mind_list, symmetric, -1)
        while game.winner is None:
            game.tick()
