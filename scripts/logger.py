"""
:description: These classes provide logging functionality for agents
"""

import collections 
import datetime
import matplotlib.pyplot as plt
import numpy as np
import os
import pickle
import sys

LOGGING_DIRECTORY = '../logs'
MAXIMUM_WEIGHT_MAGNITUDE = 1000

def moving_average(values, window_size):
    """
    :description: computes a moving average
    """
    if len(values) == 0:
        print 'the list given to moving average cannot be empty but is'
        return []

    window = np.ones(int(window_size))/float(window_size)
    values = np.hstack((np.repeat(values[0], int(window_size)), values, np.repeat(values[-1], int(window_size))))
    average = np.convolve(values, window, 'same').tolist()
    return average[window_size:-window_size]

class Logger(object):
    """
    :description: tracks and logs information about an agent
    """
    
    def __init__(self, agent_name, logging=True):
        """
        :type agent_name: string 
        :param agent_name: name of the agent whose information is being logged

        :type logging: boolean
        :param logging: whether or not to actually record any information
        """
        self.agent_name = agent_name
        self.actions = []
        self.rewards = []
        self.episode_rewards = []
        self.losses = []
        self.states = []
        self.state_values = collections.defaultdict(lambda: [])
        self.weights = None
        self.log_dir = None
        self.logging = logging

    def log_action(self, action):
        self.actions.append(action)

    def log_reward(self, reward):
        self.rewards.append(reward)

    def log_loss(self, loss):
        self.losses.append(loss)

    def log_weights(self, weights):
        self.weights = weights
        max_magnitude = np.max(np.abs(weights.values()))

        if max_magnitude > MAXIMUM_WEIGHT_MAGNITUDE:
            except_string = 'Agent weights have surpassed reasonable values. Max weight: {}'.format(max_magnitude)
            raise ValueError(except_string)

    def log_epoch(self, epoch):
        """
        :description: records the information so far collected

        :type epoch: int
        :param epoch: the current epoch number
        """
        if not self.logging:
            return

        if self.log_dir is None:
            self.create_log_dir()

        self.record_stat('actions', self.actions, epoch)
        self.record_stat('rewards', self.episode_rewards, epoch)
        self.record_stat('losses', self.losses, epoch)
        self.record_weights(self.weights, epoch)

    def finish_episode(self):
        """
        :description: performs tasks associated with the ending of an epidoe
        """
        self.episode_rewards.append(np.sum(self.rewards))
        self.rewards = []

    def record_stat(self, name, values, epoch):
        """
        :description: saves values to a file and also plots them

        :type name: string
        :param name: name of the value being recorded

        :type values: list
        :param values: values to record

        :type epoch: int
        :param epoch: current epoch number
        """
        self.save_stat(name, values, epoch)
        self.plot_stat(name, values, epoch)

    def save_stat(self, name, values, epoch):
        """
        :description: saves a set of values to a file in npz format under the name 'values'
        """
        filename = '{}'.format(name)
        filepath = os.path.join(self.log_dir, filename)
        np.savez(filepath, values=values)

    def plot_stat(self, name, values, epoch):
        """
        :description: plots the provided values
        """
        filename = '{}_graph.png'.format(name)
        filepath = os.path.join(self.log_dir, filename)
        plt.figure()
        plt.scatter(np.arange(len(values)), values)
        plt.plot(moving_average(values, 50), c='r')
        plt.xlabel('Updates')
        plt.ylabel(name)
        plt.savefig(filepath)

    def record_weights(self, weights, epoch):
        """
        :description: saves the weights to a file
        """
        filename = 'weights_epoch_{}.pkl'.format(epoch)
        filepath = os.path.join(self.log_dir, filename)
        with open(filepath, 'wb') as f:
            pickle.dump(weights, f, pickle.HIGHEST_PROTOCOL)

    def create_log_dir(self):
        """
        :description: creates a directory in which to log information for the current agent
        """
        dir_name = '{}_{}'.format(self.agent_name, datetime.datetime.now().isoformat())
        dir_path = os.path.join(LOGGING_DIRECTORY, dir_name)
        os.mkdir(dir_path)
        self.log_dir = dir_path

    def log_value_string(self, value_string):
        """
        :description: prints a string to a file. The string, when formatted, gives the values of different states in the mdp.
        """
        if self.log_dir is None:
            self.create_log_dir()

        filename = 'value_image.txt'
        filepath = os.path.join(self.log_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(value_string)

    def log_values(self, V):
        """
        :description: keeps track of how the q_values change over time
        """
        mean_value = np.mean(V.values())
        max_value = np.max(V.values())
        min_value = np.min(V.values())
        self.state_values['mean'].append(mean_value)
        self.state_values['max'].append(max_value)
        self.state_values['min'].append(min_value)
            
        self.plot_values()

    def plot_values(self):
        """
        :description: plot mean, max, and min state values so far
        """
        filename = 'state_values_graph.png'
        filepath = os.path.join(self.log_dir, filename)
        plt.figure()
        plt.xlabel('Updates')
        plt.ylabel('V(s)')
        count = 0
        plt.scatter(np.arange(len(self.state_values['mean'])), self.state_values['mean'], c='b')
        plt.scatter(np.arange(len(self.state_values['max'])), self.state_values['max'], c='r')
        plt.scatter(np.arange(len(self.state_values['min'])), self.state_values['min'], c='g')
        plt.savefig(filepath)


class NeuralLogger(Logger):
    """
    :description: inherting class that accomodates a network based agent
    """

    def __init__(self, agent_name, logging=True):
        super(NeuralLogger, self).__init__(agent_name, logging)

    def log_epoch(self, epoch, network):
        if not self.logging:
            return

        if self.log_dir is None:
            self.create_log_dir()

        self.record_stat('actions', self.actions, epoch)
        self.record_stat('rewards', self.episode_rewards, epoch)
        self.record_stat('losses', self.losses, epoch)
        self.record_weights(epoch, network)

    def record_weights(self, epoch, network):
        """
        :description: records weights by saving them to a file

        :type epoch: int 
        :param epoch: current epoch

        :type network: any class implementing get_params()
        :param network: the networks whose weights should be saved
        """
        filename = 'network_file_epoch_{}.save'.format(epoch)
        filepath = os.path.join(self.log_dir, filename)
        params = network.get_params()
        # dump params to file

    def log_hyperparameters(self, network, policy, replay_memory):
        if self.log_dir is None:
            self.create_log_dir()

        filename = 'hyperparameters.txt'
        filepath = os.path.join(self.log_dir, filename)
        hyperparameters = {}
        hyperparameters['batch_size'] = network.batch_size
        hyperparameters['num_hidden'] = network.num_hidden
        hyperparameters['discount'] = network.discount
        hyperparameters['learning_rate'] = network.learning_rate
        hyperparameters['update_rule'] = network.update_rule
        hyperparameters['freeze_interval'] = network.freeze_interval
        hyperparameters['replay_memory_capacity'] = replay_memory.capacity

        with open(filepath, 'wb') as f:
            for k, v in hyperparameters.iteritems():
                f.write('{}: {}\n'.format(k, v))



