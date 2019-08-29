#!/usr/bin/python3
from configparser import ConfigParser

class MyConfigParser(ConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.__init__(self,defaults=None)

    def optionxform(self, optionstr):
        return optionstr
    
    # def write(self, fp):
        # if self._defaults:
            # fp.write("[%s]\n" % DEFAULTSECT)
            # for (key, value) in self._defaults.items():
                # fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
                # fp.write("\n")
            # for section in self._sections:
                # fp.write("[%s]\n" % section)
