#TODO:
# - Make terrain work
# - Make ScalarView
# - Add more actions: PASS, LIFT, DROP,etc...
# - derive SelfView with more info than the general AgentView
# - render terrain and energy landscapes
# - fractal terrain generation
# - make rendering "smart"(and/or openGL)
# - Split into several files.
# - Messaging system
# - limit frame rate
# - response objects for outcome of action
# - Desynchronize agents

import sys
import pygame
import math
import random,time
import mind1,mind2

try:
  import psyco
  psyco.full()
finally:
  pass


class Game:
  def __init__(self):
    self.size = self.width,self.height = (300,300)
    self.messages = MessageQueue()
    self.disp = Display(self.size,scale=2)
    self.time = 0
    self.tic = time.time()
    self.terr = ScalarMapLayer(self.size)
    self.terr.set_random(5)
    self.minds = [mind1.AgentMind,mind2.AgentMind]
    self.update_fields = [(x,y) for x in range(self.width) for y in range(self.height)]

    self.energy_map = ScalarMapLayer(self.size)
    self.energy_map.set_random(10)

    self.plant_map = ObjectMapLayer(self.size,None)
    self.plant_population = []

    self.agent_map = ObjectMapLayer(self.size,None)
    self.agent_population = []

    for x in xrange(7):
      pos = (mx,my) = (random.randrange(self.width),random.randrange(self.height))
      eff = random.randrange(5,11)
      p = Plant(pos,eff)
      self.plant_population.append(p)
      p = Plant((my,mx),eff)
      self.plant_population.append(p)
    self.plant_map.insert(self.plant_population)
    
    for x in xrange(2):    
      (mx,my) = self.plant_population[x].get_pos() 
      pos = (mx+random.randrange(-1,2),my+random.randrange(-1,2))
      self.agent_population.append(Agent(pos,x,self.minds[x]))
      self.agent_map.insert(self.agent_population)

  def run_plants(self):
    for p in self.plant_population:
      (x,y) = p.get_pos()
      for dx in [-1,0,1]:
        for dy in [-1,0,1]:
          if self.energy_map.in_range((x+dx,y+dy)):
            self.energy_map.change((x+dx,y+dy),p.get_eff())

  def add_agent(self,a):
    self.agent_population.append(a)
    self.agent_map.set(a.get_pos(),a)
  
  def del_agent(self,a):
    self.agent_population.remove(a)
    self.agent_map.set(a.get_pos(),None)
    a.set_alive(False)
    del a 
  
  def move_agent(self,a,pos):
    self.agent_map.set(a.get_pos(),None)
    self.agent_map.set(pos,a)
    a.set_pos(pos)

  def get_next_move(self,(old_x,old_y),(x,y)):
    dx = int(math.copysign(1,x-old_x))
    if old_x == x: dx = 0
    dy = int(math.copysign(1,y-old_y))
    if old_y == y: dy = 0
    return (old_x+dx,old_y+dy)

  def run_agents(self):
    views = []
    self.update_fields = []
    for a in self.agent_population:
      self.update_fields.append(a.get_pos())
      agent_view = self.agent_map.get_view(a.get_pos(),1)
      plant_view = self.plant_map.get_view(a.get_pos(),1)
      world_view = WorldView(a,agent_view,plant_view,self.energy_map)
      views.append((a,world_view))
    
    #get actions
    actions = [(a,a.act(v,self.messages)) for (a,v) in views]
    random.shuffle(actions)

    #apply agent actions
    for (agent,action) in actions:
      agent.change_energy(-1)
      if(agent.is_alive()):
        if (action.get_type() == ActionType.MOVE):
          next_pos = self.get_next_move(agent.get_pos(),action.get_data())
          if self.agent_map.in_range(next_pos) and not self.agent_map.get(next_pos):
            self.move_agent(agent,next_pos)
        elif (action.get_type() == ActionType.SPAWN):
          next_pos = self.get_next_move(agent.get_pos(),action.get_data())
          if self.agent_map.in_range(next_pos) and (not self.agent_map.get(next_pos)) and (agent.get_energy()>=50):
            a = Agent(next_pos,agent.get_team(),self.minds[agent.get_team()])
            self.add_agent(a)
            agent.change_energy(-50)
        elif (action.get_type() == ActionType.EAT):
          intake = self.energy_map.get(agent.get_pos())
          agent.change_energy(intake)
          self.energy_map.change(agent.get_pos(),-intake)
        elif (action.get_type() == ActionType.ATTACK):
          next_pos = self.get_next_move(agent.get_pos(),action.get_data())
          if(self.agent_map.get(action.get_data())) and (next_pos == action.get_data()):
            energy = self.agent_map.get(next_pos).get_energy() + 25
            self.energy_map.change(next_pos,energy)
            self.del_agent(self.agent_map.get(next_pos)) 
        elif (action.get_type() == ActionType.LIFT):
          if (not agent.is_loaded()) and (self.terr.get(agent.get_pos())>0):
            agent.set_loaded(True)
            self.terr.change(agent.get_pos(),-1)
        elif (action.get_type() == ActionType.DROP):
          if agent.is_loaded():
            agent.set_loaded(False)
            self.terr.change(agent.get_pos(),1)

    #let agents die if their energy is too low
    for (agent,action) in actions:
      if agent.get_energy() < 0 and agent.is_alive():
        self.energy_map.change(agent.get_pos(),25)
        self.del_agent(agent)

  def tick(self):
    self.disp.update(self.terr,self.agent_population,self.plant_population,self.update_fields)
    self.disp.flip()

    self.run_agents() 
    self.run_plants() 
    self.messages.update()
    self.time = self.time+1
#pygame.time.wait(int(1000*(time.time()-self.tic)))
    self.tic = time.time()

class MapLayer:
  def __init__(self,size,val=0):
    self.size = self.width, self.height = size
    self.values = [val for x in xrange(self.width*self.height) ]

  def get(self,(x,y)):
    if self.in_range((x,y)):
      return self.values[x+y*self.width]
    else:
      return None

  def set(self,(x,y),val):
    self.values[x+y*self.width] = val
  
  def in_range(self,(x,y)):
    return (0<=x and x<self.width and 0<=y and y < self.height)


class ScalarMapLayer(MapLayer):
  def set_random(self,range):
    self.values = [random.randrange(range) for x in xrange(self.width*self.height) ]

  def change(self,(x,y),val):
    self.values[x+y*self.width] += val

class ObjectMapLayer(MapLayer):
  
  def get_view(self,(x,y),r):
    ret = []
    for x_off in xrange(-r,r+1):
      for y_off in xrange(-r,r+1):
        a = self.get((x+x_off,y+y_off))
        if a and (x_off,y_off)!=(0,0): ret.append(a.get_view())
    return ret

  def insert(self,list):
    for o in list:
      self.set(o.get_pos(),o)

class Agent:
  def __init__(self,pos,team,AgentMind):
    self.pos = self.x,self.y = pos
    self.mind = AgentMind()
    self.energy = 25
    self.alive = True
    self.team = team
    self.loaded = False
    if team == 0:
     self.color = (255,0,0)
    else:
     self.color = (0,0,255)
    self.act = self.mind.act

  def is_alive(self):
    return self.alive

  def set_alive(self,alive):
    self.alive = alive

  def is_loaded(self):
    return self.loaded

  def set_loaded(self,l):
    self.loaded = l

  def get_energy(self):
    return self.energy

  def get_team(self):
    return self.team

  def change_energy(self,n):
    self.energy += n

  def get_pos(self):
    return self.pos
  
  def set_pos(self,pos):
    self.pos = pos
  
  def get_team(self):
    return self.team
 
  def get_view(self):
    return AgentView(self)

#def act(self,view,m):
#   return self.mind.act(view,m)

class ActionType:
  SPAWN = 0
  MOVE = 1
  EAT = 2
  ATTACK = 3
  LIFT = 4
  DROP = 5

class Action:
  def __init__(self,type,data=None):
    self.type = type
    self.data = data

  def get_data(self):
    return self.data
  
  def get_type(self):
    return self.type

class PlantView:
  def __init__(self,p):
    self.pos = p.get_pos()
    self.eff = p.get_eff()

  def get_pos(self):
    return self.pos

  def get_eff(self):
    return self.eff

class AgentView:
  def __init__(self,agent):
    self.pos = agent.get_pos()
    self.team = agent.get_team()

  def get_pos(self):
    return self.pos

  def get_team(self):
    return self.team

class WorldView:
  def __init__(self,me,agent_views,plant_views,energy_map):
    self.agent_views = agent_views
    self.plant_views = plant_views
    self.energy_map = energy_map
    self.me = me

  def get_me(self):
    return self.me
  
  def get_agents(self):
    return self.agent_views
  
  def get_plants(self):
    return self.plant_views

  def get_energy(self):
    return self.energy_map


class Display:
  black = 0, 0, 0
  red = 255, 0, 0
  green = 0, 255, 0
  yellow = 255,255,0

  def __init__(self,size,scale=5):
    self.width, self.height = size
    self.scale = scale
    self.size = (self.width*self.scale,self.height*self.scale) 
    pygame.init()
    self.screen = pygame.display.set_mode(self.size)

  def update(self,terr,pop,plants,upfields):
    for event in pygame.event.get():
      if event.type == pygame.QUIT: 
        sys.exit()

    for f in upfields:
      (x,y)=f
      x *= self.scale
      y *= self.scale
      self.screen.fill((min(255,20*terr.get(f)),min(255,10*terr.get(f)),0),pygame.Rect((x,y),(self.scale,self.scale)))
    for a in pop:
      (x,y)=a.get_pos()
      x *= self.scale
      y *= self.scale
      self.screen.fill(a.color,pygame.Rect((x,y),(self.scale,self.scale)))
    for a in plants:
      (x,y)=a.get_pos()
      x *= self.scale
      y *= self.scale
      self.screen.fill(self.green,pygame.Rect((x,y),(self.scale,self.scale)))

  def flip(self):
    pygame.display.flip()

class Plant:
  def __init__(self,pos,eff):
    self.pos = self.x,self.y = pos
    self.eff = eff

  def get_pos(self):
    return self.pos

  def get_eff(self):
    return self.eff

  def get_view(self):
    return PlantView(self)


class MessageQueue:
  def __init__(self):
    self.inlist = []
    self.outlist = []

  def update(self):
    self.outlist = self.inlist
    self.inlist = []
  
  def send_message(self,m):
    self.inlist.append(m)

  def get_messages(self):
    return self.outlist

class Message:
  def __init__(self,message):
    self.message = message
  def get_message(self):
    return self.message

if __name__ == "__main__":
  game = Game()
  while 1:
    game.tick()
