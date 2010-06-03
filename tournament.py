#!/usr/bin/env python

import sys
import ConfigParser
from cells import Game

config = ConfigParser.RawConfigParser()

def get_mind(name):
    full_name = 'minds.' + name
    __import__(full_name)
    mind = sys.modules[full_name]
    mind.name = name
    return mind

bounds = None  # HACK
symmetric = None
mind_list = None

def main():
    global bounds, symmetric, mind_list
    try:
        config.read('tournament.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))

    except Exception as e:
        print 'Got error: %s' % e
        config.add_section('minds')
        config.set('minds', 'minds', 'mind1,mind2')
        config.add_section('terrain')
        config.set('terrain', 'bounds', '300')
        config.set('terrain', 'symmetric', 'true')

        with open('tournament.cfg', 'wb') as configfile:
            config.write(configfile)

        config.read('tournament.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))
    mind_list = [(n, get_mind(n)) for n in minds_str.split(',')]

    # accept command line arguments for the minds over those in the config
    try:
        if len(sys.argv)>2:
            mind_list = [(n,get_mind(n)) for n in sys.argv[1:] ]
    except (ImportError, IndexError):
        pass


if __name__ == "__main__":
    main()
    scores = [0 for x in mind_list]
    tournament_list = [[mind_list[a], mind_list[b]] for a in range(len(mind_list)) for b in range (a)]
    for pair in tournament_list:
        game = Game(bounds, pair, symmetric, 1000)
        while game.winner == None:
            game.tick()
        if game.winner >= 0:
            idx = mind_list.index(pair[game.winner])
            scores[idx] += 3
        if game.winner == -1:
            idx = mind_list.index(pair[0])
            scores[idx] += 1
            idx = mind_list.index(pair[1])
            scores[idx] += 1
        print scores
        print [m[0] for m in mind_list]

