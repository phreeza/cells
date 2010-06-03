#
# zenergizer.py
#
# Seth Zenz
# Email: cancatenate my first and last names, all lower case, at gmail.com
# June 2, 2010
#
# There is a lot of ugly machinery in this guy, I made him from tinkering 
# around and never cleaned him up completely.  Some of the things he does
# I don't really understand why.  Lost of numbers aren't tuned.
#
# But if you watch him work, you'll see that he demonstrates the value of
# going for the biggest pile of energy around and eating it -- both in
# exploration and in big melees.  This isn't obvious but it works. 
#

import random,cells

class AgentMind:
  def __init__(self, args):

    self.goto_war_at = 500
    self.diffs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    self.mytime = 0 
    self.am_warrior = False
    self.lastattack = (-1,-1,-1)

    if not args:
      self.gen = 0
      self.war_time = -1
      self.startdiff = random.choice(self.diffs)
    else:
      self.gen = args[0]
      self.war_time = args[1]
      self.startdiff = args[2]
    self.target_range = 5
    self.spawn_min = 50
    self.migrate_min = 70

    if ((random.random() < 0.7 and not (self.war_time>0)) or self.gen == 0):
      self.mygoaldir = (0,0)
    else:
      if (self.war_time > 0) and (random.random() > 0.1):
        self.am_warrior = True
        self.mygoaldir = (0,0)
      else:
        self.mygoaldir = self.startdiff
        self.questtime = 0
        self.last_x = 999
        self.last_y = 999
    pass

  def act(self,view,msg):
    me = view.get_me()
    mp = (mx,my)= me.get_pos()

    # If I think it's time to go to war, sound out a message
    if self.mytime > self.goto_war_at and not (self.war_time > 0):
      msg.send_message(("war",self.mytime))

    # personal time counter      
    self.mytime += 1    

    # Interpret war-related messages
    for m in msg.get_messages():
      if m[0] == "war" and not self.am_warrior:
        self.am_warrior = True
        self.war_time = self.mytime
      if m[0] == "attack":
        self.lastattack = (m[1],m[2],self.mytime)

    # Attack nearby enemies.  This always gets done first    
    for a in view.get_agents():
      if (a.get_team()!=me.get_team()):
        msg.send_message(("attack",mx,my))
        return cells.Action(cells.ACT_ATTACK,a.get_pos())

    # Move if at war
    if self.am_warrior and (self.lastattack[2] > self.war_time - 50):
      go = True
      for plant in view.get_plants():
        if (mx == plant.x and abs(my-plant.y) < 2) or (my == plant.y and abs(mx-plant.x) < 2):
          go = False
      if go:
        tx,ty = (self.lastattack[0],self.lastattack[1])
        if mx != self.lastattack[0]: tx += random.randrange(15,40)*(self.lastattack[0]-mx)/abs((self.lastattack[0]-mx))
        if my != self.lastattack[1]: ty += random.randrange(15,40)*(self.lastattack[1]-my)/abs((self.lastattack[1]-my))
        tx += random.randrange(-4,5)
        ty += random.randrange(-4,5)
        return cells.Action(cells.ACT_MOVE,(tx,ty))

    # If very hungry, eat
    if ((me.energy < self.target_range) and (view.get_energy().get(mx, my) > 0)): 
      return cells.Action(cells.ACT_EAT)

    # If on a quest, move.  Stop for nearby goodies or if I couldn't move last time.
    if self.mygoaldir != (0,0):
      self.questtime += 1
      highenergy = False
      for diff in self.diffs:
        tx,ty = mx+diff[0],my+diff[1]
        if (view.get_energy().get(tx,ty) > 200): highenergy = True
      if ((len(view.get_plants()) > 0 or highenergy) and self.questtime > 5) or (mx == self.last_x and my == self.last_y):
        self.mygoaldir = (0,0)
      else:
        self.last_x = mx
        self.last_y = my
        for a in view.get_agents():
          if a.x == mx+self.mygoaldir[0] and a.y == my+self.mygoaldir[1]:
            self.mygoaldir = random.choice(self.diffs) # change destination if blocked
        if random.random() < 0.9:
          return cells.Action(cells.ACT_MOVE,(mx+self.mygoaldir[0],my+self.mygoaldir[1]))
        else:
          return cells.Action(cells.ACT_MOVE,(mx+self.mygoaldir[0]+random.randrange(-1,2),my+self.mygoaldir[1]+random.randrange(-1,2)))

    # Spawn if I have the energy    
    if me.energy > self.spawn_min:
      random.shuffle(self.diffs)
      for diff in self.diffs:
        sx,sy = (mx+diff[0],my+diff[1])
        occupied = False
        for a in view.get_agents():
          if a.x == sx and  a.y == sy:
            occupied = True
            break
        if not occupied:
          return cells.Action(cells.ACT_SPAWN,(sx,sy,self.gen+1,self.war_time,diff))

    # Start a quest if I have the energy and there's no war  
    if me.energy > self.migrate_min and not self.am_warrior:
      self.mygoaldir = random.choice(self.diffs)
      self.questtime = 0
      self.last_x = -999
      self.last_y = -999
      return cells.Action(cells.ACT_MOVE,(mx+self.mygoaldir[0],my+self.mygoaldir[1]))

    # Find the highest energy square I can see.  If I'm there, eat it.  Otherwise move there.
    maxenergy = view.get_energy().get(mx,my)
    fx,fy = (mx,my)
    random.shuffle(self.diffs)
    for diff in self.diffs:
      tx,ty = (mx+diff[0],my+diff[1])
      occupied = False
      for a in view.get_agents():
        if a.x == tx and  a.y == ty:
          occupied = True
          break
      if view.get_energy().get(tx,ty) > maxenergy and not occupied:
        maxenergy = view.get_energy().get(tx,ty)
        fx,fy = (tx,ty)
    if (mx,my) == (fx,fy):
      return cells.Action(cells.ACT_EAT)
    return cells.Action(cells.ACT_MOVE,(fx,fy))
