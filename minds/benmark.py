#
#  Benjamin C. Meyer
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

import random, cells

class MessageType:
  ATTACK = 0

class AgentMind:
  def __init__(self, args):
    # The direction to walk in
    self.x = random.randrange(-3,3)
    self.y = random.randrange(-3,3)
    # Don't come to the rescue, continue looking for plants & bad guys
    self.scout = (random.random() > 0.9)
    # Once we are attacked (mainly) those reproducing at plants should eat up a defense
    self.defense = 0
    # Don't have everyone walk on the same line to 1) eat as they walk and 2) find still hidden plants easier
    self.step = 0
    # reproduce for at least X children at a plant before going out and attacking
    self.children = 0
    self.my_plant = None
    pass

  def act(self, view, msg):
    me = view.get_me()
    my_pos = (mx,my) = me.get_pos()

    # Attack anyone next to me, but first send out the distress message with my position
    for a in view.get_agents():
      if (a.get_team() != me.get_team()):
        msg.send_message((MessageType.ATTACK, mx,my))
        if (me.energy > 2000) :
            return cells.Action(cells.ACT_SPAWN,(mx+random.randrange(-5,5),my+random.randrange(-5,5), self))
        return cells.Action(cells.ACT_ATTACK, a.get_pos())

    # Eat any energy I find until I am 'full'
    if (view.get_energy().get(mx, my) > 0) :
        if (me.energy < 50) :
            return cells.Action(cells.ACT_EAT)
        if (me.energy < self.defense and (random.random()>0.3)):
           return cells.Action(cells.ACT_EAT)

    # If there is a plant near by go to it and spawn all I can
    if (not self.my_plant) :
        plants = view.get_plants()
        if (len(plants) > 0) :
            self.my_plant = plants[0];
    if (self.my_plant and (self.children < 50 or random.random()>0.9)):
        self.children += 1;
        return cells.Action(cells.ACT_SPAWN,(mx+random.randrange(-5,5),my+random.randrange(-5,5), self))

    # If I get the message of help go and rescue!
    if (self.step == 0 and True != self.scout and (random.random()>0.2)) :
        ax = 0;
        ay = 0;
        best = 1000;
        message_count = len(msg.get_messages());
        for m in msg.get_messages():
            (type, ox,oy) = m
            if (type == MessageType.ATTACK) :
                dist = max(abs(mx-ax),abs(my-ay))
                if dist < best:
                    ax = ox
                    ay = oy
                    best = dist
        if (ax != 0 and ay != 0) :
            self.defense = 2000
            self.x = ax - mx
            self.y = ay - my
            if (message_count > 1) :
                # Attack the base, not the front
                agent_offset = random.randrange(1, 50)
                if (self.x > 0) :
                    self.x += agent_offset
                else :
                    self.x -= agent_offset
                if (self.y > 0) :
                    self.y += agent_offset
                else :
                    self.y -= agent_offset
            # Don't stand still once we get there
            if (self.x == 0 and self.y == 0) :
                self.x = 1
            self.step = random.randrange(3, 10);
 
    # hit world wall
    if (mx == 0 or mx == 299) :
        self.x = random.randrange(-1,1)
    if (my == 0 or my == 299) :
        self.y = random.randrange(-1,1)

    # Back to step 0 we can change direction at the next attack
    if (self.step > 0):
        self.step -= 1;

    # Move quickly randomly in my birth direction
    return cells.Action(cells.ACT_MOVE,(mx+self.x+random.randrange(-1,1),my+self.y+random.randrange(-1,1)))
