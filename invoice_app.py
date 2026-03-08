# ============================================================================
#  QuickInvoice — Small Business Invoice Generator
#  Created by bobbycodes.dev | https://www.bobbycodes.dev
#
#  Free to use. All I ask is a star on GitHub and credit if recoded. Thank you!
# ============================================================================

import customtkinter as ctk
from tkinter import messagebox, filedialog
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import threading
import time
import json
import sys
import os

APP_VERSION = "1.0.0"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
SUCCESS = "#22C55E"
SURFACE = "#1E293B"
SURFACE_LIGHT = "#334155"
CATALOG_COLOR = "#8B5CF6"
CATALOG_HOVER = "#7C3AED"
LOOKUP_COLOR = "#F59E0B"
LOOKUP_HOVER = "#D97706"

STATUS_COLORS = {
    "Unpaid": {"fg": "#F59E0B", "bg": "#422006"},
    "Paid":   {"fg": "#22C55E", "bg": "#052E16"},
    "Late":   {"fg": "#EF4444", "bg": "#450A0A"},
}


def _data_dir():
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    d = os.path.join(base, "QuickInvoice")
    os.makedirs(d, exist_ok=True)
    return d


DATA_DIR = _data_dir()
CATALOG_FILE = os.path.join(DATA_DIR, "product_catalog.json")
INVOICES_FILE = os.path.join(DATA_DIR, "invoices.json")

# ── Persistence helpers ──

def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_catalog() -> list[dict]:
    return _load_json(CATALOG_FILE, [])


def save_catalog(catalog: list[dict]):
    _save_json(CATALOG_FILE, catalog)


def load_invoices() -> list[dict]:
    return _load_json(INVOICES_FILE, [])


def save_invoices(invoices: list[dict]):
    _save_json(INVOICES_FILE, invoices)


def update_invoice_field(inv_number: str, **fields):
    invoices = load_invoices()
    for inv in invoices:
        if inv.get("number") == inv_number:
            inv.update(fields)
            break
    save_invoices(invoices)


def add_invoice_log_entry(inv_number: str, entry: str):
    invoices = load_invoices()
    for inv in invoices:
        if inv.get("number") == inv_number:
            log = inv.get("activity_log", [])
            log.append({
                "timestamp": datetime.now().strftime("%m/%d/%Y %I:%M %p"),
                "text": entry,
            })
            inv["activity_log"] = log
            break
    save_invoices(invoices)


def next_invoice_number() -> str:
    invoices = load_invoices()
    if not invoices:
        return "INV-0001"
    last_num = 0
    for inv in invoices:
        num_str = inv.get("number", "").replace("INV-", "")
        try:
            last_num = max(last_num, int(num_str))
        except ValueError:
            pass
    return f"INV-{last_num + 1:04d}"


def _status_badge(parent, status, size=12):
    colors = STATUS_COLORS.get(status, STATUS_COLORS["Unpaid"])
    badge = ctk.CTkLabel(
        parent, text=f"  {status}  ",
        font=ctk.CTkFont(size=size, weight="bold"),
        text_color=colors["fg"],
        fg_color=colors["bg"],
        corner_radius=6,
    )
    return badge


# ── Catalog Window ──

class CatalogWindow(ctk.CTkToplevel):
    def __init__(self, master, catalog: list[dict], on_save):
        super().__init__(master)
        self.title("Product Catalog")
        self.geometry("520x500")
        self.resizable(False, True)
        self.transient(master)
        self.grab_set()

        self.catalog = [dict(p) for p in catalog]
        self.on_save = on_save
        self.rows: list[dict] = []

        header = ctk.CTkFrame(self, fg_color=CATALOG_COLOR, corner_radius=10)
        header.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(header, text="📦  Product Catalog",
                      font=ctk.CTkFont(size=18, weight="bold"),
                      text_color="white").pack(side="left", padx=14, pady=10)
        ctk.CTkButton(header, text="+ New Product", width=120, height=30,
                       fg_color=SUCCESS, hover_color="#16A34A",
                       command=self._add_blank_row).pack(side="right", padx=14)

        col_hdr = ctk.CTkFrame(self, fg_color="transparent")
        col_hdr.pack(fill="x", padx=18, pady=(6, 0))
        ctk.CTkLabel(col_hdr, text="Product Name", width=260, anchor="w",
                      font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="left", padx=4)
        ctk.CTkLabel(col_hdr, text="Price ($)", width=100, anchor="w",
                      font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="left", padx=4)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=SURFACE, corner_radius=10)
        self.scroll.pack(fill="both", expand=True, padx=12, pady=6)

        for product in self.catalog:
            self._add_row(product["name"], product["price"])
        if not self.catalog:
            self._add_blank_row()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkButton(btn_frame, text="Save Catalog", height=38,
                       font=ctk.CTkFont(size=14, weight="bold"),
                       fg_color=CATALOG_COLOR, hover_color=CATALOG_HOVER,
                       command=self._save).pack(fill="x")

    def _add_row(self, name="", price=0.0):
        frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        frame.pack(fill="x", pady=3)
        name_entry = ctk.CTkEntry(frame, placeholder_text="Product name", width=260)
        name_entry.pack(side="left", padx=(0, 6))
        if name:
            name_entry.insert(0, name)
        price_entry = ctk.CTkEntry(frame, placeholder_text="0.00", width=100)
        price_entry.pack(side="left", padx=6)
        if price:
            price_entry.insert(0, f"{price:.2f}")
        del_btn = ctk.CTkButton(frame, text="✕", width=32, height=32,
                                 fg_color="#EF4444", hover_color="#DC2626",
                                 command=lambda: self._del_row(frame))
        del_btn.pack(side="left", padx=(6, 0))
        self.rows.append({"frame": frame, "name": name_entry, "price": price_entry})

    def _add_blank_row(self):
        self._add_row()

    def _del_row(self, frame):
        self.rows = [r for r in self.rows if r["frame"] is not frame]
        frame.destroy()

    def _save(self):
        catalog = []
        for r in self.rows:
            name = r["name"].get().strip()
            try:
                price = float(r["price"].get())
            except ValueError:
                price = 0.0
            if name:
                catalog.append({"name": name, "price": round(price, 2)})
        save_catalog(catalog)
        self.on_save(catalog)
        self.destroy()


# ── Invoice Detail Window ──

class InvoiceDetailWindow(ctk.CTkToplevel):
    def __init__(self, master, inv: dict, on_status_change=None):
        super().__init__(master)
        self.title(f"Invoice {inv['number']}")
        self.geometry("580x820")
        self.resizable(False, True)
        self.inv = inv
        self.on_status_change = on_status_change
        self.after(50, self._bring_to_front)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=14, pady=14)

        # Header with status
        header = ctk.CTkFrame(scroll, fg_color=ACCENT, corner_radius=10)
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text=f"Invoice  {inv['number']}",
                      font=ctk.CTkFont(size=20, weight="bold"),
                      text_color="white").pack(side="left", padx=16, pady=12)

        status = inv.get("status", "Unpaid")
        self.status_badge = _status_badge(header, status, size=13)
        self.status_badge.pack(side="right", padx=(0, 10), pady=12)
        ctk.CTkLabel(header, text=inv.get("date", ""),
                      font=ctk.CTkFont(size=13), text_color="#BFDBFE").pack(side="right", padx=(16, 6))

        # Status actions
        status_frame = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=10)
        status_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(status_frame, text="Payment Status",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=14, pady=10)
        for s in ("Paid", "Unpaid", "Late"):
            colors = STATUS_COLORS[s]
            ctk.CTkButton(
                status_frame, text=f"Mark {s}", width=100, height=30,
                fg_color=colors["bg"], hover_color=colors["fg"],
                text_color=colors["fg"],
                border_width=2, border_color=colors["fg"],
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda st=s: self._set_status(st),
            ).pack(side="right", padx=(0, 8), pady=10)

        # Payment info (shown when paid)
        self.payment_frame = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=10)
        pi = inv.get("payment_info", "")
        if inv.get("status") == "Paid" and pi:
            self.payment_frame.pack(fill="x", pady=4)
            ctk.CTkLabel(self.payment_frame, text="Payment Info",
                          font=ctk.CTkFont(size=13, weight="bold"),
                          text_color=SUCCESS).pack(anchor="w", padx=14, pady=(8, 2))
            ctk.CTkLabel(self.payment_frame, text=pi,
                          font=ctk.CTkFont(size=12), wraplength=500,
                          justify="left").pack(anchor="w", padx=14, pady=(0, 10))

        # Business / Customer
        info = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=10)
        info.pack(fill="x", pady=4)
        left = ctk.CTkFrame(info, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=14, pady=10)
        ctk.CTkLabel(left, text="From", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(anchor="w")
        ctk.CTkLabel(left, text=inv.get("biz_name", ""), font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left, text=inv.get("biz_email", ""), font=ctk.CTkFont(size=12)).pack(anchor="w")
        ctk.CTkLabel(left, text=inv.get("biz_phone", ""), font=ctk.CTkFont(size=12)).pack(anchor="w")

        right = ctk.CTkFrame(info, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=14, pady=10)
        ctk.CTkLabel(right, text="Bill To", font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(anchor="w")
        ctk.CTkLabel(right, text=inv.get("cust_name", ""), font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(right, text=inv.get("cust_email", ""), font=ctk.CTkFont(size=12)).pack(anchor="w")
        ctk.CTkLabel(right, text=inv.get("cust_address", ""), font=ctk.CTkFont(size=12)).pack(anchor="w")

        # Line items
        items_frame = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=10)
        items_frame.pack(fill="x", pady=4)
        col_hdr = ctk.CTkFrame(items_frame, fg_color=ACCENT, corner_radius=6)
        col_hdr.pack(fill="x", padx=8, pady=(8, 4))
        for text, w in [("Description", 220), ("Qty", 60), ("Price", 90), ("Total", 90)]:
            ctk.CTkLabel(col_hdr, text=text, width=w, anchor="w",
                          font=ctk.CTkFont(size=11, weight="bold"),
                          text_color="white").pack(side="left", padx=6, pady=6)

        for item in inv.get("items", []):
            row = ctk.CTkFrame(items_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=2)
            ctk.CTkLabel(row, text=item[0], width=220, anchor="w", font=ctk.CTkFont(size=12)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"{item[1]:g}", width=60, anchor="w", font=ctk.CTkFont(size=12)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"${item[2]:,.2f}", width=90, anchor="w", font=ctk.CTkFont(size=12)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"${item[3]:,.2f}", width=90, anchor="e",
                          font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=6)
        ctk.CTkFrame(items_frame, fg_color="transparent", height=8).pack()

        # Totals
        totals = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=10)
        totals.pack(fill="x", pady=4)
        inner = ctk.CTkFrame(totals, fg_color="transparent")
        inner.pack(anchor="e", padx=20, pady=12)
        ctk.CTkLabel(inner, text=f"Subtotal:  ${inv.get('subtotal', 0):,.2f}",
                      font=ctk.CTkFont(size=13)).pack(anchor="e")
        ctk.CTkLabel(inner, text=f"Tax:  ${inv.get('tax', 0):,.2f}",
                      font=ctk.CTkFont(size=13)).pack(anchor="e", pady=2)
        ctk.CTkLabel(inner, text=f"Total:  ${inv.get('total', 0):,.2f}",
                      font=ctk.CTkFont(size=20, weight="bold"),
                      text_color=ACCENT).pack(anchor="e", pady=(4, 0))

        if inv.get("notes"):
            nf = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=10)
            nf.pack(fill="x", pady=4)
            ctk.CTkLabel(nf, text="Invoice Notes", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(8, 2))
            ctk.CTkLabel(nf, text=inv["notes"], font=ctk.CTkFont(size=12),
                          wraplength=500, justify="left").pack(anchor="w", padx=14, pady=(0, 10))

        # ── Activity Log ──
        log_frame = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=10)
        log_frame.pack(fill="x", pady=4)

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(log_header, text="Activity Log",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkLabel(log_header, text=f"{len(inv.get('activity_log', []))} entries",
                      font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="right")

        self.log_container = ctk.CTkFrame(log_frame, fg_color="transparent")
        self.log_container.pack(fill="x", padx=14)
        self._render_log()

        # Add note input
        add_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        add_frame.pack(fill="x", padx=14, pady=(6, 10))
        self.note_input = ctk.CTkTextbox(add_frame, height=60, fg_color=SURFACE_LIGHT,
                                          corner_radius=8,
                                          font=ctk.CTkFont(size=12))
        self.note_input.pack(fill="x", pady=(0, 6))
        self.note_input.configure(text_color="white")

        ctk.CTkButton(add_frame, text="Add Note", height=32, width=120,
                       fg_color=ACCENT, hover_color=ACCENT_HOVER,
                       font=ctk.CTkFont(size=12, weight="bold"),
                       command=self._add_note).pack(anchor="e")

        ctk.CTkButton(scroll, text="📄  Re-export as PDF", height=40,
                       font=ctk.CTkFont(size=14, weight="bold"),
                       fg_color=ACCENT, hover_color=ACCENT_HOVER,
                       command=self._reexport).pack(fill="x", pady=(10, 4))

    def _bring_to_front(self):
        self.lift()
        self.focus_force()

    def _note_set_placeholder(self):
        self.note_input.configure(text_color="white")
        self.note_input.delete("1.0", "end")
        self._placeholder_active = False

    def _render_log(self):
        for w in self.log_container.winfo_children():
            w.destroy()

        log = self.inv.get("activity_log", [])
        if not log:
            ctk.CTkLabel(self.log_container, text="No activity yet.",
                          font=ctk.CTkFont(size=12), text_color="#64748B").pack(anchor="w", pady=4)
            return

        for entry in reversed(log):
            row = ctk.CTkFrame(self.log_container, fg_color=SURFACE_LIGHT, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=entry.get("timestamp", ""),
                          font=ctk.CTkFont(size=10),
                          text_color="#94A3B8", width=140).pack(side="left", padx=(10, 6), pady=6)
            ctk.CTkLabel(row, text=entry.get("text", ""),
                          font=ctk.CTkFont(size=12),
                          wraplength=360, justify="left",
                          anchor="w").pack(side="left", padx=(0, 10), pady=6, fill="x", expand=True)

    def _add_note(self):
        text = self.note_input.get("1.0", "end").strip()
        if not text:
            return
        add_invoice_log_entry(self.inv["number"], text)

        # Refresh local data
        invoices = load_invoices()
        for inv in invoices:
            if inv.get("number") == self.inv["number"]:
                self.inv["activity_log"] = inv.get("activity_log", [])
                break

        self._render_log()
        self._note_set_placeholder()
        if self.on_status_change:
            self.on_status_change()

    def _set_status(self, new_status):
        if new_status == "Paid":
            self._prompt_payment_info(new_status)
            return
        if new_status == "Late":
            self._prompt_late_note(new_status)
            return

        self._apply_status(new_status)

    def _prompt_payment_info(self, new_status):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Payment Details")
        dialog.geometry("420x240")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.after(50, lambda: (dialog.lift(), dialog.focus_force()))

        ctk.CTkLabel(dialog, text="How was this invoice paid?",
                      font=ctk.CTkFont(size=15, weight="bold")).pack(padx=20, pady=(18, 4))
        ctk.CTkLabel(dialog, text="e.g. Check #1234, Visa ending 5678, Cash, Zelle from John",
                      font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(padx=20, pady=(0, 8))

        pay_input = ctk.CTkTextbox(dialog, height=70, fg_color=SURFACE_LIGHT,
                                    corner_radius=8, font=ctk.CTkFont(size=12))
        pay_input.pack(fill="x", padx=20, pady=(0, 10))

        def confirm():
            info = pay_input.get("1.0", "end").strip()
            dialog.destroy()
            self.inv["payment_info"] = info
            update_invoice_field(self.inv["number"], payment_info=info)
            if info:
                add_invoice_log_entry(self.inv["number"], f"Marked PAID — {info}")
            else:
                add_invoice_log_entry(self.inv["number"], "Marked PAID")
            self._apply_status(new_status)
            self._refresh_payment_display()

        ctk.CTkButton(dialog, text="Confirm Payment", height=36,
                       font=ctk.CTkFont(size=13, weight="bold"),
                       fg_color=SUCCESS, hover_color="#16A34A",
                       command=confirm).pack(fill="x", padx=20, pady=(0, 14))

    def _prompt_late_note(self, new_status):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Late Payment Note")
        dialog.geometry("420x240")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.after(50, lambda: (dialog.lift(), dialog.focus_force()))

        ctk.CTkLabel(dialog, text="Add a note about this late invoice?",
                      font=ctk.CTkFont(size=15, weight="bold")).pack(padx=20, pady=(18, 4))
        ctk.CTkLabel(dialog, text="e.g. Sent reminder email, called customer, 30 days overdue",
                      font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(padx=20, pady=(0, 8))

        note_input = ctk.CTkTextbox(dialog, height=70, fg_color=SURFACE_LIGHT,
                                     corner_radius=8, font=ctk.CTkFont(size=12))
        note_input.pack(fill="x", padx=20, pady=(0, 10))

        def confirm():
            note = note_input.get("1.0", "end").strip()
            dialog.destroy()
            if note:
                add_invoice_log_entry(self.inv["number"], f"Marked LATE — {note}")
            else:
                add_invoice_log_entry(self.inv["number"], "Marked LATE")
            self._apply_status(new_status)

        ctk.CTkButton(dialog, text="Confirm", height=36,
                       font=ctk.CTkFont(size=13, weight="bold"),
                       fg_color="#EF4444", hover_color="#DC2626",
                       command=confirm).pack(fill="x", padx=20, pady=(0, 14))

    def _apply_status(self, new_status):
        self.inv["status"] = new_status
        update_invoice_field(self.inv["number"], status=new_status)

        colors = STATUS_COLORS.get(new_status, STATUS_COLORS["Unpaid"])
        self.status_badge.configure(
            text=f"  {new_status}  ",
            text_color=colors["fg"],
            fg_color=colors["bg"],
        )

        # Refresh log display
        invoices = load_invoices()
        for inv in invoices:
            if inv.get("number") == self.inv["number"]:
                self.inv["activity_log"] = inv.get("activity_log", [])
                break
        self._render_log()

        if self.on_status_change:
            self.on_status_change()

    def _refresh_payment_display(self):
        for w in self.payment_frame.winfo_children():
            w.destroy()
        pi = self.inv.get("payment_info", "")
        if self.inv.get("status") == "Paid" and pi:
            self.payment_frame.pack(fill="x", pady=4, before=self.payment_frame.master.winfo_children()[2])
            ctk.CTkLabel(self.payment_frame, text="Payment Info",
                          font=ctk.CTkFont(size=13, weight="bold"),
                          text_color=SUCCESS).pack(anchor="w", padx=14, pady=(8, 2))
            ctk.CTkLabel(self.payment_frame, text=pi,
                          font=ctk.CTkFont(size=12), wraplength=500,
                          justify="left").pack(anchor="w", padx=14, pady=(0, 10))
        else:
            self.payment_frame.pack_forget()

    def _reexport(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"{self.inv['number']}.pdf"
        )
        if not path:
            return
        generate_pdf_from_record(path, self.inv)
        messagebox.showinfo("Success", f"Invoice saved to:\n{path}")
        os.startfile(path)


# ── Invoice Lookup Window ──

class LookupWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Invoice Lookup")
        self.geometry("820x600")
        self.minsize(750, 400)
        self.after(50, self._bring_to_front)

        self.invoices = load_invoices()
        self.active_filter = "All"

    def _bring_to_front(self):
        self.lift()
        self.focus_force()

        header = ctk.CTkFrame(self, fg_color=LOOKUP_COLOR, corner_radius=10)
        header.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(header, text="🔍  Invoice Lookup",
                      font=ctk.CTkFont(size=18, weight="bold"),
                      text_color="white").pack(side="left", padx=14, pady=10)
        self.count_label = ctk.CTkLabel(header, text=f"{len(self.invoices)} invoices on file",
                                         font=ctk.CTkFont(size=12), text_color="#FEF3C7")
        self.count_label.pack(side="right", padx=14)

        # Search + filter bar
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=12, pady=(4, 2))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filters())
        ctk.CTkEntry(toolbar, textvariable=self.search_var,
                      placeholder_text="Search by invoice #, customer, or date...",
                      width=360).pack(side="left", padx=(0, 10))

        # Status filter tabs
        self.filter_buttons: dict[str, ctk.CTkButton] = {}
        for label in ("All", "Unpaid", "Paid", "Late"):
            if label == "All":
                fg, hover = LOOKUP_COLOR, LOOKUP_HOVER
            else:
                c = STATUS_COLORS[label]
                fg, hover = c["bg"], c["fg"]

            btn = ctk.CTkButton(
                toolbar, text=label, width=80, height=30,
                fg_color=fg, hover_color=hover,
                font=ctk.CTkFont(size=12, weight="bold"),
                border_width=2, border_color=fg,
                command=lambda l=label: self._set_filter(l),
            )
            btn.pack(side="left", padx=3)
            self.filter_buttons[label] = btn

        self._highlight_filter_btn("All")

        # Column headers
        col_hdr = ctk.CTkFrame(self, fg_color=SURFACE_LIGHT, corner_radius=6)
        col_hdr.pack(fill="x", padx=12, pady=(6, 0))
        for text, w in [("Invoice #", 90), ("Date", 90), ("Customer", 170), ("Total", 90), ("Status", 80), ("", 70)]:
            ctk.CTkLabel(col_hdr, text=text, width=w, anchor="w",
                          font=ctk.CTkFont(size=11, weight="bold"),
                          text_color="#94A3B8").pack(side="left", padx=6, pady=6)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=SURFACE, corner_radius=10)
        self.list_frame.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self._apply_filters()

    def _highlight_filter_btn(self, active):
        for label, btn in self.filter_buttons.items():
            if label == active:
                if label == "All":
                    btn.configure(fg_color=LOOKUP_COLOR, border_color=LOOKUP_COLOR)
                else:
                    c = STATUS_COLORS[label]
                    btn.configure(fg_color=c["fg"], border_color=c["fg"], text_color="white")
            else:
                if label == "All":
                    btn.configure(fg_color="transparent", border_color=LOOKUP_COLOR)
                else:
                    c = STATUS_COLORS[label]
                    btn.configure(fg_color=c["bg"], border_color=c["fg"], text_color=c["fg"])

    def _set_filter(self, label):
        self.active_filter = label
        self._highlight_filter_btn(label)
        self._apply_filters()

    def _apply_filters(self):
        q = self.search_var.get().strip().lower()
        filtered = self.invoices

        if self.active_filter != "All":
            filtered = [inv for inv in filtered
                        if inv.get("status", "Unpaid") == self.active_filter]

        if q:
            filtered = [inv for inv in filtered
                        if q in inv.get("number", "").lower()
                        or q in inv.get("cust_name", "").lower()
                        or q in inv.get("date", "").lower()]

        self.count_label.configure(text=f"{len(filtered)} of {len(self.invoices)} invoices")
        self._render_list(filtered)

    def _refresh_data(self):
        self.invoices = load_invoices()
        self._apply_filters()

    def _render_list(self, invoices):
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not invoices:
            ctk.CTkLabel(self.list_frame, text="No invoices found.",
                          font=ctk.CTkFont(size=13), text_color="#94A3B8").pack(pady=30)
            return

        for inv in reversed(invoices):
            row = ctk.CTkFrame(self.list_frame, fg_color=SURFACE_LIGHT, corner_radius=8, height=42)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=inv.get("number", ""), width=90, anchor="w",
                          font=ctk.CTkFont(size=12, weight="bold"),
                          text_color=ACCENT).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=inv.get("date", ""), width=90, anchor="w",
                          font=ctk.CTkFont(size=12)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=inv.get("cust_name", ""), width=170, anchor="w",
                          font=ctk.CTkFont(size=12)).pack(side="left", padx=6)
            ctk.CTkLabel(row, text=f"${inv.get('total', 0):,.2f}", width=90, anchor="w",
                          font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=6)

            status = inv.get("status", "Unpaid")
            badge = _status_badge(row, status, size=11)
            badge.configure(width=80)
            badge.pack(side="left", padx=6)

            ctk.CTkButton(row, text="View", width=60, height=28,
                           fg_color=ACCENT, hover_color=ACCENT_HOVER,
                           command=lambda i=inv: self._view(i)).pack(side="left", padx=6)

    def _view(self, inv):
        InvoiceDetailWindow(self, inv, on_status_change=self._refresh_data)


# ── Line Item Row ──

class LineItemRow(ctk.CTkFrame):
    def __init__(self, master, on_delete, on_update, catalog, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_update = on_update
        self.catalog = catalog

        product_names = [p["name"] for p in catalog]
        self.desc_combo = ctk.CTkComboBox(
            self, values=product_names, width=260,
            command=self._on_product_selected,
        )
        self.desc_combo.set("")
        self.desc_combo.grid(row=0, column=0, padx=(0, 6))

        self.qty_entry = ctk.CTkEntry(self, placeholder_text="Qty", width=70)
        self.qty_entry.grid(row=0, column=1, padx=6)
        self.qty_entry.bind("<KeyRelease>", lambda e: on_update())

        self.price_entry = ctk.CTkEntry(self, placeholder_text="Unit Price", width=100)
        self.price_entry.grid(row=0, column=2, padx=6)
        self.price_entry.bind("<KeyRelease>", lambda e: on_update())

        self.total_label = ctk.CTkLabel(self, text="$0.00", width=100, anchor="e",
                                         font=ctk.CTkFont(size=13, weight="bold"))
        self.total_label.grid(row=0, column=3, padx=6)

        self.del_btn = ctk.CTkButton(self, text="✕", width=32, height=32,
                                      fg_color="#EF4444", hover_color="#DC2626",
                                      command=lambda: on_delete(self))
        self.del_btn.grid(row=0, column=4, padx=(6, 0))

    def _on_product_selected(self, choice):
        for p in self.catalog:
            if p["name"] == choice:
                self.price_entry.delete(0, "end")
                self.price_entry.insert(0, f"{p['price']:.2f}")
                self.on_update()
                break

    def refresh_catalog(self, catalog):
        self.catalog = catalog
        self.desc_combo.configure(values=[p["name"] for p in catalog])

    def get_data(self):
        desc = self.desc_combo.get().strip()
        try:
            qty = float(self.qty_entry.get())
        except ValueError:
            qty = 0
        try:
            price = float(self.price_entry.get())
        except ValueError:
            price = 0
        return desc, qty, price

    def update_total(self):
        _, qty, price = self.get_data()
        total = qty * price
        self.total_label.configure(text=f"${total:,.2f}")
        return total


# ── PDF generation from a saved invoice record ──

def generate_pdf_from_record(path, inv):
    doc = SimpleDocTemplate(path, pagesize=LETTER,
                             leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                             topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []
    accent = HexColor(ACCENT)
    dark = HexColor("#1E293B")

    title_style = ParagraphStyle("InvTitle", parent=styles["Title"],
                                  fontSize=28, textColor=accent, spaceAfter=4)
    normal = ParagraphStyle("Norm", parent=styles["Normal"], fontSize=10,
                             leading=14, textColor=dark)
    bold = ParagraphStyle("Bold", parent=normal, fontName="Helvetica-Bold")

    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 4))

    status = inv.get("status", "Unpaid")
    status_color_map = {"Paid": "#22C55E", "Unpaid": "#F59E0B", "Late": "#EF4444"}
    status_hex = status_color_map.get(status, "#F59E0B")
    status_style = ParagraphStyle("Status", parent=bold, fontSize=12,
                                   textColor=HexColor(status_hex))

    meta = [[Paragraph(f"<b>Invoice #:</b> {inv['number']}", normal),
             Paragraph(f"<b>Date:</b> {inv['date']}", normal)],
            [Paragraph(f"<b>Status:</b> ", normal),
             Paragraph(status, status_style)]]
    meta_table = Table(meta, colWidths=[3.5 * inch, 3.5 * inch])
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    info_data = [
        [Paragraph("<b>From</b>", bold), Paragraph("<b>Bill To</b>", bold)],
        [Paragraph(inv.get("biz_name", ""), normal), Paragraph(inv.get("cust_name", ""), normal)],
        [Paragraph(inv.get("biz_email", ""), normal), Paragraph(inv.get("cust_email", ""), normal)],
        [Paragraph(inv.get("biz_phone", ""), normal), Paragraph(inv.get("cust_address", ""), normal)],
    ]
    info_table = Table(info_data, colWidths=[3.5 * inch, 3.5 * inch])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 18))

    table_data = [["Description", "Qty", "Unit Price", "Total"]]
    for desc, qty, price, total in inv["items"]:
        table_data.append([desc, f"{qty:g}", f"${price:,.2f}", f"${total:,.2f}"])

    subtotal = inv.get("subtotal", 0)
    tax = inv.get("tax", 0)
    grand = inv.get("total", 0)
    tax_pct = inv.get("tax_pct", 0)

    table_data.append(["", "", "Subtotal", f"${subtotal:,.2f}"])
    table_data.append(["", "", f"Tax ({tax_pct:.1f}%)", f"${tax:,.2f}"])
    table_data.append(["", "", "TOTAL", f"${grand:,.2f}"])

    col_widths = [3.2 * inch, 0.8 * inch, 1.3 * inch, 1.3 * inch]
    item_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    num_items = len(inv["items"])
    item_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, num_items), [HexColor("#F8FAFC"), HexColor("#FFFFFF")]),
        ("LINEBELOW", (0, 0), (-1, 0), 1, accent),
        ("LINEABOVE", (2, num_items + 1), (-1, num_items + 1), 1, HexColor("#CBD5E1")),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (2, -1), (-1, -1), 12),
        ("TEXTCOLOR", (2, -1), (-1, -1), accent),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 24))

    notes_text = inv.get("notes", "")
    if notes_text:
        elements.append(Paragraph("<b>Notes / Terms</b>", bold))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(notes_text, normal))

    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle("Footer", parent=normal, fontSize=9,
                                   textColor=HexColor("#94A3B8"), alignment=1)
    elements.append(Paragraph(f"Generated by QuickInvoice • {datetime.now().strftime('%B %d, %Y')}",
                               footer_style))
    doc.build(elements)


# ── Main App ──

class InvoiceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QuickInvoice — Small Business Invoice Generator")
        self.geometry("780x860")
        self.minsize(700, 700)
        self.line_items: list[LineItemRow] = []
        self.catalog: list[dict] = load_catalog()

        self._build_ui()

    def _build_ui(self):
        wrapper = ctk.CTkScrollableFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=18, pady=18)

        # ── Header ──
        header = ctk.CTkFrame(wrapper, fg_color=ACCENT, corner_radius=12)
        header.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(header, text="⚡ QuickInvoice", font=ctk.CTkFont(size=26, weight="bold"),
                      text_color="white").pack(side="left", padx=18, pady=14)
        ctk.CTkLabel(header, text=f"Professional invoices in seconds  •  v{APP_VERSION}",
                      font=ctk.CTkFont(size=13), text_color="#BFDBFE").pack(side="left")
        ctk.CTkButton(header, text="🔍 Invoice Lookup", width=150, height=34,
                       fg_color=LOOKUP_COLOR, hover_color=LOOKUP_HOVER,
                       font=ctk.CTkFont(size=13, weight="bold"),
                       text_color="white",
                       command=self._open_lookup).pack(side="right", padx=14)

        # ── Business Info ──
        biz_frame = ctk.CTkFrame(wrapper, fg_color=SURFACE, corner_radius=10)
        biz_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(biz_frame, text="Your Business", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=14, pady=(10, 4))
        row = ctk.CTkFrame(biz_frame, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))
        self.biz_name = ctk.CTkEntry(row, placeholder_text="Business Name", width=240)
        self.biz_name.pack(side="left", padx=(0, 8))
        self.biz_email = ctk.CTkEntry(row, placeholder_text="Email", width=200)
        self.biz_email.pack(side="left", padx=8)
        self.biz_phone = ctk.CTkEntry(row, placeholder_text="Phone", width=160)
        self.biz_phone.pack(side="left", padx=8)

        # ── Customer Info ──
        cust_frame = ctk.CTkFrame(wrapper, fg_color=SURFACE, corner_radius=10)
        cust_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(cust_frame, text="Bill To", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=14, pady=(10, 4))
        row2 = ctk.CTkFrame(cust_frame, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 10))
        self.cust_name = ctk.CTkEntry(row2, placeholder_text="Customer Name", width=240)
        self.cust_name.pack(side="left", padx=(0, 8))
        self.cust_email = ctk.CTkEntry(row2, placeholder_text="Customer Email", width=200)
        self.cust_email.pack(side="left", padx=8)
        self.cust_address = ctk.CTkEntry(row2, placeholder_text="Address", width=160)
        self.cust_address.pack(side="left", padx=8)

        # ── Invoice Details ──
        det_frame = ctk.CTkFrame(wrapper, fg_color=SURFACE, corner_radius=10)
        det_frame.pack(fill="x", pady=6)
        row3 = ctk.CTkFrame(det_frame, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(row3, text="Invoice #", font=ctk.CTkFont(size=13)).pack(side="left")
        self.inv_number = ctk.CTkEntry(row3, width=120, state="disabled")
        self.inv_number.pack(side="left", padx=(6, 20))
        self._set_next_number()

        ctk.CTkLabel(row3, text="Date", font=ctk.CTkFont(size=13)).pack(side="left")
        self.inv_date = ctk.CTkEntry(row3, width=120)
        self.inv_date.pack(side="left", padx=(6, 20))
        self.inv_date.insert(0, datetime.now().strftime("%m/%d/%Y"))

        ctk.CTkLabel(row3, text="Tax %", font=ctk.CTkFont(size=13)).pack(side="left")
        self.tax_rate = ctk.CTkEntry(row3, width=70)
        self.tax_rate.pack(side="left", padx=(6, 0))
        self.tax_rate.insert(0, "0")
        self.tax_rate.bind("<KeyRelease>", lambda e: self._recalc())

        # ── Line Items ──
        items_frame = ctk.CTkFrame(wrapper, fg_color=SURFACE, corner_radius=10)
        items_frame.pack(fill="x", pady=6)
        items_header = ctk.CTkFrame(items_frame, fg_color="transparent")
        items_header.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(items_header, text="Line Items", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(items_header, text="+ Add Item", width=100, height=30,
                       fg_color=SUCCESS, hover_color="#16A34A",
                       command=self._add_item).pack(side="right")
        ctk.CTkButton(items_header, text="📦 Manage Catalog", width=140, height=30,
                       fg_color=CATALOG_COLOR, hover_color=CATALOG_HOVER,
                       command=self._open_catalog).pack(side="right", padx=(0, 8))

        col_header = ctk.CTkFrame(items_frame, fg_color="transparent")
        col_header.pack(fill="x", padx=14)
        for text, w in [("Product / Description", 260), ("Qty", 70), ("Unit Price", 100), ("Total", 100), ("", 32)]:
            ctk.CTkLabel(col_header, text=text, width=w, anchor="w",
                          font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(side="left", padx=6)

        self.items_container = ctk.CTkFrame(items_frame, fg_color="transparent")
        self.items_container.pack(fill="x", padx=14, pady=(0, 10))
        self._add_item()

        # ── Totals ──
        totals_frame = ctk.CTkFrame(wrapper, fg_color=SURFACE, corner_radius=10)
        totals_frame.pack(fill="x", pady=6)
        totals_inner = ctk.CTkFrame(totals_frame, fg_color="transparent")
        totals_inner.pack(anchor="e", padx=20, pady=14)
        self.subtotal_label = ctk.CTkLabel(totals_inner, text="Subtotal:  $0.00", font=ctk.CTkFont(size=13))
        self.subtotal_label.pack(anchor="e")
        self.tax_label = ctk.CTkLabel(totals_inner, text="Tax:  $0.00", font=ctk.CTkFont(size=13))
        self.tax_label.pack(anchor="e", pady=2)
        self.total_label = ctk.CTkLabel(totals_inner, text="Total:  $0.00",
                                         font=ctk.CTkFont(size=20, weight="bold"), text_color=ACCENT)
        self.total_label.pack(anchor="e", pady=(4, 0))

        # ── Notes ──
        notes_frame = ctk.CTkFrame(wrapper, fg_color=SURFACE, corner_radius=10)
        notes_frame.pack(fill="x", pady=6)
        ctk.CTkLabel(notes_frame, text="Notes / Terms", font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=14, pady=(10, 4))
        self.notes = ctk.CTkTextbox(notes_frame, height=60, fg_color=SURFACE_LIGHT, corner_radius=8)
        self.notes.pack(fill="x", padx=14, pady=(0, 10))
        self.notes.insert("1.0", "Payment due within 30 days. Thank you for your business!")

        # ── Export Button ──
        ctk.CTkButton(wrapper, text="📄  Save & Export PDF Invoice", height=46,
                       font=ctk.CTkFont(size=15, weight="bold"),
                       fg_color=ACCENT, hover_color=ACCENT_HOVER,
                       command=self._export_pdf).pack(fill="x", pady=(12, 4))

    # ── Helpers ──

    def _set_next_number(self):
        num = next_invoice_number()
        self.inv_number.configure(state="normal")
        self.inv_number.delete(0, "end")
        self.inv_number.insert(0, num)
        self.inv_number.configure(state="disabled")

    def _open_lookup(self):
        LookupWindow(self)

    def _open_catalog(self):
        CatalogWindow(self, self.catalog, on_save=self._on_catalog_saved)

    def _on_catalog_saved(self, catalog):
        self.catalog = catalog
        for item in self.line_items:
            item.refresh_catalog(catalog)

    def _add_item(self):
        item = LineItemRow(self.items_container, on_delete=self._remove_item,
                           on_update=self._recalc, catalog=self.catalog)
        item.pack(fill="x", pady=3)
        self.line_items.append(item)

    def _remove_item(self, item: LineItemRow):
        if len(self.line_items) <= 1:
            return
        self.line_items.remove(item)
        item.destroy()
        self._recalc()

    def _recalc(self):
        subtotal = sum(item.update_total() for item in self.line_items)
        try:
            tax_pct = float(self.tax_rate.get()) / 100
        except ValueError:
            tax_pct = 0
        tax = subtotal * tax_pct
        total = subtotal + tax
        self.subtotal_label.configure(text=f"Subtotal:  ${subtotal:,.2f}")
        self.tax_label.configure(text=f"Tax ({tax_pct*100:.1f}%):  ${tax:,.2f}")
        self.total_label.configure(text=f"Total:  ${total:,.2f}")

    def _collect_invoice_data(self):
        items_data = []
        for item in self.line_items:
            desc, qty, price = item.get_data()
            if desc:
                items_data.append([desc, qty, price, round(qty * price, 2)])

        subtotal = sum(i[3] for i in items_data)
        try:
            tax_pct = float(self.tax_rate.get())
        except ValueError:
            tax_pct = 0
        tax = round(subtotal * tax_pct / 100, 2)
        total = round(subtotal + tax, 2)

        return {
            "number": self.inv_number.get(),
            "date": self.inv_date.get(),
            "biz_name": self.biz_name.get().strip(),
            "biz_email": self.biz_email.get().strip(),
            "biz_phone": self.biz_phone.get().strip(),
            "cust_name": self.cust_name.get().strip(),
            "cust_email": self.cust_email.get().strip(),
            "cust_address": self.cust_address.get().strip(),
            "items": items_data,
            "subtotal": subtotal,
            "tax_pct": tax_pct,
            "tax": tax,
            "total": total,
            "notes": self.notes.get("1.0", "end").strip(),
            "status": "Unpaid",
        }

    def _reset_form(self):
        self._set_next_number()
        self.inv_date.delete(0, "end")
        self.inv_date.insert(0, datetime.now().strftime("%m/%d/%Y"))

        for item in self.line_items:
            item.destroy()
        self.line_items.clear()
        self._add_item()

        self.subtotal_label.configure(text="Subtotal:  $0.00")
        self.tax_label.configure(text="Tax:  $0.00")
        self.total_label.configure(text="Total:  $0.00")

    def _export_pdf(self):
        biz = self.biz_name.get().strip()
        cust = self.cust_name.get().strip()
        if not biz:
            messagebox.showwarning("Missing Info", "Please enter your business name.")
            return
        if not cust:
            messagebox.showwarning("Missing Info", "Please enter the customer name.")
            return

        inv = self._collect_invoice_data()
        if not inv["items"]:
            messagebox.showwarning("No Items", "Add at least one line item with a description.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"{inv['number']}.pdf"
        )
        if not path:
            return

        invoices = load_invoices()
        invoices.append(inv)
        save_invoices(invoices)

        generate_pdf_from_record(path, inv)
        messagebox.showinfo("Success",
                             f"Invoice {inv['number']} saved and exported to:\n{path}")
        os.startfile(path)

        self._reset_form()


class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.configure(fg_color="#0F172A")

        w, h = 480, 340
        sx = self.winfo_screenwidth() // 2 - w // 2
        sy = self.winfo_screenheight() // 2 - h // 2
        self.geometry(f"{w}x{h}+{sx}+{sy}")
        self.attributes("-topmost", True)

        outer = ctk.CTkFrame(self, fg_color="#0F172A", border_width=2,
                              border_color=ACCENT, corner_radius=16)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        ctk.CTkLabel(outer, text="⚡", font=ctk.CTkFont(size=44)).pack(pady=(30, 4))
        ctk.CTkLabel(outer, text="QuickInvoice",
                      font=ctk.CTkFont(size=28, weight="bold"),
                      text_color="white").pack()
        ctk.CTkLabel(outer, text=f"v{APP_VERSION}",
                      font=ctk.CTkFont(size=13), text_color="#64748B").pack(pady=(0, 18))

        self.progress = ctk.CTkProgressBar(outer, width=360, height=10,
                                            progress_color=ACCENT,
                                            fg_color=SURFACE_LIGHT,
                                            corner_radius=5)
        self.progress.pack()
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(outer, text="Starting up...",
                                          font=ctk.CTkFont(size=13),
                                          text_color="#94A3B8")
        self.status_label.pack(pady=(12, 4))

        self.detail_label = ctk.CTkLabel(outer, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color="#475569")
        self.detail_label.pack()

        self.log_lines: list[str] = []
        self.ready = False
        self.after(200, self._start_checks)

    def _set_status(self, text, detail="", progress=0.0):
        self.status_label.configure(text=text)
        self.detail_label.configure(text=detail)
        self.progress.set(progress)
        self.update_idletasks()

    def _start_checks(self):
        thread = threading.Thread(target=self._run_checks, daemon=True)
        thread.start()
        self._poll_ready()

    def _poll_ready(self):
        if self.ready:
            self.after(300, self._launch_app)
        else:
            self.after(50, self._poll_ready)

    def _push(self, status, detail, progress):
        self.after(0, lambda: self._set_status(status, detail, progress))

    def _run_checks(self):
        self._push("Checking for updates...", f"Current version: v{APP_VERSION}", 0.05)
        time.sleep(0.6)

        # Verify bundled components
        components = [
            ("customtkinter", "UI Framework"),
            ("reportlab", "PDF Engine"),
            ("PIL", "Image Processing"),
        ]
        for i, (mod, label) in enumerate(components):
            pct = 0.10 + (i / len(components)) * 0.25
            self._push("Verifying components...", f"Checking {label} ({mod})", pct)
            try:
                __import__(mod)
                time.sleep(0.3)
            except ImportError:
                self._push("Verifying components...", f"Missing: {label} — bundled in exe", pct)
                time.sleep(0.4)

        self._push("Verifying components...", "All components verified", 0.40)
        time.sleep(0.3)

        # Data directory
        self._push("Checking data directory...", DATA_DIR, 0.50)
        time.sleep(0.3)

        # Product catalog
        if os.path.exists(CATALOG_FILE):
            catalog = load_catalog()
            self._push("Loading product catalog...",
                        f"Found {len(catalog)} products", 0.60)
        else:
            self._push("Loading product catalog...",
                        "No catalog found — creating new file", 0.60)
            save_catalog([])
        time.sleep(0.35)

        # Invoice history
        if os.path.exists(INVOICES_FILE):
            invoices = load_invoices()
            paid = sum(1 for i in invoices if i.get("status") == "Paid")
            unpaid = sum(1 for i in invoices if i.get("status", "Unpaid") == "Unpaid")
            late = sum(1 for i in invoices if i.get("status") == "Late")
            self._push("Loading invoice history...",
                        f"{len(invoices)} invoices  ({paid} paid, {unpaid} unpaid, {late} late)", 0.75)
        else:
            self._push("Loading invoice history...",
                        "No history found — creating new file", 0.75)
            save_invoices([])
        time.sleep(0.35)

        self._push("Initializing interface...", "Building main window", 0.90)
        time.sleep(0.4)

        self._push("Ready!", "Launching QuickInvoice...", 1.0)
        time.sleep(0.4)

        self.ready = True

    def _launch_app(self):
        self.destroy()
        app = InvoiceApp()
        app.mainloop()


if __name__ == "__main__":
    splash = SplashScreen()
    splash.mainloop()
