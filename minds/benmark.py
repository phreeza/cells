#
#  Benjamin C. Meyer, improved by Mark O'Connor
#
#  Overall rules:
#  Agents at plants reproduce as much as possible
#  Agents are born with a random direction away from the plant
#  Agents send a message with they attack
#  Agents love to eat and reproduce (this is really brutal in long battles)
#  Agents always attack
#  Agents go to the location of the attack, exception scouts that keep looking
#  After a while the AI gets bored and rushes the enemy. Then it rests for a 
#  while and tries again.
#
#  Results
#  Grab plants quickly without being distracted by nearby enemies
#  Quickly convert battlefields into huge swarms of our cells
#  Once we think we've done enough expanding, make a concerted push at the enemy
#  Relax this after gaining some ground and build up more forces before a final push
#  Obliterates the standard AIs, ben and benvolution
#
#  There is clearly a lot of room for improvement in plant finding, battle tactics
#  and energy management.

import random, cells, numpy
from math import sqrt

armageddon_declared = False

class MessageType:
  ATTACK = 0

class AgentMind:
  def __init__(self, parent_args):
    if parent_args == None: # initial instance
        self.game_age = 0
    else:
        self.game_age = parent_args[0].game_age
    # The direction to walk in
    self.x = random.randrange(-3,4)
    self.y = random.randrange(-3,4)
    # Don't come to the rescue, continue looking for plants & bad guys
    self.scout = random.randrange(0, self.game_age+1) < 200
    # Once we are attacked (mainly) those reproducing at plants should eat up a defense
    self.defense = 0
    # Don't have everyone walk on the same line to 1) eat as they walk and 2) find still hidden plants easier
    self.step = 0
    self.age = 0
    # reproduce for at least X children at a plant before going out and attacking
    self.children = 0
    self.my_plant = None
    self.bumps = 0
    self.last_pos = (-1, -1)

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
    return (random.randrange(-1, 2), random.randrange(-1, 2))

  def act(self, view, msg):
      ret = self.act_wrapper(view, msg)
      self.last_pos = view.me.get_pos()
      return ret

  def act_wrapper(self, view, msg):
    global armageddon_declared
    me = view.get_me()
    my_pos = (mx,my) = me.get_pos()
    # after a while, armageddon!
    self.age += 1
    self.game_age += 1
    bored = (view.energy_map.width+view.energy_map.height)
    if self.game_age > bored and self.game_age <= bored*2 or self.game_age > bored*2.5:
        self.scout = False
        if not armageddon_declared:
            print "Mark declares armageddon!"
            armageddon_declared = True
    if self.game_age > bored*2 and self.game_age < bored*2.5 and armageddon_declared: 
        print "Mark calls armageddon off..."
        armageddon_declared = False

    # Attack anyone next to me, but first send out the distress message with my position
    for a in view.get_agents():
      if a.get_team() != me.get_team():
        msg.send_message((MessageType.ATTACK, mx,my))
        return cells.Action(cells.ACT_ATTACK, a.get_pos())

    # Eat any energy I find until I am 'full'
    if view.get_energy().get(mx, my) > 0:
        if (me.energy < 50):
            return cells.Action(cells.ACT_EAT)
        if (me.energy < self.defense):# and (random.random()>0.1)):
           return cells.Action(cells.ACT_EAT)

    # If there is a plant near by go to it and spawn all I can
    if not self.my_plant:
        plants = view.get_plants()
        if plants:
            self.my_plant = plants[0]
    if self.my_plant:
        spawn_x, spawn_y = self.smart_spawn(me, view)
        return cells.Action(cells.ACT_SPAWN, (me.x + spawn_x, me.y + spawn_y, self))

    if me.energy > 50 or (armageddon_declared and me.energy > 400):
        spawn_x, spawn_y = self.smart_spawn(me, view)
        return cells.Action(cells.ACT_SPAWN, (me.x + spawn_x, me.y + spawn_y, self))

    # If I get the message of help go and rescue!
    if (self.step == 0 and (random.random()>0.2)) :
        ax = 0;
        ay = 0;
        best = view.energy_map.width*view.energy_map.height;
        message_count = len(msg.get_messages());
        for m in msg.get_messages():
            (t, ox,oy) = m
            if (t == MessageType.ATTACK):
                dx = mx-ox
                dy = my-oy
                dist = dx*dx+dy*dy
                if dist < best:
                    ax = ox
                    ay = oy
                    best = dist
        if ax != 0 and ay != 0 and (not self.scout or best < min(self.game_age, (view.energy_map.width/8)**2)):
            self.defense = 2000
            self.x = ax - mx
            self.y = ay - my
            if (message_count > 1) :
                # Attack the base, not the front
                agent_offset = random.randrange(1, view.energy_map.width/6)
                if (self.x > 0) :
                    self.x += agent_offset
                else :
                    self.x -= agent_offset
                if (self.y > 0) :
                    self.y += agent_offset
                else :
                    self.y -= agent_offset
                # don't all aim directly at the target
                roam = int(sqrt(best))
                if roam > 1:
                    self.x += random.randrange(-roam, roam+1)
                    self.y += random.randrange(-roam, roam+1)
            # Don't stand still once we get there
            if (self.x == 0 and self.y == 0) :
                self.x = random.randrange(-3, 4)
                self.y = random.randrange(-3, 4)
            self.step = random.randrange(3, 30)

    # don't get stuck and die 
    if self.bumps >= 2:
        self.x = random.randrange(-3,4)
        self.y = random.randrange(-3,4)
        self.bumps = 0

    # hit world wall
    if (mx == 0 or mx == view.energy_map.width-1):
        self.scout = False
        self.x *= -1
        self.bumps = 0
    if (my == 0 or my == view.energy_map.height-1):
        self.scout = False
        self.y *= -1
        self.bumps = 0

    # Back to step 0 we can change direction at the next attack
    if (self.step > 0):
        self.step -= 1;

    # Move quickly randomly in my birth direction
    return cells.Action(cells.ACT_MOVE,(mx+self.x+random.randrange(-1,2),my+self.y+random.randrange(-1,2)))
