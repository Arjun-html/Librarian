#!/usr/bin/env python3
"""
librarian_gui.py — a dead-simple desktop front end for Arjun's reading library.

Reuses the existing engine in librarian.py:
  - library.db is the source of truth
  - librarian.cmd_generate() rebuilds index.html, library.html, books/*.html + library.md from the database

This window lets you add / edit / delete books, pick a cover image, write notes,
set status, and regenerate the site — no terminal, no Claude Code.

Run:   python librarian_gui.py
       (or double-click run-librarian.bat for a windowless launch)
"""

import re
import shutil
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import librarian  # the existing engine; import is side-effect-free (guarded by __main__)

# Optional thumbnail preview — works without Pillow, just skips the image.
try:
    from PIL import Image, ImageTk  # type: ignore
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

ROOT       = Path(__file__).parent
COVERS_DIR = ROOT / 'book_covers_additional'
IMAGE_TYPES = [('Image files', '*.jpg *.jpeg *.png *.gif *.webp'), ('All files', '*.*')]

# section key <-> human label, reusing the engine's maps
SECTION_KEYS   = librarian.SECTIONS
SECTION_LABELS = [librarian.SECTION_NAMES[k] for k in SECTION_KEYS]
LABEL_TO_KEY   = {librarian.SECTION_NAMES[k]: k for k in SECTION_KEYS}

STATUS_KEYS   = ['read', 'reading', 'list']        # order of radio buttons
STATUS_LABELS = librarian.STATUS_LABEL             # {'read':'Read', ...}

HERO_SLOTS = ['', 'lead', 'side', 'bottom']


def _sanitize_filename(name: str) -> str:
    """Make a filesystem-friendly base name from a string."""
    name = name.strip().replace(' ', '_')
    name = re.sub(r'[^A-Za-z0-9._-]', '', name)
    return name or 'cover'


class LibrarianGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Arjun's Library — Editor")
        self.geometry('1100x720')
        self.minsize(940, 620)

        librarian.ensure_schema()

        self.current_id = None          # None => adding a new book
        self.cover_path = None          # relative path stored in local_cover_path
        self._thumb = None              # keep a reference so Tk doesn't GC the image
        self._all_rows: list = []       # full unfiltered book list for search

        self._build_layout()
        self.refresh_list()
        self.clear_form()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        outer = ttk.Frame(self, padding=8)
        outer.pack(fill='both', expand=True)

        paned = ttk.PanedWindow(outer, orient='horizontal')
        paned.pack(fill='both', expand=True)

        self._build_list(paned)
        self._build_form(paned)
        self._build_statusbar(outer)

    def _build_list(self, parent):
        left = ttk.Frame(parent, padding=(0, 0, 8, 0))
        parent.add(left, weight=1)

        ttk.Label(left, text='Books', font=('', 11, 'bold')).pack(anchor='w', pady=(0, 4))

        # Search bar
        sf = ttk.Frame(left)
        sf.pack(fill='x', pady=(0, 4))
        ttk.Label(sf, text='Search:').pack(side='left')
        self.var_search = tk.StringVar()
        self.var_search.trace_add('write', lambda *_: self._apply_filter())
        ttk.Entry(sf, textvariable=self.var_search).pack(side='left', fill='x', expand=True, padx=(4, 0))
        ttk.Button(sf, text='×', width=2, command=lambda: self.var_search.set('')).pack(side='left', padx=(2, 0))

        cols = ('id', 'title', 'author', 'section', 'status')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', selectmode='browse')
        headings = {'id': 'ID', 'title': 'Title', 'author': 'Author',
                    'section': 'Section', 'status': 'Status'}
        widths = {'id': 40, 'title': 220, 'author': 150, 'section': 90, 'status': 70}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor='w',
                             stretch=(c in ('title', 'author')))

        vsb = ttk.Scrollbar(left, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def _build_form(self, parent):
        # Scrollable right pane so the form fits on small screens.
        right = ttk.Frame(parent)
        parent.add(right, weight=2)

        canvas = tk.Canvas(right, highlightthickness=0)
        fscroll = ttk.Scrollbar(right, orient='vertical', command=canvas.yview)
        form = ttk.Frame(canvas, padding=(4, 0, 4, 8))
        form.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=form, anchor='nw')
        canvas.configure(yscrollcommand=fscroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        fscroll.pack(side='right', fill='y')

        # Bind scroll wheel to scroll the canvas when hovering over it or its contents
        def _on_mousewheel(event):
            widget = event.widget
            parent = widget
            is_child_of_canvas = False
            while parent:
                if parent == canvas:
                    is_child_of_canvas = True
                    break
                parent_name = parent.winfo_parent()
                if not parent_name:
                    break
                try:
                    parent = self.nametowidget(parent_name)
                except Exception:
                    break
            
            if is_child_of_canvas:
                if event.num == 4:
                    canvas.yview_scroll(-2, "units")
                elif event.num == 5:
                    canvas.yview_scroll(2, "units")
                else:
                    # Windows / macOS MouseWheel
                    # event.delta is positive for scrolling up, negative for down.
                    # yview_scroll needs negative to scroll up, positive to scroll down.
                    direction = -1 * (event.delta // 120)
                    if direction == 0:
                        direction = -1 if event.delta > 0 else 1
                    canvas.yview_scroll(2 * direction, "units")

        self.bind_all("<MouseWheel>", _on_mousewheel)
        self.bind_all("<Button-4>", _on_mousewheel)
        self.bind_all("<Button-5>", _on_mousewheel)


        r = 0
        ttk.Label(form, text='Add / Edit Book', font=('', 11, 'bold')).grid(
            row=r, column=0, columnspan=2, sticky='w', pady=(0, 6)); r += 1

        # Title
        ttk.Label(form, text='Title *').grid(row=r, column=0, sticky='w')
        self.var_title = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_title, width=60).grid(
            row=r, column=1, sticky='we', pady=2); r += 1

        # Author
        ttk.Label(form, text='Author *').grid(row=r, column=0, sticky='w')
        self.var_author = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_author, width=60).grid(
            row=r, column=1, sticky='we', pady=2); r += 1

        # Section
        ttk.Label(form, text='Section').grid(row=r, column=0, sticky='w')
        self.var_section = tk.StringVar(value=SECTION_LABELS[0])
        ttk.Combobox(form, textvariable=self.var_section, values=SECTION_LABELS,
                     state='readonly', width=40).grid(row=r, column=1, sticky='w', pady=2)
        r += 1

        # Status
        ttk.Label(form, text='Status').grid(row=r, column=0, sticky='w')
        status_frame = ttk.Frame(form)
        self.var_status = tk.StringVar(value='reading')
        for key in STATUS_KEYS:
            ttk.Radiobutton(status_frame, text=STATUS_LABELS[key], value=key,
                            variable=self.var_status,
                            command=self._update_hero_state).pack(side='left', padx=(0, 10))
        status_frame.grid(row=r, column=1, sticky='w', pady=2); r += 1

        # ISBN
        ttk.Label(form, text='ISBN').grid(row=r, column=0, sticky='w')
        self.var_isbn = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_isbn, width=30).grid(
            row=r, column=1, sticky='w', pady=2)
        ttk.Label(form, text='(used for an online cover if no image is uploaded)',
                  foreground='#777').grid(row=r, column=1, sticky='e'); r += 1

        # Cover
        ttk.Label(form, text='Cover image').grid(row=r, column=0, sticky='nw')
        cover_frame = ttk.Frame(form)
        ttk.Button(cover_frame, text='Choose image…', command=self.choose_cover).pack(side='left')
        ttk.Button(cover_frame, text='Clear', command=self.clear_cover).pack(side='left', padx=4)
        self.lbl_cover = ttk.Label(cover_frame, text='(none)', foreground='#555')
        self.lbl_cover.pack(side='left', padx=6)
        cover_frame.grid(row=r, column=1, sticky='w', pady=2); r += 1

        self.lbl_thumb = ttk.Label(form)
        self.lbl_thumb.grid(row=r, column=1, sticky='w', pady=2); r += 1

        # My Notes
        ttk.Label(form, text='My Notes').grid(row=r, column=0, sticky='nw')
        self.txt_my = tk.Text(form, width=60, height=4, wrap='word')
        self.txt_my.grid(row=r, column=1, sticky='we', pady=2); r += 1

        # AI Notes
        ttk.Label(form, text='About / AI Notes').grid(row=r, column=0, sticky='nw')
        self.txt_ai = tk.Text(form, width=60, height=4, wrap='word')
        self.txt_ai.grid(row=r, column=1, sticky='we', pady=2); r += 1

        # ── Hero panel ──────────────────────────────────────────────────────
        self.hero_frame = ttk.LabelFrame(
            form, text='Newspaper hero (optional — only used for "Reading" books)',
            padding=8)
        self.hero_frame.grid(row=r, column=0, columnspan=2, sticky='we', pady=(8, 2)); r += 1

        hr = 0
        ttk.Label(self.hero_frame, text='Slot').grid(row=hr, column=0, sticky='w')
        self.var_slot = tk.StringVar(value='')
        ttk.Combobox(self.hero_frame, textvariable=self.var_slot, values=HERO_SLOTS,
                     state='readonly', width=12).grid(row=hr, column=1, sticky='w', pady=2)
        ttk.Label(self.hero_frame, text='(leave blank = not featured on the front page)',
                  foreground='#777').grid(row=hr, column=2, sticky='w', padx=6); hr += 1

        self.var_kicker   = tk.StringVar()
        self.var_headline = tk.StringVar()
        self.var_deck     = tk.StringVar()
        self.var_byline   = tk.StringVar()
        self.var_progress = tk.StringVar()
        for label, var in [('Kicker', self.var_kicker), ('Headline', self.var_headline),
                           ('Deck', self.var_deck), ('Byline extra', self.var_byline),
                           ('Progress', self.var_progress)]:
            ttk.Label(self.hero_frame, text=label).grid(row=hr, column=0, sticky='w')
            ttk.Entry(self.hero_frame, textvariable=var, width=55).grid(
                row=hr, column=1, columnspan=2, sticky='we', pady=2); hr += 1

        ttk.Label(self.hero_frame, text='Body (lead only)').grid(row=hr, column=0, sticky='nw')
        self.txt_body = tk.Text(self.hero_frame, width=50, height=4, wrap='word')
        self.txt_body.grid(row=hr, column=1, columnspan=2, sticky='we', pady=2); hr += 1
        self.hero_frame.columnconfigure(1, weight=1)

        # ── Action buttons ──────────────────────────────────────────────────
        btns = ttk.Frame(form)
        btns.grid(row=r, column=0, columnspan=2, sticky='we', pady=(10, 0)); r += 1
        ttk.Button(btns, text='New book', command=self.clear_form).pack(side='left')
        ttk.Button(btns, text='Save', command=lambda: self.save()).pack(side='left', padx=4)
        ttk.Button(btns, text='Save + Regenerate',
                   command=lambda: self.save(regenerate=True)).pack(side='left', padx=4)
        ttk.Button(btns, text='Delete', command=self.delete).pack(side='left', padx=4)
        ttk.Button(btns, text='Delete + Regenerate',
                   command=lambda: self.delete(regenerate=True)).pack(side='left', padx=4)
        ttk.Button(btns, text='Regenerate site', command=self.regenerate).pack(side='left', padx=4)

        form.columnconfigure(1, weight=1)

    def _build_statusbar(self, parent):
        self.var_status_msg = tk.StringVar(value='Ready.')
        bar = ttk.Frame(parent, relief='sunken', padding=(6, 3))
        bar.pack(fill='x', side='bottom', pady=(6, 0))
        ttk.Label(bar, textvariable=self.var_status_msg).pack(side='left')

    # ── data helpers ────────────────────────────────────────────────────────

    def status(self, msg):
        self.var_status_msg.set(msg)
        self.update_idletasks()

    def refresh_list(self):
        conn = librarian.get_db()
        rows = conn.execute(
            'SELECT id, title, author, section, status FROM books '
            'ORDER BY section, sort_order, id'
        ).fetchall()
        conn.close()
        self._all_rows = [
            (b['id'], b['title'], b['author'],
             librarian.SECTION_NAMES.get(b['section'], b['section']),
             STATUS_LABELS.get(b['status'], b['status']))
            for b in rows
        ]
        self._apply_filter()

    def _apply_filter(self):
        term = self.var_search.get().lower().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self._all_rows:
            book_id, title, author, section, status = row
            if not term or any(term in field.lower() for field in (title, author, section, status)):
                self.tree.insert('', 'end', iid=str(book_id), values=row)

    def _update_hero_state(self):
        """Enable the hero panel only for Reading books."""
        reading = self.var_status.get() == 'reading'
        state = 'normal' if reading else 'disabled'
        for child in self.hero_frame.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass

    # ── form <-> widgets ──────────────────────────────────────────────────────

    def clear_form(self):
        self.current_id = None
        self.cover_path = None
        self.var_title.set('')
        self.var_author.set('')
        self.var_section.set(SECTION_LABELS[0])
        self.var_status.set('reading')
        self.var_isbn.set('')
        self.txt_my.delete('1.0', 'end')
        self.txt_ai.delete('1.0', 'end')
        self.var_slot.set('')
        self.var_kicker.set('')
        self.var_headline.set('')
        self.var_deck.set('')
        self.var_byline.set('')
        self.var_progress.set('')
        self.txt_body.delete('1.0', 'end')
        self._set_cover_label()
        self._update_hero_state()
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.status('New book — fill in the form and click Save.')

    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        book_id = int(sel[0])
        conn = librarian.get_db()
        b = conn.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
        conn.close()
        if not b:
            return
        self.current_id = book_id
        self.cover_path = b['local_cover_path']
        self.var_title.set(b['title'])
        self.var_author.set(b['author'])
        self.var_section.set(librarian.SECTION_NAMES.get(b['section'], SECTION_LABELS[0]))
        self.var_status.set(b['status'])
        self.var_isbn.set(b['isbn'] or '')
        self.txt_my.delete('1.0', 'end'); self.txt_my.insert('1.0', b['my_notes'] or '')
        self.txt_ai.delete('1.0', 'end'); self.txt_ai.insert('1.0', b['ai_notes'] or '')
        self.var_slot.set(b['hero_slot'] or '')
        self.var_kicker.set(b['hero_kicker'] or '')
        self.var_headline.set(b['hero_headline'] or '')
        self.var_deck.set(b['hero_deck'] or '')
        self.var_byline.set(b['hero_byline_extra'] or '')
        self.var_progress.set(b['hero_progress'] or '')
        self.txt_body.delete('1.0', 'end'); self.txt_body.insert('1.0', b['hero_body'] or '')
        self._set_cover_label()
        self._update_hero_state()
        self.status(f'Loaded "{b["title"]}" (ID {book_id}).')

    def _set_cover_label(self):
        if self.cover_path:
            self.lbl_cover.configure(text=Path(self.cover_path).name)
        else:
            self.lbl_cover.configure(text='(none)')
        self._render_thumb()

    def _render_thumb(self):
        self.lbl_thumb.configure(image='')
        self._thumb = None
        if not (_HAS_PIL and self.cover_path):
            return
        img_file = ROOT / self.cover_path
        if not img_file.exists():
            return
        try:
            im = Image.open(img_file)
            im.thumbnail((110, 150))
            self._thumb = ImageTk.PhotoImage(im)
            self.lbl_thumb.configure(image=self._thumb)
        except Exception:
            pass

    # ── cover handling ──────────────────────────────────────────────────────

    def choose_cover(self):
        path = filedialog.askopenfilename(title='Choose a cover image', filetypes=IMAGE_TYPES)
        if not path:
            return
        src = Path(path)
        COVERS_DIR.mkdir(exist_ok=True)
        base = _sanitize_filename(self.var_title.get() or src.stem)
        ext = src.suffix.lower() or '.jpg'
        dest = COVERS_DIR / f'{base}{ext}'
        n = 1
        while dest.exists() and dest.resolve() != src.resolve():
            dest = COVERS_DIR / f'{base}_{n}{ext}'
            n += 1
        try:
            shutil.copy2(src, dest)
        except Exception as exc:
            messagebox.showerror('Cover copy failed', str(exc))
            return
        self.cover_path = f'{COVERS_DIR.name}/{dest.name}'
        self._set_cover_label()
        self.status(f'Cover set: {dest.name}')

    def clear_cover(self):
        self.cover_path = None
        self._set_cover_label()
        self.status('Cover cleared (will fall back to ISBN or "No cover").')

    # ── save / delete / regenerate ────────────────────────────────────────────

    def _collect(self):
        title  = self.var_title.get().strip()
        author = self.var_author.get().strip()
        if not title or not author:
            messagebox.showwarning('Missing fields', 'Title and Author are required.')
            return None
        status = self.var_status.get()
        hero = status == 'reading'
        return {
            'title':   title,
            'author':  author,
            'section': LABEL_TO_KEY[self.var_section.get()],
            'status':  status,
            'isbn':    self.var_isbn.get().strip() or None,
            'my_notes': self.txt_my.get('1.0', 'end').strip() or None,
            'ai_notes': self.txt_ai.get('1.0', 'end').strip() or None,
            'local_cover_path': self.cover_path or None,
            'hero_slot':        (self.var_slot.get() or None) if hero else None,
            'hero_kicker':      (self.var_kicker.get().strip() or None) if hero else None,
            'hero_headline':    (self.var_headline.get().strip() or None) if hero else None,
            'hero_deck':        (self.var_deck.get().strip() or None) if hero else None,
            'hero_byline_extra': (self.var_byline.get().strip() or None) if hero else None,
            'hero_progress':    (self.var_progress.get().strip() or None) if hero else None,
            'hero_body':        (self.txt_body.get('1.0', 'end').strip() or None) if hero else None,
        }

    def save(self, regenerate=False):
        data = self._collect()
        if data is None:
            return
        conn = librarian.get_db()
        try:
            if self.current_id is None:
                # New book: place it last within its section.
                max_sort = conn.execute(
                    'SELECT MAX(sort_order) FROM books WHERE section=?', (data['section'],)
                ).fetchone()[0] or 0
                hero_sort = 0
                if data['hero_slot']:
                    hero_sort = (conn.execute(
                        'SELECT MAX(hero_sort) FROM books WHERE hero_slot=?',
                        (data['hero_slot'],)).fetchone()[0] or 0) + 1
                conn.execute(
                    '''INSERT INTO books
                       (title, author, isbn, section, status, my_notes, ai_notes,
                        sort_order, hero_slot, hero_sort, hero_kicker, hero_headline,
                        hero_deck, hero_byline_extra, hero_body, hero_progress,
                        local_cover_path)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (data['title'], data['author'], data['isbn'], data['section'],
                     data['status'], data['my_notes'], data['ai_notes'], max_sort + 1,
                     data['hero_slot'], hero_sort, data['hero_kicker'], data['hero_headline'],
                     data['hero_deck'], data['hero_byline_extra'], data['hero_body'],
                     data['hero_progress'], data['local_cover_path']))
                conn.commit()
                self.current_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                msg = f'Added "{data["title"]}" (ID {self.current_id}).'
            else:
                # Existing book: keep its sort_order; assign hero_sort if newly featured.
                cur = conn.execute('SELECT hero_slot, hero_sort FROM books WHERE id=?',
                                   (self.current_id,)).fetchone()
                hero_sort = cur['hero_sort'] if cur else 0
                if data['hero_slot'] and (not cur or cur['hero_slot'] != data['hero_slot']
                                          or not cur['hero_sort']):
                    hero_sort = (conn.execute(
                        'SELECT MAX(hero_sort) FROM books WHERE hero_slot=?',
                        (data['hero_slot'],)).fetchone()[0] or 0) + 1
                conn.execute(
                    '''UPDATE books SET title=?, author=?, isbn=?, section=?, status=?,
                       my_notes=?, ai_notes=?, hero_slot=?, hero_sort=?, hero_kicker=?,
                       hero_headline=?, hero_deck=?, hero_byline_extra=?, hero_body=?,
                       hero_progress=?, local_cover_path=? WHERE id=?''',
                    (data['title'], data['author'], data['isbn'], data['section'],
                     data['status'], data['my_notes'], data['ai_notes'], data['hero_slot'],
                     hero_sort, data['hero_kicker'], data['hero_headline'], data['hero_deck'],
                     data['hero_byline_extra'], data['hero_body'], data['hero_progress'],
                     data['local_cover_path'], self.current_id))
                conn.commit()
                msg = f'Updated "{data["title"]}" (ID {self.current_id}).'
        except sqlite3.Error as exc:
            conn.close()
            messagebox.showerror('Database error', str(exc))
            return
        conn.close()

        saved_id = self.current_id
        self.refresh_list()
        if self.tree.exists(str(saved_id)):
            self.tree.selection_set(str(saved_id))
        self.status(msg)

        if regenerate:
            self.regenerate(prefix=msg + ' ')

    def delete(self, regenerate=False):
        if self.current_id is None:
            messagebox.showinfo('Nothing selected', 'Select a book to delete.')
            return
        title = self.var_title.get()
        if not messagebox.askyesno('Confirm delete', f'Delete "{title}"?\nThis cannot be undone.'):
            return
        conn = librarian.get_db()
        conn.execute('DELETE FROM books WHERE id=?', (self.current_id,))
        conn.commit()
        conn.close()
        self.refresh_list()
        self.clear_form()
        msg = f'Deleted "{title}".'
        self.status(msg)
        if regenerate:
            self.regenerate(prefix=msg + ' ')

    def regenerate(self, prefix=''):
        try:
            librarian.cmd_generate()
        except SystemExit as exc:      # cmd_generate uses sys.exit on missing template
            messagebox.showerror('Generate failed', str(exc))
            return
        except Exception as exc:
            messagebox.showerror('Generate failed', str(exc))
            return
        self.status(prefix + 'Regenerated index.html, library.html, books/ + library.md.')


if __name__ == '__main__':
    LibrarianGUI().mainloop()
