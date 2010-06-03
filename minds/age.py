#
#  Benjamin C. Meyer <ben@meyerhome.net>
#
#  Idea:
#  Keep track of how long we have been alive relative to our plant.
#  The more time has past, the farther away we will go on a rescue mission and
#  the more energy we will gather before heading out
#
#  Also a new parent idea where cells parallel to the plant stay forever and
#  spawn children.  The corners are reserved for charging
#
#  Also eat the dead keeping our strength
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
    ATTACK = 0

class AgentMind:
  def __init__(self, args):
    self.time = 0

    self.type = Type.SCOUT
    # scout vars
    self.x = None
    self.y = None
    self.search = (random.random() > 0.9)
    self.last_pos = (-1,-1)
    self.bumps = 0
    self.step = 0
    # parent vars
    self.plant = None
    self.plants = []
    if args and args[0]:
        self.time = args[0].time
        self.plants = args[0].plants
    pass

  def choose_new_direction(self, view, msg):
    me = view.get_me()
    self.x = random.randrange(view.energy_map.width) - me.x
    self.y = random.randrange(view.energy_map.height) - me.y
    self.x = random.randrange(-3,3)
    self.y = random.randrange(-3,3)
    self.bumps = 0

  def act_scout(self, view, msg):
    me = view.get_me()
    if me.get_pos() == self.last_pos:
      self.bumps += 1
    else:
      self.bumps = 0
    if self.x is None:
        self.choose_new_direction(view, msg)

    # Grabbing a plant is the most important thing, we get this we win
    plants = view.get_plants()
    if plants :
        plant = (plants[0]).get_pos()
        if plant != self.plant:
            #if self.plants.count(plant) == 0:
            self.plants.append(plant)
            self.plant = plant
            self.type = Type.PARENT
            self.time = 0
            #print str(len(self.plants)) + " " + str(me.get_team())
            return self.act_parent(view, msg)

    # Don't let this go to waste
    if (view.get_energy().get(me.x, me.y) >= 10) :
        return cells.Action(cells.ACT_EAT)

    if (self.search and me.energy > 50):
        spawn_x, spawn_y = self.smart_spawn(me, view)
        if (spawn_x != -1 and spawn_y != -1):
            return cells.Action(cells.ACT_SPAWN, (me.x + spawn_x, me.y + spawn_y, self))

    # Make sure we wont die
    if (me.energy < 25 and view.get_energy().get(me.x, me.y) > 1) :
        return cells.Action(cells.ACT_EAT)

    if self.bumps >= 2:
        self.choose_new_direction(view, msg)

    # hit world wall, bounce back
    map_size = view.energy_map.width
    if me.x <= 0 or me.x >= map_size-1 or me.y <= 0 or me.y >= map_size-1 :
        self.choose_new_direction(view, msg)

    # If I get the message of help go and rescue!
    if self.step == 0 and (not self.search) and (random.random()>0.3):
        ax = 0;
        ay = 0;
        best = 250 + self.time
        message_count = len(msg.get_messages());
        for m in msg.get_messages():
            (type, ox,oy) = m
            if (type == MessageType.ATTACK) :
                dist = max(abs(me.x-ax), abs(me.y-ay))
                if dist < best:
                    ax = ox
                    ay = oy
                    best = dist
        if (ax != 0 and ay != 0) :
            self.defense = 200
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
                self.x = random.randrange(-1, 2)
                self.y = random.randrange(-1, 2)
            self.step = random.randrange(5, 30)

    # Back to step 0 we can change direction at the next attack.
    if self.step:
        self.step -= 1

    return self.smart_move(view)

  def get_available_space_grid(self, me, view):
    grid = numpy.ones((3,3))
    for agent in view.get_agents():
      grid[agent.x - me.x + 1, agent.y - me.y + 1] = 0
    for plant in view.get_plants():
      grid[plant.x - me.x + 1, plant.y - me.y + 1] = 0
    grid[1,1] = 0
    return grid

  def smart_move(self, view):
    me = view.get_me()
    offsetx = 0
    offsety = 0
    if self.search:
        offsetx = random.randrange(-5, 5)
        offsety = random.randrange(-5, 5)

    wx = me.x + self.x + offsetx
    wy = me.y + self.y + offsety

    grid = self.get_available_space_grid(me, view)

    # Check the desired location first
    if (wx <  me.x) : bx = 0
    if (wx == me.x) : bx = 1
    if (wx >  me.x) : bx = 2
    if (wy <  me.y) : by = 0
    if (wy == me.y) : by = 1
    if (wy >  me.y) : by = 2
    if grid[bx,by]:
        return cells.Action(cells.ACT_MOVE,(wx, wy))

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
            return cells.Action(cells.ACT_MOVE,(x-1, y-1))
    return cells.Action(cells.ACT_MOVE,(wx, wy))

  def smart_spawn(self, me, view):
    grid = self.get_available_space_grid(me, view)

    # So we don't always spawn in our top left
    if grid[2,0] and random.random() > 0.5:
        return (1, -1)

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
          return (x-1, y-1)
    return (-1, -1)

  def attack(self, view, msg):
    me = view.get_me()
    for a in view.get_agents():
      if a.get_team() != me.get_team():
        msg.send_message((MessageType.ATTACK, me.x,me.y))
        if (me.energy > 100) :
            spawn_x, spawn_y = self.smart_spawn(me, view)
            if (spawn_x != -1 and spawn_y != -1):
                return cells.Action(cells.ACT_SPAWN, (me.x + spawn_x, me.y + spawn_y, self))
        return cells.Action(cells.ACT_ATTACK, a.get_pos())
    return None

  def act_parent(self, view, msg):
    me = view.get_me()
    plant_pos = (px, py) = self.plant

    # First make sure I can reproduce
    if (me.energy < 50) :
        return cells.Action(cells.ACT_EAT)

    # count how many friends I have
    touching = 0
    for a in view.get_agents():
      if a.get_team() == me.get_team():
        if a.x == px and abs(py - a.y) == 1: touching += 1 # top and bottom
        if a.y == py and abs(px - a.x) == 1: touching += 1 # left and right
        if abs(px - a.x) == 1 and abs(py - a.y) == 1:
            touching += 1

    corner = (me.x != px and me.y != py)

    # if I am not touching two parent spawn one next to me
    if touching < 2:
        xoffset = 0
        yoffset = 0
        if me.x <  px and me.y < py: xoffset = +1 # top left
        if me.x == px and me.y < py: xoffset = +1 # top
        if me.x >  px and me.y < py: yoffset = +1 # top right
        if me.y == py and me.x > px: yoffset = +1 # right
        if me.x >  px and me.y > py: xoffset = -1 # bottom right
        if me.x == px and me.y > py: xoffset = -1 # bottom
        if me.x <  px and me.y > py: yoffset = -1 # bottom left
        if me.y == py and me.x < px: yoffset = -1 # left
        return cells.Action(cells.ACT_SPAWN, (me.x + xoffset, me.y + yoffset, self))

    # Corner station, charge up and then leave
    if (len(self.plants) > 2 and touching == 2 and me.x != px and me.y != py):
        if (me.energy < (25 + self.time)) :
            return cells.Action(cells.ACT_EAT)
        else:
            self.type = Type.SCOUT
            return self.act_scout(view, msg)

    spawn_x, spawn_y = self.smart_spawn(me, view)
    return cells.Action(cells.ACT_SPAWN,(me.x + spawn_x, me.y + spawn_y, self))

  def act(self, view, msg):
      self.time += 1
      ret = self.act_wrapper(view, msg)
      self.last_pos = view.me.get_pos()
      return ret

  def act_wrapper(self, view, msg):
    r = self.attack(view, msg)
    if r: return r

    if self.type == Type.PARENT:
        return self.act_parent(view, msg)
    if self.type == Type.SCOUT:
        return self.act_scout(view, msg)
