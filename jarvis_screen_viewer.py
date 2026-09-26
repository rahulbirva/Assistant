"""
Screen Viewer Window for Jarvis (Phase 5).
Displays live screenshot with OCR bounding boxes overlaid (cyan highlights),
detected text transcript, and interactive inspection of UI coordinates.
"""
import os
import sys
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.screen_monitor import screen_monitor, ensure_interactive_desktop


class JarvisScreenViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JARVIS — Live Screen Vision & OCR Inspector")
        self.root.geometry("900x620")
        self.root.configure(bg="#0d1117")
        self.root.attributes("-topmost", True)

        self.selected_item = None
        self.current_img: Image.Image = None
        self.photo_img: ImageTk.PhotoImage = None
        self.scale_x = 1.0
        self.scale_y = 1.0

        # Top Header Bar
        header = tk.Frame(root, bg="#161b22", height=38)
        header.pack(fill=tk.X, side=tk.TOP)

        title = tk.Label(
            header,
            text="● COMPUTER VISION (OCR BOUNDING BOXES & COORDINATES)",
            font=("Consolas", 10, "bold"),
            fg="#c084fc",
            bg="#161b22",
            padx=12,
            pady=8
        )
        title.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            header,
            text="Live Feed Active (2.0s)",
            font=("Consolas", 8),
            fg="#8b949e",
            bg="#161b22"
        )
        self.status_lbl.pack(side=tk.RIGHT, padx=12)

        # Main Paned Window
        paned = tk.PanedWindow(root, orient=tk.HORIZONTAL, bg="#21262d", sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left Panel: Canvas for Screenshot + Bounding Boxes
        left_frame = tk.Frame(paned, bg="#0d1117")
        paned.add(left_frame, minsize=520)

        self.canvas = tk.Canvas(left_frame, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Right Panel: Detected OCR Items Table
        right_frame = tk.Frame(paned, bg="#161b22", width=340)
        paned.add(right_frame, minsize=300)

        right_header = tk.Label(
            right_frame,
            text="DETECTED UI ELEMENTS",
            font=("Consolas", 9, "bold"),
            fg="#58a6ff",
            bg="#161b22",
            pady=6
        )
        right_header.pack(fill=tk.X)

        # Treeview for elements
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#0d1117",
            foreground="#c9d1d9",
            fieldbackground="#0d1117",
            font=("Consolas", 8),
            rowheight=22
        )
        style.configure("Treeview.Heading", font=("Consolas", 8, "bold"), background="#21262d", foreground="#58a6ff")
        style.map("Treeview", background=[("selected", "#1f6feb")], foreground=[("selected", "#ffffff")])

        cols = ("Text", "Center", "Conf")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("Text", text="Visible Text")
        self.tree.heading("Center", text="Center (X, Y)")
        self.tree.heading("Conf", text="Conf")

        self.tree.column("Text", width=160, anchor=tk.W)
        self.tree.column("Center", width=90, anchor=tk.CENTER)
        self.tree.column("Conf", width=50, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Selected element info box
        self.info_box = tk.Label(
            right_frame,
            text="Click an element to view click coordinates",
            font=("Consolas", 8),
            fg="#34d399",
            bg="#0d1117",
            pady=8,
            wraplength=300
        )
        self.info_box.pack(fill=tk.X, side=tk.BOTTOM)

        # Initial Refresh & Loop
        self.cached_ocr_results = []
        self.refresh_display()
        self.poll_updates()

    def refresh_display(self):
        """Fetches latest screenshot and OCR detections and updates canvas and treeview."""
        img, results, summary = screen_monitor.get_latest_data()
        if img is None:
            # If no cached image, capture one now
            img, results = screen_monitor.capture_now()

        if img is None:
            return

        self.current_img = img.copy()
        self.cached_ocr_results = results

        # Overlay bounding boxes on image
        annotated = self.current_img.copy()
        draw = ImageDraw.Draw(annotated)

        for r in results:
            pts = r["box"]
            flat_pts = [coord for pt in pts for coord in pt]
            draw.polygon(flat_pts, outline="#00ffff", width=2)

        # Highlight selected element if any
        if self.selected_item:
            sel_pts = self.selected_item["box"]
            flat_sel = [coord for pt in sel_pts for coord in pt]
            draw.polygon(flat_sel, outline="#ff0055", width=4)
            cx, cy = self.selected_item["center"]
            draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill="#ff0055")

        # Resize to fit canvas
        canvas_w = max(100, self.canvas.winfo_width())
        canvas_h = max(100, self.canvas.winfo_height())
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = 540
            canvas_h = 500

        img_w, img_h = annotated.size
        scale = min(canvas_w / img_w, canvas_h / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        self.scale_x = img_w / new_w
        self.scale_y = img_h / new_h

        resized = annotated.resize((new_w, new_h), Image.Resampling.BILINEAR)
        self.photo_img = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        # Center image in canvas
        x_offset = (canvas_w - new_w) // 2
        y_offset = (canvas_h - new_h) // 2
        self.canvas_offset_x = x_offset
        self.canvas_offset_y = y_offset
        self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.photo_img)

        # Update Treeview only if count changed or empty
        current_tree_count = len(self.tree.get_children())
        if current_tree_count != len(results):
            self.tree.delete(*self.tree.get_children())
            for idx, r in enumerate(results):
                cx, cy = r["center"]
                self.tree.insert("", tk.END, iid=str(idx), values=(r["text"], f"{cx}, {cy}", f"{r['confidence']:.2f}"))

        self.status_lbl.config(text=f"Detected: {len(results)} items ({time.strftime('%H:%M:%S')})")

    def on_tree_select(self, event):
        """Highlights the selected element in the canvas."""
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.cached_ocr_results):
            self.selected_item = self.cached_ocr_results[idx]
            cx, cy = self.selected_item["center"]
            txt = self.selected_item["text"]
            self.info_box.config(
                text=f"🎯 Target: '{txt}'\nCoordinates: ({cx}, {cy}) | Confidence: {self.selected_item['confidence']:.2f}"
            )
            self.refresh_display()

    def on_canvas_click(self, event):
        """User clicks on canvas image: finds closest OCR text and selects it."""
        if not hasattr(self, "canvas_offset_x") or not self.cached_ocr_results:
            return

        # Convert canvas click to original image pixel coordinates
        img_x = int((event.x - self.canvas_offset_x) * self.scale_x)
        img_y = int((event.y - self.canvas_offset_y) * self.scale_y)

        # Find closest OCR bounding box
        closest = None
        min_dist = float("inf")

        for idx, r in enumerate(self.cached_ocr_results):
            cx, cy = r["center"]
            dist = (cx - img_x) ** 2 + (cy - img_y) ** 2
            if dist < min_dist:
                min_dist = dist
                closest = (idx, r)

        if closest and min_dist < (150 * 150):  # within ~150px
            idx, item = closest
            self.selected_item = item
            if str(idx) in self.tree.get_children():
                self.tree.selection_set(str(idx))
                self.tree.see(str(idx))
            cx, cy = item["center"]
            self.info_box.config(
                text=f"🎯 Target: '{item['text']}'\nCoordinates: ({cx}, {cy}) | Conf: {item['confidence']:.2f}"
            )
            self.refresh_display()

    def poll_updates(self):
        """Auto-refreshes display every 2 seconds."""
        self.refresh_display()
        self.root.after(2000, self.poll_updates)


def show_screen_viewer():
    """Entry point to launch the screen viewer."""
    root = tk.Tk()
    app = JarvisScreenViewer(root)
    root.mainloop()


if __name__ == "__main__":
    show_screen_viewer()
