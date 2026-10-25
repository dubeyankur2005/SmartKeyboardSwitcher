# Smart Keyboard Switcher

A small Windows desktop prototype for forwarding keyboard events from a host laptop (A) to one authenticated client laptop (B) on a trusted local network. The host uses a Windows low-level keyboard hook to suppress ordinary local input while Remote is selected. F1 selects Local, F2 selects Remote, and F12 returns to Local as an emergency stop.

## Architecture

```text
Laptop A keyboard -> low-level hook -> LOCAL: Windows app
 NDJSON/TCP + pairing token -> Laptop B SendInput
```

The client accepts one authenticated TCP session. Each message is a bounded JSON object terminated by a newline. Only allowlisted virtual keys and down/up events are accepted. The programs do not record or log key values or typed text.

## Prerequisites and install

Use Windows 10/11 and Python 3.11 or newer. Python 3.14.4 is compatible with the standard-library implementation. The current code needs no third-party runtime package; pytest is used for tests.

From this project folder, in PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Pair and run

1. Connect both laptops to the same trusted Wi-Fi or a private hotspot. Do not forward the listener port from a router or expose it to the internet.
2. On Laptop B, launch the client:

   ```powershell
   python -m client.main
   ```

3. Keep the generated pairing token private. Copy it into the host app over a trusted channel. A new token is generated each launch.
4. On Laptop B click **Start server**. If Windows Firewall asks, allow Python only on the **Private** network profile. For a manual narrow rule, run elevated PowerShell and replace the executable path with the one shown by `python`:

   ```powershell
   New-NetFirewallRule -DisplayName "Smart Keyboard Switcher (Private LAN)" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -Profile Private -Program "C:\Path\To\Python\python.exe"
   ```

   Remove it when no longer needed with `Remove-NetFirewallRule -DisplayName "Smart Keyboard Switcher (Private LAN)"`.
5. Find Laptop B's IPv4 address by running `ipconfig` on B and reading the IPv4 Address under the active Wi-Fi adapter. Avoid VPN and public network addresses.
6. On Laptop A launch the host:

   ```powershell
   python -m host.main
   ```

7. Enter B's IPv4 address, port `8765`, and the pairing token. Click **Connect**, then **Start keyboard control**. The hook starts in Local mode. Press F2 to switch to Remote and type in B's active application.

## Controls and safe stop

- **F1** selects Local. Input is passed to Laptop A.
- **F2** selects Remote, only while connected. Laptop A suppresses regular key input and forwards events to B.
- **F12** emergency stop: switch to Local and release held remote keys. It does not stop the hook; press F1 to remain local, F2 to resume, or **Stop keyboard control** to remove the hook. Disconnecting or closing also stops forwarding.
- The client shows a red active indicator while receiving key events. Use **Stop server** to disconnect and release keys on B.

## Test the connection

On B start the server and note the Connected status on A. Start host keyboard control, select F2, then type in a harmless text editor on B. Check that the characters appear on B and do not appear in the focused app on A. Press F1 and confirm local typing resumes. Test Shift/Ctrl/Alt combinations carefully, and press F12 during a held modifier to confirm release. Then test disconnecting B while remote mode is active: A should return to Local and B should release held keys.

## Tests

```powershell
python -m pytest -q
```

The automated tests cover message framing and validation, authentication comparison, and local mode transition cleanup. They do not emulate Windows hook suppression or SendInput behavior.

## Limitations and safety

- This workspace is Windows 10 with Python 3.14.4, but the two-laptop end-to-end test has not been run. Do not treat real remote typing as verified until manually tested on both laptops.
- Windows low-level hooks and `SendInput` are subject to desktop/session permissions. This does not bypass the secure desktop, UAC prompts, lock screen, or applications that reject synthetic input. Run both apps at the same integrity level as the target application.
- The listener binds to all local interfaces; restrict the Windows Firewall rule to the Private profile and trusted subnet, keep the random pairing token secret, and stop the server after use. The token authenticates but traffic is not encrypted. Use only a trusted network.
- Keyboard layouts vary. Keys are represented as virtual-key names, not text, so a different layout may produce different characters. Some international or unusual keys are unsupported.
- F1, F2 and F12 are reserved globally while the hook runs. If the host loses connection, the host returns to Local. The client releases held keys at session end. Do not run multiple host instances.
- Logs contain operational diagnostics only; key values and typed characters are never logged.
