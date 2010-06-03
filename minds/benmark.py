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

    def get_available_spaces(self, me, view):
        x, y = me.get_pos()
        agents = set((a.x - x, a.y - y) for a in view.get_agents())
        plants = set((p.x - x, p.y - y) for p in view.get_plants())
        my_pos = set((0, 0))
        all = set((x,y) for x in xrange(-1, 2) for y in xrange(-1, 2))
        return all - agents - plants - my_pos

    def smart_spawn(self, me, view):
        free = self.get_available_spaces(me, view)
        if len(free)>0:
            return free.pop()
        else:
            return None

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
        target = next((a for a in view.get_agents() if a.get_team() != me.get_team()), None)
        if target:
            msg.send_message((MessageType.ATTACK, mx, my))
            return cells.Action(cells.ACT_ATTACK, target.get_pos())
    
        # Eat any energy I find until I am 'full'
        if view.get_energy().get(mx, my) > 0:
            if (me.energy < 50):
                return cells.Action(cells.ACT_EAT)
            if (me.energy < self.defense):# and (random.random()>0.1)):
               return cells.Action(cells.ACT_EAT)
    
        # If there is a plant near by go to it and spawn all I can
        if not self.my_plant and len(view.get_plants())>0:
            self.my_plant = view.get_plants()[0]
        if self.my_plant:
            pos = self.smart_spawn(me, view)
            if pos:
                return cells.Action(cells.ACT_SPAWN, (me.x + pos[0], me.y + pos[1], self))
    
        if me.energy > 50 or (armageddon_declared and me.energy > 400):
            pos = self.smart_spawn(me, view)
            if pos:
                return cells.Action(cells.ACT_SPAWN, (me.x + pos[0], me.y + pos[1], self))
    
        # If I get the message of help go and rescue!
        if (self.step == 0 and (random.random()>0.2)) :
            calls_to_arms = [((mx-ox)**2+(my-oy)**2, ox, oy) for t, ox, oy in msg.get_messages() if t == MessageType.ATTACK]
            if len(calls_to_arms)>0:
                best, ox, oy = min(calls_to_arms)
                if not self.scout or best < min(self.game_age, (view.energy_map.width/8)**2):
                    self.defense = 2000
                    self.x = ox - mx
                    self.y = oy - my
                    if (len(calls_to_arms) > 1) :
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
