# Quick Peek

Quick Peek is a white-theme internal web app for fast batch preview of **STEP/STP**, **PDF**, **DXF**, and **OBJ** files.

It supports:

- Login page
- One-format-at-a-time toggle: STEP, PDF, DXF, or OBJ
- Paste many codes at once
- Browse/select a working folder from the web UI
- Save and load named folder presets per user
- Search pattern like `*code-number*.stp`, `*code-number*.pdf`, `*code-number*.dxf`, or `*code-number*.obj`
- Preview grid
- Bigger preview modal
- Crisp vector pan/zoom for DXF and pan/zoom for STEP placeholder
- Rotate/pan/zoom for OBJ directly and for STEP when a GLB preview is generated
- Admin user management
- Role/permission assignment
- Usage dashboard for access, preview counts, and estimated time savings
- Minimal professional white UI
- `supergraphic.svg` thin top line

## Folder structure

```text
quick-peek/
  backend/       FastAPI backend + SQLite + file indexer
  frontend/      React/Vite frontend
  tools/         optional converter helper scripts
  scripts/       dev startup scripts
```

## Quick start on Windows

Install prerequisites:

- Python 3.10+
- Node.js 20+

Then run:

```bat
scripts\run_dev_windows.bat
```

Open:

```text
http://127.0.0.1:5173
```

Default login:

```text
username: admin
password: admin123
```

Change the admin password after first run.

## Manual start

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Working folders

On the **Quick Peek** page, users can:

1. Browse folders on the machine/server where the backend is running.
2. Select one folder as the current working folder.
3. Save the folder as a named preset.
4. Load the saved folder later without retyping the path.

When a working folder is selected, Quick Peek searches only inside that folder. If the working folder is empty, it uses the backend default roots.

Important: because this is a web app, the folder browser shows folders from the backend machine, not from the browser computer unless they are the same machine or the folder is available as a network path.

## Configure default file roots

By default, the app indexes sample files in:

```text
backend/data/files
```

To point to your CAD folders, copy:

```text
backend/.env.example -> backend/.env
```

Then edit:

```text
QUICKPEEK_FILE_ROOTS=C:\local\aventics\task,\\server\shared\cad
```

Use comma or semicolon to separate multiple roots.

After changing roots, go to **Admin → Reindex files**.

## Permissions

Available permissions:

```text
use_quick_peek
view_step
view_pdf
view_dxf
view_obj
view_dashboard
manage_users
download_files
```

Admin users can access everything.

## STEP preview note

Three.js can load mesh formats such as OBJ/GLB, but STEP/STP is CAD B-rep data and should be processed by a CAD kernel before display. This app is designed to use:

```text
STEP / STP -> server converter -> cached GLB -> Three.js viewer
```

Out of the box, STEP files are found and shown with a placeholder preview. To enable real 3D browser preview, set:

```text
QUICKPEEK_STEP_CONVERTER_CMD="C:\path\to\step-to-glb.exe" "{input}" "{output}"
```

The command must create the GLB file at `{output}`.

You can use an OCCT, FreeCAD, CAD Assistant, or commercial converter depending on what works best in your environment. A FreeCAD helper skeleton is included in `tools/freecad_step_to_glb.py`, but FreeCAD export support varies by build.

## Dashboard savings formula

Default estimate:

```text
Manual open/check: 45 seconds per file
Quick Peek check: 8 seconds per file
Saving: 37 seconds per found file
```

Edit in `backend/.env`:

```text
QUICKPEEK_MANUAL_SECONDS_PER_FILE=45
QUICKPEEK_APP_SECONDS_PER_FILE=8
```

## Production notes

Before using this with real company files:

1. Change `QUICKPEEK_SECRET_KEY`.
2. Change default admin password.
3. Run behind internal network/VPN only.
4. Use HTTPS if deployed beyond localhost.
5. Move from SQLite to PostgreSQL if many users will use it at the same time.
6. Add a hardened STEP conversion service/queue for large CAD files.

## Current MVP limitations

- PDF preview uses browser PDF rendering.
- DXF renderer supports common simple entities: LINE, CIRCLE, ARC, LWPOLYLINE/POLYLINE. The large view uses inline SVG viewBox zoom so lines stay crisp when zooming.
- Folder browsing is server-side. For shared team deployment, use network paths that the backend service account can read.
- STEP needs a configured converter or a future OCCT/WASM importer to show real 3D geometry. OBJ is loaded directly in the browser.
- Native Creo files are intentionally not supported in this MVP. Export Creo to STEP first.

### PDF preview behavior

PDF previews now use an inline preview endpoint. Clicking the maximize button opens the PDF inside the Quick Peek modal instead of downloading it. The Download button in the modal is the only action that intentionally downloads the original file.


## Use from another computer on the same network

Run:

```bat
scripts\run_lan_windows.bat
```

The script prints your host PC URL, for example:

```text
http://192.168.2.230:5173
```

Other users on the same Wi-Fi/LAN should open that URL in their browser.

If it does not open, allow these ports in Windows Firewall on the host PC:

- TCP 5173 for the web UI
- TCP 8000 for the API

The folder browser and file search run on the backend PC. So users can only browse folders/drives that the backend PC can access.
