'''
Defines an agent mind that attacks any opponent agents within its view,
attaches itself to the strongest plant it finds, eats when its hungry, 
'''

import random, cells
import math, numpy

class AgentType(object):
	QUEEN = 0
	WORKER = 1
	FIGHTER = 2
	BUILDER = 3

class MessageType(object):
	FOUND = 0
	DEFEND = 1
	CLAIM = 2
	CLAIMED = 3

def dist(a, b):
	return int(math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2))

def length(xy):
	return dist(xy, (0, 0))

def offset(i):
	i = i % 9
	x = 0
	y = 0
	if i < 3:
		y = -1
	if i > 5:
		y = 1
	
	if i == 0 or i == 5 or i == 6:
		x = -1
	if i == 2 or i == 3 or i == 8:
		x = 1

	return (x, y)

def get_available_space_grid(view, agent):
	grid = numpy.ones((3,3))
	for a in view.get_agents():
		grid[a.x - agent.x + 1, a.y - agent.y + 1] = 0
	for plant in view.get_plants():
		grid[plant.x - agent.x + 1, plant.y - agent.y + 1] = 0
	grid[1,1] = 0
	return grid

def spawnPos(i, type, view, agent):
	if type == AgentType.QUEEN:
		old = offset(i)
		return (-old[0], -old[1])
	grid = get_available_space_grid(view, agent)
	for x in xrange(3):
		for y in range(3):
			if grid[x,y]:
				return (x-1, y-1)
	return (-1, -1)

class AgentMind(object):

	def __init__(self, data):
		self.target_range = random.randrange(50, 1000)

		if data == None:
			self.type = AgentType.QUEEN
			self.ratios = (1,)
		else:
			self.type = data[0]
			self.ratios = (1, 1, 1, 2)

		if self.type == AgentType.QUEEN:
			self.plant = None
			self.claimed = False
			self.claiming = False
			self.position = 0
			self.count = 0
			self.directionOfAttack = None
			self.newborn = True
			self.age = 0

		if self.type == AgentType.WORKER:
			self.plantList = list()
			self.startPoint = data[1]

		if self.type == AgentType.BUILDER:
			self.radius = 10
			self.height = 4
			self.openings = 1

		self.skip = True

		if self.type == AgentType.FIGHTER and data[1]:
			self.direction = data[1]
		else:
			self.direction = (random.randrange(0, 300), random.randrange(0, 300))

	def act(self, view, msg):
		agent = view.get_me()
		position = (x, y)= agent.get_pos()

		if dist(self.direction, position) < 2:
			self.direction = (random.randrange(0, view.energy_map.width), random.randrange(0, view.energy_map.height))

		# Attack any opponents.
		for a in view.get_agents():
			if a.get_team() != agent.get_team():
				if self.type == AgentType.QUEEN:
					msg.send_message((MessageType.DEFEND, (x,y)))
					self.ratios = [0, 2, 2, 2]
				else:
					msg.send_message((MessageType.FOUND, a.get_pos()))
				return cells.Action(cells.ACT_ATTACK, a.get_pos())

		# Process messages
		alreadyClaimed = 0
		distance = 1000000
		for message in msg.get_messages():
			# Queen message behavior
			if message[0] == MessageType.CLAIM and self.type == AgentType.QUEEN:
				if self.plant != None and self.plant.get_pos() == message[1]:
					if self.claimed:
						self.newborn = False
						msg.send_message((MessageType.CLAIMED, message[1]))
			if message[0] == MessageType.CLAIMED and self.type == AgentType.QUEEN:
				if self.plant != None and self.plant.get_pos() == message[1]:
					if not self.claimed:
						alreadyClaimed += 1
			if message[0] == MessageType.FOUND and self.type == AgentType.QUEEN:
				if dist(message[1], position) < distance:
					self.directionOfAttack = message[1]
					distance = dist(message[1], position)

			# Worker message behavior
			if self.type == AgentType.WORKER:
				if message[0] == MessageType.CLAIM:
					found = False
					for p in self.plantList:
						if p == message[1]:
							found = True
							break
					if not found:
						self.plantList.append(message[1])

				if message[0] == MessageType.DEFEND or message[0] == MessageType.FOUND:
					aDistance = dist(position, message[1])
					if aDistance < 20 and aDistance < distance:
						self.type = AgentType.FIGHTER
						self.direction = message[1]
						distance = aDistance

			# Fighter message behavior
			if self.type == AgentType.FIGHTER:
				if message[0] == MessageType.DEFEND or message[0] == MessageType.FOUND:
					if distance > dist(position, message[1]):
						self.direction = message[1]
						distance = dist(position, message[1])

		if self.type == AgentType.WORKER:
			if dist(position, self.startPoint) > 2:
				plants = view.get_plants()
				if plants:
					found = False
					for p in self.plantList:
						if p == plants[0].get_pos():
							found = True
							break
					if not found:
						self.type = AgentType.QUEEN
						self.ratios = (1,1,1,2)
						self.newborn = True
						self.plant = None
						self.claimed = False
						self.claiming = False
						self.position = 0
						self.count = 0
						self.directionOfAttack = None
						self.age = 0
						del self.plantList

			# Eat if hungry.
			hungry = (agent.energy < 50)
			energy_here = view.get_energy().get(x, y)
			food = (energy_here > 0)
			if hungry and food:
				return cells.Action(cells.ACT_EAT)

			if agent.energy > 500:
				sp = spawnPos(0, AgentType.WORKER, view, agent)
				sp = (sp[0]+x, sp[1]+y, AgentType.WORKER, (x, y))
				return cells.Action(cells.ACT_SPAWN, sp)

			if random.random() < 0.65:
				if random.random() < 0.4:
					if view.get_energy().get(x, y) > 0:
						return cells.Action(cells.ACT_EAT)

				direction = [self.direction[0]-x, self.direction[1]-y]
				if direction[0] > 0:
					direction[0] = 1
				elif direction[0] == 0:
					direction[0] = 0
				else:
					direction[0] = -1

				if direction[1] > 0:
					direction[1] = 1
				elif direction[1] == 0:
					direction[1] = 0
				else:
					direction[1] = -1

				position = (position[0]+direction[0], position[1]+direction[1])
			else:
				position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
			return cells.Action(cells.ACT_MOVE, position)

		if self.type == AgentType.FIGHTER:
			# Eat if hungry.
			hungry = (agent.energy < 100)
			energy_here = view.get_energy().get(x, y)
			food = (energy_here > 0)
			if hungry and food:
				return cells.Action(cells.ACT_EAT)

			if agent.energy > 1000:
				sp = spawnPos(0, AgentType.FIGHTER, view, agent)
				sp = (sp[0]+x, sp[1]+y, AgentType.FIGHTER, (x, y))
				return cells.Action(cells.ACT_SPAWN, sp)

			if random.random() < 0.85 or dist(position, self.direction) < 8:
				direction = [self.direction[0]-x, self.direction[1]-y]
				if direction[0] > 0:
					direction[0] = 1
				elif direction[0] == 0:
					direction[0] = 0
				else:
					direction[0] = -1

				if direction[1] > 0:
					direction[1] = 1
				elif direction[1] == 0:
					direction[1] = 0
				else:
					direction[1] = -1

				position = (position[0]+direction[0], position[1]+direction[1])
			else:
				position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
			return cells.Action(cells.ACT_MOVE, position)


		# Queen Stuff
		if self.type == AgentType.QUEEN:
			# Check claim
			if self.claiming:
				if self.skip:
					self.skip = False
				else:
					if alreadyClaimed > 39:
						# Try again
						self.plant = None
						self.claiming = False
					else:
						# We have a throne
						self.claimed = True
						self.claiming = False
						self.position = alreadyClaimed
						print alreadyClaimed
					self.skip = True

			# Get a plant
			if self.plant == None and view.get_plants():
				self.age += 1
				if self.age > 5:
					self.type = AgentType.WORKER
					self.plantList = list()

				if view.get_plants():
					plants = view.get_plants()
					bestPlant = plants[0]
					distance = dist(position, bestPlant.get_pos())
					for plant in plants:
						if distance > dist(position, bestPlant.get_pos()):
							distance = dist(position, bestPlant.get_pos())
							bestPlant = plant
						
					self.plant = bestPlant
					self.claiming = True
					msg.send_message((MessageType.CLAIM, self.plant.get_pos()))

			# Check position
			if self.claimed == False and self.claiming == False:
				# Move randomly
				if random.random() > 0.75:
					direction = [self.direction[0]-x, self.direction[1]-y]
					if direction[0] > 0:
						direction[0] = 1
					elif direction[0] == 0:
						direction[0] = 0
					else:
						direction[0] = -1

					if direction[1] > 0:
						direction[1] = 1
					elif direction[1] == 0:
						direction[1] = 0
					else:
						direction[1] = -1

					position = (position[0]+direction[0], position[1]+direction[1])
				else:
					position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
				return cells.Action(cells.ACT_MOVE, position)

			if self.claimed:
				# Move towards
				off = offset(self.position)
				pos = self.plant.get_pos()
				pos = (pos[0]+off[0], pos[1]+off[1])
				distance = dist(pos, position)
				
				if distance > 0:
					if agent.energy > distance * 1.1:
						if random.random() > 0.6:
							pos = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
						return cells.Action(cells.ACT_MOVE, pos)
					else:
						# Cannot move in one go eat if pos or move a bit
						if view.get_energy().get(x, y) > 0:
							return cells.Action(cells.ACT_EAT)
						mxy = [0, 0]
						if self.plant.get_pos()[0] > x:
							mxy[0] = 1
						elif self.plant.get_pos()[0] < x:
							mxy[0] = -1
						if self.plant.get_pos()[1] > y:
							mxy[1] = 1
						elif self.plant.get_pos()[1] < y:
							mxy[1] = -1

						mxy = (mxy[0]+x, mxy[1]+y)
						return cells.Action(cells.ACT_MOVE, mxy)
					
			# Breed or Eat
			nxt = self.ratios[self.count%len(self.ratios)]
			spawn = [x, y, nxt]
			spawning = False

			if self.newborn and agent.energy > 100:
				spawn = [x, y, AgentType.QUEEN]
				spawnOff = spawnPos(self.position, AgentType.QUEEN, view, agent)
				spawning = True
			if nxt == AgentType.QUEEN and agent.energy > 100:
				# Spawn new queen
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawning = True
			if nxt == AgentType.WORKER and agent.energy > 100:
				# Spawn new worker
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawn.append(position)
				spawning = True
			if nxt == AgentType.FIGHTER and agent.energy > 100:
				# Spawn new fighter
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawn.append(self.directionOfAttack)
				spawning = True
			if nxt == AgentType.BUILDER and agent.energy > 100:
				# Spawn new builder
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawning = True

			if spawning:
				spawn[0] += spawnOff[0]
				spawn[1] += spawnOff[1]
				self.count = self.count + 1
				return cells.Action(cells.ACT_SPAWN, spawn)

			# Must eat
			return cells.Action(cells.ACT_EAT)
			

		if random.random() > 0.75:
			direction = (self.direction[0]-x, self.direction[1]-y)
			if direction[0] > 0:
				direction[0] = 1
			elif direction[0] == 0:
				direction[0] = 0
			else:
				direction[0] = -1

			if direction[1] > 0:
				direction[1] = 1
			elif direction[1] == 0:
				direction[1] = 0
			else:
				direction[1] = -1

			position = (position[0]+direction[0], position[1]+direction[1])
		else:
			position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
		return cells.Action(cells.ACT_MOVE, position)
