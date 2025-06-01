# client_1.py
import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, font as tkFont
import random
import math
import sys
import time
import json # For serializing list of numbers
import base64 # For encoding the serialized list

# --- RSA Cryptography (Simplified) ---
def gcd(a, b):
    """Compute the greatest common divisor of a and b."""
    while b:
        a, b = b, a % b
    return a

def mod_inverse(e, phi):
    """Compute the modular multiplicative inverse of e modulo phi."""
    m0, x0, x1 = phi, 0, 1
    while e > 1:
        q = e // phi
        phi, e = e % phi, phi
        x0, x1 = x1 - q * x0, x0
    if x1 < 0:
        x1 += m0
    return x1

def is_prime(num):
    """Very basic primality test for small numbers."""
    if num < 2: return False
    for i in range(2, int(math.sqrt(num)) + 1):
        if num % i == 0:
            return False
    return True

def generate_rsa_keys(p_val=61, q_val=53): # Client 1 uses p=61, q=53
    """
    Generates a simple RSA public-private key pair for Client 1.
    """
    p = p_val 
    q = q_val
    if not (is_prime(p) and is_prime(q)): 
        raise ValueError("p and q must be prime numbers for RSA.")
    if p == q:
        raise ValueError("p and q cannot be equal.")

    n = p * q
    phi_n = (p - 1) * (q - 1)

    e = 17 
    while gcd(e, phi_n) != 1:
        e += 2 

    d = mod_inverse(e, phi_n)

    public_key = (e, n)
    private_key = (d, n)
    return public_key, private_key

def encrypt_message(public_key, message_text):
    """Encrypts message text, then JSON serializes, then Base64 encodes."""
    e, n = public_key
    encrypted_numbers = [pow(ord(char), e, n) for char in message_text]
    # Serialize the list of numbers to a JSON string
    json_string = json.dumps(encrypted_numbers)
    # Base64 encode the JSON string
    base64_encoded_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    return base64_encoded_string

def decrypt_message(private_key, base64_encoded_string):
    """Base64 decodes, JSON deserializes, then decrypts the numbers."""
    d, n = private_key
    try:
        # Base64 decode
        json_string = base64.b64decode(base64_encoded_string.encode('utf-8')).decode('utf-8')
        # Deserialize the JSON string to a list of numbers
        encrypted_numbers = json.loads(json_string)
        if not isinstance(encrypted_numbers, list): # Basic validation
             raise ValueError("Decoded data is not a list of numbers.")
        decrypted_text = "".join([chr(pow(char_code, d, n)) for char_code in encrypted_numbers])
        return decrypted_text
    except (json.JSONDecodeError, base64.binascii.Error, TypeError, ValueError) as e:
        print(f"[CLIENT 1] Decryption/Decoding error: {e}")
        return "<Decryption Error>"


# --- Client Application Class ---
class ChatClient:
    def __init__(self, master_root):
        self.root = master_root
        self.root.title("Encrypted Chat Client 1") 
        self.root.configure(bg="#282c34") # Dark background for the root window

        # Define fonts
        self.default_font = tkFont.Font(family="Arial", size=10)
        self.chat_font = tkFont.Font(family="Consolas", size=11) # Monospaced for chat
        self.button_font = tkFont.Font(family="Arial", size=10, weight="bold")
        self.title_font = tkFont.Font(family="Arial", size=12, weight="bold")

        self.client_name = ""
        self.server_ip = ""
        self.server_port = 42000

        self.my_public_key = None
        self.my_private_key = None
        self.peer_name = ""
        self.peer_public_key = None

        self.client_socket = None
        self.connected = False
        self.receive_buffer = "" 

        try:
            self.my_public_key, self.my_private_key = generate_rsa_keys()
        except ValueError as e:
            messagebox.showerror("RSA Error", f"Could not generate RSA keys: {e}", parent=self.root)
            self.root.quit()
            return

        self.setup_login_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_login_ui(self):
        self.login_frame = tk.Frame(self.root, padx=20, pady=20, bg="#282c34")
        self.login_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        tk.Label(self.login_frame, text="Secure Chat Login", font=self.title_font, fg="#61afef", bg="#282c34").grid(row=0, column=0, columnspan=2, pady=(0, 20))

        tk.Label(self.login_frame, text="Your Name:", font=self.default_font, fg="#abb2bf", bg="#282c34").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.name_entry = tk.Entry(self.login_frame, width=30, font=self.default_font, bg="#21252b", fg="#abb2bf", insertbackground="#abb2bf", relief=tk.FLAT, borderwidth=2)
        self.name_entry.insert(0, "JOHN") # Default name for Client 1
        self.name_entry.grid(row=1, column=1, pady=5, padx=5, ipady=3)

        tk.Label(self.login_frame, text="Server IP:", font=self.default_font, fg="#abb2bf", bg="#282c34").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.ip_entry = tk.Entry(self.login_frame, width=30, font=self.default_font, bg="#21252b", fg="#abb2bf", insertbackground="#abb2bf", relief=tk.FLAT, borderwidth=2)
        self.ip_entry.grid(row=2, column=1, pady=5, padx=5, ipady=3)

        tk.Label(self.login_frame, text="Server Port:", font=self.default_font, fg="#abb2bf", bg="#282c34").grid(row=3, column=0, sticky="w", pady=5, padx=5)
        self.port_entry = tk.Entry(self.login_frame, width=30, font=self.default_font, bg="#21252b", fg="#abb2bf", insertbackground="#abb2bf", relief=tk.FLAT, borderwidth=2)
        self.port_entry.insert(0, str(self.server_port))
        self.port_entry.grid(row=3, column=1, pady=5, padx=5, ipady=3)

        self.connect_button = tk.Button(self.login_frame, text="Connect", command=self.attempt_connection, font=self.button_font, bg="#61afef", fg="#282c34", activebackground="#528bcf", activeforeground="#282c34", relief=tk.FLAT, padx=10, pady=5, borderwidth=0)
        self.connect_button.grid(row=4, column=0, columnspan=2, pady=20)
        
        self.login_frame.grid_columnconfigure(1, weight=1) # Make entry column expandable

    def attempt_connection(self):
        self.client_name = self.name_entry.get().strip()
        self.server_ip = self.ip_entry.get().strip()
        port_str = self.port_entry.get().strip()

        if not self.client_name or not self.server_ip or not port_str:
            messagebox.showerror("Input Error", "Name, Server IP, and Port cannot be empty.", parent=self.root)
            return
        try:
            self.server_port = int(port_str)
        except ValueError:
            messagebox.showerror("Input Error", "Port must be a number.", parent=self.root)
            return

        if not self.my_public_key: 
            messagebox.showerror("Key Error", "RSA keys not generated. Cannot connect.", parent=self.root)
            return

        self.connect_button.config(text="Connecting...", state=tk.DISABLED, bg="#4b5263")
        
        connect_thread = threading.Thread(target=self.connect_to_server, daemon=True)
        connect_thread.start()

    def connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.server_ip, self.server_port))
            self.connected = True
            self.receive_buffer = "" 

            reg_msg = f"REG::{self.client_name}::{self.my_public_key[0]},{self.my_public_key[1]}"
            self.client_socket.sendall(reg_msg.encode('utf-8'))

            response = self.client_socket.recv(1024).decode('utf-8')
            if response.startswith("ACK::"):
                if self.login_frame.winfo_exists(): self.login_frame.destroy() # Destroy login frame
                self.setup_chat_ui()
                self.display_message(f"System: {response.split('::',1)[1]}", "system")
                self.display_message(f"System: My public key {self.my_public_key} sent.", "system")
                
                receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
                receive_thread.start()
            elif response.startswith("ERR::"):
                messagebox.showerror("Connection Failed", f"Server error: {response.split('::',1)[1]}", parent=self.root)
                self.reset_connection_ui()
            else:
                messagebox.showerror("Connection Failed", f"Unexpected server response: {response}", parent=self.root)
                self.reset_connection_ui()

        except socket.error as e:
            messagebox.showerror("Connection Error", f"Could not connect to server {self.server_ip}:{self.server_port}\nError: {e}", parent=self.root)
            self.reset_connection_ui()
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}", parent=self.root)
            self.reset_connection_ui()

    def reset_connection_ui(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except socket.error:
                pass
        self.client_socket = None
        self.connected = False
        if hasattr(self, 'connect_button') and self.connect_button.winfo_exists():
            self.connect_button.config(text="Connect", state=tk.NORMAL, bg="#61afef")

        # If chat UI exists, destroy it and show login UI again
        if hasattr(self, 'chat_frame') and self.chat_frame.winfo_exists():
            self.chat_frame.destroy()
        
        if not (hasattr(self, 'login_frame') and self.login_frame.winfo_exists()):
            self.setup_login_ui() # Recreate login if it was destroyed
        
        if self.root.winfo_exists():
            self.root.title("Encrypted Chat Client 1 (Disconnected)")


    def setup_chat_ui(self):
        self.chat_frame = tk.Frame(self.root, padx=10, pady=10, bg="#282c34")
        self.chat_frame.pack(expand=True, fill=tk.BOTH)

        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, state=tk.DISABLED, wrap=tk.WORD, height=15, width=60, font=self.chat_font, bg="#21252b", fg="#abb2bf", relief=tk.FLAT, borderwidth=0, padx=5, pady=5)
        self.chat_display.pack(pady=(0,10), expand=True, fill=tk.BOTH)

        # Configure tags for message styling
        self.chat_display.tag_configure("you", foreground="#98c379", font=tkFont.Font(family="Consolas", size=11, weight="bold")) # Greenish for self
        self.chat_display.tag_configure("peer", foreground="#e06c75", font=tkFont.Font(family="Consolas", size=11)) # Reddish for peer
        self.chat_display.tag_configure("system", foreground="#56b6c2", font=tkFont.Font(family="Consolas", size=10, slant="italic")) # Bluish for system

        input_frame = tk.Frame(self.chat_frame, bg="#282c34")
        input_frame.pack(fill=tk.X)

        self.msg_entry = tk.Entry(input_frame, width=50, font=self.chat_font, bg="#21252b", fg="#abb2bf", insertbackground="#abb2bf", relief=tk.FLAT, borderwidth=2)
        self.msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, ipady=5, padx=(0,10))
        self.msg_entry.bind("<Return>", self.send_message_event) 

        self.send_button = tk.Button(input_frame, text="Send", command=self.send_message_event, font=self.button_font, bg="#61afef", fg="#282c34", activebackground="#528bcf", activeforeground="#282c34", relief=tk.FLAT, padx=10, pady=3)
        self.send_button.pack(side=tk.RIGHT)
        
        if self.root.winfo_exists():
            self.root.title(f"Secure Chat - {self.client_name}")


    def display_message(self, message, tag="system"): # Default tag is "system"
        if hasattr(self, 'chat_display') and self.chat_display.winfo_exists():
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, message + "\n", tag)
            self.chat_display.yview(tk.END) 
            self.chat_display.config(state=tk.DISABLED)

    def send_message_event(self, event=None): 
        message_text = self.msg_entry.get()
        if message_text and self.connected:
            if not self.peer_public_key:
                self.display_message("System: Cannot send message. Peer's public key not yet received.", "system")
                return

            try:
                encrypted_payload = encrypt_message(self.peer_public_key, message_text)
                full_msg = f"MSG::{encrypted_payload}" # Payload is now Base64 string
                self.client_socket.sendall(full_msg.encode('utf-8'))
                
                self.display_message(f"You: {message_text}", "you") # Display own message locally
                self.msg_entry.delete(0, tk.END)
            except Exception as e:
                self.display_message(f"System: Error sending message - {e}", "system")
                print(f"[CLIENT 1] Encryption/Send error: {e}")
        elif not self.connected:
             self.display_message("System: Not connected to server.", "system")

    def process_message_buffer(self):
        processed_a_message = False
        # KEY::peer_name::e,n
        if self.receive_buffer.startswith("KEY::"):
            try:
                # Find the end of the key message. It's "KEY::name::e,n"
                # The 'n' part is followed by the start of another message or end of buffer.
                parts = self.receive_buffer.split("::", 2)
                if len(parts) < 3: return False 

                _key_header, peer_name_part, key_data_candidate = parts
                
                # Find where key_data_candidate (e,n part) actually ends
                # It ends before the next "KEY::", "RELAY::", or "INFO::" or end of buffer
                next_msg_starts = []
                if "KEY::" in key_data_candidate: next_msg_starts.append(key_data_candidate.find("KEY::"))
                if "RELAY::" in key_data_candidate: next_msg_starts.append(key_data_candidate.find("RELAY::"))
                if "INFO::" in key_data_candidate: next_msg_starts.append(key_data_candidate.find("INFO::"))
                
                valid_starts = [s for s in next_msg_starts if s != -1]
                end_of_key_data_idx = min(valid_starts) if valid_starts else len(key_data_candidate)
                
                actual_key_data = key_data_candidate[:end_of_key_data_idx].strip()

                e_str, n_str = actual_key_data.split(',')
                self.peer_public_key = (int(e_str), int(n_str))
                self.peer_name = peer_name_part
                self.display_message(f"System: Received public key for {self.peer_name}: {self.peer_public_key}", "system")

                consumed_length = len("KEY::") + len(peer_name_part) + len("::") + len(actual_key_data)
                self.receive_buffer = self.receive_buffer[consumed_length:]
                processed_a_message = True
            
            except ValueError as e: 
                print(f"[CLIENT 1] Partial or malformed KEY message: {self.receive_buffer[:100]}, Error: {e}")
                return False 
            except Exception as e:
                print(f"[CLIENT 1] Exception during KEY message processing: {e}, buffer: {self.receive_buffer[:100]}")
                return False

        # RELAY::sender_name::base64_payload
        elif self.receive_buffer.startswith("RELAY::"):
            try:
                parts = self.receive_buffer.split("::", 2)
                if len(parts) < 3: return False

                _relay_header, sender_name, payload_candidate = parts
                
                # Find where payload_candidate (Base64 string) actually ends
                next_msg_starts = []
                if "KEY::" in payload_candidate: next_msg_starts.append(payload_candidate.find("KEY::"))
                if "RELAY::" in payload_candidate: next_msg_starts.append(payload_candidate.find("RELAY::"))
                if "INFO::" in payload_candidate: next_msg_starts.append(payload_candidate.find("INFO::"))

                valid_starts = [s for s in next_msg_starts if s != -1]
                end_of_payload_idx = min(valid_starts) if valid_starts else len(payload_candidate)

                actual_payload = payload_candidate[:end_of_payload_idx].strip()
                if not actual_payload: return False # Empty payload part

                decrypted_text = decrypt_message(self.my_private_key, actual_payload)
                self.display_message(f"{sender_name}: {decrypted_text}", "peer")

                consumed_length = len("RELAY::") + len(sender_name) + len("::") + len(actual_payload)
                self.receive_buffer = self.receive_buffer[consumed_length:]
                processed_a_message = True

            except Exception as e: 
                print(f"[CLIENT 1] Error parsing/decrypting RELAY message: {e}, data: {self.receive_buffer[:100]}")
                 # If payload is corrupt, we might want to discard part of the buffer
                # For now, assume it's incomplete
                return False

        # INFO::message_text
        elif self.receive_buffer.startswith("INFO::"):
            info_content_candidate = self.receive_buffer[len("INFO::"):]
            
            next_key_idx = info_content_candidate.find("KEY::")
            next_relay_idx = info_content_candidate.find("RELAY::")
            next_info_idx = info_content_candidate.find("INFO::") 

            end_of_current_info = len(info_content_candidate) 
            
            possible_ends = [idx for idx in [next_key_idx, next_relay_idx, next_info_idx] if idx != -1]
            if possible_ends:
                end_of_current_info = min(possible_ends)
            
            info_text = info_content_candidate[:end_of_current_info].strip()
            
            self.display_message(f"System: {info_text}", "system")
            if "has disconnected" in info_text or "Server is shutting down" in info_text:
                self.peer_public_key = None
                if hasattr(self, 'send_button') and self.send_button.winfo_exists():
                    self.send_button.config(state=tk.DISABLED, bg="#4b5263")
            
            consumed_length = len("INFO::") + end_of_current_info # Use end_of_current_info as it's index in candidate
            self.receive_buffer = self.receive_buffer[consumed_length:]
            processed_a_message = True
        
        return processed_a_message

    def receive_messages(self):
        while self.connected:
            try:
                data_chunk = self.client_socket.recv(4096)
                if not data_chunk:
                    self.display_message("System: Disconnected from server (connection closed).", "system")
                    self.connected = False
                    self.reset_connection_ui_from_thread()
                    break
                
                self.receive_buffer += data_chunk.decode('utf-8', errors='ignore')

                while self.process_message_buffer():
                    pass 

            except socket.timeout: 
                continue 
            except socket.error as e:
                if self.connected: 
                    self.display_message(f"System: Connection error - {e}. Disconnected.", "system")
                self.connected = False
                self.reset_connection_ui_from_thread()
                break 
            except Exception as e:
                self.display_message(f"System: Error receiving/processing message - {e}", "system")
                print(f"[CLIENT 1] Unexpected error in receive_messages: {e}")
                self.connected = False 
                self.reset_connection_ui_from_thread()
                break
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except socket.error:
                pass
            self.client_socket = None
        print("[CLIENT 1] Receive thread terminated.")

    def reset_connection_ui_from_thread(self):
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(0, self._do_reset_ui_main_thread)

    def _do_reset_ui_main_thread(self):
        if hasattr(self, 'chat_frame') and self.chat_frame.winfo_exists():
            self.chat_frame.destroy() 
        
        if not (hasattr(self, 'login_frame') and self.login_frame.winfo_exists()):
            self.setup_login_ui() # Recreate login if it was destroyed
        else:
             self.login_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10) # Re-pack if just hidden


        if hasattr(self, 'connect_button') and self.connect_button.winfo_exists():
            self.connect_button.config(text="Connect", state=tk.NORMAL, bg="#61afef")
        
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.title("Encrypted Chat Client 1 (Disconnected)")
        
        self.peer_public_key = None
        self.peer_name = ""
        if hasattr(self, 'root') and self.root.winfo_exists():
            messagebox.showinfo("Disconnected", "You have been disconnected from the server.", parent=self.root)


    def on_closing(self):
        self.connected = False 
        if self.client_socket:
            try:
                self.client_socket.close()
            except socket.error:
                pass
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Center the window
    window_width = 550
    window_height = 450
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width / 2)
    center_y = int(screen_height/2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.minsize(400, 300) # Minimum size

    app = ChatClient(root)
    root.mainloop()
  
  
