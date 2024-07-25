import tkinter as tk
from socket import *
from threading import Thread
from tkinter import filedialog, messagebox, simpledialog,colorchooser
import sys
import time
import RSA

# Define a set of emojis
emojis = ["😊", "😂", "😍", "👍", "🎉", "❤️", "🌟", "🔥"]
colors = ["black", "red", "green", "blue", "yellow", "orange", "purple"]

def receive():
    """Handles receiving of messages."""
    msg_list.insert(tk.END, " Welcome! %s" % NAME)
    msg_list.insert(tk.END, " You are online!")
    while True:
        try:
            msg = CLIENT.recv(BUFFER_SIZE).decode("utf8")
            msg = RSA.decrypt_string(msg, private_key_2)
            msg_list.insert(tk.END, msg)
        except OSError:  # Possibly client has left the chat.
            break

def send(event = None):  # event is passed by binders.
    """Handles sending of messages."""
    msg = my_msg.get()    
    my_msg.set("")  # Clears input field.
    msg = NAME + ": " + msg
    msg_list.insert(tk.END, msg)
    msg = RSA.encrypt_string(msg, public_key_1)
    CLIENT.send(bytes(msg, "utf8"))
    
def upload_file():
    """Handles uploading of files."""
    filename = filedialog.askopenfilename()  # Open file dialog
    if filename:
        msg_list.insert(tk.END, "File uploaded: %s" % filename)
        # Add code to send the file to the server if needed

def insert_emoji(emoji):
    """Inserts the selected emoji into the text."""
    entry_field.insert(tk.END, emoji)

def choose_audio():
    """Handles choosing audio files."""
    filename = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3;*.wav;*.ogg")])
    if filename:
        msg_list.insert(tk.END, "Audio file selected: %s" % filename)
        # Add code to send the selected audio file to the server if needed

def retrieve_location():
    """Handles retrieving and sending user location."""
    # Add code to retrieve user's location and send it to the server
    messagebox.showinfo("Location", "Location retrieval feature not implemented yet.")

def change_color():
    """Handles changing the color of messages."""
    color = colorchooser.askcolor()[1]
    entry_field.config(fg=color)

def change_text_size():
    """Handles changing the size of text."""
    size = simpledialog.askinteger("Text Size", "Enter text size:", parent=top, initialvalue=12)
    if size:
        entry_field.config(font=("TkDefaultFont", size))
    

def on_closing(event = None):
    """This function is to be called when the window is closed."""
    msg_list.insert(tk.END, "going offline...")
    time.sleep(2)
    CLIENT.close()
    top.quit()
    sys.exit()

def open_emoji_menu():
    """Opens a pop-up menu to select an emoji."""
    menu = tk.Menu(top, tearoff=0)
    for emoji in emojis:
        menu.add_command(label=emoji, command=lambda e=emoji: insert_emoji(e))
    menu.post(emoji_button.winfo_rootx(), emoji_button.winfo_rooty() - menu.winfo_height())



#----tk GUI----
top = tk.Tk()
top.title("Chat Based")

messages_frame = tk.Frame(top)
my_msg = tk.StringVar()  # For the messages to be sent.
my_msg.set("Type your messages..")
scrollbar = tk.Scrollbar(messages_frame)  # To navigate through past messages.
# Following will contain the messages.
msg_list = tk.Listbox(messages_frame, height=25, width=100, yscrollcommand=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
msg_list.pack(side=tk.LEFT, fill=tk.BOTH)
msg_list.pack()
messages_frame.pack()

entry_field = tk.Entry(top, textvariable=my_msg)
entry_field.bind("<Return>", send)
entry_field.pack()

send_button = tk.Button(top, text="Send", command=send)
send_button.pack(side=tk.LEFT)

file_button = tk.Button(top, text="Upload File", command=upload_file)
file_button.pack(side=tk.RIGHT)

emoji_button = tk.Button(top, text="😊 Insert Emoji", command=open_emoji_menu)
emoji_button.pack(side=tk.RIGHT)

audio_button = tk.Button(top, text="🎵 Choose Audio", command=choose_audio)
audio_button.pack(side=tk.RIGHT)

location_button = tk.Button(top, text="🌍 Share Location", command=retrieve_location)
location_button.pack(side=tk.RIGHT)

color_button = tk.Button(top, text="🎨 Change Color", command=change_color)
color_button.pack(side=tk.RIGHT)

text_size_button = tk.Button(top, text="🔤 Change Text Size", command=change_text_size)
text_size_button.pack(side=tk.RIGHT)

top.protocol("WM_DELETE_WINDOW", on_closing)


#----SOCKET Part----
HOST = input('Enter host: ')
PORT = int(input('Enter port: '))
NAME = input('Enter your name: ')
BUFFER_SIZE = 1024
ADDRESS = (HOST, PORT)

CLIENT = socket(AF_INET, SOCK_STREAM)    # client socket object
CLIENT.connect(ADDRESS)	# to connect to the server socket address

public_key_2, private_key_2 = RSA.key_generator()
msg = str(public_key_2[0]) + '*' + str(public_key_2[1])
CLIENT.send(bytes(msg, "utf8"))
m = CLIENT.recv(BUFFER_SIZE).decode('utf8')
public_key_1 = [int(x) for x in m.split('*')]

receive_thread = Thread(target = receive)   # created a thread for receive method
receive_thread.start()
tk.mainloop()  # Starts GUI execution.
