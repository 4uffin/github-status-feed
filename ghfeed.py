import tkinter as tk
from tkinter import ttk, messagebox
import requests
import os
import threading
import emoji
import logging
import webbrowser
from dotenv import load_dotenv

# Load environment variables from .env file first, before they are needed.
load_dotenv()

# --- Logging Setup ---
# Configure the application's logging to write to a file.
logging.basicConfig(
    filename='ghfeed.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- GitHub API Interaction ---
def _fetch_user_feed(app_instance, status_label, refresh_button, users_to_fetch: int):
    """
    Initiates the fetching of GitHub user statuses in a background thread.
    This prevents the main application window from freezing during the network request.
    
    Args:
        app_instance: The main application class instance.
        status_label: The Tkinter label widget to update with status messages.
        refresh_button: The Tkinter button widget to disable/enable during fetch.
        users_to_fetch (int): The number of users to fetch from the API.
    """
    def run_fetch():
        """
        Performs the actual GitHub API request and processes the response.
        This function runs in a separate thread.
        """
        try:
            # Update the UI on the main thread to show "fetching" status.
            app_instance.root.after(0, lambda: status_label.config(text="Status: Fetching..."))
            app_instance.root.after(0, lambda: refresh_button.config(state="disabled"))

            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                raise ValueError("GITHUB_TOKEN environment variable is not set.")

            headers = {
                "Authorization": f"bearer {github_token}",
                "Content-Type": "application/json",
                "User-Agent": "GitHubStatusFeedApp/1.0",
            }

            # GraphQL query to search for users and their status messages.
            query = """
            query {
              search(query: "type:USER", type: USER, first: %d) {
                nodes {
                  ... on User {
                    login
                    status {
                      message
                      emoji
                    }
                  }
                }
              }
            }
            """ % users_to_fetch

            # Make the API request.
            response = requests.post("https://api.github.com/graphql", json={"query": query}, headers=headers)
            response.raise_for_status()

            # Process the JSON response.
            data = response.json()
            if "errors" in data:
                error_message = data["errors"][0].get("message", "An unknown API error occurred.")
                raise requests.exceptions.HTTPError(f"GitHub API Error: {error_message}")

            # Filter out users without an active status.
            users = [node for node in data['data']['search']['nodes'] if node and node.get('status')]

            # Update the UI on the main thread with the fetched data.
            app_instance.root.after(0, lambda: app_instance.update_feed_view(users))
            app_instance.root.after(0, lambda: status_label.config(text="Status: Feed updated successfully."))

        except requests.exceptions.RequestException as e:
            logging.error(f"Network Error: Failed to connect to GitHub API. Details: {e}")
            app_instance.root.after(0, lambda: status_label.config(text="Status: Network error. Try again."))
            messagebox.showerror(
                "Network Error",
                "Could not connect to GitHub. Please check your internet connection and proxy settings."
            )
        except ValueError as e:
            logging.error(f"Configuration Error: {e}")
            app_instance.root.after(0, lambda: status_label.config(text="Status: Configuration error."))
            messagebox.showerror(
                "Configuration Error",
                "A required configuration is missing or invalid. Please ensure your GITHUB_TOKEN is set correctly."
            )
        except Exception as e:
            logging.error(f"Unexpected Error: An unexpected error occurred during fetch. Details: {e}", exc_info=True)
            app_instance.root.after(0, lambda: status_label.config(text="Status: An unexpected error occurred."))
            messagebox.showerror(
                "Application Error",
                "An unexpected error occurred. Please check the 'ghfeed.log' for more details."
            )
        finally:
            # Re-enable the refresh button once the fetch is complete.
            app_instance.root.after(0, lambda: refresh_button.config(state="normal"))

    # Start the fetching process in a new thread.
    threading.Thread(target=run_fetch).start()

# --- Main Application Class ---
class GitHubStatusFeedApp:
    def __init__(self, root):
        """Initializes the main application window and its components."""
        self.root = root
        self.root.title("GitHub Status Feed")
        self.root.geometry("600x600")

        self.settings = self._load_settings()
        self.style = ttk.Style()
        self.fetched_users = []  # Stores fetched data to allow re-rendering without re-fetching.

        # Main frame for the application content.
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Title and refresh button layout.
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(title_frame, text="GitHub Status Feed", font=("Helvetica", 16, "bold")).pack(side="left")

        self.refresh_button = ttk.Button(
            title_frame,
            text="Refresh",
            command=self.on_refresh_button_click,
            cursor="hand2"
        )
        self.refresh_button.pack(side="right", padx=(5, 0))

        # Canvas and scrollbar for the feed.
        self.feed_canvas = tk.Canvas(main_frame)
        self.feed_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.feed_canvas.yview)
        self.feed_scrollable_frame = ttk.Frame(self.feed_canvas)

        self.feed_window_id = self.feed_canvas.create_window(
            (0, 0),
            window=self.feed_scrollable_frame,
            anchor="nw"
        )
        
        self.feed_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.feed_canvas.configure(
                scrollregion=self.feed_canvas.bbox("all")
            )
        )
        self.feed_canvas.bind("<Configure>", self._on_canvas_resize)
        self.feed_canvas.configure(yscrollcommand=self.feed_scrollbar.set)
        
        self.feed_canvas.pack(side="left", fill="both", expand=True)
        self.feed_scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel for scrolling.
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)

        # Status bar at the bottom.
        status_bar = ttk.Frame(self.root, relief="sunken", borderwidth=1)
        self.status_label = ttk.Label(status_bar, text="Status: Ready", anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=5)

        self.settings_button = ttk.Button(status_bar, text="Settings", command=self.show_settings_window)
        self.settings_button.pack(side="right", padx=5)
        
        status_bar.pack(side="bottom", fill="x")

        # Apply initial styling and fetch the first feed.
        self._refresh_ui_styling()
        self.on_refresh_button_click()

    # --- Encapsulated Settings and UI Management ---
    def _save_settings(self, settings: dict):
        """Saves application settings to a file."""
        try:
            with open("ghfeed_settings.txt", "w") as f:
                for key, value in settings.items():
                    f.write(f"{key}={value}\n")
        except IOError as e:
            logging.error(f"IOError: Failed to save settings. Check file permissions. Details: {e}")
            messagebox.showerror(
                "Save Error",
                "Failed to save settings. Please check file permissions and try again."
            )

    def _load_settings(self) -> dict:
        """Loads application settings from 'ghfeed_settings.txt'."""
        settings = {
            "theme": "dark",
            "users_to_fetch": 50,
            "font_size": 12,
        }
        try:
            with open("ghfeed_settings.txt", "r") as f:
                for line in f:
                    try:
                        key, value = line.strip().split("=")
                        if key == "theme":
                            settings["theme"] = value
                        elif key == "users_to_fetch":
                            settings["users_to_fetch"] = int(value)
                        elif key == "font_size":
                            settings["font_size"] = int(value)
                    except ValueError:
                        logging.warning(f"Invalid line format in settings file: {line.strip()}")
        except (FileNotFoundError, ValueError):
            logging.info("Settings file not found or invalid format. Using default settings.")
        except IOError as e:
            logging.error(f"IOError: Failed to load settings. Details: {e}")
        return settings

    def _on_canvas_resize(self, event):
        """Updates the width of the inner scrollable frame to match the canvas."""
        canvas_width = event.width
        self.feed_canvas.itemconfig(self.feed_window_id, width=canvas_width)

    def _on_mousewheel(self, event):
        """Handles mouse wheel scrolling for the feed canvas."""
        scroll_speed = -1 if event.num == 4 or event.delta > 0 else 1
        self.feed_canvas.yview_scroll(scroll_speed, "units")

    def _get_font_styles(self, base_size):
        """Returns a tuple of font styles based on a base size."""
        return (
            ("Helvetica", int(base_size * 1.5), "bold"),  # Heading
            ("Helvetica", int(base_size), "italic"),      # Status
            ("Helvetica", base_size, "bold", "underline")  # Link
        )

    def _refresh_ui_styling(self):
        """Applies the current theme and font settings to the UI."""
        base_font_size = self.settings["font_size"]
        heading_font, status_font, link_font = self._get_font_styles(base_font_size)

        theme_name = self.settings["theme"]
        if theme_name == "dark":
            self.style.theme_use("clam")
            background_color = "#0D1117"
            foreground_color = "#C9D1D9"
            self.style.configure("TFrame", background=background_color)
            self.style.configure("TLabel", background=background_color, foreground=foreground_color)
            self.style.configure("TButton", background="#21262D", foreground=foreground_color)
            self.style.configure("TCheckbutton", background=background_color, foreground=foreground_color)
            self.style.configure("TButton", relief="raised", borderwidth=1, bordercolor="#30363D")
            self.style.configure("TButton", background="#21262D", foreground="#C9D1D9")
            self.style.map("TButton",
                background=[("active", "#30363D"), ("!disabled", "#21262D")],
                foreground=[("active", "#58A6FF")]
            )
            self.feed_canvas.configure(background=background_color, highlightbackground=background_color)
            self.feed_scrollable_frame.configure(style="TFrame")
            self.style.configure("Link.TLabel", foreground="#58A6FF", background=background_color)
        else:
            self.style.theme_use("clam")
            background_color = "#f8f9fa"
            foreground_color = "#212529"
            self.style.configure("TFrame", background=background_color)
            self.style.configure("TLabel", background=background_color, foreground=foreground_color)
            # Correctly style buttons for light theme
            self.style.configure("TButton", background="#e9ecef", foreground="#212529", borderwidth=1, relief="raised")
            self.style.map("TButton",
                background=[("active", "#dee2e6"), ("!disabled", "#e9ecef")],
                foreground=[("active", "#0366D6")]
            )
            self.style.configure("TCheckbutton", background=background_color, foreground=foreground_color)
            self.feed_canvas.configure(background=background_color, highlightbackground=background_color)
            self.style.configure("Link.TLabel", foreground="#0366D6", background=background_color)

        # Apply the fonts to the styles.
        self.style.configure("Heading.TLabel", font=heading_font)
        self.style.configure("Status.TLabel", font=status_font)
        self.style.configure("Link.TLabel", font=link_font)  # Apply font to user name link
        self.root.configure(bg=self.style.lookup("TFrame", "background"))
        
        self.update_feed_view(self.fetched_users)

    def update_feed_view(self, users: list):
        """Updates the feed display with the fetched user statuses."""
        self.fetched_users = users

        for widget in self.feed_scrollable_frame.winfo_children():
            widget.destroy()

        if not users:
            no_statuses_label = ttk.Label(self.feed_scrollable_frame, text="No user statuses to display.")
            no_statuses_label.pack(pady=20)
            return

        base_font_size = self.settings["font_size"]
        status_font = ("Helvetica", base_font_size)
        dynamic_wraplength = int(550 * (base_font_size / 12))

        for user in users:
            login = user.get("login")
            status_data = user.get("status", {})
            message = status_data.get("message")
            emoji_text = status_data.get("emoji", "")
            
            if not message:
                continue

            card = ttk.Frame(self.feed_scrollable_frame, relief="raised", borderwidth=1, padding="10")
            card.pack(fill="x", pady=(5, 0), padx=5)

            # Link to the user's GitHub profile.
            user_label = ttk.Label(
                card,
                text=f"{login}",
                cursor="hand2",
                style="Link.TLabel"
            )
            user_label.pack(anchor="w")
            user_label.bind(
                "<Button-1>",
                lambda e, url=f"https://github.com/{login}": webbrowser.open_new(url)
            )

            full_message = f"{emoji.emojize(emoji_text)} {message}" if emoji_text else message
            status_label = ttk.Label(card, text=full_message, font=status_font, wraplength=dynamic_wraplength)
            status_label.pack(anchor="w", pady=(5, 0))


    def on_refresh_button_click(self):
        """Starts the process of fetching new user statuses."""
        _fetch_user_feed(self, self.status_label, self.refresh_button, self.settings["users_to_fetch"])

    def show_settings_window(self):
        """Displays the settings window to allow users to modify application settings."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("350x200")
        settings_window.resizable(False, False)

        frame = ttk.Frame(settings_window, padding=10)
        frame.pack(fill="both", expand=True)
        
        # Theme setting.
        theme_frame = ttk.Frame(frame)
        theme_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(theme_frame, text="Theme:").pack(side="left")
        
        self.theme_var = tk.StringVar(value=self.settings["theme"])
        theme_options = ["dark", "light"]
        theme_menu = ttk.OptionMenu(
            theme_frame,
            self.theme_var,
            self.settings["theme"],
            *theme_options,
            command=self._on_theme_change
        )
        theme_menu.pack(side="right")
        
        # Users to fetch setting.
        users_frame = ttk.Frame(frame)
        users_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(users_frame, text="Users to fetch:").pack(side="left")
        
        self.users_var = tk.IntVar(value=self.settings["users_to_fetch"])
        users_entry = ttk.Entry(users_frame, textvariable=self.users_var)
        users_entry.pack(side="right")

        # Font size setting.
        font_size_frame = ttk.Frame(frame)
        font_size_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(font_size_frame, text="Font Size:").pack(side="left")
        
        self.font_size_var = tk.IntVar(value=self.settings["font_size"])
        font_size_entry = ttk.Entry(font_size_frame, textvariable=self.font_size_var)
        font_size_entry.pack(side="right")

        def reset_settings():
            """Resets the settings to their default values."""
            self.users_var.set(50)
            self.font_size_var.set(12)

        def save_and_close():
            """Saves settings and closes the window."""
            try:
                new_users_to_fetch = self.users_var.get()
                new_font_size = self.font_size_var.get()

                if new_users_to_fetch <= 0:
                    raise ValueError("Number of users must be a positive integer.")
                if new_font_size <= 0:
                    raise ValueError("Font size must be a positive integer.")
                
                self.settings["users_to_fetch"] = new_users_to_fetch
                self.settings["theme"] = self.theme_var.get()
                self.settings["font_size"] = new_font_size
                self._save_settings(self.settings)
                self._refresh_ui_styling()
                settings_window.destroy()
            except tk.TclError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers for settings.")
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e))

        # Save and Cancel buttons.
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Save", command=save_and_close).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side="right")
        ttk.Button(button_frame, text="Reset", command=reset_settings).pack(side="left", padx=5)

    def _on_theme_change(self, new_theme):
        """Live-updates the theme when a selection is made in the settings menu."""
        self.settings["theme"] = new_theme
        self._refresh_ui_styling()

# Main execution block
if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubStatusFeedApp(root)
    root.mainloop()