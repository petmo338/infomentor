import configparser
import os

_config = None

_defaults = {
    "pushover": {"apikey": ""},
    "general": {
        "secretkey": "1loTus123",
        "baseurl": "",
        "adminmail": "",
        "im1url": "https://infomentor.se/swedish/production/mentor",
        "mimrul": "https://hub.infomentor.se",
    },
    "smtp": {"server": "", "username": "", "password": ""},
    "healthcheck": {"url": ""},
}


def _set_defaults(config):
    config = _defaults


def load(cfg_file="/infomentor.ini"):
    """Load the config from the file"""
    global _config
    if _config is None:
        _config = configparser.ConfigParser()
        _config.read_dict(_defaults)
        if not os.path.isfile(cfg_file):
            _set_defaults(_config)
            save(cfg_file)
            
        _config.read_file(open(cfg_file))
    return _config


def save(cfg_file):
    """Write config to file"""
    global _config
    with open(cfg_file, "w+") as f:
        _config.write(f)
