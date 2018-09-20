# -*- coding: utf-8 -*-
"""
@author: zx013
"""
import os
import platform
from kivy.config import Config


#是否开启楼层飞行器
#默认移动动画间隔
#默认开门动画间隔
#默认怪物动画间隔

class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()

#全局设置
class Setting:
    #标题
    title = '无尽的魔塔'

    #标题宽度
    title_width = 28

    #标题所在的圆的半径，越小越突出
    title_radius = 28

    #版本号
    version = '2.0'

    #图标路径
    icon_path = os.path.join('data', 'icon.ico')

    #字体路径
    font_path = os.path.join('data', 'font.ttf')

    #难度，very-hard, hard, normal, easy, very-easy
    #难度决定了蒙特卡洛模拟的次数，剩余的血量和初始的钥匙
    difficult_config = {
        'very-hard': {'montecarlo': 5000, 'remain_potion': 0, 'key': {}},
        'hard': {'montecarlo': 1000, 'remain_potion': 100, 'key': {}},
        'normal': {'montecarlo': 500, 'remain_potion': 500, 'key': {'yellow': 1}},
        'easy': {'montecarlo': 100, 'remain_potion': 1000, 'key': {'yellow': 1, 'blue': 1}},
        'very-easy': {'montecarlo': 0, 'remain_potion': 5000, 'key': {'yellow': 1, 'blue': 1, 'red': 1}}
    }
    difficult_type = 'easy'
    difficult = difficult_config[difficult_type]

    #每个单元多少层
    base = 2

    #迷宫的大小，最小为3，最大不限，正常11，太大影响性能，最好为奇数
    size = 7

    #放缩倍数
    multiple = 2

    #每个点的大小（像素）
    pos_size = 32

    #行数，从左上开始往下
    @classproperty
    def rows(cls):
        return cls.size

    #显示的行数，包括外面一圈墙
    @classproperty
    def row_show(cls):
        return cls.rows + 2

    #列数，从左上开始往右
    cols = size

    #显示的列数，包括外面一圈墙
    @classproperty
    def col_show(cls):
        return cls.cols + 2

    #高度
    @classproperty
    def row_size(cls):
        return cls.pos_size * cls.row_show * cls.multiple

    #宽度
    @classproperty
    def col_size(cls):
        return cls.pos_size * cls.col_show * cls.multiple

    #蒙特卡洛模拟的次数，根据设备性能尽可能的增加，不小于难度的数值
    montecarlo = 100

    #击败boss后剩余血量不超过该值加100
    remain_potion = 100

    #是否显示怪物血量
    show_health = False

    #是否显示怪物攻击
    show_attack = False

    #是否显示怪物防御
    show_defence = False

    #是否在怪物上显示对应伤害
    show_damage = True

    #触控还是虚拟按键
    touch = True

    #移动速度（触控或鼠标操作时）
    speed = 10

    #是否是wasd操作
    keyboard_wasd = True

    #背景音乐
    sound_back = True

    #背景音量
    sound_back_volume = 15

    #音效
    sound_effect = True

    #音效音量
    sound_effect_volume = 20

#默认字体没有生效，很奇怪
Config.set('graphics', 'height', (Setting.rows + 2) * Setting.pos_size * Setting.multiple)
Config.set('graphics', 'width', (Setting.cols + 2) * Setting.pos_size * Setting.multiple)
Config.set('graphics', 'default_font', Setting.font_path)
Config.set('graphics', 'resizable', 0)
#android下这个直接就会卡住，必须注释掉才可以。。。
'''
if platform.system().lower() in ('windows', 'linux'):
    Config.set('kivy', 'window_icon', Setting.icon_path)

'''


#注意，出现random的属性，每次获取时值将不同
#迷宫设置
class MazeSetting:
    #行
    @classproperty
    def rows(cls):
        return Setting.rows

    #列
    @classproperty
    def cols(cls):
        return Setting.cols

    #保存的目录
    save_dir = 'save'
    #保存的文件后缀
    save_ext = 'save'

    @staticmethod
    def save_file(num):
        return '{save_dir}/{num}.{save_ext}'.format(save_dir=MazeSetting.save_dir, num=num, save_ext=MazeSetting.save_ext)

    #保存的层数，10时占用20M左右内存，100时占用50M左右内存
    @classproperty
    def save_floor(cls):
        return Setting.base

    #每几层一个单元
    @classproperty
    def base_floor(cls):
        return Setting.base

    #每个宝石增加的属性值（总属性百分比）
    attribute_value = 0.01

    #第一个怪物造成的最低伤害
    damage_min = 200

    #第一个怪物造成的最高伤害
    damage_max = 1000

    #精英怪物造成的最低伤害
    elite_min = 1000

    #精英怪物造成的最高伤害
    elite_max = 2000

    #boss造成的最低伤害
    boss_min = 2000

    #boss造成的最高伤害
    boss_max = 5000

    #某一类怪物不超过damage_total_num的数量低于damage_total_min
    damage_total_num = 3

    damage_total_min = 100

    #蒙特卡洛模拟的次数，该值越大，越接近最优解，同时增加运行时间，10000时基本为最优解
    @classproperty
    def montecarlo(cls):
        return max(Setting.montecarlo, Setting.difficult['montecarlo'])

    #使用近似最优解通关后至少剩余的额外的血量，可以用该参数调节难度
    @classproperty
    def remain_potion(cls):
        return max(Setting.remain_potion, Setting.difficult['remain_potion'])

    @classproperty
    def start_key(cls):
        return Setting.difficult['key']


#迷宫的基础属性
class MazeBase:
    class Type:
        class Static:
            init = 11
            ground = 12
            wall = 13
            shop = 14
            stair = 15
            door = 16

        class Active:
            monster = 21
            rpc = 22

        class Item:
            key = 31
            potion = 32

            attack = 33
            defence = 34

            holy = 35

        unknown = 99

    class Value:
        class Special:
            boss = 1
            trigger = 2
            item = 3
            shop = 4
            branch = 5

        class Wall:
            static = 1
            dynamic = 2

        class Shop:
            gold = 1
            experience = 2

        class Stair:
            up = 1
            down = 2

        #key和door的颜色
        class Color:
            none = 0
            yellow = 1
            blue = 2
            red = 3
            green = 4

            prison = 5
            trap = 6

            total = (yellow, blue, red, green)

        #起始时对应攻防平均属性的1%
        class Gem:
            small = 1
            big = 3
            large = 10

            total = (small, big, large)

        #起始时对应攻防平均属性的1%，设置太低会导致空间不够的情况，按初始默认的配置，总需求在30000左右
        class Potion:
            red = 50
            blue = 200
            yellow = 600
            green = 1200

            total = (red, blue, yellow, green)

        class Rpc:
            wisdom = 1
            trader = 2
            thief = 3
            fairy = 4

    class NodeType:
        none = 0
        area_normal = 1
        area_corner = 2
        Area = (area_normal, area_corner)
        road_normal = 3
        road_corner = 4
        Road = (road_normal, road_corner)
