# **GitHub Status Feed**

This is a proof of concept for a Python application that uses tkinter to create a simple GUI. Its purpose is to fetch and display public status messages from GitHub users. The app communicates with the GitHub GraphQL API to retrieve this data in a clean and efficient way.

## **Features**

* **Live Status Feed**: Get real-time updates of public status messages and emojis from GitHub users.  
* **Customizable**: Easily switch between 'light' and 'dark' themes. You can also control the number of users to display.  
* **Font Sizing**: Adjust the font size of the feed to your personal preference.  
* **Background Fetching**: Data is fetched in a separate thread, which prevents the GUI from freezing and keeps the application responsive during network requests.  
* **User Links**: Click a user's name to open their GitHub profile in your default web browser, making it easy to see their full activity.

## **Project Structure**

The application consists of a single Python file, ghfeed.py, which is designed to be self-contained. It works alongside an environment file and a settings file.

* ghfeed.py: The main application script containing all the GUI logic, API interaction, and threading.  
* .env: An environment file where you store your GitHub Personal Access Token. This keeps your sensitive token out of the code and is a best practice for security.  
* ghfeed\_settings.txt: A simple text file that saves your application settings (theme, user count, font size) so they persist between runs.  
* ghfeed.log: A log file that records application errors and warnings, which is extremely helpful for debugging.

## **Dependencies**

To run this application, you need to have **Python 3.x** installed. The project relies on the following Python libraries, which you can install via pip:

* **requests**: Used to make HTTP requests to the GitHub GraphQL API.  
* **emoji**: A library to properly handle and display emojis from the user statuses.  
* **python-dotenv**: Used to read the GITHUB\_TOKEN from the .env file.  
* **tkinter**: This library is built into Python, so no separate installation is required.

You can install all required dependencies at once by running this command in your terminal:

pip install requests emoji python-dotenv

## **Setup and Configuration**

1. **Clone or Download**: Get the ghfeed.py file to your local machine.  
2. **Create a GitHub Personal Access Token**:  
   * Navigate to your GitHub account **Settings** \> **Developer settings** \> **Personal access tokens** \> **Tokens (classic)**.  
   * Click the **Generate new token** button.  
   * Give your token a name (e.g., ghfeed-app-token).  
   * The token **requires no permissions or scopes**. Just leave all checkboxes unchecked.  
   * Click **Generate token** and copy it. **This is your only chance to copy it, so save it somewhere safe\!**  
3. **Create the .env file**:  
   * In the same directory where you placed ghfeed.py, create a new file named .env.  
   * Add the following line to the file, replacing YOUR\_GITHUB\_TOKEN with the token you just created:

GITHUB\_TOKEN="YOUR\_GITHUB\_TOKEN"

## **How to Run**

Once everything is set up, open a terminal in the project directory and run the Python script:

python ghfeed.py

The application window should pop up and automatically begin fetching user statuses.

## **Settings**

Click the **"Settings"** button at the bottom of the window to open a new dialog where you can change the app's settings.

* **Theme**: Switches the application's color scheme between a 'dark' and a 'light' theme.  
* **Users to fetch**: Adjust the number of users whose statuses the application will attempt to retrieve. A higher number may result in a longer fetch time.  
* **Font Size**: Increases or decreases the size of the text within the feed.

When you're done, click **"Save"** to apply your changes. Your preferences will be saved in ghfeed\_settings.txt so they'll be there the next time you run the app.

## **Troubleshooting**

* **"Configuration Error"**: This means the app can't find or read your GitHub token. Make sure you have a .env file in the correct directory and that your GITHUB\_TOKEN is entered exactly as copied, including the quotation marks.  
* **"Network Error"**: This typically points to a problem with your internet connection. Confirm that you are online and that the GitHub API is accessible. This could also be caused by a firewall or proxy issue.  
* **"Application Error"**: For unexpected issues, check the ghfeed.log file in the application's directory. This log file contains detailed information about what went wrong and can help you diagnose the problem.  
* **No statuses are appearing**: This could be due to a bug in the code, or there might simply be no users with a public status in the fetched list. Try increasing the "Users to fetch" setting.

## **License**

This project is licensed under the MIT License. You are free to use, modify, and distribute this software for personal and commercial use.

MIT License

Copyright (c) 2024 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy  
of this software and associated documentation files (the "Software"), to deal  
in the Software without restriction, including without limitation the rights  
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell  
copies of the Software, and to permit persons to whom the Software is  
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all  
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,  
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE  
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER  
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,  
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE  
SOFTWARE.

