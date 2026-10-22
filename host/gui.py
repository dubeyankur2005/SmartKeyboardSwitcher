import logging
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from host.keyboard_controller import KeyboardController
from host.network_client import NetworkClient

logging.basicConfig(filename="host.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class HostApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Keyboard Switcher — Host")
        self.geometry("520x500"); self.minsize(480, 460)
        self.events = queue.Queue()
        self.network = NetworkClient(self._network_event)
        self.controller = KeyboardController(self._send_key, self._switch_from_hook)
        self.mode = "LOCAL"
        self._build(); self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        root = ttk.Frame(self, padding=20); root.pack(fill="both", expand=True)
        ttk.Label(root, text="Smart Keyboard Switcher", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(root, text="Host laptop • Laptop A", foreground="#526174").pack(anchor="w", pady=(0, 16))
        form = ttk.Frame(root); form.pack(fill="x")
        self.address = tk.StringVar(value=""); self.port = tk.StringVar(value="8765"); self.token = tk.StringVar()
        for row, (label, var, secret) in enumerate((("Laptop B IPv4",self.address,False),("Port",self.port,False),("Pairing token",self.token,True))):
            ttk.Label(form, text=label).grid(row=row,column=0,sticky="w",pady=5)
            ttk.Entry(form,textvariable=var,show="•" if secret else "").grid(row=row,column=1,sticky="ew",padx=(12,0),pady=5)
        form.columnconfigure(1,weight=1)
        buttons=ttk.Frame(root); buttons.pack(fill="x",pady=12)
        ttk.Button(buttons,text="Connect",command=self.connect).pack(side="left")
        ttk.Button(buttons,text="Disconnect",command=self.disconnect).pack(side="left",padx=8)
        self.start_btn=ttk.Button(buttons,text="Start keyboard control",command=self.start_control); self.start_btn.pack(side="right")
        ttk.Button(root,text="Stop keyboard control",command=self.stop_control).pack(anchor="e")
        ttk.Separator(root).pack(fill="x",pady=14)
        self.mode_label=ttk.Label(root,text="LOCAL — Laptop A",font=("Segoe UI",14,"bold")); self.mode_label.pack(anchor="w")
        self.status=ttk.Label(root,text="Disconnected"); self.status.pack(anchor="w",pady=(4,10))
        self.warning=ttk.Label(root,text="",foreground="#a32626",wraplength=460); self.warning.pack(anchor="w")
        ttk.Label(root,text="F1: Local  •  F2: Remote  •  F12: Emergency stop\nF12 stops forwarding; press F1 to remain local, or F2 to resume remote mode.",wraplength=460).pack(anchor="w",pady=18)
        ttk.Label(root,text="Start explicitly before using the keyboard hook. Control keys are reserved.",foreground="#526174",wraplength=460).pack(anchor="w")

    def _network_event(self, status, detail): self.events.put(("network",status,detail))
    def connect(self):
        address,port,token=self.address.get().strip(),self.port.get().strip(),self.token.get()
        if not address or not token:
            messagebox.showerror("Missing details","Enter Laptop B's IP address and pairing token."); return
        self.status.config(text="Connecting…")
        import threading
        def run():
            try: self.network.connect(address,int(port),token)
            except Exception as exc: self._network_event("Error",str(exc))
        threading.Thread(target=run,daemon=True).start()

    def disconnect(self):
        self.stop_control(); self.network.disconnect(); self.status.config(text="Disconnected")

    def start_control(self):
        try:
            self.controller.start(); self.status.config(text="Hook active; LOCAL mode")
        except Exception as exc: messagebox.showerror("Could not start keyboard control",str(exc))

    def stop_control(self):
        self.controller.stop(); self.mode="LOCAL"; self._paint_mode()

    def _send_key(self, action,key):
        try: self.network.send({"type":"key","action":action,"key":key})
        except Exception as exc:
            # Stop suppressing local input immediately if forwarding fails.
            self.network.disconnect()
            self.controller.set_mode("LOCAL")
            self.events.put(("failure",str(exc)))

    def _set_mode(self, mode):
        if mode == "REMOTE" and self.network.sock is None:
            self.status.config(text="Error: connect to Laptop B first"); mode="LOCAL"
        self.mode=mode; self.controller.set_mode(mode); self._paint_mode()

    def _switch_from_hook(self, key):
        # Apply the safety transition on the hook thread so F12 stops forwarding
        # immediately; only widget updates are deferred to Tk's main thread.
        mode = {"F1": "LOCAL", "F2": "REMOTE", "F12": "LOCAL"}[key]
        blocked = mode == "REMOTE" and self.network.sock is None
        if blocked:
            mode = "LOCAL"
        self.controller.set_mode(mode)
        if blocked:
            status = "Remote mode not selected; connect and authenticate the Client first"
        elif mode == "REMOTE":
            status = "Remote mode selected; Client connected; waiting for injection confirmation"
        else:
            status = "Local mode selected; forwarding stopped"
        self.events.put(("status", status))
        self.events.put(("mode", mode))

    def _paint_mode(self):
        self.mode_label.config(text=f"{self.mode} — {'Laptop A' if self.mode=='LOCAL' else 'Laptop B'}")
        self.warning.config(text="REMOTE MODE SELECTED: local physical input is suppressed. Check the status below for Client injection confirmation." if self.mode=="REMOTE" else "")

    def _poll(self):
        while True:
            try: item=self.events.get_nowait()
            except queue.Empty: break
            if item[0]=="network":
                self.status.config(text=f"{item[1]} — {item[2]}")
                if item[1] in ("Disconnected","Error","Injection error"): self._set_mode("LOCAL")
            elif item[0]=="mode": self.mode=item[1]; self._paint_mode()
            elif item[0]=="status": self.status.config(text=item[1])
            elif item[0]=="failure":
                self.status.config(text=f"Error: {item[1]}"); self._set_mode("LOCAL")
        self.after(100,self._poll)

    def close(self):
        self.stop_control(); self.network.disconnect(); self.destroy()
