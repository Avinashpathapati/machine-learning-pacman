# Used code from
# DQN implementation by Tejas Kulkarni found at
# https://github.com/mrkulk/deepQN_tensorflow

# Used code from:
# The Pacman AI projects were developed at UC Berkeley found at
# http://ai.berkeley.edu/project_overview.html


import numpy as np
import random
import util
import time
import sys

# Pacman game
from pacman import Directions
from game import Agent
import game

# Replay memory
from collections import deque
from PIL import Image, ImageColor

# Neural nets
import tensorflow as tf
from DeepQNetwork import *

params = {
    # Model backups
    'load_file': None,
    'save_file': None,
    'save_interval' : 10000, 

    # Training parameters
    'train_start': 15000,    # Episodes before training starts
    'batch_size': 32,       # Replay memory batch size
    'mem_size': 100000,     # Replay memory size

    'discount': 0.99,       # Discount rate (gamma value)
    'lr': .00025,            # Learning reate
    
    # Epsilon value (epsilon-greedy)
    'eps': 1.0,             # Epsilon start value
    'eps_final': 0.1,       # Epsilon end value
    'eps_step': 1000000       # Epsilon steps between start and end (linear)
}                     



class PacmanDQN(game.Agent):
    def __init__(self, args):

        print("Initialise DQN Agent")

        # Load parameters from user-given arguments
        self.params = params
        self.params['width'] = args['width']
        self.params['height'] = args['height']
        self.params['num_training'] = args['numTraining']

        # Start Tensorflow session
        gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.1)
        self.sess = tf.Session(config = tf.ConfigProto(gpu_options = gpu_options))
        self.qnet = DeepQNetwork(self.params)

        # time started
        self.general_record_time = time.strftime("%a_%d_%b_%Y_%H_%M_%S", time.localtime())
        # Q and cost
        self.Q_global = []
        self.cost_disp = 0     

        # Stats
        self.cnt = self.qnet.sess.run(self.qnet.global_step)
        self.local_cnt = 0

        self.numeps = 0
        self.last_score = 0
        self.s = time.time()
        self.last_reward = 0.

        self.replay_mem = deque()
        self.last_scores = deque()

    def getImageFromState(self, state):

        im = Image.new('RGB', (params['width'], params['height'])) # create the Image of size 1 pixel 
        for i in range(0,params['height']):
            for j in range(0,params['width']):
                im.putpixel((i,j), ImageColor.getrgb("rgb(0, 0, 0)")) # or whatever color you wish

        currentFood = state.getFood()
        for i in range(0,currentFood.width):
            for j in range(0,currentFood.height):
                if currentFood[i][j] == True:
                    im.putpixel((i,j), ImageColor.getrgb("rgb(255, 255, 255)"))

        walls = state.getWalls()
        for i in range(0,walls.width):
            for j in range(0,walls.height):
                if walls[i][j] == True:
                    im.putpixel((i,j), ImageColor.getrgb("rgb(0, 128, 255)"))

        im.putpixel((state.getPacmanPosition()[0], state.getPacmanPosition()[1]), ImageColor.getrgb("rgb(255, 255, 0)"))

        if state.getGhostState(1).scaredTimer != 0:
            im.putpixel((int(state.getGhostPosition(1)[0]), int(state.getGhostPosition(1)[1])), ImageColor.getrgb("rgb(160, 160, 160)"))
        else:
            im.putpixel((int(state.getGhostPosition(1)[0]), int(state.getGhostPosition(1)[1])), ImageColor.getrgb("rgb(255, 0, 255)"))

        # if state.getGhostState(2).scaredTimer != 0:
        #     im.putpixel((int(state.getGhostPosition(2)[1]), int(state.getGhostPosition(2)[0])), ImageColor.getrgb("rgb(160, 160, 160)"))
        # else:
        #     im.putpixel((int(state.getGhostPosition(2)[1]), int(state.getGhostPosition(2)[0])), ImageColor.getrgb("rgb(255, 0, 255)"))

        if len(state.getCapsules()) == 2:
            im.putpixel((int(state.getCapsules()[0][0]), int(state.getCapsules()[0][1])), ImageColor.getrgb("rgb(0, 255, 0)"))
            im.putpixel((int(state.getCapsules()[1][0]), int(state.getCapsules()[1][1])), ImageColor.getrgb("rgb(0, 255, 0)"))
        elif len(state.getCapsules()) == 1:
            im.putpixel((int(state.getCapsules()[0][0]), int(state.getCapsules()[0][1])), ImageColor.getrgb("rgb(0, 255, 0)"))

        return im

    def getMove(self, state):

        image = self.getImageFromState(state)

        keepLooking = True

        while keepLooking == True:
            # Exploit / Explore
            if np.random.rand() > self.params['eps']:
                # Exploit action
                self.Q_pred = self.qnet.sess.run(
                    self.qnet.y,
                    feed_dict = {self.qnet.x: np.reshape(image,
                                                       (1, params['width'], params['height'], 3)), 
                                 self.qnet.q_t: np.zeros(1),
                                 self.qnet.actions: np.zeros((1, 4)),
                                 self.qnet.terminals: np.zeros(1),
                                 self.qnet.rewards: np.zeros(1)})[0]

                self.Q_global.append(max(self.Q_pred))
                a_winner = np.argwhere(self.Q_pred == np.amax(self.Q_pred))

                if len(a_winner) > 1:
                    move = self.get_direction(
                        a_winner[np.random.randint(0, len(a_winner))][0])
                else:
                    move = self.get_direction(
                        a_winner[0][0])
            else:
                # Random:
                move = self.get_direction(np.random.randint(0, 4))

            # Save last_action
            self.last_action = self.get_value(move)

            legal = state.getLegalActions(0)
            if move in legal:
                keepLooking = False

        return move

    def get_value(self, direction):
        if direction == Directions.NORTH:
            return 0.
        elif direction == Directions.EAST:
            return 1.
        elif direction == Directions.SOUTH:
            return 2.
        else:
            return 3.

    def get_direction(self, value):
        if value == 0.:
            return Directions.NORTH
        elif value == 1.:
            return Directions.EAST
        elif value == 2.:
            return Directions.SOUTH
        else:
            return Directions.WEST
            
    def observation_step(self, state):
        if self.last_action is not None:
            # Process current experience state
            self.last_state = self.current_state
            self.current_state = self.getImageFromState(state)

            # Process current experience reward
            self.current_score = state.getScore()
            reward = self.current_score - self.last_score
            self.last_score = self.current_score

            if reward > 20:
                self.last_reward = 50.    # Eat ghost   (Yum! Yum!)
            elif reward > 0:
                self.last_reward = 10.    # Eat food    (Yum!)
            elif reward < -10:
                self.last_reward = -500.  # Get eaten   (Ouch!) -500
                self.won = False
            elif reward < 0:
                self.last_reward = -1.    # Punish time (Pff..)

            
            if(self.terminal and self.won):
                self.last_reward = 100.
            self.ep_rew += self.last_reward

            # Store last experience into memory 
            experience = (self.last_state, float(self.last_reward), self.last_action, self.current_state, self.terminal)
            self.replay_mem.append(experience)
            if len(self.replay_mem) > self.params['mem_size']:
                self.replay_mem.popleft()

            # Save model
            if(params['save_file']):
                if self.local_cnt > self.params['train_start'] and self.local_cnt % self.params['save_interval'] == 0:
                    self.qnet.save_ckpt('saves/model-' + params['save_file'] + "_" + str(self.cnt) + '_' + str(self.numeps))
                    print('Model saved')

            # Train
            self.train()

        # Next
        self.local_cnt += 1
        self.frame += 1
        self.params['eps'] = max(self.params['eps_final'],
                                 1.00 - float(self.cnt)/ float(self.params['eps_step']))


    def observationFunction(self, state):
        # Do observation
        self.terminal = False
        self.observation_step(state)

        return state

    def final(self, state):
        # Next
        self.ep_rew += self.last_reward

        # Do observation
        self.terminal = True
        self.observation_step(state)

        # Print stats
        log_file = open('./logs/'+str(self.general_record_time)+'-l-'+str(self.params['width'])+'-m-'+str(self.params['height'])+'-x-'+str(self.params['num_training'])+'.log','a')
        log_file.write("# %4d | steps: %5d | steps_t: %5d | t: %4f | r: %12f | e: %10f " %
                         (self.numeps,self.local_cnt, self.cnt, time.time()-self.s, self.ep_rew, self.params['eps']))
        log_file.write("| Q: %10f | won: %r \n" % ((max(self.Q_global, default=float('nan')), self.won)))
        sys.stdout.write("# %4d | steps: %5d | steps_t: %5d | t: %4f | r: %12f | e: %10f " %
                         (self.numeps,self.local_cnt, self.cnt, time.time()-self.s, self.ep_rew, self.params['eps']))
        sys.stdout.write("| Q: %10f | won: %r \n" % ((max(self.Q_global, default=float('nan')), self.won)))
        sys.stdout.flush()

    def train(self):
        # Train
        if (self.local_cnt > self.params['train_start']):
            batch = random.sample(self.replay_mem, self.params['batch_size'])
            batch_s = [] # States (s)
            batch_r = [] # Rewards (r)
            batch_a = [] # Actions (a)
            batch_n = [] # Next states (s')
            batch_t = [] # Terminal state (t)

            for i in batch:
                batch_s.append(np.array(i[0]))
                batch_r.append(i[1])
                batch_a.append(i[2])
                batch_n.append(np.array(i[3]))
                batch_t.append(i[4])
            batch_s = np.array(batch_s)
            batch_r = np.array(batch_r)
            batch_a = self.get_onehot(np.array(batch_a))
            batch_n = np.array(batch_n)
            batch_t = np.array(batch_t)

            self.cnt, self.cost_disp = self.qnet.train(batch_s, batch_a, batch_t, batch_n, batch_r)


    def get_onehot(self, actions):
        """ Create list of vectors with 1 values at index of action in list """
        actions_onehot = np.zeros((self.params['batch_size'], 4))
        for i in range(len(actions)):                                           
            actions_onehot[i][int(actions[i])] = 1      
        return actions_onehot   

    def registerInitialState(self, state): # inspects the starting state

        # Reset reward
        self.last_score = 0
        self.current_score = 0
        self.last_reward = 0.
        self.ep_rew = 0

        # Reset state
        self.last_state = None
        self.current_state = self.getImageFromState(state)
        # Reset actions
        self.last_action = None

        # Reset vars
        self.terminal = None
        self.won = True
        self.Q_global = []
        self.delay = 0

        # Next
        self.frame = 0
        self.numeps += 1

    def getAction(self, state):
        move = self.getMove(state)

        return move
