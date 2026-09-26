# 🏎️ Hand Steering Controller

Control driving & racing games using real-time AI hand gestures via webcam! Built with **MediaPipe**, **OpenCV**, and direct hardware scan code emulation.

---

## ⚡ 1-Line Instant Start (For Anyone on Terminal)

Any user on Windows can install, set up, and start playing immediately with just **one line** in PowerShell:

```powershell
irm https://raw.githubusercontent.com/Sabir7869/Hand-Steering-Controller/main/install.ps1 | iex
```

> **Note**: This automatically creates an isolated environment, installs all required packages, registers `hand-steer` to the system, and launches the game right away!

---

## 📦 Method 2: Standard Python / CLI Installation

If you prefer installing via `pip`:

```bash
# 1. Install directly from GitHub
pip install git+https://github.com/Sabir7869/Hand-Steering-Controller.git

# 2. Run from ANY terminal
hand-steer
```

*(Or test your camera with `hand-diag`)*

---

## 🛠️ Method 3: Manual Clone & Run

```bash
git clone https://github.com/Sabir7869/Hand-Steering-Controller.git
cd Hand-Steering-Controller
pip install -r requirements.txt
python main.py
```

*(On Windows, you can also just double-click `run.bat`)*

---

## 🎮 How to Play / Controls

| Gesture | Action | In-Game Control |
|---|---|---|
| **Two hands holding steering wheel** | Tilt left / right | Steer Left (`A`) / Steer Right (`D`) |
| **Open Palms** | Both hands open | Accelerate Forward (`W`) |
| **Fist (Closed Hand)** | Any hand in fist | Brake / Stop (`S` / Key Release) |
| **ESC key** | Exit | Closes controller & camera |

---

## 📄 License
MIT License
