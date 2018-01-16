# Written by Florian Wolf, 15.11.2017
# imports
import pygame
import random
import math
from pygame.locals import *
from random import randint
pygame.init()
res = (1920, 1080)
width = 1920
screenHeight = 1080
screen = pygame.display.set_mode(res,pygame.FULLSCREEN)
background = pygame.surface.Surface((width, screenHeight))
pygame.mouse.set_visible(False)
screen.fill((0, 0, 0))
background.fill((0, 0, 0))

# clock setup
clock = pygame.time.Clock()

# event setup
INVADERSHOTEVENT, t = pygame.USEREVENT+1, 250
pygame.time.set_timer(INVADERSHOTEVENT, t)

# font setup for the score counter
scoreFont = pygame.font.SysFont('default', 72)
waveFont = pygame.font.SysFont('Menlo, Monaco, Lucida Console, Liberation Mono, DejaVu Sans Mono, Bitstream Vera Sans Mono, Courier New', 36)
waveScoreFont = pygame.font.SysFont('default', 72)
pickupInfoFont = pygame.font.SysFont('Menlo, Monaco, Lucida Console, Liberation Mono, DejaVu Sans Mono, Bitstream Vera Sans Mono, Courier New', 18)


# check if movement keys are held down
rightKeyPressed = False
leftKeyPressed = False


# helper function - map values from one range to another
def translate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)


# helper function - stop a value from overshooting a certain maximum, keep n within two bounds
def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

# helper function - smoothclamp / sigmoid
def smoothclamp(x,mi, mx): return mi + (mx-mi)*(lambda t: (1+200**(-t+0.5))**(-1) )( (x-mi)/(mx-mi) )


# helper function - creates a gradient on a surface - taken from the web: http://www.pygame.org/wiki/GradientCode
def fill_gradient(surface, color, gradient, rect=None, vertical=True, forward=True):
    """fill a surface with a gradient pattern
    Parameters:
    color -> starting color
    gradient -> final color
    rect -> area to fill; default is surface's rect
    vertical -> True=vertical; False=horizontal
    forward -> True=forward; False=reverse

    Pygame recipe: http://www.pygame.org/wiki/GradientCode
    """
    if rect is None: rect = surface.get_rect()
    x1, x2 = rect.left, rect.right
    y1, y2 = rect.top, rect.bottom
    if vertical:
        h = y2 - y1
    else:
        h = x2 - x1
    if forward:
        a, b = color, gradient
    else:
        b, a = color, gradient
    rate = (
        float(b[0] - a[0]) / h,
        float(b[1] - a[1]) / h,
        float(b[2] - a[2]) / h
    )
    fn_line = pygame.draw.line
    if vertical:
        for line in range(y1, y2):
            color = (
                min(max(a[0] + (rate[0] * (line - y1)), 0), 255),
                min(max(a[1] + (rate[1] * (line - y1)), 0), 255),
                min(max(a[2] + (rate[2] * (line - y1)), 0), 255)
            )
            fn_line(surface, color, (x1, line), (x2, line))
    else:
        for col in range(x1, x2):
            color = (
                min(max(a[0] + (rate[0] * (col - x1)), 0), 255),
                min(max(a[1] + (rate[1] * (col - x1)), 0), 255),
                min(max(a[2] + (rate[2] * (col - x1)), 0), 255)
            )
            fn_line(surface, color, (col, y1), (col, y2))


# fill the background with the color gradient
# black - yellow
fill_gradient(background, (0,0,0), (60,60,60))

# black - turquoise
#fill_gradient(background, (0,0,0), (59, 102, 119))

# old black-red
# fill_gradient(background, (0,0,0), (120,60,60))


class Game:
    # settings
    stopInvadersOnRespawn = True

    # game booleans, when they turn true they stay true for one tick and execute all appropriate resets
    restart = False
    nextWave = False

    # scoring
    invaderHitScore = 25
    invaderKillScore = 100
    invaderBulletKillScore = 25
    defenseDeadPenalty = 300
    heartLossPenalty = 150
    pickupReward = 400

    # restart timing variables, duration: 1 sec = 60 (due to framerate of 60fps)
    restartDuration = 240
    restartTime = 0

    def __init__(self):
        self.score = 0
        self.wave = 0
        self.playerAmmoAdd = 0
        self.playerLifeAdd = 0
        self.playerReloadAdd = 0
        self.pause = False
        self.pickupPicked = False


# create a new game instance
game = Game()


# invader class - an alien, able to shoot bullets (InvaderBullet) at the player
class Invader:
    size = 35                       # invaders size, is both height and width
    moveStep = 1                  # amount of pixels to move every tick
    sideBounds = 70                # invaders padding/border to the sides
    yAddPerRow = 1000               # distance added per row lowering
    incrementY = 0                  # amount of y to add every frame
    yAddDuration = 300              # time in seconds it takes the invaders to move down in milliseconds
    yAdd = 0                        # total value to add on top of an invaders default spawn Y position
    speed = 0                       # invaders speed index
    speedSteps = [1, 2.5, 3, 3.5, 4]
    speedMax = len(speedSteps)
    invadersGettingLowered = False  # bool if the invaders are currently getting lowered, checked in game loop
    lowerInvaderStartTick = 0       # as soon as the invaders are needed to lower the current time gets saved
    switchingDirection = False
    switchDirectionDelta = 0
    switchDirectionDuration = 10

    shotSkipDefault = 2 # reset value
    shotSkip = shotSkipDefault # the game tries to shoot an invader every 250ms. A skip of 8 means only every 2000ms an invader shoots

    # colors
    # colors = [(255, 80, 80), (255, 127, 133)]
    colors = [(255, 80, 80), (255, 80, 80)]
    startColor = 0

    # shot timer, i.e. 1 sec shot delay (60 ticks)
    invaderShotSkipCounter = 0

    # constructor
    def __init__(self, x, y, indexInRow):
        self.x = x
        self.startY = y
        self.y = y
        self.bullet = False
        self.life = 2
        self.indexInRow = indexInRow # postion in the row of invaders. first element to the left starts with 0
        self.color = Invader.colors[Invader.startColor]

    # spawn an invader bullet
    def fire(self):
        self.bullet = InvaderBullet(self.x, self.y, self.life)
        InvaderBullet.invaderBullets.append(self.bullet)

    # move the invader - includes movement to the side as well as row lowering
    def moveInvader(self):
        # normal left right movement and bouncing from the edge paddings
        if not wave.moveIn and not game.restart and not (Game.stopInvadersOnRespawn and player.respawning):
            if self.x + Invader.moveStep * Invader.speedSteps[Invader.speed] > width - Invader.sideBounds or self.x + Invader.moveStep * Invader.speedSteps[Invader.speed] <= 0 + Invader.sideBounds and not Invader.switchingDirection and not Invader.invadersGettingLowered:
                Invader.moveStep = Invader.moveStep * -1
                self.x += Invader.moveStep * Invader.speedSteps[Invader.speed]
                Invader.lowerAllInvaders()
            if not Invader.invadersGettingLowered and not Invader.switchingDirection:
                self.x += (Invader.moveStep * (Invader.speedSteps[0] + (game.wave + 1)/8))


        # move in the invaders down instead of left/right movement
        elif wave.moveIn:
            Wave.moveInTime += 1

            if Wave.moveInTime <= Wave.moveInDuration:
                Invader.yAdd = smoothclamp(translate(Wave.moveInTime, 0, Wave.moveInDuration, Wave.moveInStartY, Wave.moveInEndY), Wave.moveInStartY, Wave.moveInEndY)
            else:
                Wave.moveInTime = 0
                #Invader.yAdd = 0
                wave.moveIn = False
        self.y = self.startY + Invader.yAdd

    # adjusts the color to fit the health
    def colorfix(self):
        if self.life <= 1:
            self.color = Invader.colors[1]
        else:
            self.color = Invader.colors[0]

    # activates the row lowering when an invader touches the side-bounds
    @staticmethod
    def lowerAllInvaders():
        Invader.lowerInvaderStartTick = pygame.time.get_ticks()
        if Invader.speed + 1 < Invader.speedMax:
            Invader.speed += 1
        Invader.incrementY = Invader.yAddPerRow / Invader.yAddDuration
        Invader.invadersGettingLowered = True
        Invader.switchingDirections = True
        Invader.switchingDirectionDelta = 0


# group of invaders, called a wave. Each wave (level) gets progressively stronger
class Wave:
    # wave information - each index consits out of (rowcount, invadersPerRow)
    waves = [[2, 6], [2, 8], [3, 11], [4, 11]]

    # space between upper most invader row and the edge of the screen
    invaderToTopPadding = 180

    moveInDuration = 120 * 8
    moveInTime = 0
    moveInAddYDefault = -600
    moveInStartY = moveInAddYDefault
    moveInEndY = 0

    # wave always has the same width, no matter how many invaders should spawn per row
    fixedWaveWidth = False

    def __init__(self, newWave):
        if newWave >= len(Wave.waves) - 1:
            newWave = len(Wave.waves) - 1

        self.rowcount = Wave.waves[newWave][0]
        self.invadersPerRow = Wave.waves[newWave][1]
        self.rows = []
        self.invadersAlive = self.rowcount * self.invadersPerRow
        self.spawnWave()

        # is this wave moving in? if so, dont move the invaders yet in moveinvaders()
        self.moveIn = True

        # this wave a pickup already spawned
        self.pickupSpawned = False

    def fireInvaderBullets(self):
        firedIndicies = []

        rowcount = len(self.rows)
        randomInvaderIndex = randint(0, self.invadersPerRow)

        # loop through all invaders in order to determine which one should fire
        for row in reversed(self.rows):
            rowcount -= 1

            for n in range(0, len(row)):
                if randomInvaderIndex == row[n].indexInRow and not row[n].indexInRow in firedIndicies:
                    row[n].fire()
                    firedIndicies.append(row[n].indexInRow)
                    return 0
            if rowcount == 0 and wave.invadersAlive > 0:
                self.fireInvaderBullets()

    def fireBullet(self, row, index):
        self.rows[row][index].fire()

    def spawnWave(self):
        # fill surface with invaders - inital setup

        invadersToMiddle = ((self.invadersPerRow - 1) / 2) * -1
        # invaderRowOffset = (5 / self.rowcount) * 100
        invaderRowOffset = 110

        invaderNeighbourOffset = Invader.size * 4

        if Wave.fixedWaveWidth:
            invaderNeighbourOffset = (18 / self.invadersPerRow) * 70

        self.rows = []
        for n in range(self.rowcount):
            row = []
            indexInRow = 0
            for j in range(self.invadersPerRow):
                # invader x position
                offsetX = (int(width / 2)) + (invaderNeighbourOffset * invadersToMiddle)

                # invader y position
                offsetY = invaderRowOffset * n + Wave.invaderToTopPadding

                row.append(Invader(offsetX, offsetY, indexInRow))

                invadersToMiddle += 1
                indexInRow += 1

            self.rows.append(row)
            invadersToMiddle = ((self.invadersPerRow - 1) / 2) * -1


# create a first wave
wave = Wave(game.wave)


class PlayerBullet:
    # array holding all bullets fired by the player
    playerBullets = []

    def __init__(self, x, y, startDamage):
        self.y = y - 20
        self.x = x
        self.height = 25
        self.width = 15
        self.damage = startDamage
        self.life = 100
        self.velocity = 12


class InvaderBullet:
    invaderBullets = []

    def __init__(self, x, y, invaderLife):
        self.height = 40
        self.width = 8
        self.x = x
        self.y = y + Invader.size * invaderLife + self.height/2
        self.life = 100
        self.velocity = 12


class AmmoBar:
    ammoBars = []
    padding = 50
    defaultHeight = 15

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.height = defaultHeight
        self.width = 40

    @staticmethod
    def fitBarsToPlayerLife():
        if player.ammo < len(AmmoBar.ammoBars):
            AmmoBar.popBar()
        elif player.ammo > len(AmmoBar.ammoBars):
            AmmoBar.addBar()

    @staticmethod
    def addBar():
        AmmoBar.ammoBars.append(AmmoBar(len(AmmoBar.ammoBar), player.x, player.y))

    @staticmethod
    def popBar():
        AmmoBar.ammoBars.remove(AmmoBar.ammoBar[len(AmmoBar.ammoBar)-1])


# Player class
class Player:
    # invincibility for testing
    invincible = False

    # size and position
    paddingToSide = 100
    height = 200
    maxSize = 100

    # movement
    velocityIncrement = 0.3
    maxVelocity = 10
    torque = 0.5

    # shooting
    ammoIncrement = 0.03
    ammoShotDecrease = 1.3
    maxAmmo = 4.5
    maxMaxAmmo = 6.5

    # respawning
    maxLife = 4
    respawnCounter = 0
    respawnDuration = 120
    respawnBlinks = 4

    colors = [(255, 255, 255), (60,50,50), (255,255,255)]
    defaultColor = 0
    defaultBagColor = 1
    defaultBagFadeColor = 2

    def __init__(self):
        self.y = screenHeight - 180
        self.x = width/2
        self.size = 10
        self.velocity = 1
        self.ammo = Player.maxAmmo + game.playerAmmoAdd
        self.speed = 2
        self.height = 50
        self.life = Player.maxLife + game.playerLifeAdd
        self.respawning = True
        self.color = Player.colors[Player.defaultColor]
        self.bagcolor = Player.colors[Player.defaultColor]

    def tryFire(self):
        if self.ammo - Player.ammoShotDecrease >= 1:
            self.ammo -= Player.ammoShotDecrease
            PlayerBullet.playerBullets.append(PlayerBullet(self.x, self.y, self.ammo))

    # respawning
    def hit(self):
        if not Player.invincible:
            self.life -= 1

            self.y = screenHeight - 150
            self.x = width / 2
            self.size = 10
            self.velocity = 1
            self.ammo = Player.maxAmmo + game.playerAmmoAdd
            self.speed = 2
            self.height = 50

            if self.life <= 0:
                game.restart = True

            if not game.restart:
                self.respawning = True

            game.score -= Game.heartLossPenalty

            # remove all bullets
            PlayerBullet.playerBullets = []
            InvaderBullet.invaderBullets = []
            rightKeyPressed = False
            leftKeyPressed = False


# create player
player = Player()


# Defenses
class Defense:
    # creation array, holding references to all created defenses
    defenses = []

    # should the game restart when all defenses are down
    defensesDeadRestart = False

    # creation rules
    paddingToBottom = 250
    paddingToDefense = 30
    paddingToSides = 300
    maxLife = 8
    startLife = 8
    columns = 3
    defensePerColumn = 1
    defaultWidth = 250

    # alive tracker
    defensesAlive = columns * defensePerColumn

    # constructor
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = Defense.defaultWidth
        self.height = 15
        self.life = Defense.startLife
        self.color = (255,255,255)

    # an invader hit a defense => decrease life and or remove it from the collection
    def hit(self):
        self.life -= 1
        self.width = (Defense.defaultWidth / Defense.startLife) * self.life
        if self.life <= 0:
            Defense.defenses.remove(self)
            Defense.defensesAlive -= 1
            game.score -= Game.defenseDeadPenalty
            if Defense.defensesAlive <= 0 and Defense.defensesDeadRestart:
                game.restart = True
        self.colorfix()

    # the player hit a defense => increase life
    def boost(self):
        if self.life + 1 <= Defense.maxLife:
            self.life += 1
            self.width = (Defense.defaultWidth / Defense.startLife) * self.life
        self.colorfix()

    # adjusts the defense color based on its current life
    def colorfix(self):
        # white to invader red
        r = 255
        g = translate(self.life, 1, Defense.maxLife, 80, 255)
        b = translate(self.life, 1, Defense.maxLife, 80, 255)

        self.color = (r,g,b)

    # spawns all defenses at their default locations
    @staticmethod
    def respawnDefenses():
        Defense.defenses = []
        for c in range(0, Defense.columns):
            for r in range(0, Defense.defensePerColumn):
                xPos = width - Defense.paddingToSides - (((width - Defense.paddingToSides*2) / (Defense.columns-1)) * c)
                yPos = screenHeight - Defense.paddingToBottom - Defense.paddingToDefense * r
                Defense.defenses.append(Defense(xPos, yPos))


# spawn Defenses
Defense.respawnDefenses()


# explosion class
class Explosion:
    explosions = []

    # Screentime of an explosion - 60 (frames) = 1 second
    duration = 20

    # constructor
    def __init__(self):
        self.lifetime = Explosion.duration


# pickup master class
class Pickup:
    pickups = []
    possibleSpawns = [(width/2 - 300, Wave.invaderToTopPadding), (width/2 + 300, Wave.invaderToTopPadding)]
    color = (100,200,200)

    # animatioin settings
    rollDuration = 30
    leftRightDuration = 420
    pickupBackgroundFadeDuration = 30
    pickupBackgroundFade = 0

    def __init__(self, type, spawn):
        self.spawn = Pickup.possibleSpawns[spawn]
        self.x = self.spawn[0]
        self.y = self.spawn[1]

        # heart capacity upgrade
        if type == 0:
            self.type = HeartUpgrade(self.x, self.y)

        # ammo upgrade
        elif type == 1:
            self.type = AmmoUpgrade(self.x, self.y)

        # ammo upgrade
        else:
            self.type = ReloadSpeedUpgrade(self.x, self.y)

    @staticmethod
    def clearPickups():
        Pickup.pickups.clear()

    @staticmethod
    def spawnRandom():
        spawn = random.randint(0, 1)
        type = random.randint(0, 2)
        Pickup.pickups.append(Pickup(type, spawn))


class HeartUpgrade(Pickup):
    regenerateAmount = 1

    def __init__(self, x, y):
        self.size = 20
        self.height = self.size * 2
        self.width = self.size * 2
        self.spawn = (x,y)
        self.x = -self.size - 150
        self.y = screenHeight - 350
        self.rollTime = 0
        self.leftRightTime = 0

    def hit(self):
        game.playerLifeAdd += 1
        player.life += 1
        game.score += Game.pickupReward
        game.pause = True
        game.pickupPicked = True

    def draw(self):
        # draw the heart shape
        starSize = 50

        starPoints = []
        n = 10
        for i in range(0,n):
            # Even
            if i % 2 == 0:
                rad = starSize/2
            else:
                rad = starSize/4

            angle = (2*i*math.pi)/n
            ammoRollDegrees = translate(self.rollTime, 0, Pickup.rollDuration, 0, 360)

            starX = self.x + rad * math.cos(angle + ammoRollDegrees)
            starY = self.y + rad * math.sin(angle + ammoRollDegrees)

            starPoints.append((starX, starY))

        pygame.draw.polygon(screen, player.color, starPoints, 0)

        # draw the info text
        infoText = pickupInfoFont.render("Extra Life", False, (255, 255, 255))
        infoTextSize = infoText.get_rect()
        screen.blit(infoText, (self.x - infoTextSize.width / 2, self.y - 50))


class AmmoUpgrade(Pickup):
    ammoCapacityAddAmount = 5


    def __init__(self, x, y):
        self.size = 20
        self.height = self.size * 2
        self.width = self.size * 2
        self.spawn = (x, y)
        self.x = -self.size - 150
        self.y = screenHeight - 350
        self.rollTime = 0
        self.leftRightTime = 0

    def hit(self):
        if game.playerAmmoAdd + Player.maxAmmo <= Player.maxMaxAmmo:
            game.playerAmmoAdd += 1
        game.score += Game.pickupReward
        game.pickupPicked = True
        game.pause = True


    def draw(self):
        # draw the heart shape
        starSize = 50

        starPoints = []
        n = 10
        for i in range(0,n):
            # Even
            if i % 2 == 0:
                rad = starSize/2
            else:
                rad = starSize/4

            angle = (2*i*math.pi)/n
            ammoRollDegrees = translate(self.rollTime, 0, Pickup.rollDuration, 0, 360)

            starX = self.x + rad * math.cos(angle + ammoRollDegrees)
            starY = self.y + rad * math.sin(angle + ammoRollDegrees)

            starPoints.append((starX, starY))

        pygame.draw.polygon(screen, player.color, starPoints, 0)

        # draw the info text
        infoText = pickupInfoFont.render("Ammo Capacity", False, (255, 255, 255))
        infoTextSize = infoText.get_rect()
        screen.blit(infoText, (self.x - infoTextSize.width / 2, self.y - 50))


class ReloadSpeedUpgrade(Pickup):
    reloadSpeedImprovement = 0.008

    def __init__(self, x, y):
        self.size = 20
        self.height = self.size * 2
        self.width = self.size * 2
        self.spawn = (x, y)
        self.x = -self.size - 150
        self.y = screenHeight - 350
        self.rollTime = 0
        self.leftRightTime = 0

    def hit(self):
        if Player.ammoIncrement + ReloadSpeedUpgrade.reloadSpeedImprovement <= 0.05:
            Player.ammoIncrement += ReloadSpeedUpgrade.reloadSpeedImprovement
            game.pause = True
        game.score += Game.pickupReward
        game.pickupPicked = True

    def draw(self):
        # draw the heart shape
        starSize = 50

        starPoints = []
        n = 10
        for i in range(0,n):
            # Even
            if i % 2 == 0:
                rad = starSize/2
            else:
                rad = starSize/4

            angle = (2*i*math.pi)/n
            ammoRollDegrees = translate(self.rollTime, 0, Pickup.rollDuration, 0, 360)

            starX = self.x + rad * math.cos(angle + ammoRollDegrees)
            starY = self.y + rad * math.sin(angle + ammoRollDegrees)

            starPoints.append((starX, starY))

        pygame.draw.polygon(screen, player.color, starPoints, 0)

        # draw the info text
        infoText = pickupInfoFont.render("Reload Speed", False, (255, 255, 255))
        infoTextSize = infoText.get_rect()
        screen.blit(infoText, (self.x - infoTextSize.width / 2, self.y - 50))


"""
Game Loop

"""
running = True
while running:

    # redraw screen and set clock
    screen.fill((0, 0, 0))
    screen.blit(background, (0, 0))
    delay = clock.tick(60)

    #print('ticks', delay)

    # restarting
    if (player.life <= 0 and not Player.invincible) or game.restart:
        player.respawning = True
        if Game.restartTime < Game.restartDuration:
            Game.restartTime += 1
        else:
            Game.restartTime = 0
            game.restart = False
            game = Game()
            wave = Wave(game.wave)
            player = Player()
            PlayerBullet.playerBullets = []
            InvaderBullet.invaderBullets = []
            Invader.yAdd = 0
            Invader.shotSkip = Invader.shotSkipDefault
            Defense.respawnDefenses()

    # respawning
    if player.respawning or game.restart:
        player.respawnCounter += 1
        if player.respawnCounter >= player.respawnDuration:
            if not game.restart:
                player.respawning = False
                game.pause = False
            player.respawnCounter = 0

    # next wave
    if game.nextWave:
        game.nextWave = False
        game.wave += 1
        game.pickupPicked = False
        wave = Wave(game.wave)
        player = Player()
        PlayerBullet.playerBullets = []
        InvaderBullet.invaderBullets = []
        Invader.yAdd = 0
        Invader.shotSkip = Invader.shotSkipDefault
        Pickup.clearPickups()
        wave.pickupSpawned = False
        Defense.respawnDefenses()

    # check through all events
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False

        if event.type == KEYDOWN:
            if event.key == pygame.K_RIGHT:
                player.velocity = abs(player.velocity)
                rightKeyPressed = True
                leftKeyPressed = False
            if event.key == pygame.K_LEFT:
                player.velocity = abs(player.velocity) * -1
                leftKeyPressed = True
                rightKeyPressed = False
            if event.key == pygame.K_SPACE and not player.respawning:
                player.tryFire()
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_r:
                game.restart = True

        # registering the end of a keypress and adjusting the players velocity
        if event.type == KEYUP:
            if event.key == pygame.K_RIGHT:
                rightKeyPressed = False
            if event.key == pygame.K_LEFT:
                leftKeyPressed = False

        if event.type == INVADERSHOTEVENT:
            if not (Game.stopInvadersOnRespawn and player.respawning):
                if Invader.invaderShotSkipCounter >= Invader.shotSkip:
                    Invader.invaderShotSkipCounter = 0
                    wave.fireInvaderBullets()
                Invader.invaderShotSkipCounter += 1

    # move player to the sides
    if leftKeyPressed and not player.respawning and not game.restart:
        if player.x + player.speed * player.velocity > Player.paddingToSide:
            if abs(player.velocity) < Player.maxVelocity:
                player.velocity -= Player.velocityIncrement
            player.x += player.speed * player.velocity
    elif rightKeyPressed and not player.respawning and not game.restart:
        if player.x + player.speed * player.velocity < width-Player.paddingToSide:
            if abs(player.velocity) < Player.maxVelocity:
                player.velocity += Player.velocityIncrement
            player.x += player.speed * player.velocity
    elif not player.respawning:
        if player.velocity < 0 and player.velocity + Player.torque < 0:
            player.velocity += Player.torque
        elif player.velocity > 0 and player.velocity - Player.torque > 0:
            player.velocity -= Player.torque

    # update the player ammo
    if player.ammo + Player.ammoIncrement < Player.maxAmmo + game.playerAmmoAdd:
        player.ammo += Player.ammoIncrement

    # adjust the invader shooting speed accoring to the current number of invaders alive
    if wave.invadersAlive <= wave.rowcount * wave.invadersPerRow / 2:
        Invader.shotSkip -= 2
        if not wave.pickupSpawned and not player.respawning and not game.restart:
            Pickup.spawnRandom()
            wave.pickupSpawned = True

    # lower invaders
    if Invader.invadersGettingLowered:
        Invader.switchDirectionDelta += 1
        if Invader.switchingDirection and Invader.switchDirectionDelta > Invader.switchDirectionDuration:
            Invader.switchingDirection = False
        if pygame.time.get_ticks() < Invader.lowerInvaderStartTick + Invader.yAddDuration and Invader.yAdd + Invader.incrementY < 240:
            Invader.yAdd += Invader.incrementY
            #if Invader.yAdd > 80 and not wave.pickupSpawned:
                #Pickup.spawnRandom()
                #wave.pickupSpawned = True

        else:
            Invader.invadersGettingLowered = False

    # check if player should be drawn because of respawn blinking
    drawPlayer = True
    if player.respawning or game.restart:
        divisionSteps = player.respawnBlinks * 2 - 1
        divisionStepTime = player.respawnDuration / divisionSteps
        currentStep = player.respawnCounter / player.respawnDuration
        for x in range(0, divisionSteps):
            if x * divisionStepTime < player.respawnCounter < x * divisionStepTime + divisionStepTime:
                if not x % 2 == 0:  # odd
                    drawPlayer = False

    # prepare draw player by regenerating the bounding boxes. Needed for collision checks
    gunbarrelWidth = 20
    playerDrawWidth = gunbarrelWidth * 3

    gunbarrelWidth = int(
        translate(((Player.maxAmmo + game.playerAmmoAdd) - abs(player.ammo)), 0, Player.maxAmmo + game.playerAmmoAdd, gunbarrelWidth, gunbarrelWidth * 2))
    gunbarrelHeight = 30
    gunbarrelMuzzleWidth = 30
    gunbarrelMuzzleWidth = int(
        translate(((Player.maxAmmo + game.playerAmmoAdd) - abs(player.ammo)), 0, Player.maxAmmo + game.playerAmmoAdd, gunbarrelMuzzleWidth, gunbarrelMuzzleWidth * 2))
    gunbarrelMuzzleHeight = 15

    playerDrawHeight = 10
    gunbarrelRect = (int(player.x) - gunbarrelWidth / 2, int(player.y - gunbarrelHeight), gunbarrelWidth, gunbarrelHeight)
    gunbarrelMuzzleRect = (int(player.x) - gunbarrelMuzzleWidth / 2, int(player.y) - 15 - gunbarrelHeight, gunbarrelMuzzleWidth, gunbarrelMuzzleHeight)
    playerBodyRect = (int(player.x) - playerDrawWidth/2, player.y, playerDrawWidth, playerDrawHeight)
 
    # draw player ammo bars
    ammoBarPadding = 20
    ammoBarHeight = 10
    ammoBarDefaultWidth = playerDrawWidth
    ammoBarWidthIncrease = 5
    ammoBarColor = (255,255,255)
    ammoBarEmptyColor = (100, 100, 100)
    if drawPlayer:

        # draw empties
        for a in range(0, int(player.maxAmmo + game.playerAmmoAdd)):
            ammoBarWidth = ammoBarDefaultWidth# + (a*ammoBarWidthIncrease)
            ammoBarRect = (int(player.x) - ammoBarWidth/2, player.y + ammoBarPadding * a, ammoBarWidth, ammoBarHeight)

            pygame.draw.rect(screen, ammoBarEmptyColor, ammoBarRect)

        # draw ammo ontop
        for b in range(0, int(player.ammo)):
            ammoBarWidth = ammoBarDefaultWidth# + (a*ammoBarWidthIncrease)
            ammoBarRect = (int(player.x) - ammoBarWidth/2, player.y + ammoBarPadding * b, ammoBarWidth, ammoBarHeight)

            pygame.draw.rect(screen, ammoBarColor, ammoBarRect)

    # draw player ui life hearts
    if not (game.nextWave and drawPlayer):
        heartPaddingTop = 30
        heartPaddingLeft = 30
        heartSize = 30
        heartPaddingHeart = heartSize * 2

        # draw blinking hearts
        if (game.restart or player.respawning)and drawPlayer and Player.maxLife + game.playerLifeAdd > player.life and not game.pause:

            n = player.life - 1
            blinkHeartCount = 1
            if game.restart:
                #blinkHeartCount = Player.maxLife
                blinkingHeartCount = player.life -1

            for x in range(0, blinkHeartCount):
                n += 1
                heartX = heartPaddingLeft + heartSize / 2 + (n * heartPaddingHeart)
                heartY = heartPaddingTop + heartSize / 2
                left = heartPaddingLeft + (n * heartPaddingHeart)
                heartLeftCircleCenter = (int(left + heartSize / 4), int(heartPaddingTop + heartSize / 4))
                heartRightCircleCenter = (int(left + (heartSize / 4) * 3), int(heartPaddingTop + heartSize / 4))

                pygame.draw.circle(screen, player.color, heartLeftCircleCenter, int(heartSize / 4))
                pygame.draw.circle(screen, player.color, heartRightCircleCenter, int(heartSize / 4))
                points = [(left, heartPaddingTop + heartSize / 4),
                          (left + heartSize - 2, heartPaddingTop + heartSize / 4),
                          (left + heartSize / 2, heartPaddingTop + heartSize)]
                pygame.draw.polygon(screen, player.color, points)

        fullHeartRangeMax = player.life

        # draw full hearts
        for n in range(0, fullHeartRangeMax):
            # center positions
            heartX = heartPaddingLeft + heartSize/2 + (n*heartPaddingHeart)
            heartY = heartPaddingTop + heartSize/2
            left = heartPaddingLeft + (n * heartPaddingHeart)
            heartLeftCircleCenter = (int(left + heartSize / 4), int(heartPaddingTop + heartSize / 4))
            heartRightCircleCenter = (int(left + (heartSize / 4)*3), int(heartPaddingTop + heartSize / 4))

            pygame.draw.circle(screen, player.color, heartLeftCircleCenter, int(heartSize / 4))
            pygame.draw.circle(screen, player.color, heartRightCircleCenter, int(heartSize / 4))
            points = [(left, heartPaddingTop + heartSize/4), (left + heartSize - 2, heartPaddingTop + heartSize/4), (left + heartSize/2, heartPaddingTop + heartSize)]
            pygame.draw.polygon(screen, player.color, points)



    # draw score counter
    if drawPlayer:
        scoreText = scoreFont.render(str(game.score), False, (255, 255, 255))
        scoreTextSize = scoreText.get_rect()
        screen.blit(scoreText, (width/2 - scoreTextSize.width/2, 25))

    # draw wave counter
    waveText = waveFont.render("Wave ", False, (255, 255, 255))
    waveScoreText = waveScoreFont.render(str(game.wave + 1), False, (255, 255, 255))
    waveTextSize = waveText.get_rect()
    waveScoreTextSize = waveScoreText.get_rect()
    if not (player.respawning and drawPlayer) or not (game.nextWave and drawPlayer):
        screen.blit(waveText, (width - heartPaddingLeft - waveTextSize.width - waveScoreTextSize.width, 30))
        screen.blit(waveScoreText, (width - heartPaddingLeft - waveScoreTextSize.width, 25))


    # temporary storage for updated invader bullets
    newInvaderBullets = []

    # draw invader bullets + check collisions + despawing
    if drawPlayer:
        for invaderBullet in InvaderBullet.invaderBullets:

            if not (Game.stopInvadersOnRespawn and player.respawning and game.restart) and not game.pause:
                invaderBullet.y += invaderBullet.velocity

            # bullet hits the player
            if player.y + playerDrawHeight/2 + (player.ammo * 18)> invaderBullet.y > player.y - gunbarrelHeight/2 - 20  and player.x - playerDrawWidth/2 < invaderBullet.x < player.x + playerDrawWidth/2:
                player.hit()

            destroyBullet = False

            # bullet hits defense collision check
            for defense in Defense.defenses:
                if defense.y + defense.height / 2 + 10 > invaderBullet.y > defense.y - defense.height / 2 - 20and defense.x - defense.width / 2 < invaderBullet.x < defense.x + defense.width / 2:
                    defense.hit()
                    destroyBullet = True

            # keep the bullet, it is still within the screen
            if invaderBullet.y >= screenHeight:
                destroyBullet = True

            # keep the bullet by adding it to the new bullet array
            if not destroyBullet:
                newInvaderBullets.append(invaderBullet)

            invaderBulletRect = (int(invaderBullet.x) - invaderBullet.width / 2, int(invaderBullet.y - playerDrawHeight / 2 - gunbarrelHeight / 2), invaderBullet.width, invaderBullet.height)
            pygame.draw.rect(screen, invader.color, invaderBulletRect)

        # replace the invader bullets with the updated version
        if not player.respawning:
            InvaderBullet.invaderBullets = newInvaderBullets


    # temporaty storage for updated player bullets
    newPlayerBullets = []

    # draw player bullets + check collisions + despawning + life change
    for bullet in PlayerBullet.playerBullets:
        # change bullet position
        if not (Game.stopInvadersOnRespawn and player.respawning and game.restart):
            bullet.y -= bullet.velocity

        removeBullet = False

        # Defender hit - increase life of defenders and remove bullet
        for defense in Defense.defenses:
            if defense.y + defense.height / 2 + 5> bullet.y> defense.y - defense.height / 2  -30and defense.x - defense.width / 2 < bullet.x < defense.x + defense.width / 2:
                defense.boost()
                removeBullet = True

        # check for pickup collisions
        for pickup in Pickup.pickups:
            # hit
            if pickup.type.y + pickup.type.height / 2 > bullet.y > pickup.type.y - pickup.type.height / 2 +20and pickup.type.x - pickup.type.width / 2 < bullet.x < pickup.type.x + pickup.type.width / 2:
                removeBullet = True
                if not player.respawning:
                    pickup.type.hit()
                    Pickup.pickups.remove(pickup)
                player.respawning = True

        # temporary storage for updated invaders
        newRows = []

        # check for invader collisions
        for row in wave.rows:
            newRow = []
            for invader in row:
                invaderSize = Invader.size * invader.life

                # bullet hits an invader => dont safe bullet and change invader life
                if invader.x - invaderSize/2 < bullet.x < invader.x + invaderSize/2 and invader.y - invaderSize/2 - bullet.height < bullet.y <= invader.y + invaderSize/2:
                    invader.life -= 1
                    game.score += Game.invaderHitScore * (game.wave + 1)
                    removeBullet = True

                # the invader is even though it got hit by a player bullet still alive
                if invader.life >= 1:
                    newRow.append(invader)
                # the invader has to be removed, it will not get saved and the alive counter gets tuned down by one
                else:
                    wave.invadersAlive -= 1
                    if wave.invadersAlive <= 0:
                        game.nextWave = True
                    game.score += Game.invaderKillScore * (game.wave + 1)

                # bullet is out of bounnds
                if bullet.y < 0:
                    removeBullet = True
            newRows.append(newRow)

        # bullet keeps flying
        if removeBullet == False:
            newPlayerBullets.append(bullet)
            bulletWidth = ((bullet.width + bullet.damage * 2.5) - 15) / 1.5
            bulletHeight = (bullet.width + bullet.damage * 2.5) - 15
            bulletRect = (int(bullet.x) - bullet.width / 2, int(bullet.y - playerDrawHeight / 2 - gunbarrelHeight / 2), bullet.width, bullet.height)

            pygame.draw.rect(screen, player.color, bulletRect)

        # replace the rows with the updated version
        wave.rows = newRows

    # replace the bullets with the updated version
    PlayerBullet.playerBullets = newPlayerBullets

    # draw invaders
    for row in wave.rows:
        for invader in row:
            invader.moveInvader()
            invaderSize = Invader.size * invader.life
            # pygame.draw.rect(screen, invaderColor, (invader.x - invaderSize/2, invader.y - invaderSize/2, invaderSize, invaderSize))
            invader.colorfix()

            if not (not drawPlayer and game.restart):
                pygame.draw.polygon(screen, invader.color, [
                    (invader.x - invaderSize / 2, invader.y - invaderSize / 2),
                    (invader.x + invaderSize / 2, invader.y - invaderSize / 2),
                    (invader.x, invader.y + invaderSize / 2)])

    # draw defenses
    for defense in Defense.defenses:
        defenseRect = (defense.x - defense.width/2, defense.y - defense.height/2, defense.width, defense.height)
        pygame.draw.rect(screen, defense.color, defenseRect)

    # draw player
    if drawPlayer:
        r = clamp(int(translate(playerDrawWidth, gunbarrelWidth + 15, gunbarrelWidth + 20, Player.colors[Player.defaultBagColor][0], Player.colors[Player.defaultBagFadeColor][0])), 0, 255)
        g = clamp(int(translate(playerDrawWidth, gunbarrelWidth + 15, gunbarrelWidth + 20, Player.colors[Player.defaultBagColor][1], Player.colors[Player.defaultBagFadeColor][1])), 0, 255)
        b = clamp(int(translate(playerDrawWidth, gunbarrelWidth + 15, gunbarrelWidth + 20, Player.colors[Player.defaultBagColor][2], Player.colors[Player.defaultBagFadeColor][2])), 0, 255)

        player.bagcolor = (r, g, b)

        pygame.draw.rect(screen, player.color, gunbarrelRect)
        pygame.draw.rect(screen, player.color, gunbarrelMuzzleRect)
        pygame.draw.rect(screen, player.bagcolor, playerBodyRect)

    # draw pickup backgrounds
    Pickup.pickupBackgroundFadeDuration = 20

    # draw pickups
    if drawPlayer and not game.pickupPicked and not player.respawning:
        for pickup in Pickup.pickups:
            pickup.type.rollTime += 0.003

            # update x pos
            pickup.type.x += 1.5
            if pickup.type.x >= width + pickup.type.size + 50:
                Pickup.pickups.remove(pickup)

            if pickup.type.rollTime >= Pickup.rollDuration:
                Pickup.rollDuration = 1
            pickup.type.draw()

    pygame.display.update()
pygame.quit()