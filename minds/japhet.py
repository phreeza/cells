"""
idea: spawn in waves.  everyone saves up food from the plant until a certain time at which everyone spawns soldiers as fast as possible.
Triggered by an attack.  Everyone set their spawn requirement according to the distance to the attack so that the spawn will all reach the spot at the same time.
idea: use avg pos for spawned soldier destination, local attack events for local maneuvering
idea: attack messages puts everone in 'report' state, everyone sends report on how ready they are to save up.  next tick everyone makes same decision based on reports
"""


import random,cells
import math

class Message:
	def __init__(self, pos):
		self.pos = pos

# inspired by zenergizer
diffs = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

class AgentMind:
	def __init__(self, args):
		if args:
			soldier = args[0]
		else:
			soldier = False

		self.my_plant = None
		self.mode = 1
		self.moved = 0
		#self.target_range = random.randrange(50,1000)
		self.setDirection()
		self.avgEnemyPos = (0,0)
		self.weight = 0
		self.soldier = (random.random() < .6) or soldier
		self.spawner = False
		self.spawnRequirement = 65
		self.soldierDirected = None
		self.distanceToFight = None

		if self.soldier:
			self.energyNeeded = 100 # how much energy we need before we ignore food
		else:
			self.energyNeeded = 25
		self.prevEnergy = None


	def setDirection(self, rad = None):
		if rad != None:
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


	def act(self,view,msg):
		me = view.get_me()
		pos = me.get_pos()
		(mx, my) = pos

		if len(view.get_plants()):
			self.soldier = False
			self.spawner = True
			self.spawnRequirement = 55


		# respond to nearby battles
		if self.soldier and len(msg.get_messages()):
			newPos = (0, 0)
			nCloseBy = 0
			for message in msg.get_messages():
				enemyPos = message.pos
				cartesian = (enemyPos[0] - mx, enemyPos[1] - my)
				distance = max(abs(cartesian[0]), abs(cartesian[1]))
				if distance < 30:
					nCloseBy+=1
					newPos = (newPos[0] + enemyPos[0], newPos[1] + enemyPos[1])
				
				# does the soldier have orders?  any battle call will do
				if not self.soldierDirected:
					direction = math.atan2(cartesian[1], cartesian[0])
					self.setDirection(direction)
					self.soldierDirected = True

			if nCloseBy:
				# find average of all close-by battle calls
				self.avgEnemyPos = ((self.avgEnemyPos[0] * float(self.weight) + newPos[0]) / float(self.weight + nCloseBy),
					(self.avgEnemyPos[1] * float(self.weight) + newPos[1]) / float(self.weight + nCloseBy))
				self.weight = min(25, self.weight+nCloseBy)
						
				cartesian = (self.avgEnemyPos[0] - mx, self.avgEnemyPos[1] - my)
				direction = math.atan2(cartesian[1], cartesian[0])
				self.setDirection(direction)
				self.distanceToFight = max(abs(cartesian[0]), abs(cartesian[1]))
				self.spawnRequirement = 50 + self.distanceToFight + 10

		# are we stuck?
		if self.moved and self.prevPos == pos:
			self.setDirection()		
			self.soldierDirected = False
		self.moved = 0
		self.prevPos = None

		#attack?
		for a in view.get_agents():
			if (a.get_team()!=me.get_team()):				
				msg.send_message(Message(a.get_pos()))
				return cells.Action(cells.ACT_ATTACK,a.get_pos())

		# freeSpots = where we can move/spawn
		freeSpots = diffs[:]
		for a in view.get_agents():
			apos = a.get_pos()
			dpos = (apos[0] - pos[0], apos[1] - pos[1])
			if dpos in freeSpots:
				freeSpots.remove(dpos)

		# see a ton of food nearby?
		if not self.spawner:
			for diff in diffs:
				target = (mx+diff[0], my+diff[1])
				if view.get_energy().get(target[0], target[1]) > 50 and target in freeSpots:
					return cells.Action(cells.ACT_MOVE, (mx+diff[0], my+diff[1]))

		# spawn?
		if me.energy > self.spawnRequirement:
			if len(freeSpots):
				random.shuffle(freeSpots)
				spawn = freeSpots[0]
				spawnSoldier = None
				if self.distanceToFight and self.distanceToFight < 20:
					spawnSoldier = True
				else:
					spawnSoldier = False
				return cells.Action(cells.ACT_SPAWN, (mx+spawn[0], my+spawn[1], spawnSoldier))


		# eat?
		if self.spawner or view.get_energy().get(mx, my) > 1 and (me.energy < self.energyNeeded):
			self.prevEnergy = me.energy
			return cells.Action(cells.ACT_EAT)


		# move as directed
		elif not self.spawner:
			dx = dy = 0
			while not self.moved:
				if random.random() < abs(self.cos):
					dx += self.dx
				if random.random() < abs(self.sin):
					dy += self.dy
				self.moved = dx or dy
			self.prevPos = pos
			return cells.Action(cells.ACT_MOVE, (mx+dx, my+dy))

