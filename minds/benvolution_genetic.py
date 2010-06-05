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

import cmath
import random, cells

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


class AgentMind(object):
    def __init__(self, args):
        # The direction to walk in
        self.x = None
        # Once we are attacked (mainly) those reproducing at plants should eat up a defense.
        self.defense = 0

        self.step = 0
        self.my_plant = None
        self.bumps = 0
        self.last_pos = (-1, -1)
        self.apoptosis = random.randrange(100, 201)

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
            if parent.my_plant:
                self.scout = (random.random() > 0.9)
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
            return random.choice(ret)
        return (-1, -1)

    def would_bump(self, me, view, dir_x, dir_y):
        grid = self.get_available_space_grid(me, view)
        dx = numpy.sign(dir_x)
        dy = numpy.sign(dir_y)
        adj_dx = dx + 1
        adj_dy = dy + 1
        return grid[adj_dx,adj_dy] == 0


    def act(self, view, msg):
        ret = self.act_wrapper(view, msg)
        self.last_pos = view.me.get_pos()
        return ret

    def act_wrapper(self, view, msg):
        me = view.get_me()
        my_pos = (mx,my) = me.get_pos()
        if my_pos == self.last_pos:
            self.bumps += 1
        else:
            self.bumps = 0

        if self.x is None:
            self.x = random.randrange(view.energy_map.width) - me.x
            self.y = random.randrange(view.energy_map.height) - me.y

        if self.apoptosis <= 0:
            return cells.Action(cells.ACT_MOVE, (0, 0))

        # Attack anyone next to me, but first send out the distress message with my position
        for a in view.get_agents():
            if (a.get_team() != me.get_team()):
                msg.send_message((self.strain, MessageType.ATTACK, mx,my))
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # Eat any energy I find until I am 'full'. The cost of eating
        # is 1, so don't eat just 1 energy.
        if self.my_plant is None and view.get_energy().get(mx, my) > 1:
            if me.energy <= self.genes['desired_energy'].val:
                return cells.Action(cells.ACT_EAT)
            else:
                debug('Not eating. Have %s which is above %s' %
                      (me.energy, self.genes['desired_energy'].val))
            if (me.energy < self.defense and (random.random()>0.3)):
                return cells.Action(cells.ACT_EAT)


        # If there is a plant near by go to it and spawn all I can
        if self.my_plant is None :
            plants = view.get_plants()
            if plants:
                self.my_plant = plants[0]
                self.x = self.y = 0
                self.strain = self.my_plant.x * 41 + self.my_plant.y
                debug('attached to plant, strain %s' % self.strain)
        else:
            self.apoptosis -= 1
            if self.apoptosis <= 0:
                self.my_plant = None
                return cells.Action(cells.ACT_RELEASE, (mx + 1, my, me.energy - 1))
            

        if self.my_plant is None:
            spawn_threshold = self.genes['field_spawn_energy'].val
        else:
            spawn_threshold = self.genes['plant_spawn_energy'].val
        if me.energy >= spawn_threshold:
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return cells.Action(cells.ACT_SPAWN,
                                (me.x + spawn_x, me.y + spawn_y, self))
        elif self.my_plant:
            return cells.Action(cells.ACT_EAT)

        
        # If I get the message of help go and rescue!
        if not self.step and not self.scout and random.random() > 0.1:
            ax = 0;
            ay = 0;
            best = 500;
            message_count = len(msg.get_messages());
            for m in msg.get_messages():
                (strain, type, ox,oy) = m
                if strain != self.strain:
                    continue
                if (type == MessageType.ATTACK) :
                    dist = max(abs(mx-ax), abs(my-ay))
                    if dist < best:
                        ax = ox
                        ay = oy
                        best = dist
            if ax and ay:
                self.defense = 200
                dir = ax-mx + (ay - my) * 1j
                r, theta = cmath.polar(dir)
                theta += 0.02 * random.random() - 0.5
                dir =  cmath.rect(r, theta)
                self.x = dir.real
                self.y = dir.imag
                # if (message_count > 1) :
                #     # Attack the base, not the front
                #     agent_scale = 1 + random.random()
                #     self.x *= agent_scale
                #     self.y *= agent_scale
                # don't stand still once we get there
                if (self.x == 0 and self.y == 0) :
                    self.x = random.randrange(-1, 2)
                    self.y = random.randrange(-1, 2)
                self.step = random.randrange(20, 100);

        if self.bumps >= 2:
            self.x = random.randrange(-3,4)
            self.y = random.randrange(-3,4)
            self.bumps = 0


        # hit world wall
        map_size = view.energy_map.width
        if (mx == 0 or mx == map_size-1) :
            self.x = random.randrange(-1,2)
        if (my == 0 or my == map_size-1) :
            self.y = random.randrange(-1,2)

        # Back to step 0 we can change direction at the next attack.
        if self.step:
            self.step -= 1

        return cells.Action(cells.ACT_MOVE,(mx+self.x,my+self.y))
