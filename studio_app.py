"""Tkinter desktop control panel for Photo Border Watermark Studio."""

from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
from typing import Callable, List

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from photo_processor import (
    RenderOptions,
    SUPPORTED_EXTENSIONS,
    format_exif_params,
    get_exif_data,
    output_path_for,
    render_image,
    render_preview,
)


APP_TITLE = "Photo Border Watermark Studio"
BG = "#0b0f14"
PANEL = "#121722"
PANEL_2 = "#18202d"
PANEL_3 = "#202a3a"
TEXT = "#f4f1ea"
MUTED = "#a4adba"
ACCENT = "#2dd4bf"
ACCENT_BLUE = "#38bdf8"
ACCENT_DARK = "#0f766e"
ACCENT_PURPLE = "#8b5cf6"
WARN = "#f59e0b"
EDGE = "#263241"
EDGE_ACTIVE = "#3ddbd2"
INPUT_BG = "#0d1118"


class PhotoBorderStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(1040, 680)
        self.configure(bg=BG)

        self.files: List[Path] = []
        self.preview_index = 0
        self.preview_photo = None
        self.preview_after_id = None
        self.worker_queue: queue.Queue = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.style_buttons: dict[str, tk.Button] = {}

        self.style_var = tk.StringVar(value="blur")
        self.output_dir_var = tk.StringVar(value=str(Path.cwd() / "output"))
        self.border_var = tk.DoubleVar(value=10.0)
        self.corner_var = tk.IntVar(value=34)
        self.shadow_var = tk.IntVar(value=10)
        self.shadow_blur_var = tk.IntVar(value=22)
        self.shadow_opacity_var = tk.IntVar(value=110)
        self.blur_radius_var = tk.IntVar(value=40)
        self.font_scale_var = tk.DoubleVar(value=32.0)
        self.text_spacing_var = tk.IntVar(value=14)
        self.caption_backdrop_var = tk.IntVar(value=0)
        self.text_shadow_var = tk.IntVar(value=150)
        self.quality_var = tk.IntVar(value=95)
        self.include_brand_var = tk.BooleanVar(value=True)
        self.include_model_var = tk.BooleanVar(value=True)
        self.include_params_var = tk.BooleanVar(value=True)
        self.include_lens_var = tk.BooleanVar(value=False)
        self.include_datetime_var = tk.BooleanVar(value=False)
        self.include_custom_title_var = tk.BooleanVar(value=True)
        self.include_custom_subtitle_var = tk.BooleanVar(value=True)
        self.title_var = tk.StringVar(value="")
        self.subtitle_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="准备就绪")
        self.count_var = tk.StringVar(value="0 张照片")

        self._configure_styles()
        self._build_layout()
        self._load_initial_images()
        self.after(120, self._poll_worker_queue)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Card.TFrame", background=PANEL_2)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("Muted.TLabel", foreground=MUTED, background=PANEL, font=("Microsoft YaHei UI", 9))
        style.configure("Title.TLabel", foreground=TEXT, background=BG, font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("CardTitle.TLabel", foreground=TEXT, background=PANEL, font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"), padding=(12, 8))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(10, 7))
        style.configure("TRadiobutton", background=PANEL, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("TCheckbutton", background=PANEL_2, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.map(
            "TCheckbutton",
            background=[("active", PANEL_2), ("selected", PANEL_2)],
            foreground=[("active", ACCENT)],
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=INPUT_BG,
            background=ACCENT,
            bordercolor=EDGE,
            lightcolor=ACCENT,
            darkcolor=ACCENT_DARK,
        )

    def _build_layout(self) -> None:
        root = ttk.Frame(self, style="TFrame")
        root.pack(fill="both", expand=True, padx=18, pady=16)

        header = ttk.Frame(root, style="TFrame")
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="Photo Border Watermark Studio", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.count_var, foreground=ACCENT, background=BG).pack(side="left", padx=16)
        ttk.Label(header, textvariable=self.status_var, foreground=WARN, background=BG).pack(side="right")

        body = ttk.Frame(root, style="TFrame")
        body.pack(fill="both", expand=True)

        self.controls = tk.Frame(body, bg=PANEL, width=392, highlightthickness=1, highlightbackground=EDGE)
        self.controls.pack(side="left", fill="y", padx=(0, 14))
        self.controls.pack_propagate(False)

        right = ttk.Frame(body, style="TFrame")
        right.pack(side="left", fill="both", expand=True)

        self.preview_frame = tk.Frame(right, bg="#070a0f", highlightthickness=1, highlightbackground=EDGE)
        self.preview_frame.pack(fill="both", expand=True)
        self.preview_label = tk.Label(self.preview_frame, bg="#070a0f", fg=MUTED, text="选择照片后这里显示预览")
        self.preview_label.pack(fill="both", expand=True, padx=10, pady=10)
        self.preview_frame.bind("<Configure>", lambda _event: self._schedule_preview())

        bottom = ttk.Frame(right, style="TFrame")
        bottom.pack(fill="x", pady=(12, 0))
        self.meta_label = tk.Label(
            bottom,
            text="EXIF 信息会显示在这里",
            bg=PANEL_2,
            fg=MUTED,
            anchor="w",
            justify="left",
            padx=12,
            pady=10,
            font=("Microsoft YaHei UI", 9),
        )
        self.meta_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        status_panel = tk.Frame(bottom, bg="#0b111a", highlightthickness=1, highlightbackground=EDGE)
        status_panel.pack(side="right", fill="both")
        status_header = tk.Frame(status_panel, bg="#0b111a")
        status_header.pack(fill="x", padx=10, pady=(7, 2))
        tk.Frame(status_header, bg=ACCENT, width=3, height=12).pack(side="left", pady=2)
        tk.Label(
            status_header,
            text="STATUS",
            bg="#0b111a",
            fg=ACCENT,
            font=("Consolas", 8, "bold"),
            padx=7,
        ).pack(side="left")
        tk.Label(
            status_header,
            textvariable=self.status_var,
            bg="#0b111a",
            fg=MUTED,
            anchor="e",
            font=("Microsoft YaHei UI", 8),
        ).pack(side="right", fill="x", expand=True)
        self.log = tk.Text(
            status_panel,
            width=34,
            height=2,
            bg="#070a0f",
            fg=MUTED,
            insertbackground=TEXT,
            relief="flat",
            wrap="word",
            font=("Consolas", 8),
            state="disabled",
        )
        self.log.pack(fill="x", padx=10)
        self.progress = ttk.Progressbar(status_panel, mode="determinate", style="Horizontal.TProgressbar", length=180)
        self.progress.pack(fill="x", padx=10, pady=(6, 8))

        self._build_controls()

    def _build_controls(self) -> None:
        actions = tk.Frame(self.controls, bg=PANEL)
        actions.pack(fill="x", side="bottom", padx=16, pady=16)
        self._button(actions, "打开输出目录", self._open_output_dir).pack(fill="x", pady=(0, 8))
        self.process_button = self._button(actions, "开始处理", self._start_processing, primary=True)
        self.process_button.pack(fill="x")

        self.controls_canvas = tk.Canvas(
            self.controls,
            bg=PANEL,
            highlightthickness=0,
            borderwidth=0,
        )
        self.controls_canvas.pack(side="left", fill="both", expand=True)
        controls_scroll = ttk.Scrollbar(self.controls, orient="vertical", command=self.controls_canvas.yview)
        controls_scroll.pack(side="right", fill="y")
        self.controls_canvas.configure(yscrollcommand=controls_scroll.set)
        self.controls_body = tk.Frame(self.controls_canvas, bg=PANEL)
        self.controls_window = self.controls_canvas.create_window((0, 0), window=self.controls_body, anchor="nw")
        self.controls_body.bind(
            "<Configure>",
            lambda _event: self.controls_canvas.configure(scrollregion=self.controls_canvas.bbox("all")),
        )
        self.controls_canvas.bind(
            "<Configure>",
            lambda event: self.controls_canvas.itemconfigure(self.controls_window, width=event.width),
        )
        self.controls_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.controls_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.controls_canvas.bind_all("<Button-5>", self._on_mousewheel)

        self._section_title("照片")
        file_row = tk.Frame(self.controls_body, bg=PANEL)
        file_row.pack(fill="x", padx=16, pady=(4, 8))
        self._button(file_row, "选择照片", self._choose_files, primary=True).pack(side="left", fill="x", expand=True)
        self._button(file_row, "添加文件夹", self._choose_folder).pack(side="left", padx=(8, 0))

        list_box_frame = tk.Frame(self.controls_body, bg=PANEL)
        list_box_frame.pack(fill="both", padx=16, pady=(0, 12))
        self.file_list = tk.Listbox(
            list_box_frame,
            height=4,
            bg=INPUT_BG,
            fg=TEXT,
            selectbackground=ACCENT_DARK,
            selectforeground="#ffffff",
            highlightthickness=0,
            borderwidth=0,
            activestyle="none",
            font=("Microsoft YaHei UI", 9),
        )
        self.file_list.pack(side="left", fill="both", expand=True)
        self.file_list.bind("<<ListboxSelect>>", self._on_select_file)
        scroll = ttk.Scrollbar(list_box_frame, command=self.file_list.yview)
        scroll.pack(side="right", fill="y")
        self.file_list.config(yscrollcommand=scroll.set)

        self._section_title("输出")
        output_row = tk.Frame(self.controls_body, bg=PANEL)
        output_row.pack(fill="x", padx=16, pady=(0, 10))
        output_entry = tk.Entry(
            output_row,
            textvariable=self.output_dir_var,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 9),
        )
        output_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self._button(output_row, "浏览", self._choose_output, width=7).pack(side="left", padx=(8, 0))

        self._section_title("样式")
        style_row = tk.Frame(self.controls_body, bg=PANEL)
        style_row.pack(fill="x", padx=16, pady=(0, 8))
        self._style_segment(style_row, "blur", "虚化边框").pack(side="left", fill="x", expand=True)
        self._style_segment(style_row, "white", "白色底框").pack(side="left", fill="x", expand=True, padx=(8, 0))
        self._refresh_style_selector()

        appearance = self._collapsible_section("外观参数", expanded=False)
        self._slider("边框比例", self.border_var, 4, 22, " %", parent=appearance)
        self._slider("圆角弧度", self.corner_var, 0, 180, " px", parent=appearance)
        self._slider("背景虚化", self.blur_radius_var, 0, 120, " px", parent=appearance)
        self._slider("阴影偏移", self.shadow_var, 0, 50, " px", parent=appearance)
        self._slider("阴影模糊", self.shadow_blur_var, 0, 80, " px", parent=appearance)
        self._slider("阴影深度", self.shadow_opacity_var, 0, 240, "", parent=appearance)
        self._slider("底部底纹", self.caption_backdrop_var, 0, 160, "", parent=appearance)
        self._slider("文字阴影", self.text_shadow_var, 0, 240, "", parent=appearance)
        self._slider("字体比例", self.font_scale_var, 18, 56, " %", parent=appearance)
        self._slider("文字行距", self.text_spacing_var, 0, 34, " px", parent=appearance)
        self._slider("JPG 质量", self.quality_var, 70, 100, "", parent=appearance)

        watermark = self._collapsible_section("水印内容", expanded=False)
        self._checkbox_grid(
            watermark,
            [
                ("品牌", self.include_brand_var),
                ("机型", self.include_model_var),
                ("参数", self.include_params_var),
                ("镜头", self.include_lens_var),
                ("拍摄时间", self.include_datetime_var),
                ("自定义标题", self.include_custom_title_var),
                ("自定义副标题", self.include_custom_subtitle_var),
            ],
        )
        self._entry("自定义标题", self.title_var, parent=watermark)
        self._entry("自定义副标题", self.subtitle_var, parent=watermark)
        self._log("控制台已启动。")

    def _section_title(self, text: str) -> None:
        row = tk.Frame(self.controls_body, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(14, 7))
        tk.Frame(row, bg=ACCENT_PURPLE, width=3, height=14).pack(side="left", pady=2)
        tk.Label(
            row,
            text=text,
            bg=PANEL,
            fg=ACCENT,
            anchor="w",
            font=("Microsoft YaHei UI", 10, "bold"),
            padx=8,
        ).pack(side="left", fill="x", expand=True)

    def _style_segment(self, parent: tk.Widget, value: str, label: str) -> tk.Button:
        button = tk.Button(
            parent,
            text=label,
            command=lambda: self._set_style(value),
            bg=PANEL_2,
            fg=MUTED,
            activebackground=PANEL_3,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
            highlightthickness=1,
            highlightbackground=EDGE,
            padx=12,
            pady=10,
        )
        button.bind("<Enter>", lambda _event: self._hover_style_segment(value, True))
        button.bind("<Leave>", lambda _event: self._hover_style_segment(value, False))
        self.style_buttons[value] = button
        return button

    def _set_style(self, value: str) -> None:
        self.style_var.set(value)
        self._refresh_style_selector()
        self._schedule_preview()

    def _hover_style_segment(self, value: str, hovering: bool) -> None:
        button = self.style_buttons.get(value)
        if not button or self.style_var.get() == value:
            return
        button.configure(
            bg=PANEL_3 if hovering else PANEL_2,
            fg=TEXT if hovering else MUTED,
            highlightbackground=ACCENT_BLUE if hovering else EDGE,
        )

    def _refresh_style_selector(self) -> None:
        for value, button in self.style_buttons.items():
            selected = self.style_var.get() == value
            button.configure(
                bg=ACCENT_DARK if selected else PANEL_2,
                fg="#ffffff" if selected else MUTED,
                activebackground=ACCENT if selected else PANEL_3,
                highlightbackground=ACCENT if selected else EDGE,
            )

    def _collapsible_section(self, title: str, expanded: bool = True) -> tk.Frame:
        outer = tk.Frame(self.controls_body, bg=PANEL)
        outer.pack(fill="x", padx=12, pady=(8, 0))
        shell = tk.Frame(outer, bg=PANEL_2, highlightthickness=1, highlightbackground=EDGE)
        shell.pack(fill="x")

        header = tk.Frame(shell, bg=PANEL_2, cursor="hand2")
        header.pack(fill="x")
        rail = tk.Frame(header, bg=EDGE, width=3)
        rail.pack(side="left", fill="y", pady=8)
        arrow = tk.Label(
            header,
            text="▸",
            bg=PANEL_2,
            fg=ACCENT,
            width=2,
            font=("Microsoft YaHei UI", 12, "bold"),
            cursor="hand2",
        )
        arrow.pack(side="left", padx=(8, 2), pady=10)
        title_label = tk.Label(
            header,
            text=title,
            bg=PANEL_2,
            fg=TEXT,
            anchor="w",
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="hand2",
        )
        title_label.pack(side="left", fill="x", expand=True, pady=10)
        state_label = tk.Label(
            header,
            text="READY",
            bg=PANEL_2,
            fg=MUTED,
            font=("Consolas", 8, "bold"),
            cursor="hand2",
            padx=12,
        )
        state_label.pack(side="right", pady=10)

        content_holder = tk.Frame(shell, bg=PANEL_2, height=0)
        content_holder.pack(fill="x")
        content_holder.pack_propagate(False)
        content = tk.Frame(content_holder, bg=PANEL_2)
        content.pack(fill="x", expand=True)

        state = {
            "expanded": expanded,
            "hover": False,
            "height": 0,
            "after_id": None,
        }

        def refresh_visual() -> None:
            is_open = bool(state["expanded"])
            is_hover = bool(state["hover"])
            panel_bg = PANEL_3 if is_open or is_hover else PANEL_2
            edge_color = EDGE_ACTIVE if is_open else (ACCENT_BLUE if is_hover else EDGE)
            rail_color = ACCENT if is_open else (ACCENT_BLUE if is_hover else EDGE)
            shell.configure(bg=panel_bg, highlightbackground=edge_color)
            header.configure(bg=panel_bg)
            arrow.configure(text="▾" if is_open else "▸", bg=panel_bg, fg=ACCENT if is_open else MUTED)
            title_label.configure(bg=panel_bg, fg="#ffffff" if is_open else TEXT)
            state_label.configure(
                text="ACTIVE" if is_open else "READY",
                bg=panel_bg,
                fg=ACCENT if is_open else MUTED,
            )
            rail.configure(bg=rail_color)

        def target_height() -> int:
            content.update_idletasks()
            return max(1, content.winfo_reqheight())

        def sync_scroll_region() -> None:
            self.controls_canvas.configure(scrollregion=self.controls_canvas.bbox("all"))

        def animate_height(target: int) -> None:
            if state["after_id"]:
                self.after_cancel(state["after_id"])
                state["after_id"] = None
            start = int(state["height"])
            frames = 12

            def step(index: int) -> None:
                progress = index / frames
                eased = 1 - pow(1 - progress, 3)
                height = int(start + (target - start) * eased)
                state["height"] = height
                content_holder.configure(height=height)
                sync_scroll_region()
                if index < frames:
                    state["after_id"] = self.after(14, lambda: step(index + 1))
                    return
                state["height"] = target
                state["after_id"] = None
                content_holder.configure(height=target)
                sync_scroll_region()

            step(1)

        def toggle(_event: tk.Event | None = None) -> None:
            state["expanded"] = not bool(state["expanded"])
            refresh_visual()
            animate_height(target_height() if state["expanded"] else 0)

        def set_hover(hovering: bool) -> None:
            state["hover"] = hovering
            refresh_visual()

        for widget in (header, rail, arrow, title_label, state_label):
            widget.bind("<Button-1>", toggle)
            widget.bind("<Enter>", lambda _event: set_hover(True))
            widget.bind("<Leave>", lambda _event: set_hover(False))

        def sync_initial_height() -> None:
            height = target_height() if state["expanded"] else 0
            state["height"] = height
            content_holder.configure(height=height)
            refresh_visual()
            sync_scroll_region()

        self.after_idle(sync_initial_height)
        return content

    def _checkbox_grid(self, parent: tk.Widget, items: list[tuple[str, tk.BooleanVar]]) -> None:
        bg = self._surface_bg(parent)
        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill="x", padx=16, pady=(2, 8))
        for index, (label, variable) in enumerate(items):
            row = index // 2
            column = index % 2
            check = ttk.Checkbutton(
                frame,
                text=label,
                variable=variable,
                command=self._schedule_preview,
            )
            check.grid(row=row, column=column, sticky="w", padx=(0, 18), pady=3)

    def _surface_bg(self, parent: tk.Widget | None = None) -> str:
        if parent is None:
            return PANEL
        try:
            return str(parent.cget("bg"))
        except tk.TclError:
            return PANEL

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        primary: bool = False,
        width: int | None = None,
    ) -> tk.Button:
        bg = ACCENT_DARK if primary else PANEL_3
        active_bg = ACCENT if primary else "#39404d"
        fg = "#ffffff" if primary else TEXT
        button = tk.Button(
            parent,
            text=text,
            command=command,
            width=width or 0,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold" if primary else "normal"),
            padx=12,
            pady=9,
            highlightthickness=1,
            highlightbackground=ACCENT_DARK if primary else EDGE,
        )
        button.bind("<Enter>", lambda _event: button.configure(highlightbackground=ACCENT_BLUE))
        button.bind(
            "<Leave>",
            lambda _event: button.configure(highlightbackground=ACCENT_DARK if primary else EDGE),
        )
        return button

    def _slider(
        self,
        title: str,
        var: tk.Variable,
        from_: int,
        to: int,
        suffix: str,
        parent: tk.Widget | None = None,
    ) -> None:
        container = parent or self.controls_body
        bg = self._surface_bg(container)
        frame = tk.Frame(container, bg=bg)
        frame.pack(fill="x", padx=16, pady=(2, 6))
        top = tk.Frame(frame, bg=bg)
        top.pack(fill="x")
        value_label = tk.Label(top, bg=bg, fg=ACCENT_BLUE, font=("Consolas", 9, "bold"))
        tk.Label(top, text=title, bg=bg, fg=TEXT, font=("Microsoft YaHei UI", 9)).pack(side="left")
        value_label.pack(side="right")

        def update_label(_value: str | None = None) -> None:
            current = var.get()
            if isinstance(current, float):
                shown = f"{current:.0f}{suffix}"
            else:
                shown = f"{current}{suffix}"
            value_label.config(text=shown)
            self._schedule_preview()

        scale = tk.Scale(
            frame,
            variable=var,
            from_=from_,
            to=to,
            orient="horizontal",
            resolution=1,
            command=update_label,
            bg=bg,
            fg=TEXT,
            troughcolor=INPUT_BG,
            activebackground=ACCENT,
            highlightthickness=0,
            showvalue=False,
        )
        scale.pack(fill="x")
        update_label()

    def _entry(self, title: str, var: tk.StringVar, parent: tk.Widget | None = None) -> None:
        container = parent or self.controls_body
        bg = self._surface_bg(container)
        frame = tk.Frame(container, bg=bg)
        frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(frame, text=title, bg=bg, fg=MUTED, anchor="w", font=("Microsoft YaHei UI", 9)).pack(fill="x")
        entry = tk.Entry(
            frame,
            textvariable=var,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Microsoft YaHei UI", 9),
        )
        entry.pack(fill="x", ipady=7)
        entry.bind("<KeyRelease>", lambda _event: self._schedule_preview())

    def _is_descendant_of(self, widget: tk.Misc, parent: tk.Misc) -> bool:
        current: tk.Misc | None = widget
        while current is not None:
            if current == parent:
                return True
            current = current.master
        return False

    def _wheel_units(self, event: tk.Event) -> int:
        if getattr(event, "num", None) == 4:
            return -3
        if getattr(event, "num", None) == 5:
            return 3
        delta = getattr(event, "delta", 0)
        if not delta:
            return 0
        units = int(-delta / 120)
        if units == 0:
            return -1 if delta > 0 else 1
        return units

    def _can_scroll_widget(self, widget: tk.Widget, units: int) -> bool:
        try:
            first, last = widget.yview()
        except tk.TclError:
            return False
        if units < 0:
            return first > 0
        if units > 0:
            return last < 1
        return False

    def _on_mousewheel(self, event: tk.Event) -> str | None:
        widget = event.widget
        if not self._is_descendant_of(widget, self.controls):
            return None

        units = self._wheel_units(event)
        if units == 0:
            return "break"

        for inner_scroll in (self.file_list, self.log):
            if self._is_descendant_of(widget, inner_scroll) and self._can_scroll_widget(inner_scroll, units):
                return None

        self.controls_canvas.yview_scroll(units, "units")
        return "break"

    def _load_initial_images(self) -> None:
        root_images = [
            path
            for path in sorted(Path.cwd().iterdir())
            if path.suffix.lower() in SUPPORTED_EXTENSIONS and path.parent.name.lower() != "output"
        ]
        if root_images:
            self._set_files(root_images)
            self._log(f"已自动载入当前目录的 {len(root_images)} 张照片。")
            self.after_idle(self._update_preview)

    def _choose_files(self) -> None:
        names = filedialog.askopenfilenames(
            title="选择照片",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")],
        )
        if names:
            self._set_files([Path(name) for name in names])

    def _choose_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择照片文件夹")
        if not folder:
            return
        paths = [
            path
            for path in sorted(Path(folder).iterdir())
            if path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if not paths:
            messagebox.showinfo(APP_TITLE, "这个文件夹里没有 JPG/PNG 图片。")
            return
        self._set_files(paths)

    def _choose_output(self) -> None:
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.output_dir_var.set(folder)

    def _set_files(self, files: List[Path]) -> None:
        self.files = files
        self.preview_index = 0
        self.file_list.delete(0, tk.END)
        for file_path in self.files:
            self.file_list.insert(tk.END, file_path.name)
        if self.files:
            self.file_list.selection_set(0)
        self.count_var.set(f"{len(self.files)} 张照片")
        self._update_meta()
        self.after_idle(self._update_preview)

    def _on_select_file(self, _event: tk.Event) -> None:
        selection = self.file_list.curselection()
        if selection:
            self.preview_index = selection[0]
            self._update_meta()
            self._schedule_preview()

    def _current_options(self) -> RenderOptions:
        return RenderOptions(
            border_style=self.style_var.get(),
            border_ratio=self.border_var.get() / 100.0,
            corner_radius=self.corner_var.get(),
            shadow_offset=self.shadow_var.get(),
            shadow_blur=self.shadow_blur_var.get(),
            shadow_opacity=self.shadow_opacity_var.get(),
            blur_radius=self.blur_radius_var.get(),
            font_scale=self.font_scale_var.get() / 100.0,
            text_spacing=self.text_spacing_var.get(),
            caption_backdrop_opacity=self.caption_backdrop_var.get(),
            text_shadow_opacity=self.text_shadow_var.get(),
            jpg_quality=self.quality_var.get(),
            include_brand=self.include_brand_var.get(),
            include_model=self.include_model_var.get(),
            include_params=self.include_params_var.get(),
            include_lens=self.include_lens_var.get(),
            include_datetime=self.include_datetime_var.get(),
            include_custom_title=self.include_custom_title_var.get(),
            include_custom_subtitle=self.include_custom_subtitle_var.get(),
            custom_title=self.title_var.get(),
            custom_subtitle=self.subtitle_var.get(),
        )

    def _schedule_preview(self) -> None:
        if self.preview_after_id:
            self.after_cancel(self.preview_after_id)
        self.preview_after_id = self.after(260, self._update_preview)

    def _update_preview(self) -> None:
        self.preview_after_id = None
        if not self.files:
            return
        try:
            preview = render_preview(self.files[self.preview_index], self._current_options(), max_source_side=1200)
            frame_width = max(320, self.preview_frame.winfo_width() - 36)
            frame_height = max(300, self.preview_frame.winfo_height() - 36)
            preview.thumbnail((frame_width, frame_height))
            self.preview_photo = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview_photo, text="")
            self.status_var.set("预览已更新")
        except Exception as exc:
            self.preview_label.configure(image="", text=f"预览失败: {exc}")
            self.status_var.set("预览失败")

    def _update_meta(self) -> None:
        if not self.files:
            self.meta_label.config(text="EXIF 信息会显示在这里")
            return
        path = self.files[self.preview_index]
        params = format_exif_params(get_exif_data(path))
        self.meta_label.config(
            text=(
                f"{path.name}\n"
                f"{params['brand']} {params['model']}  |  {params['params']}\n"
                f"{params['lens']}  |  {params['datetime']}"
            )
        )

    def _start_processing(self) -> None:
        if not self.files:
            messagebox.showinfo(APP_TITLE, "请先选择要处理的照片。")
            return
        output_dir = Path(self.output_dir_var.get()).expanduser()
        options = self._current_options()
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.files)
        self.process_button.configure(state="disabled")
        self.status_var.set("正在处理...")
        self._log("开始批量处理。")

        self.worker_thread = threading.Thread(
            target=self._process_worker,
            args=(self.files[:], output_dir, options),
            daemon=True,
        )
        self.worker_thread.start()

    def _process_worker(self, files: List[Path], output_dir: Path, options: RenderOptions) -> None:
        success = 0
        output_dir.mkdir(parents=True, exist_ok=True)
        for index, path in enumerate(files, 1):
            try:
                self.worker_queue.put(("progress", index - 1, f"处理中: {path.name}"))
                output_path = output_path_for(path, output_dir, options.border_style)
                render_image(path, output_path, options)
                success += 1
                self.worker_queue.put(("log", f"已保存: {output_path}"))
            except Exception as exc:
                self.worker_queue.put(("log", f"处理失败 {path.name}: {exc}"))
            self.worker_queue.put(("progress", index, f"进度 {index}/{len(files)}"))
        self.worker_queue.put(("done", success, len(files)))

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                event = self.worker_queue.get_nowait()
                kind = event[0]
                if kind == "log":
                    self._log(event[1])
                elif kind == "progress":
                    self.progress["value"] = event[1]
                    self.status_var.set(event[2])
                elif kind == "done":
                    success, total = event[1], event[2]
                    self.process_button.configure(state="normal")
                    self.status_var.set(f"完成 {success}/{total}")
                    self._log(f"处理完成: 成功 {success}/{total}")
        except queue.Empty:
            pass
        self.after(120, self._poll_worker_queue)

    def _open_output_dir(self) -> None:
        output_dir = Path(self.output_dir_var.get()).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(str(output_dir))
        else:
            messagebox.showinfo(APP_TITLE, str(output_dir))

    def _log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(tk.END, f"{message}\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")


def run_studio() -> None:
    app = PhotoBorderStudio()
    app.mainloop()
