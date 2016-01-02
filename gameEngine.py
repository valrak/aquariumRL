from _ast import mod
from graphicsHandler import GraphicsHandler
import jsonInit
from monster import *
from item import *
from mapField import *
from messageHandler import *
from eventHandler import *
from pygame.locals import *

import pygame
import sys
import pygame.locals as pg

mapmaxx = 0
mapmaxy = 0

PLAYERCREATURE = "diver"
ARENAMAPFILE = "resources/maps/arena1.csv"


mapfield = None
gameevent = None
moninfo = None
mapinfo = None
effinfo = None
iteminfo = None

# todo: item/monster rarity
# todo: level up - portal and upgrades
# todo: melee weapons
# todo: move and shoot traces graphics
# todo: small damage number bubbles in map
# todo: scoring and hiscore
# todo: ui
# todo: config file
# todo: dynamite fuse setting

class GameEngine(object):
    ALPHABET = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y', 'z']

    RESOLUTIONX = 1024
    RESOLUTIONY = 768
    SIZE = (RESOLUTIONX, RESOLUTIONY)
    SCORETABLE = [100, 300]
    turns = 0
    firingmode = False
    usemode = False
    hiscore = 0
    noscore = False
    clock = pygame.time.Clock()

    def __init__(self):
        # with open(ARENAMAPFILE, 'rb') as csvfile:
        #     csvread = csv.reader(csvfile, delimiter=';', quotechar='"')
        #     arenamap = list(csvread)
        arenamap = None
        # data load part
        # jsons
        self.resetflag = False
        self.moninfo = jsonInit.loadjson("resources/data/creatures.jsn")
        self.mapinfo = jsonInit.loadjson("resources/data/map.jsn")
        self.effinfo = jsonInit.loadjson("resources/data/effects.jsn")
        self.iteinfo = jsonInit.loadjson("resources/data/items.jsn")
        #arenamap = generatelevel(25, 15)
        self.mapfield = MapField(arenamap, self.mapinfo, self.moninfo, self.effinfo, self.iteinfo, self)
        self.mapfield.generatelevel(25, 15)
        #arenamap = self.mapfield.generatelevel(None)
        arenamap = self.mapfield.terrain
        self.messagehandler = MessageHandler()
        self.graphicshandler = GraphicsHandler(self)

        self.gameevent = EventHandler()
        self.gameevent.register(self.messagehandler)
        self.gameevent.register(self.graphicshandler)
        self.loop()

        # load hi score

    def initgame(self):
        pygame.init()
        pygame.display.set_caption('Aquarium Arena')
        player = self.generateplayer()

        # introduction messages
        self.gameevent.report("Welcome to Aquarium Arena!", None, None, None)
        self.gameevent.report("Top gladiator score is "+str(self.hiscore)+" points!", None, None, None)
        # main game loop
        player.setparam("level", "3")
        return player

    def generateplayer(self):
        # create list of entities and player entity
        player = Monster(self.moninfo[PLAYERCREATURE], self)
        player.player = True
        player.setposition(self.mapfield.getrandompassable())
        for x in range(0, 5):
            player.pick(Item(self.iteinfo['harpoon'], self))
        player.pick(Item(self.iteinfo['dynamite'], self))
        self.mapfield.addmonster(player)
        return player

    def loop(self):
        player = self.initgame()
        while True:
            if self.resetflag:
                self.resetflag = False
                self.resetgame()
                break
            # Main mode
            for event in pygame.event.get():
                if event.type == pg.QUIT:
                    self.endgame()
                elif event.type == VIDEORESIZE:
                    self.graphicshandler.resize(event.dict['size'])
                else:
                    # Debug
                    if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                        self.mapfield.addrandomspawn()
                    if event.type == pg.KEYDOWN and event.key == pg.K_DELETE:
                        self.mapfield.addatrandommonster(Monster(self.moninfo[jsonInit.getrandflagged(self.moninfo, "spawner")], self))
                    if event.type == pg.KEYDOWN and event.key == pg.K_END:
                        self.mapfield.addatrandomsurfaceitem(Item(self.iteinfo['coin'], self))

                    if self.usemode is True:
                        # cancel
                        if event.type == pg.KEYDOWN and (event.key == pg.K_ESCAPE):
                            self.usemode = False
                            self.gameevent.report("Item use cancelled.", None, None, None)
                            break
                        index = self.displayinventory("usable")
                        if index is None:
                            self.gameevent.report("You have nothing usable.", None, None, None)
                        self.usemode = False
                        if index is not None:
                            if len(player.getinventory("usable"))-1 >= index:
                                self.gameevent.report("Using ... " +
                                                      player.getinventory("usable")[index].getname(), None, None, None)
                                player.useitem(player.getinventory("usable")[index])
                                self.passturn()

                    # Firing mode toggles
                    if self.firingmode is True:
                        if event.type == pg.KEYDOWN and (event.key == pg.K_i or event.key == pg.K_SPACE):
                            index = self.displayinventory()
                            if index is not None:
                                if len(player.inventory)-1 >= index:
                                    player.rangedpreference = player.inventory[index]
                                    self.gameevent.report("Firing ... " + player.rangedpreference.getname() +
                                                          " Press i or space to change.", None, None, None)

                    # Lines
                    if event.type == pg.KEYDOWN and (event.key == pg.K_UP or event.key == pg.K_KP8):
                        coord = (player.x, player.y-1)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((0, -1), player.rangedpreference)
                        else:
                            player.action(coord)
                        self.passturn()
                    if event.type == pg.KEYDOWN and (event.key == pg.K_DOWN or event.key == pg.K_KP2):
                        coord = (player.x, player.y+1)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((0, 1), player.rangedpreference)
                        else:
                            player.action(coord)
                        self.passturn()
                    if event.type == pg.KEYDOWN and (event.key == pg.K_LEFT or event.key == pg.K_KP4):
                        coord = (player.x-1, player.y)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((-1, 0), player.rangedpreference)
                        else:
                            player.action(coord)
                        self.passturn()
                    if event.type == pg.KEYDOWN and (event.key == pg.K_RIGHT or event.key == pg.K_KP6):
                        coord = (player.x+1, player.y)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((1, 0), player.rangedpreference)
                        else:
                            player.action(coord)
                        self.passturn()

                    # Diagonals
                    if event.type == pg.KEYDOWN and (event.key == pg.K_PAGEUP or event.key == pg.K_KP9):
                        coord = (player.x+1, player.y-1)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((1, -1))
                        else:
                            player.action(coord)
                        self.passturn()
                    if event.type == pg.KEYDOWN and (event.key == pg.K_HOME or event.key == pg.K_KP7):
                        coord = (player.x-1, player.y-1)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((-1, -1))
                        else:
                            player.action(coord)
                        self.passturn()
                    if event.type == pg.KEYDOWN and (event.key == pg.K_END or event.key == pg.K_KP1):
                        coord = (player.x-1, player.y+1)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((-1, 1))
                        else:
                            player.action(coord)
                        self.passturn()
                    if event.type == pg.KEYDOWN and (event.key == pg.K_PAGEDOWN or event.key == pg.K_KP3):
                        coord = (player.x+1, player.y+1)
                        if self.firingmode is True:
                            self.firingmode = False
                            player.fire((1, 1))
                        else:
                            player.action(coord)
                        self.passturn()
                    if event.type == pg.KEYDOWN and (event.key == pg.K_SPACE or event.key == pg.K_KP5):
                        self.passturn()
                    # Commands
                    # fire
                    if event.type == pg.KEYDOWN and event.key == pg.K_f:
                        if player.getbestranged() is None:
                            self.gameevent.report("You have nothing to fire.", None, None, None)
                            break
                        else:
                            if player.rangedpreference is None:
                                self.gameevent.report("Firing ... "+player.getbestranged().getname() +
                                                      " Press i or space to change.", None, None, None)
                            else:
                                self.gameevent.report("Firing ... "+player.rangedpreference.getname() +
                                                      " Press i or space to change.", None, None, None)
                            self.firingmode = True
                            break
                    # use
                    if event.type == pg.KEYDOWN and event.key == pg.K_u:
                        self.usemode = True
                    if event.type == pg.KEYDOWN and event.key == pg.K_COMMA:
                        # pick up item
                        citems = self.mapfield.getitems(player.getposition())
                        for item in citems:
                            player.pick(item)
                        self.passturn()

            time_passed = self.clock.tick(30)
            self.graphicshandler.drawboard(self.mapfield.terrain)

    def newmap(self):
        self.mapfield.replacemap()

    def resetgame(self):
        del self.mapfield
        del self.graphicshandler
        arenamap = None
        self.mapfield = MapField(arenamap, self.mapinfo, self.moninfo, self.effinfo, self.iteinfo, self)
        self.mapfield.generatelevel(25, 15)
        self.graphicshandler = GraphicsHandler(self)

        self.loop()

    def endgame(self):
        pygame.quit()
        sys.exit()

    def passturn(self):
        self.turns += 1

        self.graphicshandler.eraseeventstack()
        self.processeffects()
        for monster in self.mapfield.monsters:
            monster.update()
        for uitem in self.mapfield.items:
            uitem.update()
        for ueffect in self.mapfield.effects:
            ueffect.update()
        self.mapfield.cleanup()
        self.mapfield.generatemonster()
        if not self.noscore:
            self.mapfield.generateitem()
        # next level trigger
        if self.turns % 100 == 0:
            self.noscore = True
            self.mapfield.generategate()

    # debug method
    def spawnmonsters(self):
        self.mapfield.addatrandommonster(Monster(self.moninfo[jsonInit.getrandflagged(self.moninfo, "spawner")], self))
        self.mapfield.addspawn("moray eel")

    def processeffects(self):
        for ueffect in self.mapfield.effects:
            if str.startswith(str(ueffect.geteffect()), 'spawn'):
                if ueffect.getspawn() == 'random':
                    self.mapfield.addmonsterat(Monster(self.moninfo[jsonInit.getrandspawn(self.moninfo)], self), ueffect.getposition())
                else:
                    self.mapfield.addmonsterat(Monster(self.moninfo[ueffect.getspawn()], self), ueffect.getposition())

    def displayinventory(self, requiredflag=None):
        items = self.mapfield.getplayer().getinventory(requiredflag)
        if len(items) == 0:
            return None
        self.graphicshandler.displayitemlist(items)
        loop = True
        while loop:
            for event in pygame.event.get():
                # cancel
                if event.type == pg.KEYDOWN and (event.key == pg.K_ESCAPE):
                    return None
                if event.type == pg.KEYDOWN and pygame.key.name(event.key) in self.ALPHABET:
                    return self.ALPHABET.index(pygame.key.name(event.key))  # returns corresponding key alphabet index
            self.clock.tick(30)