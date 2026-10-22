import logging
import queue
import secrets
import tkinter as tk
from tkinter import ttk, messagebox
from client.keyboard_injector import KeyboardInjector
from client.network_server import NetworkServer

logging.basicConfig(filename="client.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class ClientApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Smart Keyboard Switcher — Client"); self.geometry("480x370"); self.minsize(440,340)
        self.events=queue.Queue(); self.injector=KeyboardInjector(); self.server=None
        self.received_count=0; self.injected_count=0
        self._build(); self.after(100,self._poll); self.protocol("WM_DELETE_WINDOW",self.close)

    def _build(self):
        root=ttk.Frame(self,padding=20); root.pack(fill="both",expand=True)
        ttk.Label(root,text="Smart Keyboard Switcher",font=("Segoe UI",18,"bold")).pack(anchor="w")
        ttk.Label(root,text="Client laptop • Laptop B",foreground="#526174").pack(anchor="w",pady=(0,18))
        row=ttk.Frame(root); row.pack(fill="x")
        ttk.Label(row,text="Listening port").pack(side="left")
        self.port=tk.StringVar(value="8765"); ttk.Entry(row,textvariable=self.port,width=10).pack(side="left",padx=10)
        self.start_button=ttk.Button(row,text="Start server",command=self.start); self.start_button.pack(side="left")
        ttk.Button(row,text="Stop server",command=self.stop).pack(side="left",padx=8)
        ttk.Label(root,text="Pairing token (share privately with Laptop A)").pack(anchor="w",pady=(18,4))
        self.token=tk.StringVar(value=secrets.token_urlsafe(24)); ttk.Entry(root,textvariable=self.token,show="•").pack(fill="x")
        self.status=ttk.Label(root,text="Stopped",font=("Segoe UI",11,"bold")); self.status.pack(anchor="w",pady=(18,5))
        self.active=ttk.Label(root,text="Remote keyboard control inactive",foreground="#526174"); self.active.pack(anchor="w")
        ttk.Label(root,text="The server accepts one authenticated host on your local network. Use a strong token and stop the server when finished.",wraplength=420).pack(anchor="w",pady=16)

    def start(self):
        token=self.token.get()
        if len(token)<8: messagebox.showerror("Token too short","Use at least 8 characters."); return
        try:
            self.server=NetworkServer(token,lambda s,d:self.events.put(("status",s,d)),lambda active:self.events.put(("active",active)),self._inject)
            self.server.start(int(self.port.get()))
        except Exception as exc: self.status.config(text=f"Error — {exc}"); self.server=None

    def _inject(self,action,key):
        try: self.injector.event(action,key)
        except Exception as exc:
            logging.exception("Keyboard injection failed")
            self.events.put(("status","Error",f"Remote keyboard input stopped: {exc}"))
            raise

    def stop(self):
        if self.server: self.server.stop(); self.server=None
        self._release_remote_keys()
        self.active.config(text="Remote keyboard control inactive",foreground="#526174")
        self.status.config(text="Stopped")

    def _release_remote_keys(self):
        try: self.injector.release_all()
        except OSError as exc:
            logging.exception("Could not release remotely held keys")
            self.events.put(("status", "Error", str(exc)))

    def _poll(self):
        while True:
            try: item=self.events.get_nowait()
            except queue.Empty: break
            if item[0]=="status":
                self.status.config(text=f"{item[1]} — {item[2]}")
                if item[1] == "Key event received": self.received_count += 1
                elif item[1] == "Injection successful": self.injected_count += 1
                self._paint_event_counts()
            elif item[0]=="active":
                self.active.config(foreground="#a32626" if item[1] else "#526174")
                if not item[1]: self._release_remote_keys()
        self.after(100,self._poll)

    def _paint_event_counts(self):
        if self.received_count:
            text=f"Key events received: {self.received_count} | Injection successful: {self.injected_count}"
            color="#a32626"
        else:
            text="Waiting for authenticated key events"
            color="#526174"
        self.active.config(text=text,foreground=color)

    def close(self): self.stop(); self.destroy()
