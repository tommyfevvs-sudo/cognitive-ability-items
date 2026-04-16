import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Circle, Rectangle
from matplotlib import rcParams

def configure_appearance():
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['Proxima Soft', 'Arial Rounded MT Bold', 'Verdana', 'DejaVu Sans']
    rcParams['axes.linewidth'] = 0

class MobileScene:
    def __init__(self, ax):
        self.ax = ax
        self.text_props = {'family': 'sans-serif', 'weight': 'normal'}
        self.col_y, self.col_b, self.col_math, self.col_line = '#fddf85', '#98ccfe', '#1a4b84', '#3c3c3c'
        self.bar_y = 1.0
        # Syncing names: y_t_y for top, y_b_y for bottom
        self.blue_x, self.blue_y = -2.5, 0.0  
        self.y_x, self.y_t_y, self.y_b_y = 2.5, 0.0, -1.0 
        self.setup_canvas()
        self.draw_elements()

    def setup_canvas(self):
        self.ax.set_xlim(-5.0, 9.5)
        self.ax.set_ylim(-2.0, 4.2)
        self.ax.set_aspect('equal')
        self.ax.axis('off')

    def draw_elements(self):
        leg_y = 3.4
        self.ax.add_patch(Circle((-2.5, leg_y), 0.4, fc=self.col_y, ec='black', lw=1.5, zorder=4))
        self.ax.text(-1.9, leg_y, "= 4", va='center', fontsize=35, **self.text_props)
        self.ax.add_patch(Rectangle((0.5, leg_y - 0.4), 0.8, 0.8, fc=self.col_b, ec='black', lw=1.5, zorder=4))
        # Initial "?" text in legend
        self.leg_result_text = self.ax.text(1.6, leg_y, "= ?", va='center', fontsize=35, **self.text_props)

        # Structure
        self.ax.plot([0, 0], [1.0, 1.8], color=self.col_line, lw=3, zorder=1)
        self.ax.plot([-2.5, 2.5], [1.0, 1.0], color=self.col_line, lw=3, zorder=1)
        self.ax.plot([-2.5, -2.5], [1.0, self.blue_y + 0.4], color=self.col_line, lw=2, zorder=1)
        self.ax.plot([2.5, 2.5], [1.0, self.y_b_y], color=self.col_line, lw=2, zorder=1)

        # Shapes
        self.ax.add_patch(Rectangle((self.blue_x - 0.4, self.blue_y - 0.4), 0.8, 0.8, fc=self.col_b, ec='black', lw=1.5, zorder=4))
        self.ax.add_patch(Circle((self.y_x, self.y_t_y), 0.4, fc=self.col_y, ec='black', lw=1.5, zorder=4))
        self.ax.add_patch(Circle((self.y_x, self.y_b_y), 0.4, fc=self.col_y, ec='black', lw=1.5, zorder=4))

def create_animation(save_path):
    configure_appearance()
    fig = plt.figure(figsize=(12, 4.5), facecolor='white')
    ax = fig.add_axes([0, 0, 1, 1]) 
    scene = MobileScene(ax)

    sx, sy = -1.1, 3.4
    fs_main, fs_math = 32, 45
    mx, my = 5.0, 0.0
    lx_8, ly_8 = 2.0, 3.4 # Legend target position

    # Moving Text
    m4_1 = ax.text(sx, sy, "4", fontsize=fs_main, ha='center', va='center', alpha=0, zorder=10)
    m4_2 = ax.text(sx, sy, "4", fontsize=fs_main, ha='center', va='center', alpha=0, zorder=10)
    st1 = ax.text(scene.y_x, scene.y_t_y, "4", fontsize=fs_main, ha='center', va='center', alpha=0, zorder=5)
    st2 = ax.text(scene.y_x, scene.y_b_y, "4", fontsize=fs_main, ha='center', va='center', alpha=0, zorder=5)
    
    math_objs = [
        ax.text(mx, my, "4", color=scene.col_math, fontsize=fs_math, ha='center', va='center', alpha=0),
        ax.text(mx+0.8, my, "+", color=scene.col_math, fontsize=fs_math, ha='center', va='center', alpha=0),
        ax.text(mx+1.6, my, "4", color=scene.col_math, fontsize=fs_math, ha='center', va='center', alpha=0),
        ax.text(mx+2.6, my, "=", color=scene.col_math, fontsize=fs_math, ha='center', va='center', alpha=0),
        ax.text(mx+3.6, my, "8", color=scene.col_math, fontsize=50, ha='center', va='center', weight='bold', alpha=0)
    ]
    m8_mobile = ax.text(mx+3.6, my, "8", fontsize=fs_math, ha='center', va='center', weight='bold', alpha=0, zorder=10)
    m8_legend = ax.text(scene.blue_x, scene.blue_y, "8", fontsize=fs_main, ha='center', va='center', alpha=0, zorder=10)

    def update(frame):
        def ease(t): return t*t*(3-2*t)

        if frame == 0:
            scene.leg_result_text.set_text("= ?")
            for obj in [m4_1, m4_2, st1, st2, m8_mobile, m8_legend] + math_objs: obj.set_alpha(0)

        # 1. Start -> Circles
        if 0 <= frame < 50:
            t = ease(frame / 50)
            m4_1.set_alpha(1); m4_1.set_position((sx + (scene.y_x - sx)*t, sy + (scene.y_t_y - sy)*t))
            if frame > 15:
                t2 = ease((frame - 15) / 35)
                m4_2.set_alpha(1); m4_2.set_position((sx + (scene.y_x - sx)*t2, sy + (scene.y_b_y - sy)*t2))

        # 2. Pause
        if frame >= 50:
            st1.set_alpha(1); st2.set_alpha(1)
            m4_1.set_position((scene.y_x, scene.y_t_y))
            m4_2.set_position((scene.y_x, scene.y_b_y))

        # 3. Circles -> Math (Continuous Scaling handover)
        if 90 <= frame < 140:
            t = ease((frame - 90) / 50)
            curr_fs = fs_main + (fs_math - fs_main) * t
            m4_1.set_alpha(1); m4_1.set_fontsize(curr_fs)
            m4_1.set_position((scene.y_x + (mx - scene.y_x)*t, scene.y_t_y + (my - scene.y_t_y)*t))
            m4_2.set_alpha(1); m4_2.set_fontsize(curr_fs)
            m4_2.set_position((scene.y_x + ((mx+1.6) - scene.y_x)*t, scene.y_b_y + (my - scene.y_b_y)*t))

        # 4. Math display
        if 140 <= frame < 180:
            m4_1.set_alpha(0); m4_2.set_alpha(0)
            math_objs[0].set_alpha(1); math_objs[2].set_alpha(1)
            if frame > 150: math_objs[1].set_alpha(1)
            if frame > 160: math_objs[3].set_alpha(1)
            if frame > 170: math_objs[4].set_alpha(1)

        # 5. Move 8 to Blue Square (Shrinking back)
        if 180 <= frame < 220:
            t = ease((frame - 180) / 40)
            curr_fs = 45 - (45 - 32) * t
            m8_mobile.set_alpha(1); m8_mobile.set_fontsize(curr_fs)
            m8_mobile.set_weight('normal' if t > 0.8 else 'bold')
            m8_mobile.set_position((mx+3.6 + (scene.blue_x - (mx+3.6))*t, my + (scene.blue_y - my)*t))

        # 6. Duplicate 8 moves to Legend
        if 220 <= frame < 260:
            t = ease((frame - 220) / 40)
            m8_mobile.set_position((scene.blue_x, scene.blue_y))
            m8_legend.set_alpha(1)
            m8_legend.set_position((scene.blue_x + (lx_8 - scene.blue_x)*t, scene.blue_y + (ly_8 - scene.blue_y)*t))
            if t > 0.9: 
                scene.leg_result_text.set_text("= 8")
                m8_legend.set_alpha(0)

        # 7. Final Fade Out
        if frame >= 270:
            alpha = 1 - ((frame - 270) / 30)
            for obj in [st1, st2, m8_mobile] + math_objs: obj.set_alpha(alpha)
            if alpha < 0.2: scene.leg_result_text.set_text("= ?")

        return [m4_1, m4_2, st1, st2, m8_mobile, m8_legend, scene.leg_result_text] + math_objs

    ani = animation.FuncAnimation(fig, update, frames=300, interval=33, blit=True)
    ani.save(save_path, writer='pillow', fps=30)
    plt.close()

if __name__ == "__main__":
    path = os.path.join(os.path.expanduser("~"), "Desktop", "mobile_tutorial_smooth_v2.gif")
    create_animation(path)
    print("Animation saved to Desktop.")
