# -*- coding: utf-8 -*-

import os
import sys
import hashlib
import pickle
import logging
import yaml


SRC_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "..")
APP_PATH = SRC_PATH
LOG_PATH = os.path.join(APP_PATH, "logs")
CACHE_PATH = os.path.join(APP_PATH, "temp", "cache")
HAC_CACHE_PATH = os.path.join(APP_PATH, "temp", "hac")
CONFIG = {}


def _read_config():
    with open(os.path.join(APP_PATH, "swagger", "swagger.yaml"), "r") as stream:
        return yaml.load(stream)


def init_config():
    global CONFIG
    CONFIG = _read_config()


def app_host():
    return CONFIG["host"].split(":")[0]


def app_port():
    return int(CONFIG["host"].split(":")[1])


def substitute_host_in_swagger(old_host, new_host):
    with open(os.path.join(APP_PATH, 'swagger', 'swagger.yaml'), 'r') as f:
        new_content = f.read()
        new_content = new_content.replace(old_host, new_host)
    with open(os.path.join(APP_PATH, 'swagger', 'swagger.yaml'), 'w+') as f:
        f.write(new_content)
    return new_content


def is_int_or_float(str_value):
    value = int_or_float_from_string(str_value)
    return value is not None and isinstance(value, (int, float))


def int_or_float_from_string(str_value):
    assert(isinstance(str_value, str))
    try:
        value = int(str_value)
    except ValueError:
        try:
            value = float(str_value)
        except ValueError:
            value = None
    return value


def replace_german_umlaut(s):
    return s.replace(u'ß', 'ss').replace(u'ä', 'ae').replace(u'ö', 'oe').replace(u'ü', 'ue')


def merge_two_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


class ExitCode(object):
    SUCCESS = 0
    FAILED = 1


def setup_logging(log_level):
    import platform
    logging.basicConfig(
        filename=None, #os.path.join(helper.LOG_PATH, "automatic_tagger.log"),
        level=log_level,
        format='%(asctime)s: %(levelname)7s: [%(name)s]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # based on: http://stackoverflow.com/a/1336640
    if platform.system() == 'Windows':
        logging.StreamHandler.emit = add_coloring_to_emit_windows(logging.StreamHandler.emit)
    else:
        logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)


def make_dir_if_not_exists(path):
    paths = [path] if type(path) is not list else path
    for path in paths:
        try:
            if not os.path.exists(path):
                os.makedirs(path)
            elif not os.path.isdir(path):
                error("Invalid path '{0}'. This is NO directory.".format(path))
        except (Exception, e):
            error(e)


def error(msg):
    print("ERROR: {0}".format(msg))
    sys.exit(ExitCode.FAILED)


def _cache_file_paths(cached_file_name_prefix):
    cached_tags_file_path = os.path.join(CACHE_PATH, cached_file_name_prefix + "_tags.pickle")
    cached_posts_file_path = os.path.join(CACHE_PATH, cached_file_name_prefix + "_posts.pickle")
    return cached_tags_file_path, cached_posts_file_path


def cache_exists_for_preprocessed_tags_and_posts(cache_file_name_prefix):
    cached_tags_file_path, cached_posts_file_path = _cache_file_paths(cache_file_name_prefix)
    return os.path.exists(cached_tags_file_path) and os.path.exists(cached_posts_file_path)


def write_preprocessed_tags_and_posts_to_cache(cache_file_name_prefix, tags, posts):
    cache_tags_file_path, cache_posts_file_path = _cache_file_paths(cache_file_name_prefix)
    with open(cache_tags_file_path, 'wb') as fp:
        pickle.dump(tags, fp)
    with open(cache_posts_file_path, 'wb') as fp:
        pickle.dump(posts, fp)


def load_preprocessed_tags_and_posts_from_cache(cache_file_name_prefix):
    cache_tags_file_path, cache_posts_file_path = _cache_file_paths(cache_file_name_prefix)
    assert cache_tags_file_path is not None
    assert cache_posts_file_path is not None
    with open(cache_tags_file_path, 'r') as fp:
        cached_preprocessed_tags = pickle.load(fp)
    with open(cache_posts_file_path, 'r') as fp:
        cached_preprocessed_posts = pickle.load(fp)

    def relink_preprocessed_posts_and_tags(tags, posts):
        # tag instances are not same as those assigned to the posts after deserialization!
        tag_name_tag_map = dict(map(lambda t: (t.name, t), tags))
        for p in posts:
            n_tags = len(p.tag_set)
            p.tag_set = set(map(lambda t: tag_name_tag_map[t.name], p.tag_set))
            assert n_tags == len(p.tag_set)

    relink_preprocessed_posts_and_tags(cached_preprocessed_tags, cached_preprocessed_posts)
    return cached_preprocessed_tags, cached_preprocessed_posts


def compute_hash_of_file(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def clear_tag_predictions_for_posts(posts):
    for post in posts:
        post.tag_set_prediction = None


# based on: http://stackoverflow.com/a/1336640
# now we patch Python code to add color support to logging.StreamHandler
def add_coloring_to_emit_windows(fn):
    # add methods we need to the class
    def _out_handle(self):
        import ctypes
        return ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE) #@UndefinedVariable
    _ = property(_out_handle)

    def _set_color(self, code):
        import ctypes
        # constants from WinAPI
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandle(self.STD_OUTPUT_HANDLE) #@UndefinedVariable
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code) #@UndefinedVariable

    setattr(logging.StreamHandler, '_set_color', _set_color)

    def new(*args):
        FOREGROUND_BLUE      = 0x0001 # text color contains blue.
        FOREGROUND_GREEN     = 0x0002 # text color contains green.
        FOREGROUND_RED       = 0x0004 # text color contains red.
        FOREGROUND_INTENSITY = 0x0008 # text color is intensified.
        FOREGROUND_WHITE     = FOREGROUND_BLUE|FOREGROUND_GREEN |FOREGROUND_RED
        # winbase.h
        STD_INPUT_HANDLE = -10
        STD_OUTPUT_HANDLE = -11
        STD_ERROR_HANDLE = -12

        # wincon.h
        FOREGROUND_BLACK     = 0x0000
        FOREGROUND_BLUE      = 0x0001
        FOREGROUND_GREEN     = 0x0002
        FOREGROUND_CYAN      = 0x0003
        FOREGROUND_RED       = 0x0004
        FOREGROUND_MAGENTA   = 0x0005
        FOREGROUND_YELLOW    = 0x0006
        FOREGROUND_GREY      = 0x0007
        FOREGROUND_INTENSITY = 0x0008 # foreground color is intensified.

        BACKGROUND_BLACK     = 0x0000
        BACKGROUND_BLUE      = 0x0010
        BACKGROUND_GREEN     = 0x0020
        BACKGROUND_CYAN      = 0x0030
        BACKGROUND_RED       = 0x0040
        BACKGROUND_MAGENTA   = 0x0050
        BACKGROUND_YELLOW    = 0x0060
        BACKGROUND_GREY      = 0x0070
        BACKGROUND_INTENSITY = 0x0080 # background color is intensified.     

        levelno = args[1].levelno
        if(levelno>=50):
            color = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY 
        elif(levelno>=40):
            color = FOREGROUND_RED | FOREGROUND_INTENSITY
        elif(levelno>=30):
            color = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
        elif(levelno>=20):
            color = FOREGROUND_GREEN
        elif(levelno>=10):
            color = FOREGROUND_MAGENTA
        else:
            color =  FOREGROUND_WHITE
        args[0]._set_color(color)

        ret = fn(*args)
        args[0]._set_color( FOREGROUND_WHITE )
        #print "after"
        return ret
    return new

def add_coloring_to_emit_ansi(fn):
    # add methods we need to the class
    def new(*args):
        levelno = args[1].levelno
        if levelno >= 50:
            color = '\x1b[31m' # red
        elif(levelno>=40):
            color = '\x1b[31m' # red
        elif(levelno>=30):
            color = '\x1b[33m' # yellow
        elif(levelno>=20):
            color = '\x1b[32m' # green 
        elif(levelno>=10):
            color = '\x1b[35m' # pink
        else:
            color = '\x1b[0m' # normal
        args[1].msg = color + args[1].msg +  '\x1b[0m'  # normal
        return fn(*args)
    return new
