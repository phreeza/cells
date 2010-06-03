# seriously stupid bot
# eat, work out symmetric position, attack, lose to spreaded colonies

import cells, random

class AgentMind(object):
    def __init__(self, args):
        # init things
        self.home = None
        self.breeder = False

        # if called by a parent:
        if (args != None):
            self.home = args[0]

    def symmetricPos(self, pos):
        return (pos[1], pos[0])

    def get_dir(self, myX, myY, targX, targY):
        resultX = 0
        resultY = 0
        if (myX > targX): resultX = myX+1
        if (myX < targX): resultX = myX-1
        if (myY > targY): resultY = myY-1
        if (myY < targY): resultY = myY+1
        return (resultX, resultY)

    def act(self, view, msg):
        me = view.get_me()
        my_pos = (mx,my) = me.get_pos()

        # first cell only store home plant and work out direction to symmetric team
        # TODO: handle view.get_plants() somehow not working for the first cell
        if (self.home == None):
            self.home = (view.get_plants()[0].x, view.get_plants()[0].y)
            self.breeder = True

        # eat
        if (view.get_energy().get(mx, my) > 0):
            if (me.energy < 50):
                return cells.Action(cells.ACT_EAT)

        # breed if designated
        if (self.breeder):
            return cells.Action(cells.ACT_SPAWN, (mx + random.randrange(-1,2), my + random.randrange(-1,2), self.home))

        # fight if drunk
        nearby = view.get_agents()
        for a in nearby:
            if (a.team != me.team):
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # leave home
        return cells.Action(cells.ACT_MOVE, self.symmetricPos(self.home))

        # die
        pass
