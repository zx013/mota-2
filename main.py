# -*- coding: utf-8 -*-
"""
Created on Wed Aug 22 18:17:43 2018

@author: zx013
"""

'''
import sys
import platform
if platform.system().lower() == 'windows':
    from build import build
    build()
    sys.exit(0)
'''

#import jnius_config
#jnius_config.add_classpath('jars/javaclass.jar')
#from jnius import autoclass

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.clock import Clock

from setting import Setting, MazeBase
from cache import Config, Texture, Music
from maze import Maze
from hero import Opacity, Hero
from state import State

'''
扩展方法
在对应目录下新建文件夹，添加图片和info文件，格式参照之前目录的格式
目前怪物类型可无限扩展
'''
'''
长条形区域有时需要分割一下，不然显得太空旷
长条区域可以放置多个怪物
'''
class Menu(FloatLayout):
    def __init__(self, row, col, **kwargs):
        self.row = row
        self.col = col
        super(Menu, self).__init__(size=(Texture.size * self.row, Texture.size * self.col), size_hint=(None, None), **kwargs)

        self.main()

    def main(self):
        label_list = []

        label_list.append(self.add_label(-14, 7, '无', 8))
        label_list.append(self.add_label(-7, 9, '尽', 8))
        label_list.append(self.add_label(0, 10, '的', 8))
        label_list.append(self.add_label(7, 9, '魔', 8))
        label_list.append(self.add_label(14, 7, '塔', 8))

        label_list.append(self.add_label(0, 6, '2 . 0', 4))

        label_list.append(self.add_label(0, 0, '开 始', 6))
        label_list.append(self.add_label(0, -7, '设 置', 6))

        return label_list

    def add_label(self, x, y, text='', font_size=4):
        label = Label(text=text, pos=(x * Setting.size, y * Setting.size), font_name=Setting.font_path, font_size=font_size * Setting.size)
        self.add_widget(label)
        return label

    def on_touch_down(self, touch):
        print(touch)


class Layer(GridLayout):
    def __init__(self, row, col, **kwargs):
        self.row = row
        self.col = col
        super(Layer, self).__init__(rows=self.row, cols=self.col, size=(Texture.size * self.row, Texture.size * self.col), size_hint=(None, None), **kwargs)
        self.image = [[None for j in range(self.col)] for i in range(self.row)]
        self.texture = None #默认的texture

    def add(self, i, j, texture=None):
        self.texture = texture
        image = Image(size=(Texture.size, Texture.size), size_hint=(None, None))
        image.texture = texture
        self.image[i][j] = image
        self.add_widget(image)
        return image


class Map(FocusBehavior, FloatLayout):
    row = Setting.rows + 2
    col = Setting.cols + 2

    def __init__(self, **kwargs):
        super(Map, self).__init__(**kwargs)

        self.maze = Maze()
        self.maze.update()

        self.menu = Menu(self.row, self.col) #菜单
        self.state = State(self.maze.herostate, self.row, self.col) #状态显示
        self.state.easy()
        #切换楼层时显示目标楼层数，3和40是经验数据
        self.floorlabel= Label(pos=(0, Setting.size * 3), font_name=Setting.font_path, font_size=str(Setting.size * 40)) #楼层变换时显示层数
        self.floorlabel.canvas.opacity = 0

        self.front = Layer(self.row, self.col) #英雄移动
        self.middle = Layer(self.row, self.col) #物品和怪物
        self.back = Layer(self.row, self.col) #背景，全部用地面填充

        self.add_widget(self.back)
        self.add_widget(self.middle)
        self.add_widget(self.front)
        self.add_widget(self.floorlabel)
        self.add_widget(self.state)
        self.add_widget(self.menu)
        for i in range(self.row):
            for j in range(self.col):
                self.front.add(i, j, Texture.next('empty'))
                self.middle.add(i, j)
                self.back.add(i, j, Texture.next('ground'))

        self.hero = Hero(self.maze, self.row, self.col)
        Clock.schedule_interval(self.show, Config.step)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        key_map = {'w': 'up', 'a': 'left', 's': 'down', 'd': 'right'}
        key = keycode[1]
        if key in key_map:
            key = key_map[key]
        if key in ('up', 'down', 'left', 'right'):
            self.move(key)
        elif key == 'q':
            self.floorlabel.text = str(self.hero.floor_up)
            self.hero.stair = MazeBase.Value.Stair.up
            Music.play('floor')
        elif key == 'e':
            self.floorlabel.text = str(self.hero.floor_down)
            self.hero.stair = MazeBase.Value.Stair.down
            Music.play('floor')
        return True

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            x = self.row - int(touch.y / Texture.size) - 1
            y = int(touch.x / Texture.size)
            pos = (self.hero.floor, x, y)
            self.hero.move_list = self.maze.find_path(self.hero.pos, pos)
            return True
        return False


    def ismove(self, pos):
        if pos in self.hero.action:
            return False
        pos_type = self.maze.get_type(pos)
        pos_value = self.maze.get_value(pos)
        herobase = self.maze.herobase
        herostate = self.maze.herostate

        if pos_type == MazeBase.Type.Static.wall:
            return False
        elif pos_type == MazeBase.Type.Static.stair:
            if pos_value == MazeBase.Value.Stair.down:
                self.floorlabel.text = str(self.hero.floor_down)
            elif pos_value == MazeBase.Value.Stair.up:
                self.floorlabel.text = str(self.hero.floor_up)
            self.hero.stair = pos_value
            Music.play('floor')
            return True
        elif pos_type == MazeBase.Type.Static.door:
            if herostate.key[pos_value] == 0:
                return False
            herostate.key[pos_value] -= 1
            self.hero.action.add(pos)
            Music.play('opendoor')
            return False
        elif pos_type == MazeBase.Type.Item.key:
            herostate.key[pos_value] += 1
            Music.play('getitem')
        elif pos_type == MazeBase.Type.Item.attack:
            herostate.attack += herobase.base * pos_value
            Music.play('getitem')
        elif pos_type == MazeBase.Type.Item.defence:
            herostate.defence += herobase.base * pos_value
            Music.play('getitem')
        elif pos_type == MazeBase.Type.Item.potion:
            herostate.health += herobase.base * pos_value
            Music.play('getitem')
        elif pos_type == MazeBase.Type.Item.holy:
            herostate.health += herobase.base * pos_value
            Music.play('getitem')
        elif pos_type == MazeBase.Type.Active.monster:
            print('Fight monster {}'.format('-'.join(pos_value)))
            Music.play('blood')
            if pos_value[0] == 'boss':
                self.maze.kill_boss(pos)
        elif pos_type == MazeBase.Type.Active.rpc:
            return False

        self.maze.set_type(pos, MazeBase.Type.Static.ground)
        self.maze.set_value(pos, 0)
        return True

    def move(self, key):
        pos = self.hero.move_pos(key)
        if self.ismove(pos):
            self.hero.move(key)
        else:
            self.hero.move_list = []
        Config.reset(self.hero.name)
        Texture.reset(self.hero.name)
        self.show_hero()


    def get_key(self, pos, pos_style='static'):
        floor, x, y = pos
        pos_type = self.maze.get_type(pos)
        pos_value = self.maze.get_value(pos)

        if pos_type == MazeBase.Type.Static.init:
            pos_key = 'ground'
        elif pos_type == MazeBase.Type.Static.ground:
            pos_key = 'ground'
        elif pos_type == MazeBase.Type.Static.wall:
            if pos_value == MazeBase.Value.Wall.static:
                pos_key = 'wall-{:0>2}'.format(self.hero.wall)
                if self.maze.outside(pos): #有些墙会导致字体显示不清楚
                    pos_key = 'wall-02'
            elif pos_value == MazeBase.Value.Wall.dynamic:
                pos_key = 'wall-dynamic-{:0>2}'.format(self.hero.wall_dynamic)
                pos_style = 'dynamic'
        elif pos_type == MazeBase.Type.Static.stair:
            if pos_value == MazeBase.Value.Stair.down:
                pos_key = 'stair-down'
            elif pos_value == MazeBase.Value.Stair.up:
                pos_key = 'stair-up'
        elif pos_type == MazeBase.Type.Static.door:
            if pos_value == MazeBase.Value.Color.yellow:
                pos_key = 'door-yellow'
            elif pos_value == MazeBase.Value.Color.blue:
                pos_key = 'door-blue'
            elif pos_value == MazeBase.Value.Color.red:
                pos_key = 'door-red'
            elif pos_value == MazeBase.Value.Color.green:
                pos_key = 'door-green'
        elif pos_type == MazeBase.Type.Item.key:
            if pos_value == MazeBase.Value.Color.yellow:
                pos_key = 'key-yellow'
            elif pos_value == MazeBase.Value.Color.blue:
                pos_key = 'key-blue'
            elif pos_value == MazeBase.Value.Color.red:
                pos_key = 'key-red'
            elif pos_value == MazeBase.Value.Color.green:
                pos_key = 'key-green'
        elif pos_type == MazeBase.Type.Item.attack:
            if pos_value == MazeBase.Value.Gem.small:
                pos_key = 'gem-attack-small'
            elif pos_value == MazeBase.Value.Gem.big:
                pos_key = 'gem-attack-big'
            elif pos_value == MazeBase.Value.Gem.large:
                pos_key = 'weapen-attack-{:0>2}'.format(self.hero.weapon)
        elif pos_type == MazeBase.Type.Item.defence:
            if pos_value == MazeBase.Value.Gem.small:
                pos_key = 'gem-defence-small'
            elif pos_value == MazeBase.Value.Gem.big:
                pos_key = 'gem-defence-big'
            elif pos_value == MazeBase.Value.Gem.large:
                pos_key = 'weapen-defence-{:0>2}'.format(self.hero.weapon)
        elif pos_type == MazeBase.Type.Item.potion:
            if pos_value == MazeBase.Value.Potion.red:
                pos_key = 'potion-red'
            elif pos_value == MazeBase.Value.Potion.blue:
                pos_key = 'potion-blue'
            elif pos_value == MazeBase.Value.Potion.yellow:
                pos_key = 'potion-yellow'
            elif pos_value == MazeBase.Value.Potion.green:
                pos_key = 'potion-green'
        elif pos_type == MazeBase.Type.Item.holy:
            pos_key = 'holy'
        elif pos_type == MazeBase.Type.Active.monster:
            pos_key = '-'.join(pos_value)
            pos_style = 'dynamic'
        elif pos_type == MazeBase.Type.Active.rpc:
            if pos_value == MazeBase.Value.Rpc.wisdom:
                pos_key = 'npc-wisdom'
            elif pos_value == MazeBase.Value.Rpc.trader:
                pos_key = 'npc-trader'
            elif pos_value == MazeBase.Value.Rpc.thief:
                pos_key = 'npc-thief'
            elif pos_value == MazeBase.Value.Rpc.fairy:
                pos_key = 'npc-fairy'
            pos_style = 'dynamic'

        return pos_key, pos_style

    #人物移动
    def show_hero(self):
        _, x, y = self.hero.old_pos
        image = self.front.image[x][y]
        image.texture = Texture.next('empty')

        _, x, y = self.hero.pos
        image = self.front.image[x][y]
        image.texture = Texture.next(self.hero.name, 'action', False)

        pos_key, pos_style = self.get_key(self.hero.pos)
        image = self.middle.image[x][y]
        image.texture = Texture.next(pos_key, pos_style)

    #点击移动
    def show_move(self, dt):
        if not self.hero.move_list:
            return

        if Config.active('hero-click', dt):
            key = self.hero.move_list.pop(0)
            self.move(key)

    #上下楼切换
    def show_stair(self, dt):
        if not self.hero.stair:
            return
        state = self.hero.opacity.next(dt)
        if state == Opacity.Turn:
            if self.hero.stair == MazeBase.Value.Stair.down:
                self.hero.floor -= 1
            elif self.hero.stair == MazeBase.Value.Stair.up:
                self.hero.floor += 1
        elif state == Opacity.End:
            self.hero.stair = None

    def show(self, dt):
        self.focus = True

        self.show_move(dt)
        self.show_stair(dt)

        opacity = self.hero.opacity.opacity
        self.floorlabel.canvas.opacity = 1 - opacity
        self.state.canvas.opacity = opacity
        self.front.canvas.opacity = opacity
        self.middle.canvas.opacity = opacity
        floor = self.hero.floor
        if Config.active(self.hero.name, dt):
            self.show_hero()

        show = {}
        static_texture = {}
        action_texture = {}
        for i in range(self.row):
            for j in range(self.col):
                pos = (floor, i, j)
                if pos in self.hero.action:
                    pos_key, pos_style = self.get_key(pos, 'action')
                else:
                    pos_key, pos_style = self.get_key(pos)

                if pos_key not in show:
                    show[pos_key] = Config.active(pos_key, dt)
                if not show[pos_key]:
                    continue

                if pos in self.hero.action:
                    action_texture[pos_key] = Texture.next(pos_key, pos_style)
                    texture = action_texture[pos_key]
                else:
                    if pos_key not in static_texture:
                        static_texture[pos_key] = Texture.next(pos_key, pos_style)
                    texture = static_texture[pos_key]

                pos_image = self.middle.image[i][j]
                if texture:
                    pos_image.texture = texture
                else:
                    pos_image.texture = Texture.next('empty')
                    self.maze.set_type(pos, MazeBase.Type.Static.ground)
                    self.maze.set_value(pos, 0)
                    self.hero.action.remove(pos)


class Mota(App):
    def build(self):
        #javaclass = autoclass('com.test.JavaClass')
        #print(javaclass().show())

        self.map = Map()
        return self.map

    def on_start(self):
        pass

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == '__main__':
    mota = Mota()
    mota.run()
    mota.stop()
