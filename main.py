#!/usr/bin/env python
import sys
import os
import random
import string
import time
import pexpect

from functools import partial

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
    '''If any pattern matches, return its index.
    If it has capturing groups, return (index, matches) instead.
    If it timed out, return False.
    If it got an EOF, raise an exception.
    '''
    try:
        result = c.expect(pattern, timeout)
        if c.match.groups():
            return (result+1, c.match.groups())
        return result+1
    except pexpect.TIMEOUT:
        return False
    except pexpect.EOF:
        raise

command = ['crawl']

options = dict(name=random_name(),
               species='Felid',
               background='Berserker',
               )

extra_options = dict(
                auto_eat_chunks="true",
                autofight_throw="true",
                autopickup_exceptions=">skeleton",
                autopickup_no_burden="false",
                char_set='unicode',
                clean_map="true",
                # clear_messages="true",
                confirm_butcher="never",
                easy_eat_chunks="true",
                easy_eat_gourmand="true",
                explore_delay="-1",
                explore_greedy="true",
                note_all_skill_levels="true",
                runrest_ignore_monster=".*:2",
                show_more='false',
                show_newturn_mark='false',
                trapwalk_safe_hp="'dart:15, needle:25, spear:50'",
                travel_delay="-1",
                travel_key_stop="false",
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
        escape()
        redraw()
        if expect(child, "Unknown command"):
            # Back to the top
            break
        else:
            count += 1
            info("Trying to clear commands.")
            if count > 10:
                # Hung up on that damn stat pick line
                child.send("s")

def note(message):
    # Add a note
    child.send(":"+message)
    enter()


fightin = "fightin"
explorin = "explorin"
lootin = "lootin"
dumpin = "dumpin"

enter = partial(child.sendcontrol, "m")
tab = partial(child.sendcontrol, "i")
escape = partial(child.sendcontrol, "[")

# import ANSI
# term = ANSI.ANSI()

state = fightin
while True:
    try:
        time.sleep(1)
        # Reset our input back to a known state.
        reset()

        # Make sure we redraw the display.
        redraw()


        # TODO: Check if we've spent too much time here, (1400-117*depth)

        # height, width = child.getwinsize()
        # screentext = ""
        # import signal

        # donereading = False
        # def handler(x, y):
            # info("done reading")
            # donereading = True
            # signal.alarm(0)

            # import terminal
            # screentext_plain = terminal.StripAnsiText(screentext)
            # info(str(screentext_plain))

        # signal.signal(signal.SIGALRM, handler)
        # while not donereading:
            # signal.alarm(1)
            # info("read")
            # screentext += child.read(1)

        info(state.upper())

        if state is dumpin:

            # Check for burden
            # Drop useless crap

            # Drop all corpses: d&(enter)
            reset()
            child.send("d")
            result = expect(child, ["Burden", ])
            if result in (1,):
                # Drop all the carrion
                child.send("&")
                if expect(child, "turn"):
                    enter()
            else:
                info("No carrion to drop.")
            reset()

            # Butcher all corpses.
            while True:
                if expect(child, ["There isn't anything to butcher here",
                                  "There isn't anything here",
                                  ]):
                    info("Breaking out of butcher loop.")
                    break
                else:
                    info("Butchering corpse.")
                    child.send("c")
                    if expect(child, "If you dropped the corpse"):
                        child.send("d")
                        if expect(child, "turn"):
                            enter()
                        else:
                            reset()
                        continue

            # Check for hunger
            result = expect(child, ["Starving", "Hungry"])
            if result:
                # Drop all our comestables to make eating easier
                child.send("d")
                if expect(child, ["Burden:", "Comestables", ]):
                    child.send("%")
                    enter()
                    reset()

                    # Eat something on the floor
                    child.send('e')
                    if expect(child, "Eat a"):
                        child.send('y')
                        if expect(child, "You finish eating"):
                            # Pick up all our food.
                            child.send('ga')

            # If have more than 3 of one scroll,
            # And we don't know what identify scrolls are yet,
            # It's probably identify, so use it on the most interesting
            # items in our inventory.

            # No more inventory business,
            # so go back to looting to make sure we pick up anything
            # that's laying around.
            state = explorin
            continue

        elif state is fightin:
            # HOLY CRAP ENEMIES
            tab() # Tab
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
                info("Can't get to it, so walk up to a .")
                # Override autoexplore, don't stop travel if there are monsters!
                child.send("X<")
                enter()
                state = explorin
                continue
            else:
                info('MOAR ENEMIES FIGHT ON')
                state = fightin # Set it just in case
                continue

        elif state is lootin:
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
                # Search for everything, except skeletons.
                child.send(". !!skeleton")
                enter()

                findchecks = ["Can't find anything matching that",
                              ".*stacks by dist.*",
                              ]
                findresult = expect(child, findchecks)
                if findresult is 1:
                    info("No more loot. Clearing out the backpack.")
                    state = dumpin
                    continue
                elif findresult is 2:
                    info("Found some loot!")
                    child.send("a")
                    info("Try to walk there.")
                    enter()
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
                        enter()
                        enter()
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

        elif state is explorin:
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
                enter()
                continue
            elif result in (3, 4, 5):
                info("Too many monsters to wander around like this!")
                state = fightin
                continue
            elif result is 6:
                info("Starving to death.")
                state = dumpin
                continue

    except (KeyboardInterrupt, pexpect.EOF):
        # Interactive mode if ctrl+c. ctrl+] to give back control.
        try:
            child.interact()
        except:
            import pdb; pdb.set_trace()
