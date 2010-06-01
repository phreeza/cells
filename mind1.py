import random,cells

class AgentMind:
  def __init__(self):
    self.my_plant = None
    self.mode = 1
    self.target_range = random.randrange(50,1000)
    pass

  def act(self,view,msg):
    x_sum = 0
    y_sum = 0
    dir = 1
    n = len(view.get_plants())
    me = view.get_me()
    mp = (mx,my)= me.get_pos()

    for a in view.get_agents():
      if (a.get_team()!=me.get_team()):
        return cells.Action(cells.ActionType.ATTACK,a.get_pos())

    if(n>0):
      if (not self.my_plant):
        self.my_plant = view.get_plants()[0]
      elif self.my_plant.get_eff()<view.get_plants()[0].get_eff():
        self.my_plant = view.get_plants()[0]

    if (((me.energy < self.target_range) and (view.get_energy().get(mx, my) > 0)) 
        or (view.get_energy().get(mx, my) > 100)) :
      return cells.Action(cells.ActionType.EAT)

    if self.my_plant:
      dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
      if not me.loaded and dist < 5 and random.random() > 0.5:
        return cells.Action(cells.ActionType.LIFT)
      if me.loaded and dist > 5:
        return cells.Action(cells.ActionType.DROP)
      if view.get_me().energy < dist*1.5:
        (mx,my) = self.my_plant.get_pos()
        return cells.Action(cells.ActionType.MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))

    if (random.random()>0.9):
      return cells.Action(cells.ActionType.SPAWN,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
    else:
      return cells.Action(cells.ActionType.MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
