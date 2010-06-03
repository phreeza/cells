import cells
import genes

import cmath
import math
from random import random, randrange

CallForHelpGene = genes.make_normally_perturbed_gene(0.01)
CallOfDutyGene = genes.make_normally_perturbed_gene(0.01)
DraftDodgerGene = genes.make_normally_perturbed_gene(0.01)
SpawnProbabilityGene = genes.make_normally_perturbed_gene(0.01)
SpawnEnergyThresholdGene = genes.make_normally_perturbed_gene(5, 50, 5000)
ColonizeProbabilityGene = genes.make_normally_perturbed_gene(0.01)

CallTypeGene = genes.make_drastic_mutation_gene(0.01)

MODE_NORMAL = 0
MODE_PREP = 5
MODE_ATTACK = 6
MODE_COLONIZE = 7

def fuzz_coord(c):
    return c + randrange(-1,2)


class AgentMind(object):
    def __init__(self, args):
        self.my_plant = None
        self.mode = MODE_NORMAL
        self.target_range = randrange(50,200)
        if args is None:
            self.call_for_help = CallForHelpGene(genes.InitializerGene(0.25))
            self.call_of_duty = CallOfDutyGene(genes.InitializerGene(0.75))
            self.draft_dodger = DraftDodgerGene(genes.InitializerGene(0.75))
            self.spawn_prob = SpawnProbabilityGene(genes.InitializerGene(0.1))
            self.spawn_energy = SpawnEnergyThresholdGene(genes.InitializerGene(50))
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

    def _colonize_from(self, mx, my, mapsize):
        tx = randrange(mapsize)
        ty = randrange(mapsize)
        self._set_target(MODE_COLONIZE, tx, ty, mapsize)

    def _set_target(self, next_mode, tx, ty, mapsize):
        self.mode = MODE_PREP
        self.next_mode = next_mode
        tx += randrange(-3, 4)
        ty += randrange(-3, 4)
        tx = min(max(tx, 0), mapsize)
        ty = min(max(ty, 0), mapsize)
        self.target = (tx, ty)

    def act(self,view,msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        me = view.me
        mp = (mx,my)= (me.x, me.y)
        map_size = view.energy_map.width

        cfh_val = self.call_for_help.val
        for a in view.agent_views:
            if (a.team != me.team):
                if random() > cfh_val:
                    msg.send_message((self.call_type.val, MODE_ATTACK, mp))
                return cells.Action(cells.ACT_ATTACK, (a.x, a.y))

        my_call_type = self.call_type.val
        my_plant = self.my_plant
        for message in msg.get_messages():
            call_type, move_mode, m = message
            if call_type != my_call_type:
                continue
            if my_plant:
                my_team = me.team
                num_nearby = sum(1 for x in view.agent_views if x.team == my_team)
                if num_nearby > 1 and random() > self.draft_dodger.val:
                    tx, ty = m
                    self._set_target(move_mode, tx, ty, map_size)
            elif random() < self.call_of_duty.val:
                tx, ty = m
                self._set_target(move_mode, tx, ty, map_size)

        del my_plant  # Might change later, don't confuse myself by caching it.

        if view.plant_views:
            best_plant = max(view.plant_views, key=lambda x: x.eff)
            self.my_plant = best_plant
            self.mode = MODE_NORMAL

        if self.mode == MODE_PREP:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            self.target_range = max(dist,self.target_range)
            if me.energy > dist*1.5:
                self.mode = self.next_mode

        if self.mode == MODE_COLONIZE or self.mode == MODE_ATTACK:
            dist = abs(mx-self.target[0]) + abs(my-self.target[1])
            my_team = me.team
            if (dist < 2 or
                (self.mode == MODE_COLONIZE and dist < 8 and
                 sum(1 for a in view.agent_views
                     if a.team == my_team) > 7)):
                self.my_plant = None
                self.mode = MODE_NORMAL
            else:
                return cells.Action(cells.ACT_MOVE,self.target)

        if me.energy < self.target_range:
            if view.energy_map.get(mx, my) > 0:
                return cells.Action(cells.ACT_EAT)
            elif self.my_plant is not None:
                mp = self.my_plant
                self._set_target(MODE_ATTACK, mp.x, mp.y, map_size)
            else:
                self._colonize_from(mx, my, map_size)

        my_plant = self.my_plant
        if my_plant is not None:
            dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
            if me.energy < dist*1.5:
                return cells.Action(cells.ACT_MOVE,
                                    (fuzz_coord(my_plant.x), fuzz_coord(my_plant.y)))
            if (random() < self.colonize_prob.val):
                self._colonize_from(my_plant.x, my_plant.y, map_size)

        if (random() < self.spawn_prob.val and
            me.energy >= self.spawn_energy.val):
            return cells.Action(cells.ACT_SPAWN,
                                (fuzz_coord(mx), fuzz_coord(my), self))
        else:
            return cells.Action(cells.ACT_MOVE,
                                (fuzz_coord(mx), fuzz_coord(my)))
