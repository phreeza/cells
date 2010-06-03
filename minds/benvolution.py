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

import genes

def signum(x):
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


class MessageType(object):
    ATTACK = 0

class AgentMind(object):
    def __init__(self, args):
        # The direction to walk in
        self.x = None
        # Once we are attacked (mainly) those reproducing at plants should eat up a defense
        self.defense = 0
        # Don't have everyone walk on the same line to 1) eat as they walk and 2) find still hidden plants easier
        self.step = 0
        # reproduce for at least X children at a plant before going out and attacking
        self.my_plant = None
        self.bumps = 0
        self.last_pos = (-1, -1)

        if args is None:
            self.strain = 0
            self.scout = False
        else:
            parent = args[0]
            self.strain = parent.strain
            # Don't come to the rescue, continue looking for plants & bad guys
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
        for x in xrange(3):
            for y in range(3):
                if grid[x,y]:
                    return (x-1, y-1)
        return (-1, -1)

    def would_bump(self, me, view, dir_x, dir_y):
        grid = self.get_available_space_grid(me, view)
        dx = signum(dir_x)
        dy = signum(dir_y)
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
        # Attack anyone next to me, but first send out the distress message with my position
        for a in view.get_agents():
            if (a.get_team() != me.get_team()):
                msg.send_message((self.strain, MessageType.ATTACK, mx,my))
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # Eat any energy I find until I am 'full'. The cost of eating
        # is 1, so don't eat just 1 energy.
        if view.get_energy().get(mx, my) > 1:
            if (me.energy <= 50):
                return cells.Action(cells.ACT_EAT)
            if (me.energy < self.defense and (random.random()>0.3)):
                return cells.Action(cells.ACT_EAT)


        # If there is a plant near by go to it and spawn all I can
        if self.my_plant is None :
            plants = view.get_plants()
            if plants :
                self.my_plant = plants[0]
                self.x = self.y = 0
                self.strain = self.my_plant.x * 41 + self.my_plant.y

        # Current rules don't make carrying around excess energy
        # worthwhile.  Generates a very nice "They eat their
        # wounded?!" effect. Also burns extra energy so the enemy
        # can't use it.
        # Spawning takes 25 of the energy and gives it
        # to the child and reserves the other 25 for the child's death
        # drop. In addition, the action costs 1 unit. Therefore, we
        # can't create energy by spawning...
        if me.energy >= 51:
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return cells.Action(cells.ACT_SPAWN,
                                (me.x + spawn_x, me.y + spawn_y, self))

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
