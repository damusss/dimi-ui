import os
import sys

os.environ["SDL_WINDOWS_DPI_AWARENESS"] = "permonitorv2"


import dimi
import pygame
import sys
from pygame._render import Renderer, Texture

pygame.init()

REN = True

win = pygame.Window("Dimi Test", (1000, 800), resizable=True, allow_high_dpi=False)
if REN:
    scr = Renderer(win, accelerated=True, index=1)
else:
    scr = win.get_surface()

clock = pygame.Clock()

ctx = dimi.Context(win, scr)

img = pygame.transform.scale_by(
    pygame.image.load(r"C:\Users\ricci\Desktop\Ginger_european_cat.jpg"), 1
)
img = pygame.image.load(
    r"C:\Users\ricci\Desktop\Hexany's 1-bit UI Panels\Panels\Transparent\bone_breakers.png"
)


if REN:
    tex = Texture(scr, img.size, 32, scale_quality=0)
    tex.update(img)
    tex.blend_mode = pygame.BLENDMODE_BLEND
    img = tex
an = 0
print(dimi.typehinting.RectStyleOverrides)
dt = 0
xx = 0
while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            sys.exit()

    if not REN:
        scr.fill("black")
    else:
        scr.draw_color = "black"
        scr.clear()
    an += 30 * dt
    xx += 500 * dt
    # todo DOUBLE CLICKS!! and more than double
    # print("S")
    with dimi.using(ctx), dimi.push_style.text(font=dimi.Font("Segoe UI", True)):
        dimi.rect(color="black")
        if False:
            with dimi.begin(
                padding=0,
                axis=dimi.Axis.X,
                height=dimi.Hug(),
                width=dimi.Fill(),
                align_children=dimi.Align.CENTER,
            ):
                with dimi.element(
                    width=dimi.Percent(50),
                    height=dimi.Hug(),
                    align_self=dimi.Align.CENTER,
                ) as i:
                    dimi.rect(color="gray10")
                    dimi.text(
                        "This is a test and it should be able to wrap\nand be forced here too",
                        size=30,
                        align=dimi.FontAlign.LEFT,
                        anchor=dimi.Anchor.MIDRIGHT,
                        color="white",
                        wrap=True,
                    )
                    dimi.text(
                        "smol lil fucker ain't he",
                        size=20,
                        anchor=dimi.Anchor.BOTTOMRIGHT,
                        color="red",
                    )
                    # print(i.data.absolute_rect)
        with (
            dimi.begin(width="70%", height=dimi.Hug(), axis=dimi.Axis.X),
            dimi.push_id(ctx),
        ):
            dimi.rect(color="gray40")
            for i in range(7):
                with dimi.element(width=100, height=100):
                    dimi.rect(color="red")
        with dimi.element(
            width=dimi.Fill(0.5), height=300, align_self=dimi.Align.CENTER
        ) as u:
            dimi.rect(color="gray20" if u.hovered else "gray10")
            if False:
                dimi.image(
                    img,
                    fit=dimi.ImageFit.NINE_PATCH(28),
                    shape=True,
                    border_radius=1,
                    padding=("15%", "17%"),
                    scale_quality=dimi.ScaleQuality.NEAREST,
                    # repeat=dimi.ImageRepeat.BOTH,
                    # transform=dimi.Transform(angle_deg=15, angle_origin=(0, 0)),
                    color_modifier="red",
                )
            dimi.image(
                img,
                fit=dimi.ImageFit.NINE_PATCH(28),
                shape=True,
                # border_radius=1,
                padding=("40%", "40%"),
                scale_quality=dimi.ScaleQuality.NEAREST,
                repeat=dimi.ImageRepeat.BOTH,
                transform=dimi.Transform(angle_deg=an),
            )
        # dimi.element(width=dimi.Fill(), height=100).rect(color="yellow")
        if False:
            with dimi.element(
                width=300,
                height=300,
                position=dimi.Absolute(center_x="50%", center_y="50%"),
            ) as i:
                dimi.rect(color="green")
                if i.button_status == dimi.ButtonStatus.HELD:
                    print(123)
                dimi.rect(color="blue", border_width=5)
        ctx = dimi.get_current_context()
        with dimi.begin(width=dimi.Fill(1), height=dimi.Fill(1), axis=dimi.Axis.X) as a:
            dimi.rect(color="blue")
            with dimi.element(width=dimi.Fill(70), height=dimi.Fill(1)) as b:
                dimi.rect(
                    color=dimi.when(b, "dark green", "green", "light blue"),
                    border_radius="50%",
                    aspect_ratio=1,
                    shape=True,
                )
            with dimi.element(width=dimi.Fill(100), height=dimi.Fill(1)) as k:
                dimi.ellipse(
                    color=dimi.when(k, "dark green", "green", "dark blue"),
                    shape=True,
                    antialias=True,
                    aspect_ratio=1,
                )
        with dimi.begin(
            width=dimi.Fill(), height=dimi.Fill(), align_children=dimi.Align.CENTER
        ):
            dimi.rect(color="gray10")
            with dimi.begin(
                width=dimi.Percent(40), height=50, align_self=dimi.Align.CENTER
            ):
                dimi.rect(color="black")
                with dimi.widget.entry_line() as state:
                    ...

    win.title = f"{clock.get_fps():.0f}"

    if REN:
        scr.present()
    else:
        win.flip()
    dt = clock.tick_busy_loop(120)/1000
