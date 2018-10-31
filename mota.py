# -*- coding: utf-8 -*-
"""
Created on Wed Sep 19 22:16:01 2018

@author: zx013
"""

'''
扩展方法
在对应目录下新建文件夹，添加图片和info文件，格式参照之前目录的格式
目前怪物类型可无限扩展

功能点
商店功能（每一段默认加攻或加防），加入商店对蒙特卡洛求解最优路径影响很大
其他技能
特殊道具（破墙等）
机关门
地面的岩浆（不是很好加）
密室

优化点
长条形区域有时需要分割一下，不然显得太空旷
长条区域可以放置多个怪物

目前剩余的问题
观看广告可以增加生命
增加捐赠二维码

击败boss应放置些物品
后台计算后续的楼层
'''

#import jnius_config
#jnius_config.add_classpath('jars/javaclass.jar')
#from jnius import autoclass

from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.clock import Clock
from kivy.lang import Builder

from setting import Setting, MazeBase
from cache import Config, Texture, Music
from maze import Maze
from hero import Opacity
from state import State

from functools import partial

with open('mota.kv', 'r', encoding='utf-8') as fp:
    Builder.load_string(fp.read())


class MotaImage(Image): pass
class MotaLayer(FloatLayout):
    def add(self, i, j, texture=None):
        image = MotaImage()
        image.texture = texture
        image.size = (Setting.pos_real + 1, Setting.pos_real + 1)
        image.pos = (j * Setting.pos_real, (Setting.col_show - i - 1) * Setting.pos_real)
        self.image[i][j] = image
        self.add_widget(image)
        return image

class FloorLabel(Label): pass

class Mota(FocusBehavior, FloatLayout):
    row = Setting.row_show
    col = Setting.col_show

    def __init__(self, **kwargs):
        super(Mota, self).__init__(**kwargs)
        self.operate = True
        self.step = 0
        #Music.background(init=True)

        self.maze = Maze()

        self.state = State(self.maze.herostate) #状态显示
        self.floorlabel = FloorLabel()
        self.front = MotaLayer()
        self.middle = MotaLayer()
        self.back = MotaLayer()

        self.add_widget(self.back)
        self.add_widget(self.middle)
        self.add_widget(self.front)
        self.add_widget(self.floorlabel)
        self.add_widget(self.state)
        for i in range(Setting.row_show):
            for j in range(Setting.col_show):
                self.front.add(i, j, Texture.next('empty'))
                self.middle.add(i, j)
                self.back.add(i, j, Texture.next('ground'))

        self.isstart = False
        Clock.schedule_interval(self.show, Config.step)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if not self.operate:
            return False
        key_map = {'w': 'up', 'a': 'left', 's': 'down', 'd': 'right'}
        key = keycode[1]
        if Setting.keyboard_wasd:
            if key in ('up', 'down', 'left', 'right'):
                key = ''
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
        elif key == 'p': #测试作弊
            self.maze.herostate.health += 1000
        return True

    #实现长按操作，极少情况会出现长按和点击同时触发的情况
    def on_touch_hold(self, touch):
        if touch.maze_pos is None:
            return False
        if self.hero.pos == touch.maze_pos:
            key = self.hero.name_show
        else:
            key = self.get_key(touch.maze_pos)
        name = Config.config[key].get('name', '未知')
        help = Config.config[key].get('help', '未知')

        pos_type = self.maze.get_type(touch.maze_pos)
        pos_value = self.maze.get_value(touch.maze_pos)
        if pos_type == MazeBase.Type.Active.monster:
            monster = self.maze.monster[pos_value[0]][pos_value[1]]
            damage = self.maze.get_damage(self.maze.herostate.attack, self.maze.herostate.defence, pos_value)
            self.statusbar.update('{}:    生命: {}  攻击: {}  防御: {}  伤害: {}'.format(name, monster['health'], monster['attack'], monster['defence'], damage))
        else:
            self.statusbar.update(':  '.join((name, help)))
        return True

    def touch_hold(self, touch, dt):
        touch.hold_dt += dt
        if touch.hold_dt > Setting.touch_time:
            touch.is_hold = True
            self.on_touch_hold(touch)
            Clock.unschedule(touch.hold)

    def on_touch_down(self, touch):
        if not self.operate:
            return False

        x, y = touch.pos
        if not self.collide_point(x, y):
            touch.maze_pos = None
        else:
            show_x = self.row - int(y / (Setting.pos_size * Setting.multiple)) - 1
            show_y = int(x / (Setting.pos_size * Setting.multiple))
            touch.maze_pos = (self.hero.floor, show_x, show_y)

        touch.is_hold = False
        touch.hold_dt = 0
        touch.hold = Clock.schedule_interval(partial(self.touch_hold, touch), Setting.touch_step)

    def on_touch_up(self, touch):
        if not self.operate:
            return False

        if hasattr(touch, 'hold'):
            if touch.is_hold:
                return False
            Clock.unschedule(touch.hold)
        else:
            x, y = touch.pos
            if not self.collide_point(x, y):
                touch.maze_pos = None
            else:
                show_x = self.row - int(y / (Setting.pos_size * Setting.multiple)) - 1
                show_y = int(x / (Setting.pos_size * Setting.multiple))
                touch.maze_pos = (self.hero.floor, show_x, show_y)

        if touch.maze_pos is None:
            return False
        self.hero.move_list = self.maze.find_path(self.hero.pos, touch.maze_pos)
        return True


    def ismove(self, pos):
        if pos in self.hero.action:
            return False
        pos_type = self.maze.get_type(pos)
        pos_value = self.maze.get_value(pos)
        herobase = self.maze.herobase
        herostate = self.maze.herostate

        scene = self.maze.story.check(pos) #有剧情则开启对话
        if scene:
            self.dialog.dialog_start(self.hero.pos, pos, scene)

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
            monster = self.maze.get_monster(pos_value)
            damage = self.maze.get_damage(herostate.attack, herostate.defence, pos_value)
            if herostate.health <= damage:
                return False
            herostate.health -= damage
            herostate.gold += monster['gold']
            herostate.experience += monster['experience']
            Music.play('blood') #获取剑后使用剑的声音和动画
            if pos_value[0] == 'boss':
                self.maze.kill_boss(pos)
        elif pos_type == MazeBase.Type.Active.npc:
            print('meet npc:', pos_type, pos_value)
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

        self.save(pos)


    def get_key(self, pos):
        pos_type = self.maze.get_type(pos)
        pos_value = self.maze.get_value(pos)

        if pos_type == MazeBase.Type.Static.init:
            pos_key = 'ground'
        elif pos_type == MazeBase.Type.Static.ground:
            pos_key = 'ground'
        elif pos_type == MazeBase.Type.Static.wall:
            pos_key = 'wall-{:0>2}'.format(pos_value)
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
        elif pos_type == MazeBase.Type.Item.defence:
            if pos_value == MazeBase.Value.Gem.small:
                pos_key = 'gem-defence-small'
            elif pos_value == MazeBase.Value.Gem.big:
                pos_key = 'gem-defence-big'
        elif pos_type == MazeBase.Type.Item.sword:
            if pos_value == MazeBase.Value.Weapon.iron:
                pos_key = 'sword-iron'
            elif pos_value == MazeBase.Value.Weapon.silver:
                pos_key = 'sword-silver'
            elif pos_value == MazeBase.Value.Weapon.stone:
                pos_key = 'sword-stone'
            elif pos_value == MazeBase.Value.Weapon.gem:
                pos_key = 'sword-gem'
            elif pos_value == MazeBase.Value.Weapon.sacred:
                pos_key = 'sword-sacred'
        elif pos_type == MazeBase.Type.Item.shield:
            if pos_value == MazeBase.Value.Weapon.iron:
                pos_key = 'shield-iron'
            elif pos_value == MazeBase.Value.Weapon.silver:
                pos_key = 'shield-silver'
            elif pos_value == MazeBase.Value.Weapon.stone:
                pos_key = 'shield-stone'
            elif pos_value == MazeBase.Value.Weapon.gem:
                pos_key = 'shield-gem'
            elif pos_value == MazeBase.Value.Weapon.sacred:
                pos_key = 'shield-sacred'
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
        elif pos_type == MazeBase.Type.Active.npc:
            if pos_value == MazeBase.Value.Npc.wisdom:
                pos_key = 'npc-wisdom'
            elif pos_value == MazeBase.Value.Npc.trader:
                pos_key = 'npc-trader'
            elif pos_value == MazeBase.Value.Npc.thief:
                pos_key = 'npc-thief'
            elif pos_value == MazeBase.Value.Npc.fairy:
                pos_key = 'npc-fairy'

        return pos_key

    #人物移动
    def show_hero(self):
        _, x, y = self.hero.old_pos
        image = self.front.image[x][y]
        image.texture = Texture.next('empty')

        _, x, y = self.hero.pos
        image = self.front.image[x][y]
        image.texture = Texture.next(self.hero.name, 'action', False)

        pos_key = self.get_key(self.hero.pos)
        image = self.middle.image[x][y]
        image.texture = Texture.next(pos_key, 'dynamic')

    #点击移动
    def show_move(self, dt):
        if not self.hero.move_list:
            return None

        if Config.active('hero-click', dt):
            key = self.hero.move_list.pop(0)
            self.move(key)

    #上下楼切换
    def show_stair(self, dt):
        if not self.hero.stair:
            return None
        state = self.hero.opacity.next(dt)
        if state == Opacity.Turn:
            if self.hero.stair == MazeBase.Value.Stair.down:
                self.hero.floor -= 1
            elif self.hero.stair == MazeBase.Value.Stair.up:
                self.hero.floor += 1
        elif state == Opacity.End:
            self.hero.stair = None

    def show_monster(self):
        floor = self.hero.floor
        health = self.maze.herostate.health
        attack = self.maze.herostate.attack
        defence = self.maze.herostate.defence
        for i in range(self.row):
            for j in range(self.col):
                pos = (floor, i, j)
                pos_type = self.maze.get_type(pos)
                pos_value = self.maze.get_value(pos)


                if pos_type == MazeBase.Type.Active.monster:
                    damage = self.maze.get_damage(attack, defence, pos_value)
                    info = self.maze.get_monster(pos_value)
                else:
                    damage = -1
                    info = {'health': '', 'attack': '', 'defence': ''}

                if Setting.show_health:
                    self.state.set_health(i, j, info['health'])
                if Setting.show_attack:
                    self.state.set_attack(i, j, info['attack'])
                if Setting.show_defence:
                    self.state.set_defence(i, j, info['defence'])
                if Setting.show_damage:
                    self.state.set_damage(i, j, health, damage)

                if pos_type == MazeBase.Type.Item.holy:
                    self.state.set_holy(i, j, pos_value)

    def show(self, dt):
        if not self.isstart:
            return None

        #Music.background()
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
        self.show_monster()

        show = {}
        static_texture = {}
        action_texture = {}
        for i in range(self.row):
            for j in range(self.col):
                pos = (floor, i, j)
                pos_key = self.get_key(pos)
                pos_style = 'action' if pos in self.hero.action else 'dynamic'

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


    def start(self):
        self.maze.start()
        self.hero = self.maze.hero
        self.isstart = True

    def save(self, pos):
        if self.step % Setting.step == 0:
            if self.maze.get_type(pos) != MazeBase.Type.Static.stair:
                self.maze.save()
            else:
                self.step -= 1
        self.step += 1

    def load(self):
        self.maze.load()
        _, x, y = self.maze.maze_info[0]['init']
        image = self.front.image[x][y]
        image.texture = Texture.next('empty')
        self.hero = self.maze.hero
        self.isstart = True
