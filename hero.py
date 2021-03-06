# -*- coding: utf-8 -*-
"""
@author: zx013
"""
from setting import MazeBase, MazeSetting
from cache import Config, Music
from g import gmaze

#每一个level的基础数值
class HeroBase:
    def __init__(self):
        self.level = -1
        self.health = 1000
        self.attack = 10
        self.defence = 10
        self.gold = 0
        self.experience = 0

        self.key = {
            MazeBase.Value.Color.yellow: 0,
            MazeBase.Value.Color.blue: 0,
            MazeBase.Value.Color.red: 0,
            MazeBase.Value.Color.green: 0
        }
        self.base = 1

        self.boss_attack = 0
        self.boss_defence = 0

    def update(self):
        self.level += 1
        self.floor = self.level * MazeSetting.base_floor + 1
        self.base = int((self.attack + self.defence) * 0.5 * MazeSetting.attribute_value) + 1

    @property
    def floor_start(self):
        return self.level * MazeSetting.base_floor + 1

    @property
    def floor_end(self):
        return (self.level + 1) * MazeSetting.base_floor


#key的绑定
class HeroStateDict(dict):
    __bind = {}
    statis = {}
    statis_increase = {} #增加量
    statis_decrease = {} #减少量

    def count(self, color, value):
        if color not in self.statis:
            self.statis[color] = 0
        if color not in self.statis_increase:
            self.statis_increase[color] = 0
        if color not in self.statis_decrease:
            self.statis_decrease[color] = 0

        if color in self.__dict__:
            diff = value - self[color]
            if diff > 0:
                self.statis_increase[color] += diff
            else:
                self.statis_decrease[color] -= diff
            self.statis[color] = value

    def __getitem__(self, color):
        return self.__dict__[color]

    def __setitem__(self, color, value):
        self.count(color, value)
        self.__dict__[color] = value
        if color in self.__bind:
            for label in self.__bind[color]:
                label.text = str(value)

    def set_color(self, color):
        for key, label in self.__bind.items():
            label.color = color

    def bind(self, color, label):
        if color not in self.__bind:
            self.__bind[color] = []
        self.__bind[color].append(label)

    def active(self):
        for color in self.__bind.keys():
            self[color] = self[color]


#实时状态，bind将状态绑定到label上，可以实时显示
class HeroState:
    __bind = {}
    disable = ['schedule', 'progress', 'floor']
    statis = {}
    statis_increase = {} #增加量
    statis_decrease = {} #减少量
    statis_record = {} #到过的地点统计

    def __init__(self, herobase):
        self.schedule = ''
        self.progress = 0 #保存update时的进度
        self.floor = 0
        self.health = herobase.health
        self.attack = herobase.attack
        self.defence = herobase.defence
        self.gold = herobase.gold
        self.experience = herobase.experience

        self.key = HeroStateDict()
        for color in MazeBase.Value.Color.total:
            self.key[color] = herobase.key[color]

    def count(self, name, value):
        if name in self.disable or not isinstance(value, int):
            return None
        if name not in self.statis:
            self.statis[name] = 0
        if name not in self.statis_increase:
            self.statis_increase[name] = 0
        if name not in self.statis_decrease:
            self.statis_decrease[name] = 0

        if name in self.__dict__:
            diff = value - self.__dict__[name]
            if diff > 0:
                self.statis_increase[name] += diff
            else:
                self.statis_decrease[name] -= diff
            self.statis[name] = value

    def record(self, pos_type, pos_value):
        key = (pos_type, pos_value)
        if key not in self.statis_record:
            self.statis_record[key] = 0
        self.statis_record[key] += 1

    def __setattr__(self, name, value):
        self.count(name, value)
        self.__dict__[name] = value
        if name in self.__bind:
            text = str(value)
            if name == 'floor':
                text = '{} F'.format(text)
            elif name == 'health':
                if value < 100:
                    color = (1, 0, 0, 1) #红色
                elif value < 200:
                    color = (1, 0.5, 0, 1) #橙色
                elif value < 500:
                    color = (1, 1, 0.5, 1) #浅黄
                elif value < 2000:
                    color = (0.5, 1, 0.5, 1) #浅绿
                else:
                    color = (0, 1, 0, 1) #绿色
            #左右对齐使长度固定
            for label in self.__bind[name]:
                label.text = text
                if name == 'health':
                    label.color = color

        elif name == 'wall':
            color = self.get_color(value)
            for key, label in self.__bind.items():
                label.color = color.get(key, color['color'])
            self.key.set_color(color['key'])

        if gmaze.story:
            gmaze.story.check_state(self, name)


    #可以加入缓存
    def get_color(self, wall):
        default = {
            'color': (1, 1, 1, 1),
            'title': (1, 1, 1, 1),
            'floor': (1, 1, 1, 1),
            'health': (0.5, 1, 0.5, 1),
            'attack': (1, 0.5, 0.5, 1),
            'defence': (0.5, 0.5, 1, 1),
            'gold': (1, 0.84, 0, 1),
            'experience': (0.53, 0.81, 0.92, 1),
            'key': (1, 1, 0.5, 1)
        }

        color = {}
        for key, val in Config.config[wall].items():
            if 'color' not in key:
                continue
            if '-' in key:
                key = key.split('-')[1]
            color[key] = val

        return dict(default, **color)

    def update(self, schedule, progress=0, reset=False):
        self.schedule = schedule
        if reset:
            progress = 0
        else:
            progress += progress
            if progress > 100:
                progress = 100
        self.progress = progress

    #将属性和标签绑定起来，属性改变时调整标签显示
    def bind(self, name, label):
        if name not in self.__bind:
            self.__bind[name] = []
        self.__bind[name].append(label)

    #所有bind之后，使用active激活，使初始化时能够显示数字，在bind中直接设置会导致后续设置和开始的重叠
    def active(self):
        for name in self.__bind.keys():
            value = getattr(self, name)
            setattr(self, name, value)
        self.key.active()


class Opacity:
    opacity = 1.0
    minimum = 0.2
    maximum = 1.0
    step = 0.2
    down = True

    dt = 0.1
    dtp = 0

    Run = 1
    Turn = 2
    End = 3

    def next(self, dt):
        if not self.active(dt):
            return self.Run

        if self.down:
            self.opacity -= self.step
            if self.opacity <= self.minimum:
                self.down = False
                return self.Turn
        else:
            self.opacity += self.step
            if self.opacity >= self.maximum:
                self.down = True
                return self.End
        return self.Run

    def active(self, dt):
        self.dtp += dt
        if self.dtp >= self.dt:
            self.dtp = 0
            return True
        return False


class Hero:
    color = 'blue' #颜色
    key = 'down' #朝向
    old_pos = (1, 0, 0)
    pos = (1, 0, 0)
    move_list = []
    floor_max = 0

    opacity = Opacity() #不透明度
    stair = None #是否触发上下楼的动作
    action = set() #执行动画的点

    def __init__(self, maze, **kwargs):
        self.maze = maze

    @property
    def name(self):
        return 'hero-{}-{}'.format(self.color, self.key)

    @property
    def name_show(self):
        return 'hero-{}-down'.format(self.color)

    def isfloor(self, floor):
        if self.maze.is_boss_floor(floor - 1): #往上时楼层还不存在
            return True
        if floor in self.maze.maze_info: #楼层存在
            stair = self.maze.maze_info[floor]['stair']
            if self.floor == floor + 1: #下楼
                if not self.maze.is_initial_floor(floor) and not self.maze.is_boss_floor(floor) and MazeBase.Value.Stair.up in stair: #楼梯存在
                    return True
            elif self.floor == floor - 1: #上楼
                if MazeBase.Value.Stair.down in stair:
                    return True
        elif self.maze.is_initial_floor(floor - 1):
            return True
        return False

    @property
    def floor(self):
        return self.pos[0]

    @floor.setter
    def floor(self, floor):
        if self.floor == floor - 1:
            if self.maze.is_initial_floor(floor - 1) or self.maze.is_boss_floor(floor - 1):
                Music.background(change=True)
                self.maze.update(self.maze.is_boss_floor(floor - 1))

        update_pos = None
        self.old_pos = self.pos
        if self.isfloor(floor) and floor in self.maze.maze_info:
            stair = self.maze.maze_info[floor]['stair']
            if self.floor == floor + 1: #下楼
                update_pos = set(stair[MazeBase.Value.Stair.up]).pop()
            elif self.floor == floor - 1: #上楼
                update_pos = set(stair[MazeBase.Value.Stair.down]).pop()
                if self.floor_max < floor:
                    self.floor_max = floor

        if update_pos:
            self.pos = update_pos
            self.maze.herostate.floor = self.floor


    @property
    def floor_up(self):
        return self.floor + self.isfloor(self.floor + 1)

    @property
    def floor_down(self):
        return self.floor - self.isfloor(self.floor - 1)

    #移动到的位置
    def move_pos(self, key):
        self.key = key
        key_map = {
            'up': (-1, 0),
            'down': (1, 0),
            'left': (0, -1),
            'right': (0, 1)
        }
        floor, x1, y1 = self.pos
        x2, y2 = key_map.get(self.key, (0, 0)) #将key转换为具体方向
        return (floor, x1 + x2, y1 + y2)

    def move(self, key):
        self.old_pos = self.pos
        self.pos = self.move_pos(key)
