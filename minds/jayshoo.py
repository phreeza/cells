import cells, random

class AgentMind:
	def __init__(self, args):
		self.state = 0
		self.dx = 0
		self.dy = 0
		
	def act(self, view, msg):
		me = view.get_me()
		my_pos = (mx,my) = me.get_pos()
		
		# eat
		if (view.get_energy().get(mx, my) > 0):
			if (me.energy < 20):
				return cells.Action(cells.ACT_EAT)
		
		# breed
		if (len(view.get_plants()) > 0):
			return cells.Action(cells.ACT_SPAWN, (mx + random.randrange(-1,2), my + random.randrange(-1,2)))
		

				
		# find a direction in life
		if (self.dx == 0):
			self.dx = random.randrange(-1,2)
			self.dy = random.randrange(-1,2)
		
		# leave home
		return cells.Action(cells.ACT_MOVE, (mx+self.dx, my+self.dy))
			
		# die
		pass
		