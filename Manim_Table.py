from manim import *

class ManimTable(Scene):
    def construct(self):
        background = Rectangle(height = 6.5, width = 13)
        background.set_fill(opacity = 0.5)
        background.set_color = ([TEAL, RED, YELLOW])
        self.add(background)
        t0 = Table(
                [
                    ["This", "Is a"],
                    ["Manim", "Table"],

                ]
        )
        t1 = Table(
            [
                ["This", "Is a"],
                ["Manim", "Table"],
            ],
            row_labels = [Text("R1"), Text("R2")],
            col_labels = [Text("C1"), Text("C1")],
            )
        t1.add_highlighted_cell((2,2), color = YELLOW)


        t2 = Table(
            [
                ["This", "Is a"],
                ["Manim", "Table"],
            ],
            row_labels = [Text("R1"), Text("R2")],
            col_labels = [Text("C1"), Text("C2")],
            top_left_entry = Star().scale(0.3),
            include_outer_lines = True,
            arrange_in_grid_config = {"cell_alignment": RIGHT},
            include_background_rectangle = True,
            )
        t2.add(t2.get_cell((2,2), color = RED))

        t3 = Table(
            [
                ["This", "Is a"],
                ["Manim", "Table"],
            ],
            row_labels = [Text("R1"), Text("R2")],
            col_labels = [Text("C1"), Text("C2")],
            top_left_entry = Star().scale(0.3),
            include_outer_lines = True,
            arrange_in_grid_config = {"cell alignment": RIGHT},
            line_config = {"stroke_width": 1, "color": YELLOW},
            include_background_rectangle = True,

        )
        t3.remove(*t3.get_vertical_lines())

        g = Group(
            t0,t1,t2,t3
        ).scale(0.7).arrange_in_grid(buff = 1)

        self.add(g)
class MathTable1(Scene):
    def construct(self):
        t0 = MathTable(
                [["+", 0, 5, 10],
                [0, 0, 5, 10],
                [2, 2, 7, 12],
                [4, 4, 9, 14]],
                include_outer_lines = True
        )

        self.add(t0)
