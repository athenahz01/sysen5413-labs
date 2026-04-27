"""Graph GUI object encapsulating UniHiker display and scatter plot."""

from datetime import datetime


class GraphGUI:
    """Encapsulates all GUI elements and plot logic for the light monitor display."""

    def __init__(
        self,
        gui,
        n_points=30,
        screen_width=240,
        screen_height=320,
        plot_x=20,
        plot_y=55,
        plot_w=200,
        plot_h=220,
    ):
        self._gui = gui
        self._n_points = n_points
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._plot_x = plot_x
        self._plot_y = plot_y
        self._plot_w = plot_w
        self._plot_h = plot_h
        self._point_objects = []

        # Title and status labels
        self._title_label = gui.draw_text(
            x=screen_width // 2,
            y=10,
            text="Light Monitor",
            origin="top",
        )
        self._status_label = gui.draw_text(
            x=screen_width // 2,
            y=30,
            text="Initializing...",
            origin="top",
        )
        self._value_label = gui.draw_text(
            x=10,
            y=screen_height - 25,
            text="Light: --",
            origin="top_left",
        )
        self._info_label = gui.draw_text(
            x=screen_width - 10,
            y=screen_height - 45,
            text=f"N={n_points}",
            origin="top_right",
        )

        # Plot background and axes
        gui.fill_rect(
            x=plot_x,
            y=plot_y,
            w=plot_w,
            h=plot_h,
            color="#1a1a2e",
        )
        gui.draw_line(
            x0=plot_x,
            y0=plot_y,
            x1=plot_x,
            y1=plot_y + plot_h,
            width=1,
            color="#ffffff",
        )
        gui.draw_line(
            x0=plot_x,
            y0=plot_y + plot_h,
            x1=plot_x + plot_w,
            y1=plot_y + plot_h,
            width=1,
            color="#ffffff",
        )
        self._y_min_label = gui.draw_text(
            x=plot_x + 4,
            y=plot_y + plot_h,
            text="0",
            color="#ffffff",
            origin="bottom_left",
        )
        self._y_max_label = gui.draw_text(
            x=plot_x + 4,
            y=plot_y,
            text="4095",
            color="#ffffff",
            origin="top_left",
        )

    def set_status(self, text):
        """Update the status label text."""
        if self._status_label is not None:
            self._status_label.config(text=text)

    def set_value(self, text):
        """Update the current value label text."""
        if self._value_label is not None:
            self._value_label.config(text=text)

    def _clear_points(self):
        """Remove existing point objects from the plot."""
        for obj in self._point_objects:
            try:
                self._gui.remove(obj)
            except Exception:
                pass
        self._point_objects = []

    def _scale_points_to_plot(self, points):
        """Scale (time, value) points to (x, y) coordinates in the plot area."""
        if not points:
            return []

        values = [v for _, v in points]
        min_val = min(values)
        max_val = max(values)

        if min_val == max_val:
            min_val = max(0, min_val - 1)
            max_val = min(4095, max_val + 1)

        y_bottom = self._plot_y + self._plot_h - 5
        y_top = self._plot_y + 5

        def value_to_y(v):
            ratio = (v - min_val) / float(max_val - min_val)
            return y_bottom - ratio * (y_bottom - y_top)

        x_left = self._plot_x + 5
        x_right = self._plot_x + self._plot_w - 5
        n = len(points)

        coords = []
        if n == 1:
            x = (x_left + x_right) / 2.0
            y = value_to_y(values[0])
            coords.append((x, y))
        else:
            step = (x_right - x_left) / float(n - 1)
            for idx, (_, v) in enumerate(points):
                x = x_left + idx * step
                y = value_to_y(v)
                coords.append((x, y))

        try:
            self._y_min_label.config(text=str(int(min_val)))
            self._y_max_label.config(text=str(int(max_val)))
        except Exception:
            pass

        return coords

    def redraw_scatter(self, points):
        """Redraw the scatter plot using the given points."""
        self._clear_points()

        if not points:
            try:
                self._info_label.config(text=f"N={self._n_points} (no data)")
            except Exception:
                pass
            return

        coords = self._scale_points_to_plot(points)
        for x, y in coords:
            obj = self._gui.fill_circle(
                x=int(x),
                y=int(y),
                r=3,
                color="#e94560",
            )
            self._point_objects.append(obj)

        last_ts = points[-1][0]
        if isinstance(last_ts, datetime):
            ts_str = last_ts.strftime("%H:%M:%S")
        else:
            ts_str = str(last_ts)
        try:
            self._info_label.config(text=f"N={len(points)} last@{ts_str}")
        except Exception:
            pass