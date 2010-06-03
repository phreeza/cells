import cells
import genes

import cmath
import math
import random

CallForHelpGene = genes.make_normally_perturbed_gene(0.0)
CallOfDutyGene = genes.make_normally_perturbed_gene(0.0)
DraftDodgerGene = genes.make_normally_perturbed_gene(0.0)

class AgentMind(object):
    def __init__(self, args):
        self.my_plant = None
        self.mode = 1
        self.target_range = random.randrange(50,200)
        if args is None:
            self.call_for_help = CallForHelpGene(genes.InitializerGene(0.5))
            self.call_of_duty = CallOfDutyGene(genes.InitializerGene(0.5))
            self.draft_dodger = DraftDodgerGene(genes.InitializerGene(0.5))
        else:
            parent = args[0]
            self.call_for_help = parent.call_for_help.spawn()
            self.call_of_duty = parent.call_of_duty.spawn()
            self.draft_dodger = parent.draft_dodger.spawn()

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
                    msg.send_message(mp)
                return cells.Action(cells.ActionType.ATTACK,a.get_pos())

        for m in msg.get_messages():
            r = random.random()
            if ((self.my_plant and random.random() > self.draft_dodger.val) or
                (not self.my_plant and random.random() < self.call_of_duty.val)):
                self.mode = 5
                (tx,ty) = m
                self.target = (tx+random.randrange(-3,4),ty+random.randrange(-3,4))

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
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            if dist > 4:
                return cells.Action(cells.ActionType.MOVE,self.target)
            else:
                self.my_plant = None
                self.mode = 0

        if (me.energy < self.target_range) and (view.get_energy().get(mx, my) > 0):
            return cells.Action(cells.ActionType.EAT)

        if self.my_plant:
            dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
            if me.energy < dist*1.5:
                (mx,my) = self.my_plant.get_pos()
                return cells.Action(cells.ActionType.MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
            if (random.random()>0.9999):
                (mx,my) = self.my_plant.get_pos()
                dtheta = random.random() * 2 * math.pi
                dr = random.randrange(100)
                curr_r, curr_theta = cmath.polar(mx + my*1j)
                m = cmath.rect(curr_r + dr, curr_theta + dtheta)
                msg.send_message((m.real, m.imag))

        if (random.random()>0.9 and me.energy >= 50):
            return cells.Action(cells.ActionType.SPAWN,(mx+random.randrange(-1,2),my+random.randrange(-1,2), self))
        else:
            return cells.Action(cells.ActionType.MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
