#-*- coding:utf-8 -*-
import random
import pickle
from functools import reduce
#import copy


#限制随机，防止S/L，S/L时需存取__staticrandom
__random = random._inst.random
__staticrandom = []
def staticrandom(number=0):
    for i in range(number):
        __staticrandom.append(__random())
    def new_random():
        r = __random()
        __staticrandom.append(r)
        return __staticrandom.pop(0)
    random.random = random._inst.random = new_random


#异常时返回默认值
def except_default(default=None):
    def run_func(func):
        def run(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                print(ex)
                return default
        run.__name__ = func.__name__
        return run
    return run_func


class Tools:
    #从目录中选出一个值
    @staticmethod
    def dict_choice(dictionary):
        total = sum(dictionary.values())
        if total < 1:
            return
        rand = random.randint(1, total)
        for key, val in dictionary.items():
            rand -= val
            if rand <= 0:
                return key

    #迭代当前值和上一个值
    @staticmethod
    def iter_previous(iterator):
        previous = None
        for number, element in enumerate(iterator):
            if number > 0:
                yield previous, element
            previous = element


class MazeBase:
    class Type:
        class Static:
            ground = 11
            wall = 12
            shop = 13
            stair = 14
            door = 15

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

    class NodeType:
        none = 0
        area_normal = 1
        area_corner = 2
        Area = (area_normal, area_corner)
        road_normal = 3
        road_corner = 4
        Road = (road_normal, road_corner)


class TreeNode:
    def __init__(self, area, crack, special=False):
        self.Area = area
        self.Crack = crack
        self.Cover = self.Area | self.Crack

        self.Forward = {}
        self.Backward = {}

        self.Special = special
        self.Space = len(area)

        self.Door = 0
        self.Key = {
            MazeBase.Value.Color.yellow: 0,
            MazeBase.Value.Color.blue: 0,
            MazeBase.Value.Color.red: 0,
            MazeBase.Value.Color.green: 0
        }

        self.AttackGem = {
            MazeBase.Value.Gem.small: 0,
            MazeBase.Value.Gem.big: 0,
            MazeBase.Value.Gem.large: 0
        }

        self.DefenceGem = {
            MazeBase.Value.Gem.small: 0,
            MazeBase.Value.Gem.big: 0,
            MazeBase.Value.Gem.large: 0
        }

        self.Potion = {
            MazeBase.Value.Potion.red: 0,
            MazeBase.Value.Potion.blue: 0,
            MazeBase.Value.Potion.yellow: 0,
            MazeBase.Value.Potion.green: 0
        }

        self.IsDoor = False
        self.IsMonster = False
        self.IsElite = False
        self.IsBoss = False

        #英雄到达区域时获得的宝石属性总和，该值用来设置怪物
        self.Attack = 0
        self.Defence = 0

        self.Monster = None
        self.Damage = 0

        #圣水，开始时放置，用来调整第一个节点无法放置足够药水的问题
        self.HolyWater = 0

    @property
    def floor(self):
        return list(self.Area)[0][0]

    @property
    def start_floor(self):
        return self.boss_floor - MazeSetting.base_floor + 1

    @property
    def boss_floor(self):
        return int((self.floor - 1) / MazeSetting.base_floor + 1) * MazeSetting.base_floor

    @property
    def forbid(self):
        return filter(lambda x: Pos.inside(x) and (not (Pos.beside(x) & self.Crack)), reduce(lambda x, y: x ^ y, map(lambda x: Pos.corner(x) - self.Cover, self.Crack)))



class Cache:
    class staticproperty(property):
        def __get__(self, cls, owner):
            return staticmethod(self.fget).__get__(owner)()

    __staticcache = {}
    @classmethod
    def staticcache(self, func):
        self.__staticcache.setdefault(func, {'check': True, 'result': None})
        cache = self.__staticcache[func]
        def run(*args, **kwargs):
            if cache['check']:
                cache['result'] = func(*args, **kwargs)
                cache['check'] = False
            return cache['result']
        return run

    @classmethod
    def static(self, func):
        func = self.staticcache(func)
        func = self.staticproperty(func)
        return func

    #两个reloadcache之间获取的值相同
    @classmethod
    def staticrecount(self):
        for cache in self.__staticcache.values():
            cache['check'] = True

#注意，出现random的属性，每次获取时值将不同
class MazeSetting:
    #层数
    floor = 11
    #行
    rows = 11
    #列
    cols = 11
    #保存的目录
    save_dir = 'save'
    #保存的文件后缀
    save_ext = 'save'

    @staticmethod
    def save_file(num):
        return '{save_dir}/{num}.{save_ext}'.format(save_dir=MazeSetting.save_dir, num=num, save_ext=MazeSetting.save_ext)

    #保存的层数，10时占用20M左右内存，100时占用50M左右内存
    save_floor = 10
    #每几层一个单元
    base_floor = 10

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
    montecarlo_time = 3

    #使用近似最优解通关后至少剩余的额外的血量，可以用该参数调节难度
    extra_potion = 100


class MonsterInfo:
    path = 'data/monster'
    data_fluctuate = 10
    data_range = 20

    #name, resource, locate, level, health, attack, defence, skill
    data = {
        'slime': {
            'green':       ('name', '001.png', 0,  0, 60, 5, -2, False),
            'red':         ('name', '001.png', 1,  5, 80, 5, -2, False),
            'black':       ('name', '001.png', 2, 10, 100, 5, -2, False),
            'king':        ('name', '001.png', 3, 30, 120, 5, -2, False)
        },
        'bat': {
            'small':       ('name', '002.png', 0,  5, 80, 5, -2, False),
            'big':         ('name', '002.png', 1, 15, 100, 5, -2, False),
            'red':         ('name', '002.png', 2, 35, 120, 5, -2, False),
            'purple':      ('name', '011.png', 2, 65, 140, 5, -2, False)
        },
        'skeleton': {
            '1':           ('name', '003.png', 0, 10, 60, 5, -2, False),
            '2':           ('name', '003.png', 1, 15, 70, 5, -2, False),
            '3':           ('name', '003.png', 2, 30, 80, 5, -2, False),
            '4':           ('name', '003.png', 3, 50, 90, 5, -2, False),
            '5':           ('name', '011.png', 1, 70, 100, 5, -2, False)
        },
        'knight': {
            'yellow':      ('name', '007.png', 1, 25, 100, 5, -2, False),
            'red':         ('name', '007.png', 2, 40, 110, 5, -2, False),
            'blue':        ('name', '010.png', 3, 55, 120, 5, -2, False),
            'black':       ('name', '007.png', 3, 85, 130, 5, -2, False)
        },
        'mage': {
            'blue':        ('name', '005.png', 0, 10, 80, 5, -2, True),
            'yellow':      ('name', '009.png', 0, 20, 100, 5, -2, True),
            'red':         ('name', '005.png', 1, 40, 120, 5, -2, True)
        },
        'orcish': {
            '1':           ('name', '004.png', 0, 15, 120, 5, -2, False),
            '2':           ('name', '004.png', 1, 45, 130, 5, -2, False),
            '3':           ('name', '009.png', 3, 65, 140, 5, -2, False)
        },
        'guard': {
            'yellow':      ('name', '006.png', 0, 20, 110, 5, -2, False),
            'blue':        ('name', '006.png', 1, 40, 120, 5, -2, False),
            'red':         ('name', '006.png', 2, 60, 130, 5, -2, False)
        },
        'wizard': {
            'brown':       ('name', '005.png', 2, 30, 120, 5, -2, True),
            'red':         ('name', '005.png', 3, 60, 140, 5, -2, True)
        },
        'quicksilver': {
            'white':       ('name', '004.png', 3, 20, 80, 5, -2, False),
            'gray':        ('name', '009.png', 2, 80, 90, 5, -2, False)
        },
        'rock': {
            'brown':       ('name', '004.png', 2, 15, 40, 5, -2, False),
            'gray':        ('name', '011.png', 3, 75, 60, 5, -2, False)
        },
        'swordman': {
            'brown':       ('name', '006.png', 3, 25, 100, 5, -2, False),
            'red':         ('name', '009.png', 1, 90, 120, 5, -2, False)
        },
        'elite': {
            'vampire':     ('name', '002.png', 3, 85, 160, 20, 20, False),
            'darkmage':    ('name', '008.png', 2, 95, 80, -60, 20, True),
            'silverslime': ('name', '008.png', 3, 80, 100, 20, 10, False),
            'glodslime':   ('name', '011.png', 0, 90, 120, 30, 10, False),
        },
        'boss': {
            'blue':        ('name', '008.png', 1, 100, 160, 5, -2, False),
            'green':       ('name', '010.png', 2, 100, 170, 5, -2, False),
            'yellow':      ('name', '010.png', 1, 100, 180, 5, -2, False),
            'red':         ('name', '008.png', 0, 100, 190, 5, -2, False),
            'black':       ('name', '010.png', 0, 100, 200, 5, -2, False)
        }
    }


class Pos:
    class Move:
        up = (1, 0)
        down = (-1, 0)
        left = (0, 1)
        right = (0, -1)

    @staticmethod
    def inside(pos):
        z, x, y = pos
        if 0 < x < MazeSetting.rows + 1:
            if 0 < y < MazeSetting.cols + 1:
                return True
        return False

    @staticmethod
    def add(pos, move):
        z1, x1, y1 = pos
        x2, y2 = move
        return (z1, x1 + x2, y1 + y2)

    @staticmethod
    def sub(pos1, pos2):
        z1, x1, y1 = pos1
        z2, x2, y2 = pos2
        return (x1 - x2, y1 - y2)

    @staticmethod
    def beside(pos):
        z, x, y = pos
        return {(z, x - 1, y), (z, x + 1, y), (z, x, y - 1), (z, x, y + 1)}

    @staticmethod
    def corner(pos):
        z, x, y = pos
        return {(z, x - 1, y - 1), (z, x - 1, y + 1), (z, x + 1, y - 1), (z, x + 1, y + 1)}

    @staticmethod
    def around(pos):
        z, x, y = pos
        return {(z, x - 1, y - 1), (z, x - 1, y), (z, x - 1, y + 1), (z, x, y - 1), (z, x, y + 1), (z, x + 1, y - 1), (z, x + 1, y), (z, x + 1, y + 1)}

    @staticmethod
    def inline(pos_list):
        z, x, y = map(lambda x: len(set(x)), zip(*pos_list))
        if z == 1 and (x == 1 or y == 1):
            return True
        return False


#每一个level的基础数值
class HeroBase:
    def __init__(self):
        self.level = -1
        self.floor = 0
        self.health = 1000
        self.attack = 10
        self.defence = 10

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


#实时状态
class HeroState:
    def __init__(self, herobase):
        self.pos = (0, 0, 0)
        self.direction = Pos.Move.down
        self.floor = herobase.floor
        self.health = herobase.health
        self.attack = herobase.attack
        self.defence = herobase.defence

        self.key = {}
        for color in MazeBase.Value.Color.total:
            self.key[color] = herobase.key[color]


class Maze2:
    def __init__(self):
        self.maze = {}
        self.maze_map = {} #每一层不同点的分类集合
        self.maze_info = {} #每一层的信息，node, stair等
        self.monster = {}
        self.herobase = HeroBase()
        self.herostate = HeroState(self.herobase)

    def init(self, floor):
        for key in list(self.maze.keys()):
            if key < floor - MazeSetting.save_floor:
                del self.maze[key]
                del self.maze_map[key]
                del self.maze_info[key]

        self.maze[floor] = [[[0, 0] for j in range(MazeSetting.cols + 2)] for i in range(MazeSetting.rows + 2)]
        self.maze_map[floor] = {MazeBase.Type.Static.ground: set()}
        self.maze_info[floor] = {}
        for i in range(MazeSetting.rows + 2):
            for j in range(MazeSetting.cols + 2):
                if i in (0, MazeSetting.rows + 1) or j in (0, MazeSetting.cols + 1):
                    self.maze[floor][i][j][0] = MazeBase.Type.Static.wall
                else:
                    self.maze[floor][i][j][0] = MazeBase.Type.Static.ground
                    self.maze_map[floor][MazeBase.Type.Static.ground].add((floor, i, j))

        self.monster = {}


    def get_type(self, pos):
        z, x, y = pos
        return self.maze[z][x][y][0]

    def get_value(self, pos):
        z, x, y = pos
        return self.maze[z][x][y][1]

    def set_type(self, pos, value):
        z, x, y = pos
        if x < 1 or x > MazeSetting.rows:
            return
        if y < 1 or y > MazeSetting.cols:
            return
        type = self.maze[z][x][y][0]
        self.maze_map[z].setdefault(type, set())
        self.maze_map[z].setdefault(value, set())
        self.maze_map[z][type].remove(pos)
        self.maze_map[z][value].add(pos)
        self.maze[z][x][y][0] = value

    def set_value(self, pos, value):
        z, x, y = pos
        self.maze[z][x][y][1] = value

    def get_beside(self, pos, type):
        return {(z, x, y) for z, x, y in Pos.beside(pos) if self.maze[z][x][y][0] == type}

    #寻路使用
    def get_beside_way(self, pos):
        return {(z, x, y) for z, x, y in Pos.beside(pos) if self.maze[z][x][y][0] not in (MazeBase.Type.Static.wall, MazeBase.Type.Static.door, MazeBase.Type.Active.monster)}

    def get_corner(self, pos, type):
        return {(z, x, y) for z, x, y in Pos.corner(pos) if self.maze[z][x][y][0] == type}

    def get_around(self, pos, type):
        return {(z, x, y) for z, x, y in Pos.around(pos) if self.maze[z][x][y][0] == type}


    def get_extend(self, pos, type):
        extend = set()
        for beside in self.get_beside(pos, type):
            move = Pos.sub(beside, pos)
            next = beside
            while self.get_type(next) == type:
                beside = next
                next = Pos.add(beside, move)
            extend.add(beside)
        return extend



    #在floor层的type类型的区域中寻找符合func要求的点
    def find_pos(self, floor, type, func=None):
        if type not in self.maze_map[floor]:
            return set()
        if func:
            return {pos for pos in self.maze_map[floor][type] if func(pos)}
        else:
            return set(self.maze_map[floor][type])


    def is_pure(self, pos):
        if len(self.get_beside(pos, MazeBase.Type.Static.wall)) != 1:
            return False
        z, x, y = zip(*self.get_around(pos, MazeBase.Type.Static.wall))
        if len(set(x)) != 1 and len(set(y)) != 1:
            return False
        return True

    def get_pure(self, floor):
        #如果需要提高速度，每次放置wall时改变该值
        ground = self.maze_map[floor][MazeBase.Type.Static.ground] - self.maze_info[floor]['special']
        return {pos for pos in ground if self.is_pure(pos)}

    def is_wall(self, wall):
        for pos in wall[1:-1]:
            if self.get_beside(pos, MazeBase.Type.Static.wall):
                return False
        return True

    def get_wall(self, pos):
        wall = []
        move = Pos.sub(pos, self.get_beside(pos, MazeBase.Type.Static.wall).pop())
        while self.get_type(pos) == MazeBase.Type.Static.ground:
            wall.append(pos)
            pos = Pos.add(pos, move)
        return wall


    def is_rect(self, pos, rect1, rect2, row, col):
        floor, x, y = pos
        if x + row > MazeSetting.rows + 2 or y + col > MazeSetting.cols + 2:
            return False
        for i in range(row):
            for j in range(col):
                if self.get_type((floor, x + i, y + j)) != rect1[i][j]:
                    return False
        if rect2:
            for i in range(row):
                for j in range(col):
                    if rect2[i][j]:
                        type, value = rect2[i][j]
                        if type:
                            self.set_type((floor, x + i, y + j), type)
                        if value:
                            self.set_value((floor, x + i, y + j), value)
        return True

    #查找矩形，设置rect2的话则用rect2替换找到的矩形
    def find_rect(self, floor, rect1, rect2=None):
        _rect1 = list(zip(*rect1))
        _rect2 = list(zip(*rect2) if rect2 else None)
        row = len(rect1)
        col = len(_rect1)
        pos_list = [(floor, i, j) for i in range(0, MazeSetting.rows + 2) for j in range(0, MazeSetting.cols + 2)]
        random.shuffle(pos_list)
        for pos in pos_list:
            self.is_rect(pos, rect1, rect2, row, col)
            self.is_rect(pos, _rect1, _rect2, col, row)


    #获取pos的类型area, road, end
    def pos_type(self, pos):
        beside = self.get_beside(pos, MazeBase.Type.Static.ground)
        if len(beside) >= 3:
            return MazeBase.NodeType.area_normal
        if len(beside) == 1:
            return MazeBase.NodeType.road_corner
        if len(beside) == 2:
            (z1, x1, y1), (z2, x2, y2) = beside
            if x1 == x2 or y1 == y2:
                return MazeBase.NodeType.road_normal
            if self.get_type((z2, x2, y1) if pos == (z1, x1, y2) else (z1, x1, y2)) == MazeBase.Type.Static.wall:
                return MazeBase.NodeType.road_normal
            return MazeBase.NodeType.area_corner
        return MazeBase.NodeType.none

    #获取一片区域
    def get_area(self, pos):
        area = set()
        beside = set([pos])

        while beside:
            pos = beside.pop()
            area.add(pos)
            beside = beside | self.get_beside(pos, MazeBase.Type.Static.ground) - area
        return area


    def is_crack(self, pos):
        beside = self.get_beside(pos, MazeBase.Type.Static.ground)
        if len(beside) != 2:
            return False
        (z1, x1, y1), (z2, x2, y2) = beside
        if x1 != x2 and y1 != y2:
            return False
        return True

    def get_crack(self, floor):
        return self.find_pos(floor, MazeBase.Type.Static.wall, self.is_crack)

    def node_info(self, floor):
        self.maze_info[floor]['node'] = set()
        ground = self.find_pos(floor, MazeBase.Type.Static.ground)

        crack_list = self.get_crack(floor) #可打通的墙
        while ground:
            pos = None
            around = []
            area = self.get_area(ground.pop())
            for pos in area:
                around.append(self.get_beside(pos, MazeBase.Type.Static.wall))
            crack = reduce(lambda x, y: x | y, around) & crack_list
            node = TreeNode(area=area, crack=crack, special=pos in self.maze_info[floor]['special'])
            self.maze_info[floor]['node'].add(node)
            ground -= area

    def find_node(self, pos):
        z, x, y = pos
        for node in self.maze_info[z]['node']:
            if pos in node.Area:
                return node

    def merge_rect(self, floor):
        wall = MazeBase.Type.Static.wall
        ground = MazeBase.Type.Static.ground
        rect1 = [[wall, wall, wall, wall],
                [wall, ground, ground, wall],
                [wall, wall, wall, wall],
                [wall, ground, ground, wall],
                [wall, wall, wall, wall]]
        rect2 = [[0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, (ground, 0), (ground, 0), 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]
        self.find_rect(floor, rect1, rect2)

    def is_initial_floor(self, floor):
        if floor:
            return False
        return True

    def is_boss_floor(self, floor):
        if not floor % MazeSetting.base_floor:
            return True
        return False



    def get_rect(self, pos, width, height):
        z, x, y = pos
        rect = set()
        for i in range(x, x + width):
            for j in range(y, y + height):
                rect.add((z, i, j))
        return rect

    def get_rect_crack(self, pos, width, height):
        z, x, y = pos
        return self.get_rect((z, x - 1, y - 1), width + 2, height + 2) - self.get_rect(pos, width, height)

    #特殊区域，一块较大的矩形
    def create_special(self, floor):
        self.maze_info[floor]['special'] = set()
        if self.is_initial_floor(floor):
            pass
        elif self.is_boss_floor(floor): #boss层只有一个特殊区域
            pos_list = [(floor, 1, 1)]
            width = 7
            height = 7
            for pos in pos_list:
                area = self.get_rect(pos, width, height)
                crack = self.get_rect_crack(pos, width, height)
                for pos in crack:
                    self.set_type(pos, MazeBase.Type.Static.wall)
                self.maze_info[floor]['special'] |= area


    def create_wall(self, floor):
        pure = True
        while pure:
            pure = self.get_pure(floor)
            while pure:
                pos = random.choice(tuple(pure))
                wall = self.get_wall(pos)
                if self.is_wall(wall):
                    for pos in wall:
                        self.set_type(pos, MazeBase.Type.Static.wall)
                    break
                else:
                    pure -= set(wall)
        self.merge_rect(floor)
        self.node_info(floor)


    def crack_wall(self, floor):
        #special区域只开一个口
        #crack_list = self.get_crack(floor) #可打通的墙

        next_node = list(self.maze_info[floor]['node'])
        crack_set = set() #已设置墙和未设置墙区域之间可打通的墙
        special_set = set()

        while next_node:
            if not crack_set:
                node = random.choice(list(filter(lambda x: not x.Special, next_node)))
            else:
                crack_pos = random.choice(list(crack_set - special_set))
                #该区域和上一个区域之间的墙
                self.set_type(crack_pos, MazeBase.Type.Static.door)
                #self.set_value(crack_pos, MazeBase.Value.Color.yellow)

                for node in next_node:
                    if crack_pos in node.Crack:
                        break
            if node.Special:
                special_set |= node.Crack

            crack_set = (crack_set | node.Crack) - (crack_set & node.Crack)
            next_node.remove(node)


    def overlay_pos(self, node_list):
        pos_list = []
        for node in node_list: #选取当前楼层的一个区域
            if node.Special:
                continue
            for pos in node.Area:
                type = self.pos_type(pos)
                if type == MazeBase.NodeType.road_normal:
                    continue
                if self.get_beside(pos, MazeBase.Type.Static.door):
                    continue
                pos_list.append([node, pos])
        return pos_list

    def create_stair(self, floor):
        self.maze_info[floor]['stair'] = {MazeBase.Value.Stair.up: set(), MazeBase.Value.Stair.down: set()}
        down_node = list(self.maze_info[floor]['node'])
        random.shuffle(down_node)
        if self.is_initial_floor(floor - 1) or self.is_boss_floor(floor - 1):
            down_overlay = self.overlay_pos(down_node)
            down, down_pos = down_overlay.pop()
        else:
            up_node = list(self.maze_info[floor - 1]['node'])
            random.shuffle(up_node)
            #生成下行楼梯和上一层上行楼梯
            #两个区域重叠的点，尽可能避开特殊区域，如果没有合适的点，则楼梯不在同一位置
            class StairException(Exception): pass
            try:
                down_overlay = self.overlay_pos(down_node)
                up_overlay = self.overlay_pos(up_node)
                if not down_overlay:
                    down_overlay = map(lambda x: (x, random.choice(list(x.Area))), down_node)
                if not up_overlay:
                    up_overlay = map(lambda x: (x, random.choice(list(x.Area))), up_node)
                for down, down_pos in down_overlay:
                    for up, up_pos in up_overlay:
                        if self.maze_info[floor - 1]['stair'][MazeBase.Value.Stair.down] & up.Area:
                            continue
                        if down_pos[1] == up_pos[1] and down_pos[2] == up_pos[2]:
                            raise StairException
                #没有上下楼同一位置的楼梯，上下楼楼梯设置为不同位置
                #maze较小时可能触发
                raise StairException
            except StairException:
                up_node.remove(up)
                self.maze_info[floor - 1]['stair'][MazeBase.Value.Stair.up].add(up_pos)

        down_node.remove(down)
        self.maze_info[floor]['stair'][MazeBase.Value.Stair.down].add(down_pos)



    def create_tree(self, floor):
        self.maze_info[floor]['tree'] = set()
        for down in self.maze_info[floor]['stair'][MazeBase.Value.Stair.down]: #只有一个
            node = self.find_node(down)
            self.maze_info[floor]['tree'].add(node) #每一层起点

            node_list = [node]
            door_list = self.find_pos(floor, MazeBase.Type.Static.door)
            while node_list:
                node = node_list.pop()
                for door in door_list & node.Crack:
                    beside_pos = (self.get_beside(door, MazeBase.Type.Static.ground) - node.Area).pop()
                    beside_node = self.find_node(beside_pos)
                    node.Forward[door] = beside_node
                    beside_node.Backward[door] = node
                    node_list.append(beside_node)
                door_list -= node.Crack


    #遍历树
    def ergodic_yield(self, floor, across=1):
        node_list = [set(self.maze_info[floor]['tree']).pop()]
        boss_node = None #boss区域放在最后
        while node_list:
            node = random.choice(node_list)
            node_list += list(set(node.Forward.values()) - set(node_list))
            if floor + across > node.floor + 1:
                if node.Area & self.maze_info[node.floor]['stair'][MazeBase.Value.Stair.up]:
                    node_list.append(set(self.maze_info[node.floor + 1]['tree']).pop())
            node_list.remove(node)
            if self.is_boss_floor(node.floor) and node.Special:
                boss_node = node
            else:
               yield node
        if boss_node:
            yield boss_node

    def ergodic(self, floor, across=1):
        ergodic_list = [node for node in self.ergodic_yield(floor, across)]
        return ergodic_list


    def adjust_corner(self, floor):
        corner = set()
        for door in self.find_pos(floor, MazeBase.Type.Static.door):
            for beside in self.get_beside(door, MazeBase.Type.Static.ground):
                if self.pos_type(beside) == MazeBase.NodeType.road_corner:
                    corner.add(beside)
        #print(len(corner), len(self.find_pos(floor, MazeBase.Type.Static.door)))

    def adjust_trap(self, floor):
        wall = MazeBase.Type.Static.wall
        ground = MazeBase.Type.Static.ground
        rect = [[wall, wall, ground, wall, wall],
                [wall, ground, ground, ground, wall],
                [wall, wall, ground, wall, wall]]

    def adjust_crack(self, floor):
        for node in self.ergodic(floor, 1):
            for pos, forward in node.Forward.items():
                crack = node.Crack & forward.Crack
                if len(crack) <= 1:
                    continue
                if not Pos.inline(crack):
                    continue
                if not len(crack) % 2:
                    continue
                #print(crack)

    def adjust(self, floor):
        self.adjust_corner(floor)
        self.adjust_trap(floor)
        self.adjust_crack(floor)


    def set_stair(self, floor):
        for up in self.maze_info[floor]['stair'][MazeBase.Value.Stair.up]:
            self.set_type(up, MazeBase.Type.Static.stair)
            self.set_value(up, MazeBase.Value.Stair.up)
        for down in self.maze_info[floor]['stair'][MazeBase.Value.Stair.down]:
            self.set_type(down, MazeBase.Type.Static.stair)
            self.set_value(down, MazeBase.Value.Stair.down)


    #重新确定space大小，需要排除掉楼梯的空间
    def set_space(self, node_list):
        for node in node_list:
            space = 0
            for pos in node.Area:
                if self.get_type(pos) == MazeBase.Type.Static.stair:
                    continue
                space += 1
            node.Space = space


    #空间小于2不放置key，空间越小放置key概率越小
    def set_door(self, node_list):
        key_choice = {
            MazeBase.Value.Color.yellow: 27,
            MazeBase.Value.Color.blue: 9,
            MazeBase.Value.Color.red: 3,
            MazeBase.Value.Color.green: 1
        }

        key_choice_special = {
            MazeBase.Value.Color.red: 3,
            MazeBase.Value.Color.green: 1
        }

        #当前key的数量
        key_number = {
            MazeBase.Value.Color.yellow: 0,
            MazeBase.Value.Color.blue: 0,
            MazeBase.Value.Color.red: 0,
            MazeBase.Value.Color.green: 0
        }
        for number, node in enumerate(node_list):
            #第一个区域不放置
            if number == 0:
                continue
            #如果到达该区域还有有key时，可以设置门
            if sum(key_number.values()) > 0:
                if random.random() < 0.3 * (node.Space - 2):
                    door = Tools.dict_choice(key_number)
                    node.IsDoor = True
                    node.Door = door
                    node.Space -= 1
                    key_number[door] -= 1

                #特殊区域使用red或green的key
                if node.Special:
                    door = node.Door
                    for i in range(number - 1, -1, -1):
                        if node_list[i].Key[door] > 0:
                            node_list[i].Key[door] -= 1
                            key_number[door] -= 1
                            door = Tools.dict_choice(key_choice_special)
                            node_list[i].Key[door] += 1
                            key_number[door] += 1
                            node.IsDoor = True
                            node.Door = door
                            break
                    #boss区域需要放置门但不放置钥匙
                    if node.IsBoss:
                        continue
            else:
                if node.Special:
                    #到达特殊区域但没有钥匙，目前没出现过
                    print('speciel has no door')

            key_sum = sum(key_number.values())
            key_chance = 1 / (1.5 * (1.5 + float(key_sum)))
            if key_sum == 0:
                number = 1 #没有key时至少放置一把
            else:
                number = 0

            #一定概率放置多把，不超过空间减一（只放一把时，需放置其他奖励）
            #没有门时，需放置怪物
            while number <= node.Space - 1:
                if random.random() < key_chance:
                    number += 1
                    continue
                break

            for i in range(number):
                key = Tools.dict_choice(key_choice)
                if not key:
                    continue

                key_number[key] += 1
                node.Key[key] += 1
                node.Space -= 1

        #删除多余的key，从后往前
        if sum(key_number.values()) > 0:
            for node in node_list[::-1]:
                for key in key_number.keys():
                    while key_number[key] > 0 and node.Key[key] > 0:
                        key_number[key] -= 1
                        node.Key[key] -= 1
                        node.Space += 1
                if sum(key_number.values()) == 0:
                    break

    def set_monster(self, node_list):
        #没有door的需要放置monster
        #若空间小于等于1，不能放怪物，第一个区域不放置
        for node in node_list[1:-1]:
            if node.Space == 0:
                continue
            ismonster = False
            if not node.IsDoor:
                ismonster = True
            elif random.random() < 0.3 * (node.Space - 2):
                ismonster = True
            if ismonster:
                node.IsMonster = True
                node.Space -= 1

    #每个单元提升50%左右
    #应该根据当前属性分配，攻击高于防御时应提高防御宝石的数量，反之亦然
    def set_gem(self, node_list):
        gem_choice = {
            MazeBase.Value.Gem.small: 90,
            MazeBase.Value.Gem.big: 9,
            MazeBase.Value.Gem.large: 1
        }
        #确保攻防加成接近
        gem_chance = 0.5

        #有门且放置的钥匙数小于等于1，必须放置宝物，第一个位置不放宝石，防止空间不够
        for node in node_list[1:-1]:
            if node.Space == 0:
                continue
            isgem = False
            if node.IsDoor and sum(node.Key.values()) <= 1:
                isgem = True
            elif random.random() < 0.1 + 0.1 * node.Space:
                isgem = True
            if isgem:
                gem = Tools.dict_choice(gem_choice)
                if random.random() < gem_chance:
                    itemgem = node.AttackGem
                    gem_chance -= 0.02 * gem
                else:
                    itemgem = node.DefenceGem
                    gem_chance += 0.02 * gem
                itemgem[gem] += 1
                node.Space -= 1


    def set_elite(self, node_list):
        #自动生成的elite总数大致8个左右，可能有靠近或连续的情况
        #将elite数量限制在elite种类数，保证每个elite都不同
        list_len = len(node_list) - 1 #除去boss
        elite_number = 0
        elite_max = min(len(MonsterInfo.data['elite']), int(MazeSetting.base_floor / 2)) #最大elite数
        elite_range = MazeSetting.base_floor #两个elite之间的间隔
        elite_enable = [False if n < int(list_len / 4) or n > list_len -  elite_range else True for n in range(list_len)] #开始若干节点不设置elite

        for frequency in range(3):
            index_list = [v for v in range(list_len)]
            random.shuffle(index_list)
            for index in index_list:
                node = node_list[index]
                if not node.IsMonster:
                    continue
                if elite_number >= elite_max:
                    break

                iselite = False

                if frequency == 0:
                    if node.AttackGem[MazeBase.Value.Gem.large] > 0 or node.DefenceGem[MazeBase.Value.Gem.large] > 0: #剑盾
                        iselite = True
                    elif node.AttackGem[MazeBase.Value.Gem.big] > 0 or node.DefenceGem[MazeBase.Value.Gem.big] > 0: #大宝石，如果有钥匙增加几率
                        if random.random() < 0.3 + 0.5 * sum(node.Key.values()):
                            iselite = True
                    elif node.AttackGem[MazeBase.Value.Gem.small] > 0 or node.DefenceGem[MazeBase.Value.Gem.small] > 0: #小宝石，概率取决于钥匙数量
                        if random.random() < 0.2 * sum(node.Key.values()):
                            iselite = True
                    elif node.Key[MazeBase.Value.Color.red] > 0 or node.Key[            MazeBase.Value.Color.green] > 0: #红绿钥匙
                        iselite = True
                    elif sum(node.Key.values()) >= 3: #大量钥匙
                        iselite = True
                elif frequency == 1:
                    #若elite数量不足时，在空间大的区域设置elite
                    if node.Space > elite_number:
                        iselite = True
                elif frequency == 2:
                    #还是不足时，设置普通的monster
                    iselite = True

                if iselite and elite_enable[index]:
                    node.IsElite = True
                    elite_number += 1
                    #范围内不再设置elite
                    for i in range(max(0, index - elite_range), min(list_len, index + elite_range)):
                        elite_enable[i] = False


    def set_attribute(self, node_list):
        for pnode, node in Tools.iter_previous(node_list):
            node.Attack = pnode.Attack
            node.Defence = pnode.Defence

            for gem in MazeBase.Value.Gem.total:
                node.Attack += gem * pnode.AttackGem[gem]
                node.Defence += gem * pnode.DefenceGem[gem]


    def apply_monster(self, node_list):
        while True:
            random_list = [[] for node in node_list if node.IsMonster and not node.IsElite]
            monster_length = len(random_list)
            for key1, data1 in MonsterInfo.data.items():
                if key1 in ('elite', 'boss'):
                    continue
                for key2, data2 in data1.items():
                    level = random.choice(range(max(0, data2[3] - MonsterInfo.data_fluctuate), min(100, data2[3] + MonsterInfo.data_fluctuate)))
                    minimum = max(0, int(float(level - MonsterInfo.data_range) * monster_length / 100))
                    maximum = min(monster_length, int(float(level + MonsterInfo.data_range) * monster_length / 100))
                    for index in range(minimum, maximum):
                        random_list[index].append((key1, key2))

            if [] not in random_list:
                break
            print('random has empty data.')

        index = 0
        for node in node_list:
            if not node.IsMonster or node.IsElite:
                continue
            random_data = random_list[index]
            node.Monster = random.choice(random_data)
            index += 1


    #理论上每个elite应该尽量不同，避免elite间隔太大导致的偏差
    def apply_elite(self, node_list):
        random_list = list(MonsterInfo.data['elite'].keys())
        random.shuffle(random_list)
        for node in node_list:
            if not node.IsElite:
                continue
            node.Monster = ('elite', random_list.pop())


    def apply_boss(self, node_list):
        node = node_list[-1]
        node.IsMonster = True
        node.IsBoss = True
        node.Monster = ('boss', random.choice(list(MonsterInfo.data['boss'])))
        self.herobase.boss_attack = node.Attack
        self.herobase.boss_defence = node.Defence


    def adjust_monster(self, node_list):
        number_enable = [False for node in node_list]
        for number, node in enumerate(node_list):
            if not node.IsMonster:
                continue
            if number_enable[number] == True:
                continue

            monster = node.Monster
            monster_info = MonsterInfo.data[monster[0]][monster[1]]
            monster_health = monster_info[4] - 10 + random.randint(0, 20)
            monster_ismagic = monster_info[7]
            monster_number = []
            for number, node in enumerate(node_list):
                if node.IsMonster and node.Monster == monster:
                    monster_number.append(number)
                    number_enable[number] = True

            #monster_number跨度越大，越偏向于攻击，跨度越小，越偏向于防御
            #保证能够通过
            if monster_ismagic == True:
                attack = 20 + random.randint(1, 1 + len(monster_number))
            else:
                attack = node_list[monster_number[-1]].Defence + random.randint(1, 1 + len(monster_number))
            defence = node_list[monster_number[0]].Attack - random.randint(1, 1 + len(monster_number))

            #将伤害限制在范围内
            while True:
                damage_list = []
                for number in monster_number:
                    node = node_list[number]
                    if monster_ismagic:
                        damage = (monster_health - 1) // (node.Attack - defence) * attack
                    else:
                        damage = (monster_health - 1) // (node.Attack - defence) * (attack - node.Defence)
                    damage_list.append(damage)
                    node.Damage = damage

                damage = damage_list[0]
                if node.IsBoss:
                    if damage < MazeSetting.boss_min:
                        attack += random.randint(1, 20)
                        continue
                    if damage > MazeSetting.boss_max:
                        defence -= 1
                        continue
                elif node.IsElite:
                    if damage < MazeSetting.elite_min:
                        attack += random.randint(1, 10)
                        continue
                    if damage > MazeSetting.elite_max:
                        defence -= 1
                        continue
                else:
                    if damage < MazeSetting.damage_min:
                        #第一个怪物伤害太低
                        attack += random.randint(1, 5)
                        continue
                    if damage > MazeSetting.damage_max:
                        #第一个怪物伤害太高
                        #正常来说，defence不会小于-100（即实际值小于0）
                        defence -= 1
                        continue
                if len([damage for damage in damage_list if damage < MazeSetting.damage_total_min]) >= MazeSetting.damage_total_num:
                    attack += 1
                    continue
                break

            #初始值不一定为100
            #if monster_ismagic == False:
            #    attack += 100
            #defence += 100
            if monster[0] not in self.monster:
                self.monster[monster[0]] = {}
            self.monster[monster[0]][monster[1]] = {'health': monster_health, 'attack': attack, 'defence': defence, 'magic': monster_ismagic}


    #蒙特卡洛模拟获取尽可能的最优解
    def montecarlo(self, node_list, floor, across):
        min_damage = sum([node.Damage for node in node_list if node.IsMonster and not node.IsBoss])
        min_path = node_list
        boss = node_list[-1]

        number = 0
        while number < MazeSetting.montecarlo_time:
            total_damage = 0
            attack = 0
            defence = 0
            key = {
                MazeBase.Value.Color.yellow: 0,
                MazeBase.Value.Color.blue: 0,
                MazeBase.Value.Color.red: 0,
                MazeBase.Value.Color.green: 0
            }

            node_path = []
            node_list = [set(self.maze_info[floor]['tree']).pop()]
            node_len = len(node_list)
            random.shuffle(node_list)

            while node_list:
                node = None
                damage = 0
                for node in node_list:
                    if node.IsBoss:
                        node = None
                        continue
                    if node.IsDoor:
                        if key[node.Door] == 0:
                            node = None
                            continue
                    if node.IsMonster:
                        monster = node.Monster
                        monster_info = MonsterInfo.data[monster[0]][monster[1]]
                        monster_ismagic = monster_info[7]

                        monster_state = self.monster[monster[0]][monster[1]]
                        monster_health = monster_state['health']
                        monster_attack = monster_state['attack']
                        monster_defence = monster_state['defence']

                        if attack <= monster_defence:
                            node = None
                            continue
                        if monster_ismagic:
                            damage = (monster_health - 1) // (attack - monster_defence) * monster_attack
                        else:
                            damage = (monster_health - 1) // (attack - monster_defence) * (monster_attack - defence)
                        if damage < 0:
                            damage = 0

                        if total_damage + damage > min_damage:
                            node = None
                            continue
                    break

                #该次遍历失败
                if node == None:
                    break

                for color in MazeBase.Value.Color.total:
                    key[color] += node.Key[color]


                for gem in MazeBase.Value.Gem.total:
                    attack += gem * node.AttackGem[gem]
                    defence += gem * node.DefenceGem[gem]

                total_damage += damage
                node_path.append(node)

                #随机插入到列表中
                for __node in list(set(node.Forward.values()) - set(node_list)):
                    node_list.insert(random.randint(0, node_len), __node)
                    node_len += 1

                if floor + across > node.floor + 1:
                    if node.Area & self.maze_info[node.floor]['stair'][MazeBase.Value.Stair.up]:
                        __node = set(self.maze_info[node.floor + 1]['tree']).pop()
                        node_list.insert(random.randint(0, node_len), __node)
                        node_len += 1

                node_list.remove(node)
                node_len -= 1

            number += 1

            #未找到解决路径
            if len(node_list) > 1:
                continue

            if not node_list[0].IsBoss:
                continue

            node_path.append(boss)
            #找到更优路径
            if min_damage > total_damage:
                print('find min %d, old is %d (%d)' % (total_damage, min_damage, number))
                min_damage = total_damage
                min_path = node_path


        #重设属性值
        self.set_attribute(min_path)
        #重置伤害值，设置血瓶时使用
        for node in min_path:
            if node.IsMonster:
                monster = node.Monster
                monster_info = MonsterInfo.data[monster[0]][monster[1]]
                monster_ismagic = monster_info[7]

                monster_state = self.monster[monster[0]][monster[1]]
                monster_health = monster_state['health']
                monster_attack = monster_state['attack']
                monster_defence = monster_state['defence']

                if monster_ismagic:
                    damage = (monster_health - 1) // (node.Attack - monster_defence) * monster_attack
                else:
                    damage = (monster_health - 1) // (node.Attack - monster_defence) * (monster_attack - node.Defence)
                if damage < 0:
                    damage = 0
                node.Damage = damage

        return min_path


    def set_potion(self, node_list):
        #需要的总数
        potion = MazeSetting.extra_potion
        #boss区域不设置potion
        for node in node_list[-2::-1]:
            while node.Space > 0 and potion > 0:
                if potion >= MazeBase.Value.Potion.green:
                    node.Potion[MazeBase.Value.Potion.green] += 1
                    potion -= MazeBase.Value.Potion.green
                    node.Space -= 1
                elif potion >= MazeBase.Value.Potion.yellow:
                    node.Potion[MazeBase.Value.Potion.yellow] += 1
                    potion -= MazeBase.Value.Potion.yellow
                    node.Space -= 1
                elif potion >= MazeBase.Value.Potion.blue:
                    node.Potion[MazeBase.Value.Potion.blue] += 1
                    potion -= MazeBase.Value.Potion.blue
                    node.Space -= 1
                else:
                    node.Potion[MazeBase.Value.Potion.red] += 1
                    potion -= MazeBase.Value.Potion.red
                    node.Space -= 1

            if node.IsMonster:
                potion += node.Damage

        #第一格空间不够，去除放置的所有血瓶，放置圣水
        if potion >= 0:
            node = node_list[0]
            for color in MazeBase.Value.Potion.total:
                potion += color * node.Potion[color]
                node.Potion[color] = 0

            #圣水为100的倍数
            node.HolyWater = potion + 1
            node.HolyWater = ((node.HolyWater - 1) // 100 + 1) * 100
            potion -= node.HolyWater
            print('set holy: %d' % node.HolyWater)
        print('best way: %d' % (MazeSetting.extra_potion - potion))


    def set_maze(self, node_list):
        for node in node_list:
            for pos in node.Backward:
                if node.IsDoor:
                    self.set_type(pos, MazeBase.Type.Static.door)
                    self.set_value(pos, node.Door)
                    if node.IsMonster:
                        beside = self.get_beside(pos, MazeBase.Type.Static.ground)
                        pos = (beside & node.Area).pop()
                if node.IsMonster:
                    self.set_type(pos, MazeBase.Type.Active.monster)
                    self.set_value(pos, node.Monster)

            pos_set = set()
            for pos in node.Area:
                if self.get_type(pos) == MazeBase.Type.Static.ground:
                    pos_set.add(pos)

            for color in MazeBase.Value.Color.total:
                for i in range(node.Key[color]):
                    pos = pos_set.pop()
                    self.set_type(pos, MazeBase.Type.Item.key)
                    self.set_value(pos, color)

            for gem in MazeBase.Value.Gem.total:
                for i in range(node.AttackGem[gem]):
                    pos = pos_set.pop()
                    self.set_type(pos, MazeBase.Type.Item.attack)
                    self.set_value(pos, gem)
                for i in range(node.DefenceGem[gem]):
                    pos = pos_set.pop()
                    self.set_type(pos, MazeBase.Type.Item.defence)
                    self.set_value(pos, gem)

            for potion in MazeBase.Value.Potion.total:
                for i in range(node.Potion[potion]):
                    pos = pos_set.pop()
                    self.set_type(pos, MazeBase.Type.Item.potion)
                    self.set_value(pos, potion)

            if node.HolyWater > 0:
                pos = pos_set.pop()
                self.set_type(pos, MazeBase.Type.Item.holy)
                self.set_value(pos, node.HolyWater)


    def set_boss(self):
        pass

    #先确定一个较优路线，再通过蒙特卡洛模拟逼近最优路线
    def set_item(self):
        for f in range(self.herobase.floor_start, self.herobase.floor_end + 1):
            self.set_stair(f)
        node_list = self.ergodic(self.herobase.floor_start, MazeSetting.base_floor)
        node_list[-1].IsBoss = True
        self.set_space(node_list)
        self.set_door(node_list)
        self.set_monster(node_list)
        self.set_gem(node_list)
        self.set_elite(node_list)
        self.set_attribute(node_list)
        self.apply_monster(node_list)
        self.apply_elite(node_list)
        self.apply_boss(node_list)
        self.adjust_monster(node_list)

        node_list = self.montecarlo(node_list, self.herobase.floor_start, MazeSetting.base_floor)
        self.set_potion(node_list)

        self.set_maze(node_list)


    #更新为具体数值
    def update_monster(self):
        for name1, info1 in self.monster.items():
            for name2, info2 in info1.items():
                info2['health'] *= self.herobase.base
                info2['attack'] *= self.herobase.base
                if not info2['magic']:
                    info2['attack'] += self.herobase.defence
                info2['defence'] *= self.herobase.base
                info2['defence'] += self.herobase.attack


    def update(self):
        self.herobase.update() #进入下一个level
        #set_items该值才会被刷新
        self.herobase.attack += self.herobase.base * maze.herobase.boss_attack
        self.herobase.defence += self.herobase.base * maze.herobase.boss_defence

        for i in range(3):
            try:
                for floor in range(self.herobase.floor_start, self.herobase.floor_end + 1):
                    self.init(floor)
                    self.create_special(floor)
                    self.create_wall(floor)
                    self.crack_wall(floor)
                    self.create_stair(floor)
                    self.create_tree(floor)
                    self.adjust(floor)

                self.set_item()
                self.set_boss()
            except Exception as ex:
                #生成异常时重新生成
                print('reset : ', ex)
                continue
            break

        self.update_monster()


    def show(self, floor=None):
        for k in range(self.herobase.floor_start, self.herobase.floor_end + 1):
            if floor:
                k = floor
            print('floor :', k)
            for i in range(MazeSetting.rows + 2):
                line = ''
                for j in range(MazeSetting.cols + 2):
                    if self.get_type((k, i, j)) == MazeBase.Type.Static.ground:
                        line += '  '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Static.wall:
                        line += 'x '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Static.door:
                        line += 'o '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Active.monster:
                        line += 'm '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Item.key:
                        line += 'k '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Item.attack:
                        line += 'a '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Item.defence:
                        line += 'd '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Item.potion:
                        line += 'p '
                    elif self.get_type((k, i, j)) == MazeBase.Type.Item.holy:
                        line += 'h '
                    else:
                        line += str(self.get_value((k, i, j))) + ' '
                print(line)
            print()
            print()
            if floor:
                break
        import sys
        sys.stdout.flush()
        

    def save(self, num):
        record_dict = {
            'maze': self.maze, #迷宫构成
            'monster': self.monster, #怪物属性
            'herobase': self.herobase.__dict__, #等级状态
            'herostate': self.herostate.__dict__ #实时状态
        }

        record = pickle.dumps(record_dict, protocol=2)
        with open(MazeSetting.save_file(num), 'wb') as fp:
            fp.write(record)


    def load(self, num):
        try:
            with open(MazeSetting.save_file(num), 'rb') as fp:
                record = fp.read()

            record_dict = pickle.loads(record)
            self.maze = record_dict['maze']
            self.monster = record_dict['monster']
            for k, v in record_dict['herobase'].items():
                setattr(self, k, v)
            for k, v in record_dict['herostate'].items():
                setattr(self, k, v)
        except Exception as ex:
            print('load error: ', ex)


    #向外扩张，每一圈计数加一
    def find_around(self, pos_list, num):
        around = set()
        for pos in pos_list:
            around |= self.get_beside_way(pos)
        around -= pos_list | self.around[num - 1]
        return around

    @except_default([])
    def find_path(self, start_pos, end_pos):
        if self.get_type(end_pos) == MazeBase.Type.Static.wall:
            return []
        self.around = {-1: set()}
        around = set([start_pos])
        num = 0
        while around:
            self.around[num] = around
            around = self.find_around(around, num)
            num += 1
            if end_pos in around:
                way = []
                pos = end_pos
                for i in range(num)[::-1]:
                    old_z, old_x, old_y = pos
                    new_z, new_x, new_y = (self.get_beside_way(pos) & self.around[i]).pop()
                    pos = new_z, new_x, new_y
                    way.insert(0, (new_x - old_x, new_y - old_y))
                return way
        return []

    
    def move(self, move):
        move_pos = Pos.add(self.herostate.pos, move)
        move_type = self.get_type(move_pos)
        move_value = self.get_value(move_pos)
        move_enable = True

        if move_type == MazeBase.Type.Static.wall:
            move_enable = False
            print('wall')
        elif move_type == MazeBase.Type.Static.door:
            if self.herostate.key[move_value] == 0:
                move_enable = False
                print('no key')
            else:
                self.herostate.key[move_value] -= 1
                print('open door')
        elif move_type == MazeBase.Type.Active.monster:
            print('attack monster')
        elif move_type == MazeBase.Type.Item.key:
            self.herostate.key[move_value] += 1
        elif move_type == MazeBase.Type.Item.attack:
            self.herostate.attack += self.herobase.base * move_value
        elif move_type == MazeBase.Type.Item.defence:
            self.herostate.defence += self.herobase.base * move_value
        elif move_type == MazeBase.Type.Item.potion:
            self.herostate.health += self.herobase.base * move_value
        elif move_type == MazeBase.Type.Static.stair:
            if move_value == MazeBase.Value.Stair.up:
                self.herobase.floor += 1
                self.herostate.floor += 1
            elif move_value == MazeBase.Value.Stair.down:
                #if self.herostate.floor:
                self.herostate.floor -= 1
            print('stair')
                
        if move_enable:
            self.set_type(move_pos, MazeBase.Type.Static.ground)
            self.set_value(move_pos, 0)
            print('move')
            self.herostate.pos = move_pos
    
    def jump(self, type):
        pass


if __name__ == '__main__':
    maze = Maze2()
    maze.update()

    stairs_start = set(maze.maze_info[1]['stair'][MazeBase.Value.Stair.down]).pop()
    stairs_end = set(maze.maze_info[1]['stair'][MazeBase.Value.Stair.up]).pop()
    print(stairs_start, stairs_end)
    #print maze.tree_map[1]['info']['area']

    print(maze.find_path(stairs_start, stairs_end))

