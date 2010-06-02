'''
Defines an agent mind that attacks any opponent agents within its view,
attaches itself to the strongest plant it finds, eats when its hungry, 
'''

import random, cells
import math


class AgentMind:
    def __init__(self, junk):
        self.my_plant = None
        self.mode = 1
        self.target_range = random.randrange(50, 1000)

    def length(self, a, b):
        return int(math.sqrt((a * a) + (b * b)))

    def act(self, view, msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        n = len(view.get_plants())
        me = view.get_me()
        mp = (mx, my)= me.get_pos()

        # attack any opponents
        for a in view.get_agents():
            if a.get_team() != me.get_team():
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # attach to the strongest plant it finds
        if n > 0:
            plant = view.get_plants()[0]
            if not self.my_plant:
                self.my_plant = view.get_plants()[0]
            elif self.my_plant.get_eff() < plant.get_eff():
                self.my_plant = plant
        
        # eat if hungry or if this is an exceptionally energy-rich spot
        hungry = (me.energy < self.target_range)
        energy_here = view.get_energy().get(mx, my)
        food = (energy_here > 0)
        if hungry and food or energy_here > 100:
            return cells.Action(cells.ACT_EAT)

        # what to do if it has a plant
        if self.my_plant:
            plant_pos = self.my_plant.get_pos()
            # distance from plant
            plant_dist = self.length(
                abs(mx - plant_pos[0]), 
                abs(my - plant_pos[1]))
            # a condition required for lifting dirt: lambda for lazy evaluation
            lift_condition = lambda: (plant_dist % 5 > 0 or abs(mx - plant_pos[0]) < 2)
            
            if not me.loaded and lift_condition() and random.random() > 0.5:
                return cells.Action(cells.ACT_LIFT)
            if me.loaded and plant_dist % 5 == 0 and abs(mx - plant_pos[0]) >= 2:
                return cells.Action(cells.ACT_DROP)
            if me.energy < plant_dist * 1.5:
                (mx, my) = plant_pos
                pos = (mx + random.randrange(-1, 2), my + random.randrange(-1, 2))
                return cells.Action(cells.ACT_MOVE, pos)

        pos = (mx + random.randrange(-1, 2), my + random.randrange(-1, 2))
        action = cells.ACT_SPAWN if random.random() > 0.9 else cells.ACT_MOVE
        return cells.Action(action, pos)