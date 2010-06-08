#
# Copyright (c) 2010, Benjamin C. Meyer <ben@meyerhome.net>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Benjamin Meyer nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

#
#  Idea:
#  Keep track of how long we have been alive relative to our plant.
#  The more time has past, the farther away we will go on a rescue mission and
#  the more energy we will gather before heading out
#
#  Result:
#  strong cells have a good chance of making it to another plant where there
#  are many attacks one after another causing the battle line to shift to a plant
#
#  At the start (weak) cells goto closer attacks and not far away
#  At the end (strong) cells are sent straight to the (far away) attacking area
#

import random, cells
import cmath, numpy

class Type:
  PARENT  = 0
  SCOUT   = 1

class MessageType:
    ATTACK     = 0
    FOUNDPLANT = 1

class AgentMind:
  def __init__(self, args):
    self.id = 0
    self.time = 0

    self.type = Type.SCOUT
    # scout vars
    self.x = None
    self.y = None
    self.search = (random.random() > 0.9) # AKA COW, mostly just go and eat up the world grass so the other team can't
    self.last_pos = (-1,-1)
    self.bumps = 0
    self.step = 0
    self.rescue = None
    # parent vars
    self.children = 0
    self.plant = None
    self.plants = []
    if args:
        parent = args[0]
        self.time = parent.time
        self.plants = parent.plants
        if len(self.plants) > 7:
            self.id = random.randrange(0,1)
        if parent.search:
            self.search = (random.random() > 0.2)
    pass

  def choose_new_direction(self, view, msg):
    me = view.get_me()
    self.x = random.randrange(-9,9)
    self.y = random.randrange(-9,9)
    if self.x == 0 and self.y == 0:
        self.choose_new_direction(view, msg)
    self.step = 3
    self.bumps = 0

  def act_scout(self, view, msg):
    me = view.get_me()
    if self.x is None:
        self.choose_new_direction(view, msg)

    currentEnergy = view.get_energy().get(me.x, me.y)

    # Grabbing a plant is the most important thing, we get this we win
    plants = view.get_plants()
    if plants :
        plant = (plants[0]).get_pos()
        if plant != self.plant:
            if self.plants.count(plant) == 0:
                #print "Found a new plant, resetting time: " + str(len(self.plants))
                msg.send_message((MessageType.FOUNDPLANT, 0, self.id, me.x, me.y))
                self.plants.append(plant)
                self.time = 0
            self.plant = plant
            self.type = Type.PARENT
            self.search = None
            #print str(len(self.plants)) + " " + str(me.get_team())
            return self.act_parent(view, msg)
    else:
        # Don't let this go to waste
        if currentEnergy >= 3:
            return cells.Action(cells.ACT_EAT)

    if self.search:
        if me.energy > 100:
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return cells.Action(cells.ACT_SPAWN, (me.x + spawn_x, me.y + spawn_y, self))
        if (currentEnergy > 3) :
            return cells.Action(cells.ACT_EAT)

    # Make sure we wont die
    if (me.energy < 25 and currentEnergy > 1) :
        return cells.Action(cells.ACT_EAT)

    # hit world wall, bounce back
    map_size = view.energy_map.width
    if me.x <= 0 or me.x >= map_size-1 or me.y <= 0 or me.y >= map_size-1 :
        self.choose_new_direction(view, msg)

    # If I get the message of help go and rescue!
    if self.step == 0 and (not self.search) and (random.random()>0.2):
        ax = 0;
        ay = 0;
        best = 300 + self.time / 2
        message_count = len(msg.get_messages());
        for m in msg.get_messages():
            (type, count, id, ox, oy) = m
            if (id == self.id and type == MessageType.ATTACK) :
                dist = abs(me.x-ax) + abs(me.y-ay)
                if count >= 2:
                    dist /= count
                if dist < best and dist > 1:
                    ax = ox
                    ay = oy
                    best = dist
        if (ax != 0 and ay != 0) :
            dir = ax-me.x + (ay - me.y) * 1j
            r, theta = cmath.polar(dir)
            theta += 0.1 * random.random() - 0.5
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
                self.x = random.randrange(-2, 2)
                self.y = random.randrange(-2, 2)

            self.step = random.randrange(1, min(30, max(2,int((best+2)/2))))
            self.rescue = True

    if not self.rescue and me.energy > cells.SPAWN_MIN_ENERGY and me.energy < 100:
        spawn_x, spawn_y = self.smart_spawn(me, view)
        return cells.Action(cells.ACT_SPAWN,(me.x + spawn_x, me.y + spawn_y, self))

    # Back to step 0 we can change direction at the next attack.
    if self.step:
        self.step -= 1

    return self.smart_move(view, msg)

  def get_available_space_grid(self, me, view):
    grid = numpy.ones((3,3))
    grid[1,1] = 0
    for agent in view.get_agents():
      grid[agent.x - me.x + 1, agent.y - me.y + 1] = 0
    for plant in view.get_plants():
      grid[plant.x - me.x + 1, plant.y - me.y + 1] = 0
    return grid

  def smart_move(self, view, msg):
    me = view.get_me()

    # make sure we can actually move
    if me.get_pos() == self.last_pos:
      self.bumps += 1
    else:
      self.bumps = 0
    if self.bumps >= 2:
        self.choose_new_direction(view, msg)
    self.last_pos = view.me.get_pos()

    offsetx = 0
    offsety = 0
    if self.search:
        offsetx = random.randrange(-1, 1)
        offsety = random.randrange(-1, 1)

    wx = me.x + self.x + offsetx
    wy = me.y + self.y + offsety

    grid = self.get_available_space_grid(me, view)

    bestEnergy = 2
    bestEnergyX = -1
    bestEnergyY = -1

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
            e = view.get_energy().get(me.x + x-1, me.y + y-1)
            if e > bestEnergy:
                bestEnergy = e;
                bestEnergyX = x
                bestEnergyY = y;

    # Check the desired location first
    if (wx <  me.x) : bx = 0
    if (wx == me.x) : bx = 1
    if (wx >  me.x) : bx = 2
    if (wy <  me.y) : by = 0
    if (wy == me.y) : by = 1
    if (wy >  me.y) : by = 2
    if bx == bestEnergyX and bestEnergy > 1:
        return cells.Action(cells.ACT_MOVE,(me.x + bestEnergyX-1, me.y + bestEnergyY-1))
    if by == bestEnergyY and bestEnergy > 1:
        return cells.Action(cells.ACT_MOVE,(me.x + bestEnergyX-1, me.y + bestEnergyY-1))

    if grid[bx,by]:
        return cells.Action(cells.ACT_MOVE,(wx, wy))

    if bestEnergy > 1:
        return cells.Action(cells.ACT_MOVE,(me.x + bestEnergyX-1, me.y + bestEnergyY-1))

    if grid[2,0] and random.random() > 0.5:
        return cells.Action(cells.ACT_MOVE,(me.x + 1, me.y - 1))

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
            return cells.Action(cells.ACT_MOVE,(x-1, y-1))
    return cells.Action(cells.ACT_MOVE,(wx, wy))

  def smart_spawn(self, me, view):
    grid = self.get_available_space_grid(me, view)

    # So we don't always spawn in our top left
    if grid[2,0] and random.random() > 0.8:
        return (1, -1)

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
          return (x-1, y-1)
    return (-1, -1)

  def should_attack(self, view, msg):
        me = view.get_me()
        count = 0
        for a in view.get_agents():
            if a.get_team() != me.get_team():
                count += 1
        if count > 0:
            currentEnergy = view.get_energy().get(me.x, me.y)
            if currentEnergy > 20:
                return cells.Action(cells.ACT_EAT)
            if self.plant:
                count = 10
            msg.send_message((MessageType.ATTACK, count, self.id, me.x, me.y))
            return cells.Action(cells.ACT_ATTACK, a.get_pos())
        return None

  def check(self, x, y, view):
    plant_pos = (px, py) = self.plant
    me = view.get_me()
    oldx = x
    oldy = y
    x += me.x
    y += me.y
    # Make sure the plant is always populated
    grid = self.get_available_space_grid(me, view)
 
    if abs(px - x) <= 1 and abs(py - y) <= 1:
        grid = self.get_available_space_grid(me, view)
        if grid[oldx+1, oldy+1] == 1:
            #print str(x) + " " + str(y) + " " + str(abs(px - x)) + " " + str(abs(py - y))
            return True
    return None

  def act_parent(self, view, msg):
    me = view.get_me()
    plant_pos = (px, py) = self.plant

    # Make sure the plant is always populated
    grid = self.get_available_space_grid(me, view)
    xoffset = -2
    yoffset = -2
    if self.check( 1,  0, view):  xoffset = 1;  yoffset = 0;  # right
    if self.check(-1,  0, view):  xoffset = -1; yoffset = 0;  # left
    if self.check( 0,  1, view):  xoffset = 0;  yoffset = 1;  # down
    if self.check( 0, -1, view):  xoffset = 0;  yoffset = -1; # up
    if self.check( -1, -1, view): xoffset = -1; yoffset = -1; # diag left
    if self.check( -1, 1, view):  xoffset = -1; yoffset = 1; # diag right
    if self.check( 1, -1, view):  xoffset = 1;  yoffset = -1;  # diag left
    if self.check( 1, 1, view):   xoffset = 1;  yoffset = 1;  # diag right
    if xoffset != -2:
        if me.energy < cells.SPAWN_MIN_ENERGY : return cells.Action(cells.ACT_EAT)
        # When we are populating plant cells we must spawn some children in case we are being attacked
        # When we are all alone we don't spawn any cheap children and only do high quality cells
        self.children += 1
        return cells.Action(cells.ACT_SPAWN, (me.x + xoffset, me.y + yoffset, self))

    # When there are more then two plants always charge up and then leave
    # when there are less then two plants only half of the cells should charge up and then leave
    if self.children <= 0:
        if me.energy >= cells.ENERGY_CAP or me.energy > cells.SPAWN_MIN_ENERGY + self.time + random.randrange(-10,100):
            self.type = Type.SCOUT
            return self.act_scout(view, msg)
        return cells.Action(cells.ACT_EAT)

    if me.energy < cells.SPAWN_MIN_ENERGY :
        return cells.Action(cells.ACT_EAT)
    self.children -= 1
    spawn_x, spawn_y = self.smart_spawn(me, view)
    return cells.Action(cells.ACT_SPAWN,(me.x + spawn_x, me.y + spawn_y, self))

  def act(self, view, msg):
    self.time += 1
    r = self.should_attack(view, msg)
    if r: return r

    if self.type == Type.PARENT:
        return self.act_parent(view, msg)
    if self.type == Type.SCOUT:
        return self.act_scout(view, msg)
