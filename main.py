#!/usr/bin/env python
import sys
import os
import random
import string
import time
import pexpect

import logging
LOGGER = logging.getLogger('crawlbot')
hdlr = logging.FileHandler('crawlbot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
LOGGER.addHandler(hdlr)
LOGGER.setLevel(logging.DEBUG)
info = LOGGER.info

def random_name(length=8):
    name = ""
    while len(name) < length:
        name += random.choice(string.ascii_lowercase)
    return name.title()

def expect(c, pattern, timeout=0.1):
    try:
        result = c.expect(pattern, timeout)
        return result+1
    except pexpect.TIMEOUT:
        return False

command = ['crawl']

options = dict(name=random_name(),
               species='Human',
               background='fighter',
               )

extra_options = dict(
                weapon="'short sword'",
                clean_map="true",
                view_max_width="64",
                view_max_height="64",
                view_lock="true",
                explore_delay="-1",
                explore_greedy="true",
                confirm_butcher="never",
                travel_delay="-1",
                char_set='unicode',
                show_more='false',
                show_newturn_mark='false',
                trapwalk_safe_hp="'dart:15, needle:25, spear:50'",
               )

for option, value in options.iteritems():
    command.append('-'+option+' '+value)

for option, value in extra_options.iteritems():
    command.append('-extra-opt-last '+option+'='+value)

command = ' '.join(command)
info(command)
child = pexpect.spawn(command)
child.logfile = sys.stdout

child.expect(".*Welcome, .* the .*")

fightin = True
explorin = True
lootin = True
while True:
    try:
        os.system("clear") # idk
        child.sendcontrol("r")

        # Clear any commands that got half-baked.
        while True:
            if expect(child, "Unknown command"):
                # Back to the top
                break
            else:
                info("Trying to clear commands.")
                child.send(chr(27)) # Escape

        # TODO: Check if we've spent too much time here, (1400-117*depth)

        if fightin:
            info("FIGHTIN")
            # HOLY CRAP ENEMIES
            child.sendcontrol("i") # Tab
            lootin = False
            explorin = False
            if expect(child, "No target in view"):
                info('No more targets, go back to lootin.')
                fightin = False
                lootin = True
                continue
            elif expect(child, "You are too injured to fight blindly"):
                info("Holy crap, we got the tar beaten out of us.")
                # Wait it out. Fuq da police.
                # TODO: Probably shouldn't wait it out.
                child.send("s")
                continue
            elif expect(child, "You have reached level"):
                if expect(child, "Increase .*trength"):
                    child.send("s") # Strength
                    continue
            else:
                info('MOAR ENEMIES FIGHT ON')
                fightin = True
                lootin = False
                explorin = False
                continue

        if lootin:
            info("LOOTIN")
            # Coast is clear, look for loot

            # Find all the items
            info("Searching for everything.")
            child.sendcontrol("f")
            if expect(child, ".*Search for what"):
                child.send(".")
                child.sendcontrol('m')
            elif expect(child, ".*A .* is nearby"):
                info("Found a monster, so don't loot right now.")
                fightin = True
                lootin = False
                continue
            else:
                info("Search prompt never showed.")

            if expect(child, ".*Can't find anything matching that"):
                lootin = False
                explorin = True
                info("No more loot. Going back to exploring.")
                continue

            if expect(child, ".*stacks by dist.*"):
                info("Found some loot!")
                child.send("a")
                info("Walk to the first item, or back out if we have all of them.")
                child.sendcontrol('m')
                if not expect(child, "You see here"):
                    # Didn't find the item, so we probably got stuck on the map.
                    child.sendcontrol('m')
                    child.sendcontrol('m')
                    child.sendcontrol(']')
                    child.sendcontrol(']')
                    child.sendcontrol(']')
                if expect(child, "Infinite lua loop detected"):
                    lootin = False
                    explorin = True
                    continue
                if expect(child, ".*don't know how to get there.*"):
                    info("Couldn't get there.")
                    explorin = True
                    lootin = False
                    continue

            if expect(child, [".*A .* comes into view", "There are monsters nearby"]):
                fightin = True
                lootin = False
                explorin = False
                info("OSHIT A MONSTER")
                continue

            info("No monsters, so go ahead and pick it up")
            child.send(",")
            if expect(child, [".*stacks by dist.*", ".*Pick up a.*"]):
                info("Multiple things, so grab the topmost.")
                child.send("a")
            if expect(child, "There are no items here."):
                info("Got hung up on a trap, bailing.")
                explorin = True
                lootin = False
                continue

        if explorin:
            info("EXPLORIN")
            # Got all the loot, resume wandering.
            while True:
                child.send("o")
                checks = ["Partly explored", "Done exploring"]
                checks += ["A .* comes into view", "A.* is nearby", "There are monsters nearby"]
                result = expect(child, checks)
                if result == 1:
                    info("Partly explored the map. Resetting and trying again.")
                    child.sendcontrol('c')
                    child.send("X")
                    child.sendcontrol('e') # Erase any travel exclusions.
                    child.sendcontrol('f')
                    child.send("y")
                    child.sendcontrol(']')
                    break
                elif result == 2:
                    info("Done exploring. Heading downstairs.")

                    # Add a note
                    child.send(":Done exploring level.")
                    child.sendcontrol('m')

                    # Head downstairs.
                    # Go, Dungeon, Down
                    child.send("GD>")
                    child.sendcontrol('m')
                    break
                elif result > 2:
                    info("Too many monsters to wander around like this!")
                    fightin = True
                    lootin = True
                    break
        # time.sleep(3)
    except KeyboardInterrupt:
        child.interact()
