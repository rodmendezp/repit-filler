

def replace_game_characters(game):
    game = game.replace(' ', '_')
    game = game.replace('-', '_')
    game = game.replace("'", '_')
    game = game.replace(':', '_')
    game = game.replace('__', '_')
    return game.replace('.', '_').lower()


def params_to_queue_name(game, streamer='', user=''):
    game = replace_game_characters(game)
    if streamer or user:
        queue_name = '_%s_%s_%s' % (user, streamer, game)
    else:
        queue_name = 'game_%s' % game
    return queue_name


def params_to_routing_key(game, streamer='*', user='all'):
    game = replace_game_characters(game)
    routing_key = '%s.%s.%s' % (game, streamer, user)
    return routing_key


def routing_key_to_params(routing_key):
    first_dot = routing_key.find('.')
    second_dot = routing_key.find('.', first_dot + 1)
    game = routing_key[:first_dot]
    streamer = routing_key[first_dot + 1: second_dot]
    user = routing_key[second_dot + 1:]
    user = '' if user == 'all' else user
    return game, streamer, user
