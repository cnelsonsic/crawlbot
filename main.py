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
    except pexpect.TIMEOUT:
        raise KeyboardInterrupt

command = ['crawl']

options = dict(name=random_name(),
               species='Human',
               background='fighter',
               )

extra_options = dict(
                auto_eat_chunks="true",
                # autopickup_exceptions=">skeleton",
                char_set='unicode',
                clean_map="true",
                confirm_butcher="never",
                easy_eat_chunks="true",
                easy_eat_gourmand="true",
                explore_delay="-1",
                explore_greedy="true",
                note_all_skill_levels="true",
                show_more='false',
                show_newturn_mark='false',
                trapwalk_safe_hp="'dart:15, needle:25, spear:50'",
                travel_delay="-1",
                view_lock="true",
                view_max_height="64",
                view_max_width="64",
                weapon="'short sword'",
               )

for option, value in options.iteritems():
    command.append('-'+option+' '+value)

for option, value in extra_options.iteritems():
    command.append('-extra-opt-last '+option+'='+value)

command = ' '.join(command)
info(("-"*30)+" New Game "+("-"*30))
info(command)
child = pexpect.spawn(command)
child.logfile = sys.stdout

child.expect(".*Welcome, .* the .*")

def redraw():
    os.system("clear") # idk
    child.sendcontrol("r")

def reset():
    '''Reset the input back to a known state.'''
    # Clear any commands that got half-baked.
    count = 0
    while True:
        if expect(child, "Unknown command"):
            # Back to the top
            break
        else:
            count += 1
            info("Trying to clear commands.")
            child.send(chr(27)) # Escape
            if count > 10:
                # Hung up on that damn stat pick line
                child.send("s")

def note(message):
    # Add a note
    child.send(":"+message)
    child.sendcontrol('m')


fightin = "fightin"
explorin = "explorin"
lootin = "lootin"

state = fightin
while True:
    try:
        # Make sure we redraw the display.
        redraw()

        # Reset our input back to a known state.
        reset()

        # TODO: Check if we've spent too much time here, (1400-117*depth)

        # Check for hunger
        # Drop all corpses
        # Butcher all corpses
        # Pick up everything: ,a
        # Starving, Near Starving, Very Hungry
        # ey
        # If we see "Comestables", bail until we get some more chunks.

        # Check for burden
        # Drop useless crap

        # If have more than 3 of one scroll,
        # And we don't know what identify scrolls are yet,
        # It's probably identify, so use it on the most interesting
        # items in our inventory.

        info(state.upper())
        if state is fightin:
            # HOLY CRAP ENEMIES
            child.sendcontrol("i") # Tab
            checks = ["No target in view",
                      "You are too injured to fight blindly",
                      "You have reached level",
                      "Increase .*trength",
                      "You die",
                      "Failed to move towards target",
                      ]
            result = expect(child, checks)
            if result is 1:
                info("No more targets, go back to lootin'.")
                state = lootin
                continue
            elif result is 2:
                info("Holy crap, we got the tar beaten out of us.")
                # Wait it out. Fuq da police.
                # TODO: Probably shouldn't wait it out.
                child.send("s")
                continue
            elif result is 3:
                info("Gained a level!")
            elif result is 4:
                child.send("s") # Strength
                continue
            elif result is 5:
                info("Died. :(")
                raise KeyboardInterrupt
            elif result is 6:
                info("Can't get to it, so try to explore.")
                state = explorin
                continue
            else:
                info('MOAR ENEMIES FIGHT ON')
                state = fightin # Set it just in case
                continue

        if state is lootin:
            # Coast is clear, look for loot

            # Find all the items
            info("Searching for everything.")
            child.sendcontrol("f")
            checks = ["Search for what",
                      "A.* is nearby",
                      "A.* comes into view",
                      "There are monsters nearby",
                      ]
            result = expect(child, checks)
            if result is 1:
                # Search for everything
                child.send(".")
                child.sendcontrol('m')

                findchecks = ["Can't find anything matching that",
                              ".*stacks by dist.*",
                              ]
                findresult = expect(child, findchecks)
                if findresult is 1:
                    info("No more loot. Going back to exploring.")
                    state = explorin
                    continue
                elif findresult is 2:
                    info("Found some loot!")
                    child.send("a")
                    info("Walk to the first item, or back out if we have all of them.")
                    child.sendcontrol('m')
                    lootchecks = ["You see here",
                                  "Infinite lua loop detected",
                                  ".*don't know how to get there.*",
                                  ]
                    lootresult = expect(child, lootchecks)
                    if lootresult in (2, 3):
                        if lootresult is 3:
                            info("Couldn't get there.")
                        elif lootresult is 2:
                            info("Got stuck in an infinite lua loop.")
                        state = explorin
                        continue
                    else:
                        # Didn't find the item, so we probably got stuck on the map.
                        info("Maybe stuck in the map.")
                        child.sendcontrol('m')
                        child.sendcontrol('m')
                        reset()

                info("No monsters, so go ahead and pick it up")
                child.send(",")
                pickupchecks = [".*stacks by dist.*",
                                "Pick up a.*",
                                "There are no items here.",
                                "There are several objects here",
                                ]
                pickupresult = expect(child, pickupchecks)
                if pickupresult in (1, 2, 4):
                    info("Multiple things, so grab them all.")
                    child.send("a")
                elif pickupresult is 3:
                    info("Got hung up on a trap, bailing.")
                    state = explorin
                    continue
            elif result is (2, 3, 4):
                info("Found a monster, so don't loot right now.")
                state = fightin
                continue
            else:
                info("Search prompt never showed.")
                continue

        if state is explorin:
            # Got all the loot, resume wandering.

            checks = ["Partly explored",
                      "Done exploring",
                      "A.* comes into view",
                      "A.* is nearby",
                      "There are monsters nearby",
                      "You need to eat something",
                      ]

            # Before wandering off, rest until fully healed.

            child.send("o")
            result = expect(child, checks)
            if result is 1:
                info("Partly explored the map. Resetting and trying again.")
                child.send("X")
                child.sendcontrol('e') # Erase any travel exclusions.
                child.sendcontrol('f') # Forget level map
                child.send("y") # Yes, I'm sure.
                reset()
                continue
            elif result is 2:
                info("Done exploring. Heading downstairs.")

                child.send("GD$>") # Go, Dungeon, Last Visited, Down
                child.sendcontrol('m')
                continue
            elif result in (3, 4, 5):
                info("Too many monsters to wander around like this!")
                state = fightin
                continue
            elif result is 6:
                info("Starving to death.")
                continue

    except KeyboardInterrupt:
        # Interactive mode if ctrl+c. ctrl+] to give back control.
        child.interact()
