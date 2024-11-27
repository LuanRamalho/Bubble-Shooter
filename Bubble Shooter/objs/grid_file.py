import time, random
from objs.constants import *
from objs.bubble_file import *
from math import sqrt
import pygame as pg
import json

class GridManager():

        def __init__(self):
                self.rows = GRID_ROWS
                self.cols = GRID_COLS
                self.even_offset = True
                self.targets = []
                self.grid = [[0 for col in range(self.cols)] for row in range(self.rows)]
                self.collided = False
                self.collision_counter = 0
                self.animations = []
                self.paths = []
                self.prev_time = 0

                # Inicializar o HighScore
                self.highscore = self.loadHighScore()

                for row in range(self.rows):
                    for col in range(self.cols):
                        pos = GridManager.calcPos(row, col, self.even_offset)
                        self.grid[row][col] = GridBubble(row, col, pos)

                for row in range(self.rows):
                    for col in range(self.cols):
                        self.findComrades(self.grid[row][col])

                self.appendBottom()
                self.findTargets()

        def view(self, gun, game):
                if gun.fired.exists:
                    self.checkCollision(gun.fired)

                if self.collided:
                    self.collision_counter += 1
                    bubble = self.reviveBubble(gun.fired)
                    self.updateRows()
                    self.popCluster(bubble, game)
                    self.findTargets()
                    self.checkGameOver(game)
                    self.collided = False

                # Atualizar o HighScore se necessário
                if game.score > self.highscore:
                    self.highscore = game.score
                    self.saveHighScore(self.highscore)

                self.draw()

        def loadHighScore(self):
                """Carregar o HighScore do arquivo JSON."""
                try:
                    with open("highscore.json", "r") as file:
                        data = json.load(file)
                        return data.get("highscore", 0)
                except (FileNotFoundError, json.JSONDecodeError):
                    return 0

        def saveHighScore(self, score):
                """Salvar o HighScore no arquivo JSON."""
                with open("highscore.json", "w") as file:
                    json.dump({"highscore": score}, file)

        def checkGameOver(self, game):
                if self.rows < GAMEOVER_ROWS:
                    return

                for col in range(self.cols):
                    if self.grid[GAMEOVER_ROWS - 1][col].exists:
                        game.over = True
                        return

        def checkCollision(self, bullet):

                # Get the bullet and 'see' its future position
                # this is so that when the bullet stops existing and turns into the grid, it looks more smooth
                bullet_x, bullet_y = bullet.pos
                bullet_x += 0.5*bullet.dx
                bullet_y += 0.5*bullet.dy

                # Check every target and see if the bullet has collided with it
                for target in self.targets:
                        target_x, target_y = target.pos

                        # get the target's hitbox U,D,L,R position
                        L = target_x - (HITBOX_SIZE/2)
                        R = target_x + (HITBOX_SIZE/2)
                        U = target_y - (HITBOX_SIZE/2)
                        D = target_y + (HITBOX_SIZE/2)

                        # Check if the bullet is within the hitbox
                        if (bullet_y - (HITBOX_SIZE/2)) < D:		
                                if (bullet_x + (HITBOX_SIZE/2)) > L:	
                                        if (bullet_x - (HITBOX_SIZE/2)) < R:			
                                                if (bullet_y + (HITBOX_SIZE/2)) > U:

                                                        # If the bullet is within the hitbox, destroy it
                                                        bullet.exists = False

                                                        # There's been a collision
                                                        self.collided = True

                                                        # NOTE: theres another function that revives a bubble

                # if the bullet goes over the top of the screen, it counts a collision
                if bullet_y - BUBBLE_RADIUS < 0: 
                        bullet.exists = False
                        self.collided = True

        # Finds the closest non-existent bubble to the position of the bullet and revive it
        def reviveBubble(self, bullet):

                # renaming the var for readability
                collide_point = bullet.pos

                imaginary = []	# a list of all the non-existent bubbles
                dists = []		# a list of distances to the non-existent bubbles

                # create a list of all the non-existent bubbles
                for row in range(self.rows):
                        for col in range(self.cols):
                                if not self.grid[row][col].exists:
                                        imaginary.append(self.grid[row][col])

                # get the distance from the collision point to the non-existent bubble
                for bubble in imaginary:
                        x,y = collide_point
                        bubble_x, bubble_y = bubble.pos

                        dist = sqrt( (((x - bubble_x) ** 2) + (y - bubble_y) ** 2) )
                        dists.append(dist)

                # get the index if the closest non-existent bubble
                idx = dists.index(min(dists))
                # closest non-existent bubble is its replacement
                replacement = imaginary[idx]

                # revive the replacement bubble
                replacement.exists = True
                # its color is the bubblet's color
                replacement.color = bullet.color

                # we will use this bubble to check if it forms any clusters to pop
                return replacement

        # add/deletes rows to the top and/or bottom as necessary
        def updateRows(self):

                # after 'APPEND_COUNTDOWN' of collisions, add a row to the top
                if (self.collision_counter % APPEND_COUNTDOWN == 0) and (self.collision_counter != 0): self.appendTop()

                # if theres an existent bubble in the very last row, add a new row to the bottom
                # A bullet takes the place of a non-existent bubble so there should always be an empty
                # row at the very bottom of the grid
                for col in range(self.cols):
                        if self.grid[self.rows-1][col].exists:
                                self.appendBottom()
                                return

                # if the second last row is completely empty (have no existing bubbles), we can delete the last row
                for col in range(self.cols):
                        if self.grid[self.rows - 2][col].exists:
                                return

                self.deleteBottom()

        # simple function to add to the top 
        def appendTop(self):

                # add one to the row of every bubble that is already on the grid
                for row in range(self.rows):
                        for col in range(self.cols):
                                self.grid[row][col].row += 1

                # update total amount of rows
                self.rows += 1

                # Since we want to shift everything down, the opposite row will have an offset
                self.even_offset = not self.even_offset

                # create a new row and insert it to the grid
                new_row = []
                for col in range(self.cols):
                        # for now, the position will be 0,0
                        new_row.append(GridBubble(0, col, (0,0)))

                self.grid.insert(0, new_row)

                # calc the new position for every bubble
                for row in range(self.rows):
                        for col in range(self.cols):
                                self.grid[row][col].pos = GridManager.calcPos(row, col, self.even_offset)
                                # the bubbles are connected to other bubble objects, so we don't need to calc the comrades of every bubble
                                # we only need to reset the comrades of the bubbles of the first two rows
                                if (row == 0) or (row == 1): self.findComrades(self.grid[row][col])	

        # a simple function to add to the bottom
        def appendBottom(self):

                row = []

                # initialize a new row of bubbles with row = total rows
                for col in range(self.cols):
                        # calc the postition of the bubble
                        pos = GridManager.calcPos(self.rows, col, self.even_offset)
                        row.append(GridBubble(self.rows, col, pos, exists = False, color = BG_COLOR))

                # add it to the grid
                self.grid.append(row)

                # update the total amount of rows
                self.rows += 1

                # find the comrades of the last two rows
                for row in range(self.rows - 2, self.rows):
                        for col in range(self.cols):
                                self.findComrades(self.grid[row][col])

        # to delete a row from the bottom
        def deleteBottom(self):
                self.grid.pop()	# simply pop the last row
                self.rows -= 1	# update total amount of rows

                # Update the comrades of the new bottom
                for col in range(self.cols):
                        self.findComrades(self.grid[self.rows - 1][col])



        def popCluster(self, bubble, game):

                # get a list of all the bubbles of the same color using dept first search
                cluster = self.findCluster(bubble)

                if (len(cluster) >= 3) or (bubble.color == BLACK):			
                        while len(cluster) > 0:
                                bubble = cluster.pop()

                                frames = bubble.pop()
                                self.animations.append(frames)

                                game.score += 1

                                for comrade in bubble.getComrades():
                                        if comrade.exists and (comrade not in cluster):
                                                rooted = self.findRoot(comrade)
                                                if not rooted: cluster.append(comrade)


        def findCluster(self, bubble, reached = None):
                
                if reached == None: reached = []

                for comrade in bubble.getComrades():
                        if comrade.exists:
                                if (comrade not in reached) and ((comrade.color == bubble.color) or (bubble.color == BLACK)):
                                        reached.append(comrade)
                                        reached = self.findCluster(comrade, reached)

                return reached

        def findRoot(self, bubble, reached = None, rooted = False):

                # print('row, col = ({}, {})'.format(bubble.row, bubble.col))

                if reached == None:	reached = []

                if bubble.row == 0:
                        self.paths.append(reached)
                        return True

                for comrade in bubble.getComrades():
                        if comrade.exists and (comrade not in reached):
                                reached.append(comrade)

                                rooted = self.findRoot(comrade, reached)
                                if rooted:	return True



                return rooted
                

        def findComrades(self, bubble):
                bubble.L = None
                bubble.R = None
                bubble.UL = None
                bubble.UR = None
                bubble.DL = None
                bubble.DR = None

                even_offset = self.even_offset
                row = bubble.row
                col = bubble.col

                if col > 0: bubble.L = self.grid[row][col - 1]
                if col < (self.cols - 1): bubble.R = self.grid[row][col + 1]
                
                if not ((row % 2) == even_offset):  
                        if row > 0:
                                bubble.UL = self.grid[row - 1][col]

                                if col < (self.cols - 1):
                                        bubble.UR = self.grid[row - 1][col + 1]

                        if row < (self.rows - 1):
                                bubble.DL = self.grid[row + 1][col]

                                if col < (self.cols - 1):
                                        bubble.DR = self.grid[row + 1][col + 1]

                else:
                        if row > 0:
                                bubble.UR = self.grid[row - 1][col]

                                if col > 0:
                                        bubble.UL = self.grid[row - 1][col - 1]

                        if row < (self.rows - 1):
                                bubble.DR = self.grid[row + 1][col]

                                if col > 0:
                                        bubble.DL = self.grid[row + 1][col - 1]


        def updateComrades(self, bubble):

                for comrade in bubble.getComrades():
                        self.findComrades(comrade)

                        
        def findTargets(self):
                self.targets = []

                for row in range(self.rows):
                        for col in range(self.cols):
                                bubble = self.grid[row][col]

                                if not bubble.exists:
                                        for comrade in bubble.getComrades():
                                                if (comrade not in self.targets) and comrade.exists:
                                                        self.targets.append(comrade)

                # for target in self.targets: print('row, col = {}, {}'.format(target.row, target.col))

        @staticmethod
        def calcPos(row, col, even_offset):

                x = (col * ((ROOM_WIDTH - BUBBLE_RADIUS) / (GRID_COLS))) + WALL_BOUND_L + BUBBLE_RADIUS

                if not ((row % 2) == even_offset): 
                        x += BUBBLE_RADIUS

                y = BUBBLE_RADIUS + (row * BUBBLE_RADIUS * 2) 

                return (x,y)

        def draw(self):
                # Desenhar as bolhas na grade
                for row in range(self.rows):
                        for col in range(self.cols):
                            if ((self.collision_counter + 1) % APPEND_COUNTDOWN == 0):
                                self.grid[row][col].shake()
                            else:
                                self.grid[row][col].draw()

                # Exibir animações de bolhas estourando
                for animation in self.animations:
                        if not animation: 
                            self.animations.remove(animation)
                            continue
                        frame = animation.pop()
                        frame.draw()

                # Visualizações adicionais (opcional)
                if SHOW_COMRADES or VISUALIZATIONS:
                        for row in range(self.rows):
                            for col in range(self.cols):
                                bubble = self.grid[row][col]
                                bubble_x, bubble_y = bubble.pos

                                for comrade in bubble.getComrades():
                                    comrade_x, comrade_y = comrade.pos
                                    x_vec = (comrade_x - bubble_x) / 2
                                    y_vec = (comrade_y - bubble_y) / 2
                                    pg.draw.line(display, BLACK, bubble.pos, (bubble_x + x_vec, bubble_y + y_vec))

                if SHOW_TARGETS or VISUALIZATIONS:
                        for target in self.targets:
                            x, y = int(target.pos[0]), int(target.pos[1])
                            pg.draw.circle(display, BLACK, (x, y), 5)

                if SHOW_HITBOXES or VISUALIZATIONS:
                        for target in self.targets:
                            x, y = target.pos
                            hitbox = pg.Surface((HITBOX_SIZE, HITBOX_SIZE), pg.SRCALPHA, 32)
                            hitbox.fill((50, 50, 50, 180))
                            display.blit(hitbox, (x - HITBOX_SIZE / 2, y - HITBOX_SIZE / 2))

                if SHOW_ROOT_PATH or VISUALIZATIONS:
                        for path in self.paths:
                            for idx in range(len(path)):
                                if idx == 0:
                                    continue
                                pg.draw.line(display, BLACK, path[idx - 1].pos, path[idx].pos, 3)

                        if time.time() - self.prev_time > 0.01:
                            self.prev_time = time.time()
                            if self.paths:
                                del self.paths[0][0]
                                if not self.paths[0]:
                                    del self.paths[0]

                # Chamar o método para desenhar o HighScore na tela
                self.drawHighScore()

        def drawHighScore(self):
                """Desenha o placar HighScore na tela."""
                font = pg.font.Font(None, 36)  # Escolha de fonte e tamanho
                text = font.render(f"HighScore: {self.highscore}", True, (255, 255, 255))  # Texto em branco
                text_rect = text.get_rect(center=(ROOM_WIDTH // 3, 650))  # Posição centralizada no topo
                display.blit(text, text_rect)

