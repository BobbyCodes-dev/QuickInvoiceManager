# QuickInvoice

A simple, professional invoice generator built for small businesses. Create, track, and manage invoices from a single desktop app — no account needed, no cloud, fully offline.

Created by [bobbycodes.dev](https://www.bobbycodes.dev)

---

## Features

- **Create Invoices** — Fill in your business info, customer details, and line items. Auto-calculates subtotals, tax, and totals.
- **Product Catalog** — Save your products and prices. Select from a dropdown or type custom items.
- **PDF Export** — Generate professional, styled PDF invoices with one click.
- **Sequential Invoice Numbers** — Auto-incrementing invoice numbers (INV-0001, INV-0002, ...) that stay in order.
- **Invoice Lookup** — Separate window to search and browse all past invoices by number, customer, or date.
- **Payment Status Tracking** — Mark invoices as **Paid**, **Unpaid**, or **Late** with color-coded badges.
- **Payment Details** — When marking paid, record how it was paid (check, card, cash, etc.).
- **Activity Log** — Add unlimited notes to any invoice (sent reminder email, called customer, partial payment received, etc.).
- **Filter by Status** — One-click filter tabs in the lookup window: All / Paid / Unpaid / Late.
- **Splash Screen** — Loading screen on startup that verifies components and loads your data.
- **Secure Data Storage** — All data stored in `%APPDATA%\QuickInvoice`, not next to the exe.
- **Dark Mode UI** — Modern dark theme built with CustomTkinter.

## Screenshot

> *Launch the app and see for yourself!*

## Getting Started

### Option 1: Run the .exe (no install needed)

Download `QuickInvoice.exe` from [Releases](../../releases) and double-click it. That's it — everything is bundled.

### Option 2: Run from source

**Requirements:** Python 3.10+

```bash
git clone https://github.com/YOUR_USERNAME/QuickInvoice.git
cd QuickInvoice
pip install -r requirements.txt
python invoice_app.py
```

### Build the .exe yourself

```bash
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --name "QuickInvoice" --collect-all customtkinter invoice_app.py
```

The exe will be in the `dist/` folder.

## Project Structure

```
InvoiceGenerator/
├── invoice_app.py          # Full application source
├── requirements.txt        # Python dependencies
├── QuickInvoice_Setup.bat  # Dev launcher (auto-installs deps & rebuilds)
├── README.md
└── dist/
    └── QuickInvoice.exe    # Standalone executable
```

## Data Storage

All user data is stored in:

```
%APPDATA%\QuickInvoice\
├── invoices.json           # Invoice history & activity logs
└── product_catalog.json    # Saved products & prices
```

## Tech Stack

- **Python 3.12**
- **CustomTkinter** — Modern desktop UI
- **ReportLab** — PDF generation
- **PyInstaller** — Standalone .exe packaging

## License

Free to use. All I ask is a star on GitHub and credit if recoded. Thank you!

## Author

**bobbycodes.dev** — [https://www.bobbycodes.dev](https://www.bobbycodes.dev)
