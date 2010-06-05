#
#  Benjamin C. Meyer
#  Modified by Scott Wolchok
#
#  Overall rules:
#  Agents at plants reproduce as much as possible
#  Agents are born with a random direction away from the plant
#  Agents send a message with they attack
#  Agents always attack
#  Agents goto the location of the attack, exception scouts that keep looking
#
#  Results
#  Large growing swarm that explores that area for all plants as fast as possible
#  until the enemy is found.  By the time the enemy is found everyone is spread out
#  Once the enemy is found everyone heads in that direction and if there are any
#  plants between the two they are usually taken before they enemy.
#  Once a new plant is reached more are quickly spawned and that plant is overrun
#  From there it is simple attrition
#

import cells

from cells import Action
from cells import ACT_SPAWN, ACT_MOVE, ACT_EAT, ACT_RELEASE, ACT_ATTACK
from cells import ACT_LIFT, ACT_DROP

import cmath
from random import choice, random, randrange

import numpy

from genes import InitializerGene, make_normally_perturbed_gene


DesiredEnergyGene = make_normally_perturbed_gene(5, cells.ATTACK_POWER,
                                                 cells.ENERGY_CAP)
FieldSpawnEnergyGene = make_normally_perturbed_gene(5, cells.SPAWN_MIN_ENERGY,
                                                    cells.ENERGY_CAP)
PlantSpawnEnergyGene = make_normally_perturbed_gene(5, cells.SPAWN_MIN_ENERGY,
                                                    cells.ENERGY_CAP)


def debug(s):
    #print s
    pass

class MessageType(object):
    ATTACK = 0

size = 300 #cells.config.getint('terrain', 'bounds')

class AgentMind(object):
    def __init__(self, args):
        # The direction to walk in
        self.tx = randrange(size)
        self.ty = randrange(size)

        self.step = 0
        self.my_plant = None
        self.apoptosis = randrange(100, 201)

        if args is None:
            self.strain = 0
            self.scout = False
            self.genes = genes = {}
            genes['desired_energy'] = DesiredEnergyGene(
                InitializerGene(2 * cells.SPAWN_MIN_ENERGY))
            genes['field_spawn_energy'] = FieldSpawnEnergyGene(
                InitializerGene(4 * cells.ENERGY_CAP / 5))
            genes['plant_spawn_energy'] = PlantSpawnEnergyGene(
                InitializerGene(2 * cells.SPAWN_MIN_ENERGY))
        else:
            parent = args[0]
            self.strain = parent.strain
            # Don't come to the rescue, continue looking for plants & bad guys.
            self.genes = dict((k, v.spawn()) for (k,v) in parent.genes.iteritems())
            if parent.my_plant is not None:
                self.scout = (random() > 0.9)
            else:
                self.scout = False


    def get_available_space_grid(self, me, view):
        grid = numpy.ones((3,3))
        for agent in view.get_agents():
            grid[agent.x - me.x + 1, agent.y - me.y + 1] = 0
        for plant in view.get_plants():
            grid[plant.x - me.x + 1, plant.y - me.y + 1] = 0
        grid[1,1] = 0
        return grid

    def smart_spawn(self, me, view):
        grid = self.get_available_space_grid(me, view)
        ret = []
        for x in xrange(3):
            for y in range(3):
                if grid[x,y]:
                    ret.append((x-1, y-1))
        if ret:
            return choice(ret)
        return (-1, -1)

    def would_bump(self, me, view, dir_x, dir_y):
        grid = self.get_available_space_grid(me, view)
        dx = numpy.sign(dir_x)
        dy = numpy.sign(dir_y)
        adj_dx = dx + 1
        adj_dy = dy + 1
        return grid[adj_dx,adj_dy] == 0


    def act(self, view, msg):
        me = view.me
        mx = me.x
        my = me.y
        my_pos = mx, my

        tx = self.tx
        ty = self.ty
        if mx == tx and my == ty:
            self.tx = tx = randrange(tx - 5, tx + 6)
            self.ty = ty = randrange(tx - 5, tx + 6)
            self.step = 0


        if self.apoptosis <= 0:
            return Action(ACT_MOVE, (0, 0))

        # Attack anyone next to me, but first send out the distress message with my position
        my_team = me.team
        for a in view.agent_views:
            if a.team != my_team:
                ax = a.y
                ay = a.y
                msg.send_message((self.strain, MessageType.ATTACK, ax, ay))
                return Action(ACT_ATTACK, (ax, ay))

        # Eat any energy I find until I am 'full'. The cost of eating
        # is 1, so don't eat just 1 energy.
        my_energy = me.energy
        if self.my_plant is None and view.energy_map.values[my_pos] > 1:
            if my_energy <= self.genes['desired_energy'].val:
                return Action(ACT_EAT)
#            else:
#                debug('Not eating. Have %s which is above %s' %
#                      (my_energy, self.genes['desired_energy'].val))


        # If there is a plant near by go to it and spawn all I can
        if self.my_plant is None :
            plants = view.get_plants()
            if plants:
                self.my_plant = plants[0]
                self.tx = tx = mx
                self.ty = ty = my
                self.strain = self.my_plant.x * 41 + self.my_plant.y
                debug('attached to plant, strain %s' % self.strain)
        else:
            self.apoptosis -= 1
            if self.apoptosis <= 0:
                self.my_plant = None
                return Action(ACT_RELEASE, (mx + 1, my, my_energy - 1))
            

        if self.my_plant is None:
            spawn_threshold = self.genes['field_spawn_energy'].val
        else:
            spawn_threshold = self.genes['plant_spawn_energy'].val
        if my_energy >= spawn_threshold:
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return Action(ACT_SPAWN,
                                (me.x + spawn_x, me.y + spawn_y, self))
        elif self.my_plant is not None:
            return Action(ACT_EAT)

        
        # If I get the message of help go and rescue!
        if (not self.step) and (not self.scout) and random() > 0.1:
            ax = 0;
            ay = 0;
            best = 500;
            message_count = len(msg.get_messages());
            for strain, type, ox, oy in msg.get_messages():
                if strain != self.strain:
                    continue
                if (type == MessageType.ATTACK) :
                    dist = max(abs(mx-ax), abs(my-ay))
                    if dist < best:
                        ax = ox
                        ay = oy
                        best = dist
            if ax and ay:
                self.tx = tx = ax + randrange(-3, 4)
                self.ty = ty = ay + randrange(-3, 4)
                # if (message_count > 1) :
                #     # Attack the base, not the front
                #     agent_scale = 1 + random()
                #     self.x *= agent_scale
                #     self.y *= agent_scale
                # don't stand still once we get there
                self.step = randrange(20, 100);

        # Back to step 0 we can change direction at the next attack.
        if self.step:
            self.step -= 1

        return Action(ACT_MOVE, (tx, ty))
