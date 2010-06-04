import random,cells
import math

class Message:
	def __init__(self, pos, avgEnemeyPos, weight):
		self.pos = pos
		self.avgEnemeyPos = avgEnemeyPos
		self.weight = weight
	

class AgentMind:
	def __init__(self, soldier=None):
		self.my_plant = None
		self.mode = 1
		self.moved = 0
		#self.target_range = random.randrange(50,1000)
		self.setDirection()
		self.avgEnemeyPos = (0,0)
		self.weight = 0
		if not soldier:
			self.soldier = random.random() < .7
		else:
			self.soldier = soldier
		self.spawnSoldiers = False
		self.energyNeeded = 100 # how much energy we need before we go fight
		self.prevEnergy = None


	def setDirection(self, rad = None):
		if rad:
			self.direction = rad
		else:
			self.direction = random.random()*math.pi*2
		self.cos = math.cos(self.direction)
		self.sin = math.sin(self.direction)

		if self.cos < 0:
			self.dx = -1
		else:
			self.dx = 1

		if self.sin < 0:
			self.dy = -1
		else:
			self.dy = 1


	def length(self,a,b):
		return int(math.sqrt((a*a)+(b*b)))
  
	def act(self,view,msg):
		me = view.get_me()
		pos = me.get_pos()
		(mx, my) = pos

		# calc avg enemy pos
		nMessages = len(msg.get_messages())
		if nMessages:
			newPos = (0, 0)
			for m in msg.get_messages():
				newPos = (newPos[0] + m.pos[0], newPos[1] + m.pos[1])
				self.avgEnemeyPos = m.avgEnemeyPos
				self.weight = m.weight
			newPos = (newPos[0] / float(nMessages), newPos[1] / float(nMessages))
			self.avgEnemeyPos = ((self.avgEnemeyPos[0] * float(self.weight) + newPos[0] * float(nMessages)) / float(self.weight + nMessages), 
				(self.avgEnemeyPos[1] * float(self.weight) + newPos[1] * float(nMessages)) / float(self.weight + nMessages))
			if self.weight < 30:
				self.weight = min(30, self.weight+nMessages)

			cartesian = (self.avgEnemeyPos[0] - pos[0], self.avgEnemeyPos[1] - pos[1])
			distance = math.sqrt(cartesian[0]*cartesian[0] + cartesian[1]*cartesian[1])
			self.spawnSoldiers = distance < 10
			
			# do we move there?
			if self.soldier:
				self.energyNeeded = distance*1.2
				if self.energyNeeded < me.energy: # i know we can eat along the way but not in late-game
					direction = math.atan2(cartesian[1], cartesian[0])
					self.setDirection(direction)
				if me.energy == 1:
					pass#print self.avgEnemeyPos
		

		# are we stuck?
		if self.moved and self.prevPos == pos:
			self.setDirection()		
		self.moved = 0
		self.prevPos = None

		# did we just eat a dead guy?
		#if self.prevEnergy and me.energy > self.prevEnergy and ((me.energy - self.prevEnergy + 1) % 25) == 0: 
		#	self.spawnSoldiers = True
		self.prevEnergy = me.energy


		for a in view.get_agents():
			if (a.get_team()!=me.get_team()):				
				msg.send_message(Message(pos, self.avgEnemeyPos, self.weight))
				return cells.Action(cells.ACT_ATTACK,a.get_pos())

		if me.energy > 100:
			return cells.Action(cells.ACT_SPAWN, (mx+random.randint(-1,1), my+random.randint(-1,1) ))#, self.spawnSoldiers)) # mx, my+1

		if view.get_energy().get(mx, my):# and me.energy < self.energyNeeded:
			self.prevEnergy = me.energy
			return cells.Action(cells.ACT_EAT)

		else:
			dx = dy = 0
			while not self.moved:
				if random.random() < abs(self.cos):
					dx += self.dx
				if random.random() < abs(self.sin):
					dy += self.dy
				self.moved = dx or dy
			if self.spawnSoldiers:
				pass
			self.prevPos = pos
			return cells.Action(cells.ACT_MOVE, (mx+dx, my+dy))

