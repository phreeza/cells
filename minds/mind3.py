import random,cells
#rylsan
#phreeza


##   Message Grammar
##sentence = [uniqueid,object_type,obj_instance)
##such that coords = (x,y)
##which means: "my name is uniqueid and I have found an obj_instance of an object"
##object_type=2 : plant
##object_type=3 : enemy
##2,3,5,7,11 are possible control vals

class AgentMind(object):
    def __init__(self,junk):
        self.my_plant = None
        self.mode = 1
        self.target_range = random.randrange(50,200)

        self.memory=[]
        self.outmemory=[]

        self.uniqueid = 0

    def act(self,view,msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        n = len(view.get_plants())
        me = view.get_me()
        mp = (mx,my)= me.get_pos()

        #If I don't have an id yet, get one.
        if(self.uniqueid==0):
            self.uniqueid = self.GetID()

        for a in view.get_agents():
            if (a.get_team()!=me.get_team()):
                #If I see an enemy, broadcast it, then attack it.
                sentence = [self.uniqueid,3,a]
                self.outmemory.append(sentence)
                if sentence not in self.outmemory:
                    msg.send_message(sentence)
                return self.Attack(a)



        #Go through my messages, then memorize them
        for m in msg.get_messages():
            self.memory.append(m)



        #Choosing a plant
        if(n>0):
            #If I see a plant, broadcast it.
            sentence = [self.uniqueid,2,view.get_plants()[0]]
            self.outmemory.append(sentence)
            if sentence not in self.outmemory:
                msg.send_message(sentence)

            if (not self.my_plant):
                #If I don't have a plant, get one.
                self.my_plant = view.get_plants()[0]
            elif self.my_plant.get_eff()<view.get_plants()[0].get_eff():
                #If I see a plant that is better than my current one, get it.
                self.my_plant = view.get_plants()[0]
            else:
                #Otherwise, check my memory to see if someone else has found a plant
                for mem in self.memory:
                    if(mem[1]==2):
                        #Ok, go to the plant that I have in memory
                        self.my_plant=mem[2]
                        break



        if self.mode == 5:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            self.target_range = max(dist,self.target_range)
            if view.get_me().energy > dist*1.5:
                self.mode = 6

        if self.mode == 6:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            if dist > 4:
                return cells.Action(cells.ACT_MOVE,self.target)
            else:
                self.my_plant = None
                self.mode = 0


        if (view.get_me().energy < self.target_range) and (view.get_energy().get(mx,my) > 0):
            return self.Eat()

        #If I have a plant, move towards it if i need to.
        if self.my_plant:
            dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
            if view.get_me().energy < dist*1.5:
                (mx,my) = self.my_plant.get_pos()
                return self.Move(mx,my)

        #Spawn near my plant, or just move near it.
        if (random.random()>0.9):
            return self.Spawn(mx,my)
        else:
            return self.Move(mx,my)


    def Spawn(self,x,y):
        return cells.Action(cells.ACT_SPAWN,(x+random.randrange(-1,2),y+random.randrange(-1,2)))

    def Move(self,x,y):
        return cells.Action(cells.ACT_MOVE,(x+random.randrange(-1,2),y+random.randrange(-1,2)))

    def Attack(self,a):
        return cells.Action(cells.ACT_ATTACK,a.get_pos())

    def Eat(self):
        return cells.Action(cells.ACT_EAT)


    def GetID(self):
        ulist = [11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,
                     73,79,83,89,97,101,103,107,109,113,127,131,137,139,149,151,157,163,167,173]

        r = random.randint(5,35)
        random.shuffle(ulist)
        uid = 1
        for i in range(0,r):
            uid *= ulist[i]
        uid=uid*3571
        return uid
