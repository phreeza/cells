import cells
import genes

import cmath
import math
import random

CallForHelpGene = genes.make_normally_perturbed_gene(0.01)
CallOfDutyGene = genes.make_normally_perturbed_gene(0.01)
DraftDodgerGene = genes.make_normally_perturbed_gene(0.01)
SpawnProbabilityGene = genes.make_normally_perturbed_gene(0.01)
SpawnEnergyThresholdGene = genes.make_normally_perturbed_gene(5, 50, 5000)
ColonizeProbabilityGene = genes.make_normally_perturbed_gene(0.01)

CallTypeGene = genes.make_drastic_mutation_gene(0.01)

class AgentMind:
  def __init__(self, args):
    self.my_plant = None
    self.mode = 1
    self.target_range = random.randrange(50,200)
    if args is None:
      self.call_for_help = CallForHelpGene(genes.InitializerGene(0.25))
      self.call_of_duty = CallOfDutyGene(genes.InitializerGene(0.75))
      self.draft_dodger = DraftDodgerGene(genes.InitializerGene(0.75))
      self.spawn_prob = SpawnProbabilityGene(genes.InitializerGene(0.1))
      self.spawn_energy = SpawnEnergyThresholdGene(genes.InitializerGene(60))
      self.call_type = CallTypeGene(genes.InitializerGene(0))
      self.colonize_prob = ColonizeProbabilityGene(genes.InitializerGene(0.001))
    else:
      parent = args[0]
      self.call_for_help = parent.call_for_help.spawn()
      self.call_of_duty = parent.call_of_duty.spawn()
      self.draft_dodger = parent.draft_dodger.spawn()
      self.spawn_prob = parent.spawn_prob.spawn()
      self.spawn_energy = parent.spawn_energy.spawn()
      self.call_type = parent.call_type.spawn()
      self.colonize_prob = parent.colonize_prob.spawn()

  def _set_target(self, tx, ty):
    self.mode = 5
    tx += random.randrange(-3, 4)
    ty += random.randrange(-3, 4)
    tx = min(max(tx, 0), 300)
    ty = min(max(tx, 0), 300)
    self.target = (tx, ty)

  def act(self,view,msg):
    x_sum = 0
    y_sum = 0
    dir = 1
    n = len(view.get_plants())
    me = view.get_me()
    mp = (mx,my)= me.get_pos()
    for a in view.get_agents():
      if (a.get_team()!=me.get_team()):
        if random.random() > self.call_for_help.val:
          msg.send_message((self.call_type.val, mp))
        return cells.Action(cells.ActionType.ATTACK,a.get_pos())

    for message in msg.get_messages():
      call_type, m = message
      assert isinstance(m, tuple)
      if call_type != self.call_type.val:
        next
      if self.my_plant:
        my_team = me.get_team()
        num_nearby = sum(1 for x in view.get_agents() if x.get_team() == my_team)
        if num_nearby > 1 and random.random() > self.draft_dodger.val:
          self._set_target(*m)
      elif random.random() < self.call_of_duty.val:
        self._set_target(*m)

    if n:
      best_plant = max(view.get_plants(), key=lambda x: x.eff)
      if not self.my_plant or self.my_plant.eff < best_plant.eff:
        self.my_plant = view.get_plants()[0]
        self.mode = 0

    if self.mode == 5:
      dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
      self.target_range = max(dist,self.target_range)
      if me.energy > dist*1.5:
        self.mode = 6 

    if self.mode == 6:
      dist = abs(mx-self.target[0]) + abs(my-self.target[1])
      if dist > 2:
        return cells.Action(cells.ActionType.MOVE,self.target)
      else:
        self.my_plant = None
        self.mode = 0

    if me.energy < self.target_range:
      if view.get_energy().get(mx, my) > 0:
        return cells.Action(cells.ActionType.EAT)
      elif self.my_plant is not None:
        self._set_target(*self.my_plant.get_pos())

    if self.my_plant:
      dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1])) 
      if me.energy < dist*1.5:
        (mx,my) = self.my_plant.get_pos()
        return cells.Action(cells.ActionType.MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
      if (random.random() < self.colonize_prob.val):
        (mx,my) = self.my_plant.get_pos()
        dtheta = random.random() * 2 * math.pi
        dr = random.randrange(100)
        curr_r, curr_theta = cmath.polar(mx + my*1j)
        t = cmath.rect(curr_r + dr, curr_theta + dtheta)
        self._set_target(t.real, t.imag)

    if (random.random() < self.spawn_prob.val and me.energy >= self.spawn_energy.val):
      return cells.Action(cells.ActionType.SPAWN,(mx+random.randrange(-1,2),my+random.randrange(-1,2), self))
    else:
      return cells.Action(cells.ActionType.MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
