::: {align="center"}
# Smart Keyboard Switcher

### Control two Windows laptops using one keyboard

A Python-based keyboard-sharing application that lets you switch
keyboard input between a **Host laptop (Laptop A)** and a **Client
laptop (Laptop B)** using keyboard shortcuts.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows&logoColor=white)
![Status](https://img.shields.io/badge/Project-Version%201-orange)
![License](https://img.shields.io/badge/License-Add%20your%20license-lightgrey)
:::

------------------------------------------------------------------------

## Table of contents

-   [Overview](#overview)
-   [Features](#features)
-   [How it works](#how-it-works)
-   [Keyboard shortcuts](#keyboard-shortcuts)
-   [Requirements](#requirements)
-   [Installation](#installation)
-   [Run on two laptops](#run-on-two-laptops)
-   [Test the application](#test-the-application)
-   [Troubleshooting](#troubleshooting)
-   [Security notes](#security-notes)
-   [Project structure](#project-structure)
-   [Future improvements](#future-improvements)

## Overview

**Smart Keyboard Switcher** is a Windows desktop project built with
Python. It is designed to forward keyboard input from one computer to
another over a local network, allowing the user to choose which laptop
receives keyboard input.

-   **Laptop A --- Host:** The laptop with the physical keyboard and the
    Host application.
-   **Laptop B --- Client:** The second laptop running the Client
    application that receives forwarded keyboard events.

> **Important:** Both computers must be powered on, connected to a
> network that allows device-to-device communication, and running the
> appropriate application. A successful TCP connection alone does not
> prove keyboard injection is working; complete the two-laptop test
> described below.

## Features

-   Switch between local and remote input with keyboard shortcuts.
-   Client/Host communication over TCP on a configurable port (the
    examples below use `8765`).
-   Pairing-token check, when enabled by the project's configuration.
-   Emergency-stop shortcut intended to return to local mode and release
    held remote keys.
-   Separate Host and Client graphical interfaces built with Tkinter.
-   Automated tests with `pytest`.

Features and security behavior depend on the current code and
configuration in your checked-out version.

## How it works

![Smart Keyboard Switcher architecture](assets/architecture.svg)

1.  The Host runs on Laptop A.
2.  The Client listens for a connection on Laptop B.
3.  The Host connects to Laptop B using its reachable IPv4 address and
    the configured port.
4.  When remote mode is selected, the Host forwards keyboard events to
    the Client.
5.  The Client attempts to inject the received keyboard events on Laptop
    B.

## Keyboard shortcuts

  -----------------------------------------------------------------------
  Shortcut                            Intended behavior
  ----------------------------------- -----------------------------------
  `F1`                                **Local mode** --- use Laptop A
                                      locally and stop remote forwarding.

  `F2`                                **Remote mode** --- forward
                                      keyboard input to Laptop B.

  `F12`                               **Emergency stop** --- stop
                                      forwarding, return to local mode,
                                      and attempt to release held remote
                                      keys.
  -----------------------------------------------------------------------

The GUI indicates the selected mode and connection/injection status. If
the status reports an error or timeout, stop and troubleshoot the
connection before using keyboard control.

## Requirements

-   Two Windows laptops for the real end-to-end test.
-   Python installed on both laptops. Use a version supported by this
    repository.
-   Git, if cloning from GitHub.
-   Both laptops connected to the same trusted Wi-Fi/LAN/hotspot, with
    device-to-device communication permitted.
-   The same project version on both laptops.
-   TCP port `8765` available, unless you configure another port.
-   Matching Host/Client settings, including the pairing token if
    required.

## Installation

### 1. Install Python and Git

Check that they are available in PowerShell:

``` powershell
python --version
git --version
```

If either command is not recognized, install the missing program first.
On Windows, ensure Python includes **Tcl/Tk** support because the
graphical interface uses Tkinter.

### 2. Clone the repository

Replace the URL below with the actual URL of this GitHub repository:

``` powershell
git clone https://github.com/YOUR_USERNAME/SmartKeyboardSwitcher.git
cd SmartKeyboardSwitcher
```

Do not copy the example URL unchanged. Use your real repository URL.

### 3. Create and activate a virtual environment

Run from the repository root on **each laptop**:

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the environment's Python
executable directly in the commands below instead of changing
system-wide execution policy.

### 4. Install dependencies

``` powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If dependency installation fails, check the error and the repository's
supported Python version before proceeding.

### 5. Run the automated tests

``` powershell
python -m pytest -q
```

Resolve any failing tests before testing live keyboard input. Automated
tests do not replace the real two-laptop test.

## Run on two laptops

### Step 1 --- Connect both laptops to a trusted network

Connect Laptop A and Laptop B to the same trusted Wi-Fi network or
hotspot. Some guest Wi-Fi and hotspot configurations isolate connected
devices and prevent them from communicating.

### Step 2 --- Find Laptop B's IPv4 address

On **Laptop B**, open PowerShell and run:

``` powershell
ipconfig
```

Find the IPv4 address under the active Wi-Fi adapter. For example,
`192.168.1.105` is only an example; use the address shown on your
laptop.

Do **not** use `127.0.0.1` in Laptop A's Host configuration. That
address refers to Laptop A itself.

### Step 3 --- Start the Client on Laptop B

Open PowerShell in the cloned project directory:

``` powershell
cd path\to\SmartKeyboardSwitcher
.\.venv\Scripts\python.exe -m client.main
```

Keep the Client application running. If it reports a startup error,
resolve that error before continuing.

### Step 4 --- Start the Host on Laptop A

On Laptop A, open another PowerShell terminal in the cloned project
directory:

``` powershell
cd path\to\SmartKeyboardSwitcher
.\.venv\Scripts\python.exe -m host.main
```

Keep the Host application running.

### Step 5 --- Configure the Host

In the Host window, enter:

-   **Laptop B IPv4:** the actual IPv4 address found on Laptop B.
-   **Port:** `8765`, if that is the port configured for the Client.
-   **Pairing token:** the token expected by both applications, if token
    authentication is enabled.

Click **Connect** and wait for a successful connection status. Do not
assume a connection succeeded just because the button was clicked.

### Step 6 --- Check network reachability if it times out

On Laptop B, check whether a process is listening on port `8765`:

``` powershell
netstat -ano | findstr :8765
```

On Laptop A, test the connection (replace the example address with
Laptop B's actual IPv4 address):

``` powershell
Test-NetConnection -ComputerName 192.168.1.105 -Port 8765
```

-   `TcpTestSucceeded : True` means the TCP port is reachable.
-   `TcpTestSucceeded : False` means you should check the IP address,
    Client listener, network isolation, port configuration, and
    firewall.

If required, create a narrowly scoped inbound Windows Firewall rule for
the configured TCP port on the **Private** profile only, and only on a
trusted network. Do not disable the firewall or expose the service to
public networks.

### Step 7 --- Start keyboard control and test

Use Notepad on both computers:

1.  On Laptop A, open Notepad and press `F1`. Type a harmless test
    message and confirm it appears on Laptop A.
2.  On Laptop B, open Notepad.
3.  On Laptop A, press `F2` and type a different harmless test message.
4.  Confirm the text appears in Laptop B's Notepad.
5.  Press `F1` on Laptop A and type again. Confirm local input works.
6.  Test `F12` and confirm remote forwarding stops and the Host returns
    to local mode.
7.  If the Client GUI reports injection errors, stop testing and inspect
    the error before continuing.

**Note:** Keep the intended destination application's window focused on
each laptop. Do not type passwords, private messages, or other sensitive
information during testing.

## Troubleshooting

### Host shows `Error — timed out`

1.  Confirm the Client app is running on Laptop B.
2.  Re-run `ipconfig` on Laptop B and verify the Host's IP field.
3.  Confirm both apps use the same port.
4.  Run `netstat -ano | findstr :8765` on Laptop B.
5.  Run `Test-NetConnection -ComputerName CLIENT_IP -Port 8765` on
    Laptop A.
6.  Check whether the Wi-Fi/hotspot isolates devices.
7.  Check Windows Firewall for a narrowly scoped Private-network inbound
    rule.

Replace `CLIENT_IP` with Laptop B's actual address.

### Host connects but keyboard events do not appear on Laptop B

-   Confirm the GUI says remote mode is active.
-   Check the Client's received-event and injection status.
-   Ensure Notepad is focused on Laptop B.
-   Confirm the Host and Client versions/configuration match.
-   Stop keyboard control and return to local mode before further
    troubleshooting.

### `Can't find a usable init.tcl` / Tkinter error

The Python installation may be missing Tcl/Tk files. Repair or modify
the Python installation and ensure **Tcl/Tk and IDLE** is installed.
Then verify:

``` powershell
python -m tkinter
```

A small Tkinter test window should open.

### `python` or the virtual environment is not found

Run commands from the repository root and check:

``` powershell
python --version
Test-Path .\.venv\Scripts\python.exe
```

If the virtual environment does not exist, create it and install
dependencies again as described above.

### Tests fail

Run:

``` powershell
python -m pytest -q
```

Read the first failing test and traceback. Do not treat a passing test
suite as proof of successful real keyboard forwarding.

## Security notes

-   Use this project only on computers and networks you own or are
    authorized to use.
-   Use a trusted private network.
-   A pairing token is not encryption. Do not assume keyboard traffic is
    encrypted unless the implementation explicitly provides and verifies
    transport encryption.
-   Do not expose the listening port to the public internet.
-   Avoid entering passwords or sensitive data while testing.
-   Use the emergency stop and verify that held keys are released when a
    session is interrupted.
-   Stop the Host/Client applications when finished.

## Project structure

The following is the expected high-level structure; your repository may
contain additional files:

``` text
SmartKeyboardSwitcher/
├── client/
│   ├── gui.py
│   ├── keyboard_injector.py
│   ├── main.py
│   └── network_server.py
├── host/
│   ├── gui.py
│   ├── keyboard_controller.py
│   ├── main.py
│   └── network_client.py
├── shared/
│   ├── protocol.py
│   └── security.py
├── tests/
├── requirements.txt
└── README.md
```

## Future improvements

-   Camera-based face detection to assist laptop selection.
-   Head-direction-based switching with manual hotkeys as a fallback.
-   Improved reconnection and connection-status handling.
-   Additional integration tests and clearer error reporting.

## Screenshots

Add screenshots from your **current working build** to a `docs/images/`
directory and link them here. Suggested screenshots:

-   `docs/images/host-window.png` --- Host GUI in local mode.
-   `docs/images/client-window.png` --- Client GUI listening or
    connected.
-   `docs/images/remote-mode.png` --- successful remote mode and
    injection status.
-   `docs/images/two-laptop-demo.png` --- both laptops during a
    successful test.

Example Markdown:

``` markdown
![Host window](docs/images/host-window.png)
```

Do not use a timeout/error screenshot as the primary success screenshot.
Capture the actual working state with any pairing token hidden.

------------------------------------------------------------------------

::: {align="center"}
**Smart Keyboard Switcher --- Version 1**

Built with Python • Tkinter • TCP sockets • pytest
:::
