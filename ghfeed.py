import tkinter as tk
from tkinter import ttk, messagebox
import requests
import os
import threading
import emoji
import logging
import webbrowser
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# --- Environment Variable & Settings Management ---
def save_settings(settings: dict):
    """
    Saves application settings to a file named 'ghfeed_settings.txt'.

    This function attempts to write the key-value pairs of the provided dictionary
    to a text file, with each pair on a new line. It handles potential I/O errors
    and logs them without crashing the application.

    Args:
        settings (dict): A dictionary containing the application settings to save.
                         Expected keys are 'theme' and 'users_to_fetch'.
    """
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

def load_settings() -> dict:
    """
    Loads application settings from 'ghfeed_settings.txt'.

    The function initializes a default settings dictionary and then attempts to
    overwrite these defaults with values read from the settings file. It gracefully
    handles cases where the file does not exist, is empty, or contains invalid data.

    Returns:
        dict: A dictionary containing the loaded settings or the default settings
              if the file could not be read.
    """
    settings = {
        "theme": "dark",
        "users_to_fetch": 50,
        "font_size": 12, # Added font size setting
    }
    try:
        with open("ghfeed_settings.txt", "r") as f:
            for line in f:
                key, value = line.strip().split("=")
                if key == "theme":
                    settings["theme"] = value
                elif key == "users_to_fetch":
                    settings["users_to_fetch"] = int(value)
                elif key == "font_size": # Load the new setting
                    settings["font_size"] = int(value)
    except (FileNotFoundError, ValueError):
        # File not found or invalid format; use default settings.
        logging.info("Settings file not found or invalid format. Using default settings.")
    except IOError as e:
        # Other I/O errors
        logging.error(f"IOError: Failed to load settings. Details: {e}")
    return settings

# --- Logging Setup ---
logging.basicConfig(
    filename='ghfeed.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- GitHub API Interaction ---
def fetch_user_feed(
    app_instance,
    status_label,
    refresh_button,
    users_to_fetch: int
):
    """
    Fetches GitHub user statuses from the API in a background thread.

    This function performs a GraphQL query to retrieve a list of recent GitHub
    user statuses. It handles network requests and API responses, updating the
    GUI status bar with real-time feedback. Errors such as network issues or
    API key problems are caught and displayed to the user.

    Args:
        app_instance (GitHubStatusFeedApp): The main application instance to
                                             facilitate thread-safe UI updates.
        status_label (ttk.Label): The label widget used to display status messages.
        refresh_button (ttk.Button): The button to disable/enable during the fetch.
        users_to_fetch (int): The number of users to fetch from the API.

    Raises:
        requests.exceptions.RequestException: Propagated if a network error occurs.
        ValueError: Propagated if the response data is malformed or invalid.
    """
    def run_fetch():
        """Handles the actual fetching logic in a separate thread."""
        try:
            # Update UI to show loading state (must be done in the main thread)
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

            # A simple GraphQL query to get the first N users with a status.
            # Note: This is a placeholder as GitHub's GraphQL API does not have
            # a simple public "feed" endpoint without a user context.
            # A more advanced version would use the viewer's feed.
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

            response = requests.post("https://api.github.com/graphql", json={"query": query}, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

            data = response.json()
            # Check for API-specific errors, e.g., bad credentials
            if "errors" in data:
                error_message = data["errors"][0].get("message", "An unknown API error occurred.")
                raise requests.exceptions.HTTPError(f"GitHub API Error: {error_message}")

            users = [node for node in data['data']['search']['nodes'] if node and node.get('status')]

            # Pass the fetched data to the main thread for processing
            app_instance.root.after(0, lambda: app_instance.update_feed_view(users))
            app_instance.root.after(0, lambda: status_label.config(text="Status: Feed updated successfully."))

        except requests.exceptions.RequestException as e:
            # Handle network-related errors and HTTP status code errors
            logging.error(f"Network Error: Failed to connect to GitHub API. Details: {e}")
            app_instance.root.after(0, lambda: status_label.config(text="Status: Network error. Try again."))
            messagebox.showerror(
                "Network Error",
                "Could not connect to GitHub. Please check your internet connection and proxy settings."
            )
        except ValueError as e:
            # Handle issues with the API key or JSON decoding
            logging.error(f"Configuration Error: {e}")
            app_instance.root.after(0, lambda: status_label.config(text="Status: Configuration error."))
            messagebox.showerror(
                "Configuration Error",
                "A required configuration is missing or invalid. Please ensure your GITHUB_TOKEN is set correctly."
            )
        except Exception as e:
            # Catch any other unexpected errors
            logging.error(f"Unexpected Error: An unexpected error occurred during fetch. Details: {e}", exc_info=True)
            app_instance.root.after(0, lambda: status_label.config(text="Status: An unexpected error occurred."))
            messagebox.showerror(
                "Application Error",
                "An unexpected error occurred. Please check the 'ghfeed.log' for more details."
            )
        finally:
            # Always re-enable the refresh button
            app_instance.root.after(0, lambda: refresh_button.config(state="normal"))

    # Start the fetch operation in a separate thread to prevent the UI from freezing
    threading.Thread(target=run_fetch).start()


# --- Main Application Class ---
class GitHubStatusFeedApp:
    """
    The main application class for the GitHub Status Feed.

    This class encapsulates the entire Tkinter GUI application, managing its
    layout, widgets, themes, and interactions. It orchestrates the process of
    fetching data in a separate thread and updating the UI safely.

    Attributes:
        root (tk.Tk): The main Tkinter window.
        settings (dict): A dictionary holding the application's settings.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub Status Feed")
        self.root.geometry("600x600")

        self.settings = load_settings()
        self.style = ttk.Style()

        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Title and buttons frame
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(title_frame, text="GitHub Status Feed", font=("Helvetica", 16, "bold")).pack(side="left")

        # Create refresh button without an icon
        self.refresh_button = ttk.Button(
            title_frame,
            text="Refresh",
            command=self.on_refresh_button_click,
            cursor="hand2"
        )
        self.refresh_button.pack(side="right", padx=(5, 0))

        # Feed display area
        self.feed_canvas = tk.Canvas(main_frame)
        self.feed_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.feed_canvas.yview)
        self.feed_scrollable_frame = ttk.Frame(self.feed_canvas)

        # Create the window item once and store its ID
        self.feed_window_id = self.feed_canvas.create_window(
            (0, 0),
            window=self.feed_scrollable_frame,
            anchor="nw"
        )
        
        # Bind events to manage resizing and scrolling
        self.feed_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.feed_canvas.configure(
                scrollregion=self.feed_canvas.bbox("all")
            )
        )
        # Bind the canvas's resize event to call a new method that updates the inner frame's width
        self.feed_canvas.bind("<Configure>", self._on_canvas_resize)
        self.feed_canvas.configure(yscrollcommand=self.feed_scrollbar.set)
        
        self.feed_canvas.pack(side="left", fill="both", expand=True)
        self.feed_scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel for scrolling
        self.root.bind("<MouseWheel>", self._on_mousewheel)  # For Windows/Linux
        self.root.bind("<Button-4>", self._on_mousewheel)    # For Linux (scroll up)
        self.root.bind("<Button-5>", self._on_mousewheel)    # For Linux (scroll down)

        # Status bar
        status_bar = ttk.Frame(self.root, relief="sunken", borderwidth=1)
        self.status_label = ttk.Label(status_bar, text="Status: Ready", anchor="w")
        self.status_label.pack(side="left", fill="x", expand=True, padx=5)

        self.settings_button = ttk.Button(status_bar, text="Settings", command=self.show_settings_window)
        self.settings_button.pack(side="right", padx=5)
        
        status_bar.pack(side="bottom", fill="x")

        # Now that all widgets are created, apply the initial theme
        self.update_theme(self.settings["theme"])
        
        # Initial fetch
        self.on_refresh_button_click()

    def _on_canvas_resize(self, event):
        """
        Updates the width of the inner scrollable frame to match the canvas.
        """
        canvas_width = event.width
        self.feed_canvas.itemconfig(self.feed_window_id, width=canvas_width)


    def _on_mousewheel(self, event):
        """
        Handles mouse wheel scrolling for the feed canvas.

        This function is a cross-platform solution for vertical scrolling using
        the mouse wheel, adapting to different event bindings on Windows/Linux
        and macOS.
        """
        # A simple normalization for different OS scroll amounts
        if event.num == 4 or event.delta > 0:
            self.feed_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.feed_canvas.yview_scroll(1, "units")

    def update_theme(self, theme_name: str):
        """
        Updates the application's theme and all dynamic fonts.

        This function configures the Tkinter style to apply a dark or light theme.
        It also manages custom styles for the widgets to ensure a consistent look.

        Args:
            theme_name (str): The name of the theme to apply ('dark' or 'light').
        """
        base_font_size = self.settings["font_size"]
        
        # Define dynamic fonts based on the base font size
        heading_font = ("Helvetica", int(base_font_size * 1.5), "bold")
        status_font = ("Helvetica", int(base_font_size * 0.9), "italic")
        link_font = ("Helvetica", base_font_size, "bold", "underline")

        if theme_name == "dark":
            self.style.theme_use("clam")
            background_color = "#0D1117"
            foreground_color = "#C9D1D9"
            self.style.configure("TFrame", background=background_color)
            self.style.configure("TLabel", background=background_color, foreground=foreground_color)
            self.style.configure("TButton", background="#21262D", foreground=foreground_color)
            self.style.configure("TCheckbutton", background=background_color, foreground=foreground_color)
            
            # Additional styles for a more GitHub-like feel
            self.style.configure("TButton", relief="raised", borderwidth=1, bordercolor="#30363D")
            self.style.configure("TButton", background="#21262D", foreground="#C9D1D9")
            self.style.map("TButton",
                background=[("active", "#30363D"), ("!disabled", "#21262D")],
                foreground=[("active", "#58A6FF")]
            )
            
            # The canvas and inner frame should match the main background
            self.feed_canvas.configure(background=background_color, highlightbackground=background_color)
            self.feed_scrollable_frame.configure(style="TFrame")

            # Update link color
            self.style.configure("Link.TLabel", foreground="#58A6FF", background=background_color, font=link_font)
        else: # Light theme
            self.style.theme_use("clam")
            background_color = "#f8f9fa"
            foreground_color = "#212529"
            self.style.configure("TFrame", background=background_color)
            self.style.configure("TLabel", background=background_color, foreground=foreground_color)
            self.style.configure("TButton", background="#e9ecef", foreground="#212529")
            self.style.configure("TCheckbutton", background=background_color, foreground=foreground_color)
            # Fix for white canvas background
            self.feed_canvas.configure(background=background_color, highlightbackground=background_color)

        # Custom styles for different widgets for consistency
        self.style.configure("Heading.TLabel", font=heading_font)
        self.style.configure("Status.TLabel", font=status_font)
        self.root.configure(bg=self.style.lookup("TFrame", "background"))


    def update_feed_view(self, users: list):
        """
        Updates the feed display with the fetched user statuses.

        This function is called from the main GUI thread to safely update the
        Tkinter widgets after a background thread has finished fetching data.
        It clears the old content and populates the feed with new user status cards.

        Args:
            users (list): A list of dictionaries, where each dictionary represents
                          a user with a 'login' and 'status'.
        """
        # Clear existing widgets
        for widget in self.feed_scrollable_frame.winfo_children():
            widget.destroy()

        if not users:
            no_statuses_label = ttk.Label(self.feed_scrollable_frame, text="No user statuses to display.")
            no_statuses_label.pack(pady=20)
            return

        base_font_size = self.settings["font_size"]
        status_font = ("Helvetica", base_font_size)
        # Calculate a dynamic wraplength to prevent text from overflowing.
        # This scales based on the current font size, assuming a base font size of 12.
        dynamic_wraplength = int(550 * (base_font_size / 12))

        for user in users:
            login = user.get("login")
            status_data = user.get("status", {})
            message = status_data.get("message")
            emoji_text = status_data.get("emoji", "")
            
            # Skip users without a status message
            if not message:
                continue

            # Create a card for each user
            card = ttk.Frame(self.feed_scrollable_frame, relief="raised", borderwidth=1, padding="10")
            card.pack(fill="x", pady=(5, 0), padx=5)

            # User login link
            user_label = ttk.Label(
                card,
                text=f"{login}",
                cursor="hand2",
                style="Link.TLabel" # Use the new style
            )
            user_label.pack(anchor="w")
            user_label.bind(
                "<Button-1>",
                lambda e, url=f"https://github.com/{login}": webbrowser.open_new(url)
            )

            # Status message with emoji and dynamic font size
            full_message = f"{emoji.emojize(emoji_text)} {message}" if emoji_text else message
            status_label = ttk.Label(card, text=full_message, font=status_font, wraplength=dynamic_wraplength)
            status_label.pack(anchor="w", pady=(5, 0))

    def on_refresh_button_click(self):
        """Starts the process of fetching new user statuses."""
        fetch_user_feed(self, self.status_label, self.refresh_button, self.settings["users_to_fetch"])

    def show_settings_window(self):
        """Displays the settings window to allow users to modify application settings."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("350x200")
        settings_window.resizable(False, False)

        frame = ttk.Frame(settings_window, padding=10)
        frame.pack(fill="both", expand=True)
        
        # Theme setting
        theme_frame = ttk.Frame(frame)
        theme_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(theme_frame, text="Theme:").pack(side="left")
        
        theme_options = ["dark", "light"]
        self.theme_var = tk.StringVar(value=self.settings["theme"])
        theme_menu = ttk.OptionMenu(
            theme_frame,
            self.theme_var,
            self.settings["theme"],
            *theme_options,
            command=self.update_theme
        )
        theme_menu.pack(side="right")
        
        # Users to fetch setting
        users_frame = ttk.Frame(frame)
        users_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(users_frame, text="Users to fetch:").pack(side="left")
        
        self.users_var = tk.IntVar(value=self.settings["users_to_fetch"])
        users_entry = ttk.Entry(users_frame, textvariable=self.users_var)
        users_entry.pack(side="right")

        # Font size setting
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
                save_settings(self.settings)
                self.update_theme(self.settings["theme"])
                self.update_feed_view([]) # Refresh with empty list to force re-render with new font size
                settings_window.destroy()
            except tk.TclError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers for settings.")
            except ValueError as e:
                messagebox.showerror("Invalid Input", str(e))

        # Save and Cancel buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="Save", command=save_and_close).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side="right")
        ttk.Button(button_frame, text="Reset", command=reset_settings).pack(side="left", padx=5)

# Main execution block
if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubStatusFeedApp(root)
    root.mainloop()