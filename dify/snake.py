"""
贪吃蛇游戏 - 单文件版
基于 Pygame 实现的经典贪吃蛇游戏
作者: AI 应用开发工程师
版本: 1.0
"""

import pygame
import random
import sys
from enum import Enum

# 初始化 Pygame
pygame.init()

# ==================== 常量定义 ====================
# 屏幕尺寸
SCREEN_WIDTH = 1000  # 增加屏幕宽度以容纳信息区域
SCREEN_HEIGHT = 600

# 游戏区域尺寸
GAME_AREA_WIDTH = 600
GAME_AREA_HEIGHT = 600

# 网格系统
GRID_SIZE = 20  # 20x20 的网格
CELL_SIZE = GAME_AREA_WIDTH // GRID_SIZE  # 每个单元格30像素

# 信息区域尺寸（增加宽度以完整显示文字）
INFO_AREA_WIDTH = 400  # 增加到400像素
INFO_AREA_HEIGHT = SCREEN_HEIGHT

# 游戏区域位置（靠左显示，为信息区域留出空间）
GAME_AREA_X = 0
GAME_AREA_Y = 0

# 信息区域位置（在游戏区域右侧）
INFO_AREA_X = GAME_AREA_WIDTH
INFO_AREA_Y = 0

# 颜色定义 (RGB)
COLORS = {
    'background': (44, 62, 80),      # 深灰色 #2C3E50
    'grid': (52, 73, 94),           # 浅灰色 #34495E
    'snake_head': (46, 204, 113),   # 亮绿色 #2ECC71
    'snake_body': (39, 174, 96),    # 绿色 #27AE60
    'food': (231, 76, 60),          # 红色 #E74C3C
    'obstacle': (127, 140, 141),    # 灰色 #7F8C8D
    'text': (236, 240, 241),        # 浅灰色 #ECF0F1
    'text_dark': (52, 73, 94),      # 深灰色 #34495E
    'overlay': (0, 0, 0, 180)       # 半透明黑色覆盖层
}

# 游戏状态枚举
class GameState(Enum):
    START = 1      # 开始界面
    PLAYING = 2    # 游戏中
    PAUSED = 3     # 暂停
    GAME_OVER = 4  # 游戏结束

# 方向枚举
class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

# ==================== 字体辅助函数 ====================
def get_chinese_font(size):
    """获取支持中文的字体"""
    import os
    
    # macOS 系统字体路径（按优先级排序）
    font_paths = [
        '/System/Library/Fonts/STHeiti Medium.ttc',     # 华文黑体（最常用）
        '/System/Library/Fonts/STHeiti Light.ttc',      # 华文黑体（细体）
        '/System/Library/Fonts/Supplemental/Songti.ttc', # 宋体
        '/Library/Fonts/Arial Unicode.ttf',             # Arial Unicode
    ]
    
    # 尝试使用字体文件路径直接加载
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = pygame.font.Font(font_path, size)
                # 测试字体是否能正确渲染中文
                test_surface = font.render('测试', True, (255, 255, 255))
                if test_surface.get_width() > 20:  # 确保能正确渲染
                    return font
            except Exception:
                continue
    
    # 如果字体文件不存在，尝试使用系统字体名称
    chinese_font_names = [
        'PingFang SC',
        'STHeiti',
        'STSong',
        'Songti SC',
        'Arial Unicode MS',
    ]
    
    test_chinese = '测试'
    for font_name in chinese_font_names:
        try:
            font = pygame.font.SysFont(font_name, size)
            # 测试字体是否能正确渲染中文
            test_surface = font.render(test_chinese, True, (255, 255, 255))
            test_width = test_surface.get_width()
            # 中文应该比单个英文字母宽
            if test_width > 20:
                # 验证：中文应该比英文宽
                english_test = font.render('AA', True, (255, 255, 255))
                if test_width >= english_test.get_width() * 0.7:  # 中文通常和英文差不多宽或更宽
                    return font
        except Exception:
            continue
    
    # 最后的备选方案：使用系统默认字体
    try:
        return pygame.font.SysFont(None, size)
    except Exception:
        return pygame.font.Font(None, size)

# ==================== 游戏主类 ====================
class SnakeGame:
    def __init__(self):
        """初始化游戏"""
        # 创建游戏窗口
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Python 贪吃蛇游戏")
        
        # 设置窗口不可调整大小
        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
        
        # 创建时钟对象控制帧率
        self.clock = pygame.time.Clock()
        
        # 创建支持中文的字体对象
        self.font_large = get_chinese_font(72)
        self.font_medium = get_chinese_font(48)
        self.font_small = get_chinese_font(32)
        self.font_tiny = get_chinese_font(24)
        
        # 游戏状态
        self.state = GameState.START
        
        # 初始化障碍物列表（在 reset_game 之前初始化，避免属性错误）
        self.obstacles = []
        
        # 初始化游戏变量
        self.reset_game()
        
        # 帧率控制
        self.fps = 60
        self.move_timer = 0
        self.move_delay = 100  # 初始移动延迟(毫秒)，对应10帧/秒
        
        # 最高分记录
        self.high_score = 0
    
    def reset_game(self):
        """重置游戏状态"""
        # 蛇的初始位置（游戏区域中央）
        start_x = GRID_SIZE // 2
        start_y = GRID_SIZE // 2
        
        # 初始化蛇：长度为3，水平排列
        self.snake = [
            (start_x, start_y),      # 蛇头
            (start_x - 1, start_y),  # 蛇身第一节
            (start_x - 2, start_y)   # 蛇身第二节
        ]
        
        # 初始方向：向右
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        
        # 分数
        self.score = 0
        
        # 初始化障碍物（如果还没有初始化）
        if not hasattr(self, 'obstacles'):
            self.obstacles = []
        
        # 重新生成障碍物
        self.generate_obstacles()
        
        # 生成第一个食物
        self.food = self.generate_food()
        
        # 重置移动延迟
        self.move_delay = 100
        
        # 重置移动计时器
        self.move_timer = 0
    
    def generate_food(self):
        """生成食物，确保不在蛇身或障碍物上"""
        while True:
            # 随机生成食物位置
            food_pos = (
                random.randint(0, GRID_SIZE - 1),
                random.randint(0, GRID_SIZE - 1)
            )
            
            # 检查位置是否合法
            if (food_pos not in self.snake and 
                food_pos not in self.obstacles):
                return food_pos
    
    def generate_obstacles(self):
        """生成障碍物"""
        self.obstacles = []
        num_obstacles = random.randint(3, 5)  # 3-5个障碍物
        
        for _ in range(num_obstacles):
            while True:
                # 随机生成障碍物位置
                obstacle_pos = (
                    random.randint(2, GRID_SIZE - 3),  # 避免在边界生成
                    random.randint(2, GRID_SIZE - 3)
                )
                
                # 确保不在蛇的初始位置和食物位置（如果食物已存在）
                food_check = (obstacle_pos != self.food) if hasattr(self, 'food') else True
                if (obstacle_pos not in self.snake and 
                    food_check and
                    obstacle_pos not in self.obstacles):
                    self.obstacles.append(obstacle_pos)
                    break
    
    def handle_events(self):
        """处理游戏事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            elif event.type == pygame.KEYDOWN:
                # ESC键：退出游戏
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                
                # 空格键：控制游戏状态
                elif event.key == pygame.K_SPACE:
                    if self.state == GameState.START:
                        self.state = GameState.PLAYING
                    elif self.state == GameState.PLAYING:
                        self.state = GameState.PAUSED
                    elif self.state == GameState.PAUSED:
                        self.state = GameState.PLAYING
                    elif self.state == GameState.GAME_OVER:
                        self.reset_game()
                        self.state = GameState.PLAYING
                
                # 方向键控制（仅在游戏中有效）
                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_UP and self.direction != Direction.DOWN:
                        self.next_direction = Direction.UP
                    elif event.key == pygame.K_DOWN and self.direction != Direction.UP:
                        self.next_direction = Direction.DOWN
                    elif event.key == pygame.K_LEFT and self.direction != Direction.RIGHT:
                        self.next_direction = Direction.LEFT
                    elif event.key == pygame.K_RIGHT and self.direction != Direction.LEFT:
                        self.next_direction = Direction.RIGHT
    
    def update(self, delta_time):
        """更新游戏状态"""
        # 更新移动计时器
        self.move_timer += delta_time
        
        # 只有在游戏进行中时才更新游戏逻辑
        if self.state != GameState.PLAYING:
            return
        
        # 更新方向（防止在同一帧内反向移动）
        self.direction = self.next_direction
        
        # 检查是否到了移动时间
        if self.move_timer >= self.move_delay:
            self.move_timer = 0
            
            # 获取蛇头当前位置
            head_x, head_y = self.snake[0]
            
            # 根据方向计算新的蛇头位置
            dx, dy = self.direction.value
            new_head = (head_x + dx, head_y + dy)
            
            # 检查碰撞
            if self.check_collision(new_head):
                self.state = GameState.GAME_OVER
                # 更新最高分
                if self.score > self.high_score:
                    self.high_score = self.score
                return
            
            # 移动蛇
            self.snake.insert(0, new_head)
            
            # 检查是否吃到食物
            if new_head == self.food:
                # 增加分数
                self.score += 10
                
                # 每得50分增加速度（减少移动延迟）
                if self.score % 50 == 0:
                    self.move_delay = max(50, self.move_delay - 10)  # 最小延迟50ms
                
                # 生成新食物
                self.food = self.generate_food()
            else:
                # 如果没有吃到食物，移除蛇尾
                self.snake.pop()
    
    def check_collision(self, position):
        """检查碰撞"""
        x, y = position
        
        # 检查是否撞墙
        if x < 0 or x >= GRID_SIZE or y < 0 or y >= GRID_SIZE:
            return True
        
        # 检查是否撞到自己
        if position in self.snake:
            return True
        
        # 检查是否撞到障碍物
        if position in self.obstacles:
            return True
        
        return False
    
    def draw(self):
        """绘制游戏界面"""
        # 清屏，填充背景色
        self.screen.fill(COLORS['background'])
        
        # 绘制游戏区域背景
        pygame.draw.rect(
            self.screen,
            COLORS['grid'],
            (GAME_AREA_X, GAME_AREA_Y, GAME_AREA_WIDTH, GAME_AREA_HEIGHT)
        )
        
        # 绘制网格线
        for i in range(GRID_SIZE + 1):
            # 垂直线
            pygame.draw.line(
                self.screen,
                COLORS['background'],
                (GAME_AREA_X + i * CELL_SIZE, GAME_AREA_Y),
                (GAME_AREA_X + i * CELL_SIZE, GAME_AREA_Y + GAME_AREA_HEIGHT),
                1
            )
            # 水平线
            pygame.draw.line(
                self.screen,
                COLORS['background'],
                (GAME_AREA_X, GAME_AREA_Y + i * CELL_SIZE),
                (GAME_AREA_X + GAME_AREA_WIDTH, GAME_AREA_Y + i * CELL_SIZE),
                1
            )
        
        # 绘制障碍物
        for obstacle in self.obstacles:
            x, y = obstacle
            rect = pygame.Rect(
                GAME_AREA_X + x * CELL_SIZE,
                GAME_AREA_Y + y * CELL_SIZE,
                CELL_SIZE, CELL_SIZE
            )
            pygame.draw.rect(self.screen, COLORS['obstacle'], rect)
        
        # 绘制蛇
        for i, (x, y) in enumerate(self.snake):
            # 计算绘制位置和大小
            rect = pygame.Rect(
                GAME_AREA_X + x * CELL_SIZE + 1,
                GAME_AREA_Y + y * CELL_SIZE + 1,
                CELL_SIZE - 2, CELL_SIZE - 2
            )
            
            # 蛇头用不同颜色
            if i == 0:
                pygame.draw.rect(self.screen, COLORS['snake_head'], rect)
                # 绘制蛇头眼睛
                eye_size = CELL_SIZE // 6
                if self.direction == Direction.RIGHT:
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.right - eye_size, rect.top + eye_size*2), eye_size)
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.right - eye_size, rect.bottom - eye_size*2), eye_size)
                elif self.direction == Direction.LEFT:
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.left + eye_size, rect.top + eye_size*2), eye_size)
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.left + eye_size, rect.bottom - eye_size*2), eye_size)
                elif self.direction == Direction.UP:
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.left + eye_size*2, rect.top + eye_size), eye_size)
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.right - eye_size*2, rect.top + eye_size), eye_size)
                elif self.direction == Direction.DOWN:
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.left + eye_size*2, rect.bottom - eye_size), eye_size)
                    pygame.draw.circle(self.screen, COLORS['text_dark'], 
                                     (rect.right - eye_size*2, rect.bottom - eye_size), eye_size)
            else:
                pygame.draw.rect(self.screen, COLORS['snake_body'], rect)
        
        # 绘制食物（圆形）
        food_x, food_y = self.food
        food_rect = pygame.Rect(
            GAME_AREA_X + food_x * CELL_SIZE + CELL_SIZE//4,
            GAME_AREA_Y + food_y * CELL_SIZE + CELL_SIZE//4,
            CELL_SIZE//2, CELL_SIZE//2
        )
        pygame.draw.ellipse(self.screen, COLORS['food'], food_rect)
        
        # 绘制信息区域
        self.draw_info_area()
        
        # 根据游戏状态绘制覆盖层
        if self.state == GameState.START:
            self.draw_start_screen()
        elif self.state == GameState.PAUSED:
            self.draw_pause_screen()
        elif self.state == GameState.GAME_OVER:
            self.draw_game_over_screen()
        
        # 更新显示
        pygame.display.flip()
    
    def draw_info_area(self):
        """绘制信息区域"""
        # 信息区域背景
        info_bg = pygame.Rect(INFO_AREA_X, INFO_AREA_Y, INFO_AREA_WIDTH, INFO_AREA_HEIGHT)
        pygame.draw.rect(self.screen, COLORS['text_dark'], info_bg)
        
        # 绘制信息区域边框
        pygame.draw.line(self.screen, COLORS['grid'], 
                        (INFO_AREA_X, 0), (INFO_AREA_X, SCREEN_HEIGHT), 2)
        
        # 计算文字起始位置（留出足够的边距）
        text_x = INFO_AREA_X + 20  # 左边距20像素
        
        # 当前分数
        score_text = self.font_medium.render("分数", True, COLORS['text'])
        score_value = self.font_large.render(f"{self.score}", True, COLORS['snake_head'])
        self.screen.blit(score_text, (text_x, 30))
        self.screen.blit(score_value, (text_x, 80))
        
        # 最高分
        high_score_text = self.font_small.render(f"最高分: {self.high_score}", True, COLORS['text'])
        self.screen.blit(high_score_text, (text_x, 150))
        
        # 速度指示
        speed = int(1000 / self.move_delay)  # 转换为帧/秒
        speed_text = self.font_small.render(f"速度: {speed} FPS", True, COLORS['text'])
        self.screen.blit(speed_text, (text_x, 190))
        
        # 蛇长度
        length_text = self.font_small.render(f"长度: {len(self.snake)}", True, COLORS['text'])
        self.screen.blit(length_text, (text_x, 230))
        
        # 操作说明
        controls_y = 290
        controls = [
            "操作说明:",
            "↑ ↓ ← → : 控制方向",
            "空格键 : 开始/暂停/重玩",
            "ESC键 : 退出游戏"
        ]
        
        for i, text in enumerate(controls):
            control_text = self.font_tiny.render(text, True, COLORS['text'])
            self.screen.blit(control_text, (text_x, controls_y + i * 30))
        
        # 游戏提示
        tips_y = 420
        tips = [
            "提示:",
            "• 不要撞墙或撞到自己",
            "• 吃到食物可以增加长度",
            "• 避开灰色障碍物",
            "• 分数越高速度越快"
        ]
        
        for i, text in enumerate(tips):
            tip_text = self.font_tiny.render(text, True, COLORS['text'])
            self.screen.blit(tip_text, (text_x, tips_y + i * 28))
    
    def draw_start_screen(self):
        """绘制开始界面"""
        # 创建半透明覆盖层
        overlay = pygame.Surface((GAME_AREA_WIDTH, GAME_AREA_HEIGHT), pygame.SRCALPHA)
        overlay.fill(COLORS['overlay'])
        self.screen.blit(overlay, (GAME_AREA_X, GAME_AREA_Y))
        
        # 游戏标题（在游戏区域中心）
        game_center_x = GAME_AREA_X + GAME_AREA_WIDTH // 2
        title = self.font_large.render("贪吃蛇游戏", True, COLORS['snake_head'])
        title_rect = title.get_rect(center=(game_center_x, SCREEN_HEIGHT//2 - 100))
        self.screen.blit(title, title_rect)
        
        # 开始提示
        start_text = self.font_medium.render("按空格键开始游戏", True, COLORS['text'])
        start_rect = start_text.get_rect(center=(game_center_x, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(start_text, start_rect)
        
        # 作者信息
        author_text = self.font_tiny.render("Python 贪吃蛇游戏 v1.0", True, COLORS['text'])
        author_rect = author_text.get_rect(center=(game_center_x, SCREEN_HEIGHT - 50))
        self.screen.blit(author_text, author_rect)
    
    def draw_pause_screen(self):
        """绘制暂停界面"""
        # 创建半透明覆盖层
        overlay = pygame.Surface((GAME_AREA_WIDTH, GAME_AREA_HEIGHT), pygame.SRCALPHA)
        overlay.fill(COLORS['overlay'])
        self.screen.blit(overlay, (GAME_AREA_X, GAME_AREA_Y))
        
        # 暂停文字（在游戏区域中心）
        game_center_x = GAME_AREA_X + GAME_AREA_WIDTH // 2
        pause_text = self.font_large.render("游戏暂停", True, COLORS['text'])
        pause_rect = pause_text.get_rect(center=(game_center_x, SCREEN_HEIGHT//2 - 50))
        self.screen.blit(pause_text, pause_rect)
        
        # 继续提示
        continue_text = self.font_medium.render("按空格键继续", True, COLORS['text'])
        continue_rect = continue_text.get_rect(center=(game_center_x, SCREEN_HEIGHT//2 + 50))
        self.screen.blit(continue_text, continue_rect)
    
    def draw_game_over_screen(self):
        """绘制游戏结束界面"""
        # 创建半透明覆盖层
        overlay = pygame.Surface((GAME_AREA_WIDTH, GAME_AREA_HEIGHT), pygame.SRCALPHA)
        overlay.fill(COLORS['overlay'])
        self.screen.blit(overlay, (GAME_AREA_X, GAME_AREA_Y))
        
        # 游戏结束文字（在游戏区域中心）
        game_center_x = GAME_AREA_X + GAME_AREA_WIDTH // 2
        game_over_text = self.font_large.render("游戏结束", True, COLORS['food'])
        game_over_rect = game_over_text.get_rect(center=(game_center_x, SCREEN_HEIGHT//2 - 100))
        self.screen.blit(game_over_text, game_over_rect)
        
        # 最终分数
        final_score_text = self.font_medium.render(f"最终分数: {self.score}", True, COLORS['text'])
        final_score_rect = final_score_text.get_rect(center=(game_center_x, SCREEN_HEIGHT//2))
        self.screen.blit(final_score_text, final_score_rect)
        
        # 重新开始提示
        restart_text = self.font_medium.render("按空格键重新开始", True, COLORS['text'])
        restart_rect = restart_text.get_rect(center=(game_center_x, SCREEN_HEIGHT//2 + 80))
        self.screen.blit(restart_text, restart_rect)
        
        # 退出提示
        quit_text = self.font_small.render("按ESC键退出游戏", True, COLORS['text'])
        quit_rect = quit_text.get_rect(center=(game_center_x, SCREEN_HEIGHT//2 + 140))
        self.screen.blit(quit_text, quit_rect)
    
    def run(self):
        """运行游戏主循环"""
        last_time = pygame.time.get_ticks()
        
        while True:
            # 计算时间增量（毫秒）
            current_time = pygame.time.get_ticks()
            delta_time = current_time - last_time
            last_time = current_time
            
            # 处理事件
            self.handle_events()
            
            # 更新游戏状态
            self.update(delta_time)
            
            # 绘制游戏
            self.draw()
            
            # 控制帧率
            self.clock.tick(self.fps)

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    try:
        # 创建游戏实例并运行
        game = SnakeGame()
        game.run()
    except pygame.error as e:
        print(f"Pygame初始化失败: {e}")
        print("请确保已安装pygame: pip install pygame")
    except Exception as e:
        print(f"游戏运行出错: {e}")
    finally:
        pygame.quit()